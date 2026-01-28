# P&L Model Coding Spec for Agent

本文档旨在为 Vibe Coding Agent 提供开发 **P&L（损益）预估模型** 的详细规范。

## 1. 项目目标 (Project Goal)

构建一个基于**天级数据**的 P&L 预估仿真工具。用户通过手动输入预算策略和业务参数，模型计算并输出未来的 DAU、收入、成本及 P&L 趋势。

**核心特性**:
- 支持 **自然量（Organic）** 和 **付费量（Paid）** 的分离建模
- 所有参数支持 **按月份和地区** 维度设定，允许不同时期和地区使用不同值
- 提供合理的 **缺省值**，降低使用门槛

## 2. 核心概念 (Core Concepts)

### 2.1 自然量 vs 付费量

| 类型 | 定义 | 驱动因素 |
|:---|:---|:---|
| **自然量 (Organic DNU)** | 无付费营销投入的自然增长用户 | 与当前地区的活跃用户数（DAU）正相关 |
| **付费量 (Paid DNU)** | 通过营销预算买量获得的新增用户 | 与投放预算正相关（Budget / CPI） |

**总 DNU**:
$$
DNU_{total} = DNU_{organic} + DNU_{paid}
$$

### 2.2 参数的时空维度

所有业务参数支持以下配置方式：
1. **全局缺省值**: 适用于所有月份和地区的默认值
2. **按月份覆盖**: 为特定月份设定值（适用于所有地区）
3. **按地区覆盖**: 为特定地区设定值（适用于所有月份）
4. **按月份+地区覆盖**: 为特定月份和地区的组合设定值（优先级最高）

**参数查询优先级**: 月份+地区 > 地区 > 月份 > 全局缺省值

## 3. 用户输入参数 (User Inputs)

### 3.1 决策变量 (Decision Variables)

用户用来模拟不同增长策略的变量：

| 参数 | 类型 | 说明 | 缺省值 |
|:---|:---|:---|:---|
| `base_budget_ratio` | float | 基准预算比例。每日投放预算占前一日税后总收入的比例 | 100% |
| `additional_budget` | Dict[month, float] | 额外投放预算（按月）。在基准预算基础上增加的固定金额 | 0 |
| `region_distribution` | Dict[region, float] | 各地区预算分配比例（需加和为 100%） | 均分 |

**税后收入计算**:
$$
Revenue_{after\_tax} = (IAP_{revenue} \times 0.7) + (Ad_{revenue} \times 1.0)
$$

### 3.2 地区枚举 (Region Enum)

模型支持以下地区：
- `JP` (日本)
- `US` (美国)
- `EMEA` (英语T1 + 西欧)
- `LATAM` (拉美)
- `CN` (港澳台)
- `OTHER` (其他)

### 3.3 业务参数 (Business Parameters)

以下参数均支持 **按月份和地区** 设定，格式为嵌套字典或配置对象。

#### 3.3.1 基础参数

| 参数 | 类型 | 说明 | 缺省值示例 |
|:---|:---|:---|:---|
| `cpi` | float | 静态 CPI（每获取一个付费用户的成本） | 2.0 USD |
| `arpu_iap` | float | 单用户日均内购收入 | 0.01 USD |
| `arpu_ad` | float | 单用户日均广告收入 | 0.005 USD |
| `unit_cost_api` | float | 单用户日均 API 成本 | 0.006 USD |
| `unit_cost_machine` | float | 单用户日均机器成本 | 0.00001 USD |

#### 3.3.2 留存率关键点输入

用户只需提供 **7 个关键留存率节点**，模型会自动拟合出完整的留存率曲线。

**输入参数**

| 参数 | 类型 | 说明 | 缺省值示例 |
|:---|:---|:---|:---|
| `retention_day1` | TimeRegionParam | 次日留存率（Day 1 Retention） | 0.50 (50%) |
| `retention_day2` | TimeRegionParam | 第3日留存率（Day 2 Retention） | 0.40 |
| `retention_day3` | TimeRegionParam | 第4日留存率（Day 3 Retention） | 0.35 |
| `retention_day7` | TimeRegionParam | 第7日留存率（Day 7 Retention） | 0.28 |
| `retention_day14` | TimeRegionParam | 第14日留存率（Day 14 Retention） | 0.22 |
| `retention_day30` | TimeRegionParam | 第30日留存率（Day 30 Retention） | 0.16 |
| `retention_day60` | TimeRegionParam | 第60日留存率（Day 60 Retention） | 0.10 |

> **重要说明**:
> - 这些参数均为 `TimeRegionParam` 类型，支持**按月份和地区**设定（月份 × 地区的全组合）
> - 缺省值可从历史数据中统计得出
> - 不同月份和地区可以使用不同的留存率曲线

**拟合逻辑**

模型内部会根据这7个关键点，使用分段拟合方法生成完整的留存率曲线：

**1. Day 1 ~ Day 30（早期留存）**

使用 **幂函数拟合**:
$$
R_{new}(d) = \alpha \times d^{\beta}, \quad d \in [1, 30]
$$

通过已知的关键点（Day 1, 2, 3, 7, 14, 30）进行最小二乘拟合，求解最优的 $\alpha$ 和 $\beta$ 参数。

**示例拟合过程**:
```

import numpy as np

from scipy.optimize import curve_fit

# 关键留存点

days = [1, 2, 3, 7, 14, 30]

retentions = [0.50, 0.40, 0.35, 0.28, 0.22, 0.16]

# 拟合函数
def power_func(d, alpha, beta):
    return alpha * (d ** beta)

# 最小二乘拟合

(alpha, beta), _ = curve_fit(power_func, days, retentions)

print(f"拟合结果: alpha={alpha:.3f}, beta={beta:.3f}")

# 输出示例: alpha=0.502, beta=-0.301

# 生成 Day 1-30 的完整留存率曲线
retention_curve_1_30 = [alpha * (d ** beta) for d in range(1, 31)]

```

**2. Day 31 ~ Day 60（长期留存）**

使用 **指数衰减拟合**:
$$
R_{long}(d) = R_{30} \times \gamma^{(d - 30)}, \quad d \in [31, 60]
$$

通过 Day 30 和 Day 60 的留存率，计算日衰减率 $\gamma$:
$$
\gamma = \left(\frac{R_{60}}{R_{30}}\right)^{\frac{1}{30}}
$$

**示例计算**:
```

R_30 = 0.16

R_60 = 0.10

# 计算日衰减率
gamma = (R_60 / R_30) ** (1 / 30)

print(f"日衰减率 gamma={gamma:.4f}")  # 输出: gamma=0.9841

# 生成 Day 31-60 的留存率曲线
retention_curve_31_60 = [R_30 * (gamma ** (d - 30)) for d in range(31, 61)]

```

**3. Day 61+ 和存量老用户留存率**

- **新用户 Day 61+**: 继续使用 $\gamma$ 进行指数衰减
	$$
	R_{new}(d) = R_{60} \times \gamma^{(d - 60)}, \quad d > 60
	$$

- **存量老用户**: 从模拟第1天开始按 $\gamma$ 衰减
	$$
	R_{active}(d) = \gamma^d
	$$

**示例**:
```

# 新用户 Day 90 留存率
R_90 = R_60 * (gamma ** (90 - 60))

print(f"Day 90 留存率: {R_90:.3f}")  # ≈ 0.062

# 存量老用户在模拟第30天的活跃率
R_active_30 = gamma ** 30

print(f"存量用户第30天活跃率: {R_active_30:.3f}")  # ≈ 0.628

```

#### 3.3.3 自然量增长系数

| 参数 | 类型 | 说明 | 缺省值 |
|:---|:---|:---|:---|
| `organic_growth_rate` | TimeRegionParam | 自然量增长系数 k。公式: $DNU_{organic} = DAU \times k$ | 0.01 (即 1%) |

**说明**: 
- `organic_growth_rate` 表示当前活跃用户中每天自发带来新用户的比例
- 支持按月份和地区设定（`TimeRegionParam` 类型）
- **缺省值设定策略**: 先根据产品经验设定初始值（如 1%），后续基于历史数据回溯优化
- 该参数已列入**取数需求清单**（见第8节）

#### 3.3.4 全局参数

| 参数 | 类型 | 说明 |
|:---|:---|:---|
| `simulation_days` | int | 预估天数 |
| `global_fixed_cost` | float | 每日固定成本（人力、行政等） |
| `initial_dau` | Dict[region, int] | 各地区初始 DAU（用户手动输入，未输入时使用缺省值） |

> **说明**: `initial_dau` 为用户手动输入的各地区起始活跃用户数。若用户未输入某地区的值，则使用全局缺省值（建议设为 1000）。

## 4. 核心逻辑与算法 (Core Logic)

### 4.1 参数查询函数

```

def get_param(param_name, month, region, config):
    """
    优先级: 月份+地区 > 地区 > 月份 > 全局缺省值
    """
    if (month, region) in config[param_name]:
        return config[param_name][(month, region)]
    elif region in config[param_name]:
        return config[param_name][region]
    elif month in config[param_name]:
        return config[param_name][month]
    else:
        return config[param_name]['default']

```

### 4.2 自然量与付费量计算

对于每个地区，在每一天：

**付费量**:
$$
DNU_{paid} = \frac{Budget_{region}}{CPI_{region,month}}
$$

**自然量**:
$$
DNU_{organic} = DAU_{region,prev} \times k_{region,month}
$$

其中 $k$ 为 `organic_growth_rate`，$DAU_{prev}$ 为前一日的活跃用户数。

**总新增**:
$$
DNU_{total} = DNU_{organic} + DNU_{paid}
$$

### 4.3 留存率计算函数

**新用户留存率**:

```

def fit_retention_params(r1, r2, r3, r7, r14, r30, r60):
    """
    根据7个关键留存点拟合参数
    返回: (alpha, beta, gamma)
    """
    from scipy.optimize import curve_fit
    
    # 1. 拟合 Day 1-30 的幂函数参数
    days_early = [1, 2, 3, 7, 14, 30]
    retentions_early = [r1, r2, r3, r7, r14, r30]
    
    def power_func(d, alpha, beta):
        return alpha * (d ** beta)
    
    (alpha, beta), _ = curve_fit(power_func, days_early, retentions_early)
    
    # 2. 计算 Day 31+ 的指数衰减率
    gamma = (r60 / r30) ** (1 / 30)
    
    return alpha, beta, gamma

def calc_retention_new(day: int, alpha: float, beta: float, gamma: float) -> float:
    """
    计算新用户在注册后第 day 天的留存率
    day: 1 = 次日留存, 2 = 第3日留存, ...
    alpha, beta, gamma: 由 fit_retention_params() 拟合得到
    """
    if day <= 30:
        return alpha * (day ** beta)
    else:
        # Day 31+ 从 Day 30 的值开始衰减
        r_day30 = alpha * (30 ** beta)
        return r_day30 * (gamma ** (day - 30))

```

**存量用户留存率**:

```

def calc_retention_active(day: int, gamma: float) -> float:
    """
    计算初始 DAU 在模拟第 day 天的留存率
    day: 0 = 模拟第1天, 1 = 模拟第2天, ...
    """
    return gamma ** day

```

### 4.4 DAU 滚动预测

$$
DAU_t = DNU_{total,t} + \sum_{i=1}^{60} \left(DNU_{total,t-i} \times R_{new}(i, \alpha, \beta, \gamma)\right) + \left(DAU_{initial} \times R_{active}(t, \gamma)\right)
$$

- $R_{new}(i, \alpha, \beta, \gamma)$: 新用户第 $i$ 天的留存率（由拟合公式计算）
- $R_{active}(t, \gamma)$: 初始存量用户在第 $t$ 天的活跃率（由指数衰减计算）

### 4.5 预算计算

**前一日税后收入**:
$$
Revenue_{after\_tax, t-1} = (Revenue_{IAP,t-1} \times 0.7) + (Revenue_{Ad,t-1} \times 1.0)
$$

**当日总预算**:
$$
Budget_{total,t} = (Revenue_{after\_tax,t-1} \times base\_budget\_ratio) + additional\_budget_t
$$

**各地区预算**:
$$
Budget_{region,t} = Budget_{total,t} \times region\_distribution_{region}
$$

### 4.6 财务指标计算

对于每个地区：

**收入**:
$$
Revenue_{region} = DAU_{region} \times (ARPU_{iap} + ARPU_{ad})
$$

**变动成本**:
$$
Cost_{variable} = Budget_{region} + DAU_{region} \times (unit\_cost_{api} + unit\_cost_{machine})
$$

**毛利**:
$$
Profit_{gross} = Revenue_{region} - Cost_{variable}
$$

**全局净利**:
$$
Profit_{net} = \sum_{regions} Profit_{gross} - global\_fixed\_cost
$$

## 5. 数据结构定义 (Data Structures)

### 5.1 TimeRegionParam (时空参数)

用于存储支持按月份和地区设定的参数：

```

@dataclass
class TimeRegionParam:
    default: float  # 全局缺省值
    by_month: Dict[int, float] = field(default_factory=dict)  # 按月份覆盖
    by_region: Dict[str, float] = field(default_factory=dict)  # 按地区覆盖
    by_month_region: Dict[Tuple[int, str], float] = field(default_factory=dict)  # 按月份+地区覆盖
    
    def get(self, month: int, region: str) -> float:
        # 查询优先级逻辑
        if (month, region) in self.by_month_region:
            return self.by_month_region[(month, region)]
        elif region in self.by_region:
            return self.by_region[region]
        elif month in self.by_month:
            return self.by_month[month]
        else:
            return self.default

```

### 5.2 RegionConfig (地区配置)

```

@dataclass
class RegionConfig:
    name: str  # 地区名称
    initial_dau: int  # 初始 DAU
    
    # 以下参数均为 TimeRegionParam 类型
    cpi: TimeRegionParam
    arpu_iap: TimeRegionParam
    arpu_ad: TimeRegionParam
    unit_cost_api: TimeRegionParam
    unit_cost_machine: TimeRegionParam
    organic_growth_rate: TimeRegionParam
    
    # 留存率关键点（用于拟合）
    retention_day1: TimeRegionParam   # 次日留存
    retention_day2: TimeRegionParam   # 第3日留存
    retention_day3: TimeRegionParam   # 第4日留存
    retention_day7: TimeRegionParam   # 第7日留存
    retention_day14: TimeRegionParam  # 第14日留存
    retention_day30: TimeRegionParam  # 第30日留存
    retention_day60: TimeRegionParam  # 第60日留存

```

### 5.3 SimulationResult (输出结果)

```

@dataclass
class DailyMetrics:
    date: date
    region: str
    dau: int
    dnu_organic: int
    dnu_paid: int
    dnu_total: int
    revenue_iap: float
    revenue_ad: float
    revenue_total: float
    cost_marketing: float
    cost_api: float
    cost_machine: float
    gross_profit: float

@dataclass
class SimulationResult:
    daily_metrics: List[DailyMetrics]  # 天级明细（分地区）
    summary: Dict[str, Any]  # 汇总指标
    # summary 可包含: 累计盈亏, 盈亏平衡天数, 最终DAU等

```

## 6. 伪代码逻辑 (Pseudo-code)

```

def run_simulation(config: SimulationConfig) -> SimulationResult:
    results = []
    state = initialize_state(config)  # 包含各地区 DAU 和历史 DNU 队列
    
    for day in range(config.simulation_days):
        month = get_month(day)
        
        # 1. 计算当日总预算
        prev_revenue_after_tax = calculate_after_tax_revenue(state.prev_day_revenue)
        total_budget = (prev_revenue_after_tax * config.base_budget_ratio) + config.additional_budget.get(month, 0)
        
        # 2. 各地区计算
        day_summary = {'date': day, 'regions': []}
        
        for region in config.regions:
            # A. 预算分配
            reg_budget = total_budget * config.region_distribution[region.name]
            
            # B. 获取当月地区参数
            cpi = region.cpi.get(month, region.name)
            k_organic = region.organic_growth_rate.get(month, region.name)
            arpu_iap = region.arpu_iap.get(month, region.name)
            arpu_ad = region.arpu_ad.get(month, region.name)
            
            # C. 计算 DNU
            dnu_paid = reg_budget / cpi
            dnu_organic = state.prev_dau[region.name] * k_organic
            dnu_total = dnu_paid + dnu_organic
            
            # D. 获取留存率关键点并拟合参数
            r1 = region.retention_day1.get(month, region.name)
            r2 = region.retention_day2.get(month, region.name)
            r3 = region.retention_day3.get(month, region.name)
            r7 = region.retention_day7.get(month, region.name)
            r14 = region.retention_day14.get(month, region.name)
            r30 = region.retention_day30.get(month, region.name)
            r60 = region.retention_day60.get(month, region.name)
            
            alpha, beta, gamma = fit_retention_params(r1, r2, r3, r7, r14, r30, r60)
            
            dau = calculate_dau(
                dnu_total, 
                state.dnu_history[region.name],  # 过去60天的DNU
                alpha, beta, gamma,  # 留存率拟合参数
                state.initial_dau[region.name],
                day
            )
            
            # E. 财务计算
            revenue_iap = dau * arpu_iap
            revenue_ad = dau * arpu_ad
            revenue_total = revenue_iap + revenue_ad
            cost_marketing = reg_budget
            cost_api = dau * region.unit_cost_api.get(month, region.name)
            cost_machine = dau * region.unit_cost_machine.get(month, region.name)
            gross_profit = revenue_total - (cost_marketing + cost_api + cost_machine)
            
            # F. 记录指标
            metrics = DailyMetrics(
                date=day, region=region.name,
                dau=dau, dnu_organic=dnu_organic, dnu_paid=dnu_paid, dnu_total=dnu_total,
                revenue_iap=revenue_iap, revenue_ad=revenue_ad, revenue_total=revenue_total,
                cost_marketing=cost_marketing, cost_api=cost_api, cost_machine=cost_machine,
                gross_profit=gross_profit
            )
            results.append(metrics)
            
            # G. 更新状态
            state.prev_dau[region.name] = dau
            state.dnu_history[region.name].append(dnu_total)
        
        # 3. 全局净利（扣除固定成本）
        total_gross_profit = sum(m.gross_profit for m in results if m.date == day)
        net_profit = total_gross_profit - config.global_fixed_cost
    
    return SimulationResult(daily_metrics=results, summary=calculate_summary(results))

```

## 7. 输入验证与校验规则 (Validation Rules)

模型在运行前需进行以下输入校验：

### 7.1 预算分配校验

```

def validate_region_distribution(region_distribution: Dict[str, float]) -> bool:
    """
    校验各地区预算分配比例之和是否为 100%
    """
    total = sum(region_distribution.values())
    if not (0.999 <= total <= 1.001):  # 允许浮点误差
        raise ValueError(f"地区预算分配比例之和必须为 100%，当前为 {total*100:.2f}%")
    return True

```

### 7.2 参数有效性校验

- **CPI**: 必须 > 0
- **ARPU**: 必须 >= 0
- **留存率**: 必须在 [0, 1] 区间内
- **增长系数**: 必须 >= 0
- **初始 DAU**: 必须 >= 0（整数）

### 7.3 缺省值回退机制

- 所有 `TimeRegionParam` 类型参数必须提供 `default` 值
- 用户未输入 `initial_dau` 时，各地区默认使用 1000
- 用户未输入 `region_distribution` 时，各地区均分预算

## 8. 数据需求清单 (Data Requirements)

为优化模型参数，后续需要从历史数据中提取以下指标：

| **需求项** | **指标名称** | **维度** | **统计周期** | **优先级** | **备注** |
|:---|:---|:---|:---|:---|:---|
| **留存率关键点** | 次日留存率 (Day 1)<br>2日留存率 (Day 2)<br>3日留存率 (Day 3)<br>7日留存率 (Day 7)<br>14日留存率 (Day 14)<br>30日留存率 (Day 30)<br>60日留存率 (Day 60) | 地区 × 月份 | 近90天的用户 cohort 的留存表现 | P0 | 用于拟合留存率曲线；需要较长周期才能计算 Day 60 |
| **自然量增长系数** | organic_growth_rate<br>(自然新增 / 前日DAU) | 地区 | 近30天的日均值<br>(仅统计无投放期间) | P1 | 先用经验值 0.01，后续优化 |
| **ARPU (IAP)** | 单用户日均内购收入 | 地区 × 月份 | 近7天的日均值 | P0 | 税前收入 |
| **ARPU (Ad)** | 单用户日均广告收入 | 地区 × 月份 | 近7天的日均值 | P0 | 税前收入 |
| **CPI** | 单个付费用户获取成本 | 地区 × 月份 | 近7天的日均值 | P0 | 从投放平台获取 |
| **单位 API 成本** | 单用户日均 API 成本 | 全局 | 近7天的日均值 | P2 | 从成本核算系统获取 |
| **单位机器成本** | 单用户日均机器成本 | 全局 | 近7天的日均值 | P2 | 从成本核算系统获取 |

**说明**:
- **地区枚举**: JP, US, EMEA, LATAM, CN, OTHER
- **月份**: 1-12 月
- **优先级**: P0 (高) > P1 (中) > P2 (低)

---

<!-- 
═══════════════════════════════════════════════════════════════════════════
以下内容为 Python 后端实现规范和 Web 工具开发规范
核心模型开发时可参考第 9 节的 API 设计
═══════════════════════════════════════════════════════════════════════════
-->

## 9. Python 后端实现规范

本章节定义 Python 后端的项目结构、API 接口规范和数据格式。

### 9.1 项目结构

```
pl_model/
├── src/
│   ├── __init__.py
│   ├── models/                    # 数据模型（Pydantic）
│   │   ├── __init__.py
│   │   ├── config.py              # 输入配置类
│   │   ├── results.py             # 输出结果类
│   │   └── params.py              # 时空参数类
│   ├── core/                      # 核心计算引擎
│   │   ├── __init__.py
│   │   ├── retention.py           # 留存率拟合
│   │   ├── dau.py                 # DAU 计算
│   │   └── simulator.py           # 主模拟器
│   ├── api/                       # FastAPI 接口
│   │   ├── __init__.py
│   │   └── routes.py
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       └── validation.py
├── tests/                         # 测试
│   ├── test_retention.py
│   ├── test_simulator.py
│   └── test_api.py
├── examples/                      # 示例
│   ├── basic_example.py
│   └── sample_config.json
├── requirements.txt
└── README.md
```

### 9.2 依赖管理

**requirements.txt**:
```
# 核心计算
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0

# 数据验证
pydantic>=2.0.0

# API 框架
fastapi>=0.104.0
uvicorn>=0.24.0

# 工具
python-dotenv>=1.0.0

# 开发
pytest>=7.4.0
black>=23.0.0
```

### 9.3 API 输入格式（SimulationConfig）

采用"全局默认值 + 地区覆盖 + 月份覆盖"的三层结构，简化配置输入：

```json
{
  "simulation_days": 180,
  "start_date": "2025-02-01",
  
  "budget": {
    "base_ratio": 1.0,
    "additional_by_month": {
      "1": 5000,
      "2": 3000
    },
    "region_distribution": {
      "JP": 0.4,
      "US": 0.3,
      "EMEA": 0.2,
      "OTHER": 0.1
    }
  },
  
  "defaults": {
    "initial_dau": 1000,
    "cpi": 2.0,
    "arpu_iap": 0.01,
    "arpu_ad": 0.005,
    "unit_cost_api": 0.006,
    "unit_cost_machine": 0.00001,
    "organic_growth_rate": 0.01,
    "retention": {
      "day1": 0.50,
      "day2": 0.40,
      "day3": 0.35,
      "day7": 0.28,
      "day14": 0.22,
      "day30": 0.16,
      "day60": 0.10
    }
  },
  
  "regions": {
    "JP": {
      "initial_dau": 5000,
      "cpi": 3.5,
      "retention": {
        "day1": 0.55,
        "day7": 0.30
      }
    },
    "US": {
      "initial_dau": 3000,
      "cpi": 2.8
    },
    "EMEA": {
      "initial_dau": 2000
    }
  },
  
  "monthly_overrides": {
    "2025-01": {
      "JP": {
        "cpi": 4.0
      }
    },
    "2025-12": {
      "US": {
        "cpi": 2.5
      }
    }
  },
  
  "global_fixed_cost": 1000.0,
  
  "output_options": {
    "include_daily_details": true,
    "include_region_breakdown": true,
    "aggregate_by": "day"
  }
}
```

**字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|:---|:---|:---|:---|
| `simulation_days` | int | 是 | 模拟天数（1-730） |
| `start_date` | string | 否 | 模拟开始日期，用于确定月份（默认当天） |
| `budget` | object | 是 | 预算策略配置 |
| `defaults` | object | 是 | 全局默认参数 |
| `regions` | object | 否 | 地区级参数覆盖（未指定的地区使用 defaults） |
| `monthly_overrides` | object | 否 | 月份级参数覆盖（优先级最高） |
| `global_fixed_cost` | float | 是 | 每日固定成本 |
| `output_options` | object | 否 | 输出选项 |

**参数继承优先级**: `monthly_overrides` > `regions` > `defaults`

### 9.4 API 输出格式（SimulationResult）

```json
{
  "status": "success",
  "execution_time_ms": 234,
  "config_hash": "abc123",
  
  "summary": {
    "simulation_days": 180,
    "active_regions": ["JP", "US", "EMEA", "OTHER"],
    
    "final_metrics": {
      "total_dau": 125000,
      "dau_by_region": {
        "JP": 50000,
        "US": 40000,
        "EMEA": 25000,
        "OTHER": 10000
      },
      "dau_growth_rate": 24.0
    },
    
    "cumulative_metrics": {
      "total_revenue": 2450000.0,
      "revenue_iap": 1800000.0,
      "revenue_ad": 650000.0,
      "total_cost": 2100000.0,
      "cost_marketing": 1500000.0,
      "cost_api": 500000.0,
      "cost_machine": 50000.0,
      "cost_fixed": 180000.0,
      "net_profit": 350000.0,
      "roi": 0.167
    },
    
    "milestones": {
      "break_even_day": 156,
      "first_profitable_day": 89,
      "peak_dau_day": 180,
      "peak_dau_value": 125000
    }
  },
  
  "timeseries": {
    "dates": ["2025-02-01", "2025-02-02", "..."],
    "days": [1, 2, 3, "..."],
    
    "totals": {
      "dau": [8000, 8500, 9100, "..."],
      "dnu_organic": [80, 85, 91, "..."],
      "dnu_paid": [1000, 1050, 1100, "..."],
      "revenue": [120, 128, 137, "..."],
      "cost": [2500, 2600, 2700, "..."],
      "profit": [-2380, -2472, -2563, "..."],
      "cumulative_profit": [-2380, -4852, -7415, "..."]
    },
    
    "by_region": {
      "JP": {
        "dau": [5000, 5300, 5650, "..."],
        "dnu_organic": [50, 53, 57, "..."],
        "dnu_paid": [400, 420, 440, "..."],
        "revenue": [75, 80, 85, "..."],
        "cost": [1000, 1050, 1100, "..."],
        "profit": [-925, -970, -1015, "..."]
      },
      "US": { "..." : "..." },
      "EMEA": { "..." : "..." },
      "OTHER": { "..." : "..." }
    }
  },
  
  "retention_curves": {
    "JP": {
      "alpha": 0.552,
      "beta": -0.285,
      "gamma": 0.9841,
      "fitted_values": {
        "day1": 0.55,
        "day7": 0.30,
        "day30": 0.18,
        "day60": 0.12
      }
    },
    "US": { "..." : "..." }
  }
}
```

**输出字段说明**:

| 字段 | 说明 |
|:---|:---|
| `summary.final_metrics` | 模拟结束时的指标快照 |
| `summary.cumulative_metrics` | 整个模拟周期的累计值 |
| `summary.milestones` | 关键里程碑（盈亏平衡日等） |
| `timeseries.totals` | 全局汇总的时序数据（用于绑图） |
| `timeseries.by_region` | 分地区的时序数据（用于地区对比） |
| `retention_curves` | 各地区的留存率拟合参数（用于展示拟合曲线） |

### 9.5 API 接口定义

#### 9.5.1 模拟计算

**POST /api/simulate**

| 参数 | 位置 | 类型 | 说明 |
|:---|:---|:---|:---|
| config | body | SimulationConfig | 完整配置 |

**响应**: SimulationResult

**示例请求**:
```bash
curl -X POST http://localhost:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d @config.json
```

#### 9.5.2 参数校验

**POST /api/validate**

仅校验配置有效性，不执行计算。

**响应**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["留存率 Day 60 低于 5%，可能导致长期 DAU 快速下降"]
}
```

#### 9.5.3 导出数据

**POST /api/export**

| 参数 | 位置 | 类型 | 说明 |
|:---|:---|:---|:---|
| config | body | SimulationConfig | 完整配置 |
| format | query | string | 导出格式：`csv` / `xlsx` / `json` |

**响应**: 文件下载

### 9.6 Pydantic 模型定义

```python
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from datetime import date

class RetentionConfig(BaseModel):
    day1: float = Field(ge=0, le=1, description="次日留存率")
    day2: float = Field(ge=0, le=1, description="2日留存率")
    day3: float = Field(ge=0, le=1, description="3日留存率")
    day7: float = Field(ge=0, le=1, description="7日留存率")
    day14: float = Field(ge=0, le=1, description="14日留存率")
    day30: float = Field(ge=0, le=1, description="30日留存率")
    day60: float = Field(ge=0, le=1, description="60日留存率")
    
    @field_validator('*')
    @classmethod
    def check_decreasing(cls, v, info):
        # 校验留存率递减（可选）
        return v

class BudgetConfig(BaseModel):
    base_ratio: float = Field(ge=0, description="基准预算比例")
    additional_by_month: Dict[str, float] = Field(default_factory=dict)
    region_distribution: Dict[str, float]
    
    @field_validator('region_distribution')
    @classmethod
    def validate_distribution(cls, v):
        total = sum(v.values())
        if not (0.999 <= total <= 1.001):
            raise ValueError(f"地区分配比例之和必须为100%，当前为{total*100:.2f}%")
        return v

class DefaultParams(BaseModel):
    initial_dau: int = Field(ge=0, default=1000)
    cpi: float = Field(gt=0, default=2.0)
    arpu_iap: float = Field(ge=0, default=0.01)
    arpu_ad: float = Field(ge=0, default=0.005)
    unit_cost_api: float = Field(ge=0, default=0.006)
    unit_cost_machine: float = Field(ge=0, default=0.00001)
    organic_growth_rate: float = Field(ge=0, le=1, default=0.01)
    retention: RetentionConfig

class RegionOverride(BaseModel):
    initial_dau: Optional[int] = None
    cpi: Optional[float] = None
    arpu_iap: Optional[float] = None
    arpu_ad: Optional[float] = None
    organic_growth_rate: Optional[float] = None
    retention: Optional[Dict[str, float]] = None  # 部分覆盖

class OutputOptions(BaseModel):
    include_daily_details: bool = True
    include_region_breakdown: bool = True
    aggregate_by: str = Field(default="day", pattern="^(day|week|month)$")

class SimulationConfig(BaseModel):
    simulation_days: int = Field(ge=1, le=730)
    start_date: Optional[date] = None
    budget: BudgetConfig
    defaults: DefaultParams
    regions: Dict[str, RegionOverride] = Field(default_factory=dict)
    monthly_overrides: Dict[str, Dict[str, RegionOverride]] = Field(default_factory=dict)
    global_fixed_cost: float = Field(ge=0)
    output_options: OutputOptions = Field(default_factory=OutputOptions)
```

### 9.7 本地运行指南

#### 9.7.1 环境准备

```bash
# 创建项目目录
mkdir pl_model && cd pl_model

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 9.7.2 启动后端服务

```bash
# 开发模式（自动重载）
uvicorn src.api.routes:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn src.api.routes:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 9.7.3 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 运行模拟
curl -X POST http://localhost:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d @examples/sample_config.json

# 导出 CSV
curl -X POST "http://localhost:8000/api/export?format=csv" \
  -H "Content-Type: application/json" \
  -d @examples/sample_config.json \
  -o result.csv
```

---

## 10. Web 前端开发规范

本章节定义 Web 前端的界面设计和交互规范。

### 10.1 技术架构

**架构模式**: 前后端分离，前端调用 Python API

#### 10.1.1 技术栈

| 技术 | 选型 | 说明 |
|:---|:---|:---|
| **框架** | React 18 + TypeScript | 组件化开发 |
| **构建工具** | Vite | 快速开发体验 |
| **UI 组件** | Ant Design 5.x | 企业级组件库 |
| **图表库** | ECharts 5.x | 功能强大，支持复杂图表 |
| **状态管理** | Zustand | 轻量级状态管理 |
| **HTTP 客户端** | Axios | API 调用 |
| **样式** | Tailwind CSS | 原子化 CSS |

#### 10.1.2 前端项目结构

```
frontend/
├── src/
│   ├── components/           # UI 组件
│   │   ├── ConfigPanel/      # 参数配置面板
│   │   │   ├── BasicSettings.tsx
│   │   │   ├── BudgetSettings.tsx
│   │   │   ├── RegionSettings.tsx
│   │   │   ├── RetentionSettings.tsx
│   │   │   └── CostSettings.tsx
│   │   ├── ResultPanel/      # 结果展示面板
│   │   │   ├── MetricCards.tsx
│   │   │   ├── DAUChart.tsx
│   │   │   ├── PLChart.tsx
│   │   │   ├── RegionPieChart.tsx
│   │   │   └── DataTable.tsx
│   │   └── common/           # 通用组件
│   │       ├── Header.tsx
│   │       └── Loading.tsx
│   ├── hooks/                # 自定义 Hooks
│   │   ├── useSimulation.ts
│   │   └── useConfig.ts
│   ├── services/             # API 服务
│   │   └── api.ts
│   ├── store/                # 状态管理
│   │   └── configStore.ts
│   ├── types/                # TypeScript 类型
│   │   └── index.ts
│   ├── utils/                # 工具函数
│   │   └── format.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

### 10.2 输入界面设计

#### 10.2.1 整体布局

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Header: P&L 模拟器                           [保存场景] [加载场景] [导出]  │
├─────────────────────────┬───────────────────────────────────────────────────┤
│                         │                                                   │
│   📋 参数配置           │   📊 模拟结果                                     │
│   (左侧面板 320px)      │   (右侧主内容区)                                  │
│                         │                                                   │
│   ┌───────────────────┐ │   ┌─────────────────────────────────────────────┐ │
│   │ 📊 基础设置    ▼ │ │   │  关键指标卡片                               │ │
│   │  模拟天数: 180    │ │   │  ┌───────┬───────┬───────┬───────┐         │ │
│   │  开始日期: 02-01  │ │   │  │ DAU   │ 收入  │ 成本  │ 利润  │         │ │
│   └───────────────────┘ │   │  │125,000│$2.45M │$2.10M │$350K  │         │ │
│                         │   │  └───────┴───────┴───────┴───────┘         │ │
│   ┌───────────────────┐ │   └─────────────────────────────────────────────┘ │
│   │ 💰 预算策略    ▼ │ │                                                   │
│   │  基准比例: 100%   │ │   [Tab] 📈趋势图 | 🗂️明细表 | 🌍地区对比        │
│   │  额外预算: +$5000 │ │   ┌─────────────────────────────────────────────┐ │
│   │  地区分配:        │ │   │                                             │ │
│   │    JP: 40%        │ │   │           DAU & DNU 趋势图                  │ │
│   │    US: 30%        │ │   │                                             │ │
│   │    EMEA: 20%      │ │   │    /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾                │ │
│   │    OTHER: 10%     │ │   │   /                                         │ │
│   └───────────────────┘ │   │  /                                          │ │
│                         │   │ /___________________________________        │ │
│   ┌───────────────────┐ │   │  Day 1    Day 60    Day 120   Day 180      │ │
│   │ 🌍 地区参数    ▼ │ │   │                                             │ │
│   │  [JP ▼]           │ │   └─────────────────────────────────────────────┘ │
│   │  初始DAU: 5000    │ │                                                   │
│   │  CPI: $3.5        │ │   ┌─────────────────────────────────────────────┐ │
│   │  ARPU(IAP): $0.01 │ │   │                                             │ │
│   │  ARPU(Ad): $0.005 │ │   │           P&L 累计曲线                      │ │
│   │  自然增长: 1%     │ │   │                      ___________            │ │
│   └───────────────────┘ │   │                     /                       │ │
│                         │   │  ═══════════════════╳═══════════════        │ │
│   ┌───────────────────┐ │   │                   Day 156 (盈亏平衡)        │ │
│   │ 📈 留存率      ▼ │ │   │                                             │ │
│   │  [JP ▼]           │ │   └─────────────────────────────────────────────┘ │
│   │  Day1: 55%        │ │                                                   │
│   │  Day7: 30%        │ │                                                   │
│   │  Day30: 18%       │ │                                                   │
│   │  [预览曲线]       │ │                                                   │
│   └───────────────────┘ │                                                   │
│                         │                                                   │
│   ┌───────────────────┐ │                                                   │
│   │ 💵 成本参数    ▼ │ │                                                   │
│   │  API: $0.006      │ │                                                   │
│   │  机器: $0.00001   │ │                                                   │
│   │  固定: $1000/天   │ │                                                   │
│   └───────────────────┘ │                                                   │
│                         │                                                   │
│   ┌───────────────────┐ │                                                   │
│   │  [▶ 运行模拟]     │ │                                                   │
│   │  [↺ 重置参数]     │ │                                                   │
│   └───────────────────┘ │                                                   │
│                         │                                                   │
└─────────────────────────┴───────────────────────────────────────────────────┘
```

#### 10.2.2 输入表单组件详细设计

**1. 基础设置面板**

```
┌─────────────────────────────────────────────────────────┐
│ 📊 基础设置                                      [▼/▲] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  模拟天数                                               │
│  ┌────────────────────────────────────────────┐        │
│  │ 180                                    [天] │        │
│  └────────────────────────────────────────────┘        │
│  💡 建议范围: 30-365 天                                 │
│                                                         │
│  开始日期                                               │
│  ┌────────────────────────────────────────────┐        │
│  │ 📅 2025-02-01                              │        │
│  └────────────────────────────────────────────┘        │
│                                                         │
│  快速模板                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ 保守增长 │ │ 激进买量 │ │ 精细运营 │               │
│  └──────────┘ └──────────┘ └──────────┘               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**2. 预算策略面板**

```
┌─────────────────────────────────────────────────────────┐
│ 💰 预算策略                                      [▼/▲] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  基准预算比例（占前日税后收入）                         │
│  ┌────────────────────────────────────────────┐        │
│  │ 100                                    [%] │        │
│  └────────────────────────────────────────────┘        │
│  ├────────────●────────────────────────────┤ 0-200%    │
│                                                         │
│  额外投放预算（按月）                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  月份    │  金额 (USD)         │  操作         │   │
│  │──────────┼─────────────────────┼───────────────│   │
│  │  1月     │  5,000              │  [✕ 删除]     │   │
│  │  2月     │  3,000              │  [✕ 删除]     │   │
│  └─────────────────────────────────────────────────┘   │
│  [+ 添加月份]                                           │
│                                                         │
│  地区预算分配                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  JP     ├████████████████──────────┤ 40%       │   │
│  │  US     ├████████████──────────────┤ 30%       │   │
│  │  EMEA   ├████████──────────────────┤ 20%       │   │
│  │  OTHER  ├████──────────────────────┤ 10%       │   │
│  └─────────────────────────────────────────────────┘   │
│  合计: 100% ✓                                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**3. 地区参数面板**

```
┌─────────────────────────────────────────────────────────┐
│ 🌍 地区参数配置                                  [▼/▲] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  选择地区:  [JP ▼] [US] [EMEA] [OTHER] [默认值]        │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  📍 JP (日本) 配置                                │ │
│  │                                                   │ │
│  │  初始 DAU                                         │ │
│  │  ┌─────────────────────────────────────┐         │ │
│  │  │ 5,000                               │         │ │
│  │  └─────────────────────────────────────┘         │ │
│  │                                                   │ │
│  │  CPI (用户获取成本)                               │ │
│  │  ┌─────────────────────────────────────┐         │ │
│  │  │ 3.5                             [$] │         │ │
│  │  └─────────────────────────────────────┘         │ │
│  │  ☑ 启用月份覆盖  [设置...]                        │ │
│  │                                                   │ │
│  │  ARPU (IAP)           ARPU (Ad)                  │ │
│  │  ┌───────────────┐    ┌───────────────┐          │ │
│  │  │ 0.01      [$] │    │ 0.005     [$] │          │ │
│  │  └───────────────┘    └───────────────┘          │ │
│  │                                                   │ │
│  │  自然量增长系数                                   │ │
│  │  ┌─────────────────────────────────────┐         │ │
│  │  │ 1.0                             [%] │         │ │
│  │  └─────────────────────────────────────┘         │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  [复制到其他地区 ▼]   [重置为默认值]                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**4. 留存率配置面板**

```
┌─────────────────────────────────────────────────────────┐
│ 📈 留存率配置                                    [▼/▲] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  选择地区:  [JP ▼] [US] [EMEA] [OTHER] [默认值]        │
│                                                         │
│  关键留存率节点                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Day 1  │ ████████████████████████████░░░░ │ 55%  │ │
│  │  Day 2  │ ██████████████████████████░░░░░░ │ 45%  │ │
│  │  Day 3  │ ████████████████████████░░░░░░░░ │ 38%  │ │
│  │  Day 7  │ ████████████████████░░░░░░░░░░░░ │ 30%  │ │
│  │  Day 14 │ ████████████████░░░░░░░░░░░░░░░░ │ 24%  │ │
│  │  Day 30 │ ████████████░░░░░░░░░░░░░░░░░░░░ │ 18%  │ │
│  │  Day 60 │ ████████░░░░░░░░░░░░░░░░░░░░░░░░ │ 12%  │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  [📊 预览拟合曲线]                                      │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │   100% ┤                                          │ │
│  │        │ ●                                        │ │
│  │    50% ┤   ●                                      │ │
│  │        │     ●──●                                 │ │
│  │    25% ┤          ●───●                           │ │
│  │        │                ●─────●─────●────         │ │
│  │     0% ┼────┼────┼────┼────┼────┼────┼────       │ │
│  │        1    7   14   30   60   90  120  180      │ │
│  │                                                   │ │
│  │  拟合参数: α=0.552, β=-0.285, γ=0.9841           │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**5. 成本参数面板**

```
┌─────────────────────────────────────────────────────────┐
│ 💵 成本参数                                      [▼/▲] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  单位 API 成本（每 DAU 每天）                           │
│  ┌────────────────────────────────────────────┐        │
│  │ 0.006                                  [$] │        │
│  └────────────────────────────────────────────┘        │
│                                                         │
│  单位机器成本（每 DAU 每天）                            │
│  ┌────────────────────────────────────────────┐        │
│  │ 0.00001                                [$] │        │
│  └────────────────────────────────────────────┘        │
│                                                         │
│  每日固定成本（人力、行政等）                           │
│  ┌────────────────────────────────────────────┐        │
│  │ 1,000                                  [$] │        │
│  └────────────────────────────────────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 10.3 输出界面设计

#### 10.3.1 关键指标卡片

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              关键指标概览                                   │
├──────────────────┬──────────────────┬──────────────────┬──────────────────┤
│                  │                  │                  │                  │
│   📊 最终 DAU    │   💰 累计收入    │   💸 累计成本    │   📈 净利润     │
│                  │                  │                  │                  │
│    125,000       │   $2,450,000     │   $2,100,000     │   +$350,000     │
│                  │                  │                  │                  │
│   ↑ 2400%        │   IAP: $1.8M     │   营销: $1.5M    │   ROI: 16.7%    │
│   vs 初始 DAU    │   Ad: $0.65M     │   运营: $0.6M    │                  │
│                  │                  │                  │   📅 Day 156    │
│                  │                  │                  │   盈亏平衡      │
│                  │                  │                  │                  │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

#### 10.3.2 趋势图表

**图表 1: DAU & DNU 趋势（双Y轴）**

```
DAU (万)                                                        DNU
    │                                                              │
 12 ┤                                          ___________         ┤ 1500
    │                                    _____/                    │
 10 ┤                              _____/                          ┤ 1250
    │                        _____/                                │
  8 ┤                  _____/                                      ┤ 1000
    │            _____/                                            │
  6 ┤      _____/                                                  ┤ 750
    │ ____/                                                        │
  4 ┤/                                                             ┤ 500
    │    ════════════════════════════════════════════  (DNU 付费)  │
  2 ┤    ────────────────────────────────────────────  (DNU 自然)  │
    │                                                              │
  0 ┼────────┼────────┼────────┼────────┼────────┼────────┼───────┤ 0
         30       60       90      120      150      180    天数

    图例: ▓ DAU   ═══ DNU(付费)   ─── DNU(自然)

    [📍 JP] [📍 US] [📍 EMEA] [📍 OTHER]  （点击切换地区显示）
```

**图表 2: P&L 累计曲线**

```
累计利润 ($)
         │
  +400K  ┤                                        ________●
         │                                   ____/
  +200K  ┤                              ____/
         │                         ____/
      0  ┼═════════════════════════╳══════════════════════════════
         │                    ____/
  -200K  ┤               ____/     ↑ Day 156 盈亏平衡
         │          ____/
  -400K  ┤     ____/
         │____/
  -600K  ┼────────┼────────┼────────┼────────┼────────┼────────┼───
              30       60       90      120      150      180

         ▓▓▓ 亏损区间（红色）    ▓▓▓ 盈利区间（绿色）
```

**图表 3: 收入成本结构（堆叠柱状图，按周聚合）**

```
金额 ($)
         │
  150K   ┤     ████████████████████████████████████████████████████
         │     ████  ████  ████  ████  ████  ████  ████  ████
  100K   ┤     ████  ████  ████  ████  ████  ████  ████  ████
         │     ████  ████  ████  ████  ████  ████  ████  ████
   50K   ┤     ████  ████  ████  ████  ████  ████  ████  ████
         │     ████  ████  ████  ████  ████  ████  ████  ████
      0  ┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────
             W1    W4    W8   W12   W16   W20   W24   W26

         图例: ▓ IAP收入  ▓ 广告收入  ▓ 营销成本  ▓ 运营成本
```

**图表 4: 地区贡献度（饼图）**

```
         DAU 分布                    收入贡献                    成本分布
    
        ┌──────┐                   ┌──────┐                   ┌──────┐
       /   JP   \                 /   JP   \                 /   JP   \
      │   40%    │               │   45%    │               │   42%    │
      │          │               │          │               │          │
       \   US   /                 \   US   /                 \   US   /
        │ 32%  │                  │ 28%  │                   │ 30%  │
        └──────┘                  └──────┘                   └──────┘
      EMEA 20%                   EMEA 18%                   EMEA 20%
      OTHER 8%                   OTHER 9%                   OTHER 8%

    [切换维度: DAU ▼]
```

#### 10.3.3 明细数据表

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📋 明细数据                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  筛选: 地区 [全部 ▼]  日期范围 [Day 1 - Day 180 ▼]    🔍 搜索...           │
│                                                                             │
│  ┌───────┬────────┬────────┬──────────┬──────────┬─────────┬─────────┬─────────┐
│  │ 日期  │ 地区   │  DAU   │ DNU(自然) │ DNU(付费) │  收入   │  成本   │  毛利   │
│  │   ▲   │   ▲    │    ▼   │     ▼     │     ▼     │    ▼    │    ▼    │    ▼    │
│  ├───────┼────────┼────────┼──────────┼──────────┼─────────┼─────────┼─────────┤
│  │ Day 1 │   JP   │  5,000 │       50 │      400 │    $75  │  $1,200 │   -$925 │
│  │ Day 1 │   US   │  3,000 │       30 │      300 │    $45  │    $840 │   -$795 │
│  │ Day 1 │  EMEA  │  2,000 │       20 │      200 │    $30  │    $560 │   -$530 │
│  │ Day 1 │ OTHER  │  1,000 │       10 │      100 │    $15  │    $280 │   -$265 │
│  │ Day 2 │   JP   │  5,300 │       53 │      420 │    $80  │  $1,260 │   -$970 │
│  │  ...  │  ...   │   ...  │      ... │      ... │    ...  │    ...  │    ...  │
│  │Day 180│   JP   │ 50,000 │      500 │    2,000 │   $750  │  $6,000 │ +$5,250 │
│  └───────┴────────┴────────┴──────────┴──────────┴─────────┴─────────┴─────────┘
│                                                                             │
│  显示 1-20 / 共 720 条    [◀ 上一页]  1  2  3  ... 36  [下一页 ▶]          │
│                                                                             │
│  [📥 导出 CSV]  [📥 导出 Excel]  [📥 导出全部 JSON]                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.4 本地运行指南

#### 10.4.1 一键启动脚本

创建 `start.sh` (macOS/Linux) 或 `start.bat` (Windows):

**start.sh**:
```bash
#!/bin/bash

echo "🚀 启动 P&L 模拟器..."

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python 3，请先安装"
    exit 1
fi

# 检查 Node.js 环境
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装"
    exit 1
fi

# 启动后端
echo "📦 启动后端服务..."
cd backend
python3 -m venv venv 2>/dev/null
source venv/bin/activate
pip install -r requirements.txt -q
uvicorn src.api.routes:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "🎨 启动前端服务..."
cd ../frontend
npm install -q
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 服务已启动!"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
```

#### 10.4.2 Docker 一键部署

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=http://localhost:5173,http://localhost:3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
```

**启动命令**:
```bash
docker-compose up -d
```

#### 10.4.3 开发环境要求

| 依赖 | 版本要求 | 安装命令 |
|:---|:---|:---|
| Python | >= 3.10 | `brew install python` (macOS) |
| Node.js | >= 18.0 | `brew install node` (macOS) |
| npm | >= 9.0 | 随 Node.js 安装 |
| Docker (可选) | >= 20.0 | `brew install docker` |

### 10.5 部署方案

#### 10.5.1 本地部署（开发/演示）

```bash
# 克隆项目
git clone https://github.com/your-repo/pl-model.git
cd pl-model

# 启动服务
./start.sh

# 访问
open http://localhost:5173
```

#### 10.5.2 云端部署

**方案 A: Vercel + Railway（推荐）**
- 前端部署到 Vercel（免费）
- 后端部署到 Railway（$5/月起）

**方案 B: 全栈部署到 Render**
- 前后端都部署到 Render
- 免费 tier 有休眠限制

**方案 C: 自托管服务器**
- 使用 Docker Compose
- 配合 Nginx 反向代理
- 需要自有服务器或 VPS

### 10.6 前端与后端通信

#### 10.6.1 API 调用封装

```typescript
// frontend/src/services/api.ts
import axios from 'axios';
import type { SimulationConfig, SimulationResult } from '@/types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function runSimulation(config: SimulationConfig): Promise<SimulationResult> {
  const response = await api.post('/api/simulate', config);
  return response.data;
}

export async function validateConfig(config: SimulationConfig): Promise<{
  valid: boolean;
  errors: string[];
  warnings: string[];
}> {
  const response = await api.post('/api/validate', config);
  return response.data;
}

export async function exportData(
  config: SimulationConfig, 
  format: 'csv' | 'xlsx' | 'json'
): Promise<Blob> {
  const response = await api.post(`/api/export?format=${format}`, config, {
    responseType: 'blob',
  });
  return response.data;
}
```

#### 10.6.2 状态管理

```typescript
// frontend/src/store/configStore.ts
import { create } from 'zustand';
import type { SimulationConfig, SimulationResult } from '@/types';

interface ConfigStore {
  config: SimulationConfig;
  result: SimulationResult | null;
  isLoading: boolean;
  error: string | null;
  
  setConfig: (config: Partial<SimulationConfig>) => void;
  setResult: (result: SimulationResult) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const defaultConfig: SimulationConfig = {
  simulation_days: 180,
  start_date: new Date().toISOString().split('T')[0],
  budget: {
    base_ratio: 1.0,
    additional_by_month: {},
    region_distribution: { JP: 0.4, US: 0.3, EMEA: 0.2, OTHER: 0.1 },
  },
  defaults: {
    initial_dau: 1000,
    cpi: 2.0,
    arpu_iap: 0.01,
    arpu_ad: 0.005,
    unit_cost_api: 0.006,
    unit_cost_machine: 0.00001,
    organic_growth_rate: 0.01,
    retention: {
      day1: 0.5, day2: 0.4, day3: 0.35, day7: 0.28,
      day14: 0.22, day30: 0.16, day60: 0.1,
    },
  },
  regions: {},
  monthly_overrides: {},
  global_fixed_cost: 1000,
};

export const useConfigStore = create<ConfigStore>((set) => ({
  config: defaultConfig,
  result: null,
  isLoading: false,
  error: null,
  
  setConfig: (partial) => set((state) => ({
    config: { ...state.config, ...partial },
  })),
  setResult: (result) => set({ result }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () => set({ config: defaultConfig, result: null, error: null }),
}));
```

---

## 11. 开发优先级与迭代计划

### 11.1 Phase 1: 后端核心 MVP

**目标**: 实现可运行的 Python 计算引擎和 API

**任务清单**:
- [ ] 搭建项目结构
- [ ] 实现 Pydantic 数据模型
- [ ] 实现留存率拟合函数
- [ ] 实现 DAU 计算函数
- [ ] 实现主模拟器
- [ ] 实现 FastAPI 接口
- [ ] 编写单元测试
- [ ] 编写示例配置文件

### 11.2 Phase 2: 前端核心 MVP

**目标**: 实现基础的 Web 界面

**任务清单**:
- [ ] 搭建 React + Vite 项目
- [ ] 实现参数配置面板（基础参数）
- [ ] 实现 API 调用逻辑
- [ ] 实现关键指标卡片
- [ ] 实现 DAU 趋势图
- [ ] 实现 P&L 曲线图
- [ ] 实现基础响应式布局

### 11.3 Phase 3: 功能完善

**目标**: 增强用户体验和功能

**任务清单**:
- [ ] 地区参数配置界面
- [ ] 留存率曲线预览
- [ ] 预设模板功能
- [ ] 参数实时校验
- [ ] 明细数据表
- [ ] 地区对比图
- [ ] CSV/Excel 导出

### 11.4 Phase 4: 高级功能（可选）

**任务清单**:
- [ ] 场景保存/加载（LocalStorage）
- [ ] 场景对比功能
- [ ] PDF 报告导出
- [ ] 敏感性分析
- [ ] 移动端优化
- [ ] Docker 容器化
- [ ] 云端部署

---

**文档版本**: v1.2  
**最后更新**: 2025-01-28  
**核心模型规范**: 第 1-8 节  
**Python 后端规范**: 第 9 节  
**Web 前端规范**: 第 10 节  
**开发计划**: 第 11 节
          type="number"
          value={config.simulation_days}
          onChange={(e) => setConfig({
            ...config,
            simulation_days: parseInt(e.target.value)
          })}
        />
      </label>
      {/* 其他参数输入 */}
      <button onClick={handleSimulate}>运行模拟</button>
    </div>
  );
}
```

### A.2 图表渲染（ECharts）

```typescript
import * as echarts from 'echarts';

function renderDAUChart(dailyMetrics: DailyMetrics[]) {
  const chart = echarts.init(document.getElementById('dau-chart'));
  
  const option = {
    title: { text: 'DAU 趋势' },
    xAxis: {
      type: 'category',
      data: dailyMetrics.map(m => `Day ${m.date}`)
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'DAU',
        type: 'line',
        data: dailyMetrics.map(m => m.dau),
        smooth: true
      }
    ]
  };
  
  chart.setOption(option);
}
```

---

**文档版本**: v1.1  
**最后更新**: 2025-01-28  
**核心模型规范**: 第 1-8 节  
**Web 工具规范**: 第 9-10 节 + 附录