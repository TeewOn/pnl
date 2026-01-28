# 后端代码文件功能说明

本文档详细说明后端每个文件的功能、关键公式和缺省值设定。

---

## 📁 目录结构

```
backend/
├── main.py                    # FastAPI 应用入口
├── requirements.txt           # Python 依赖
│
├── src/
│   ├── models/               # 数据模型层
│   │   ├── config.py         # API 输入配置模型（缺省值定义）
│   │   ├── params.py         # 时空参数类（三层覆盖逻辑）
│   │   └── results.py        # API 输出结果模型
│   │
│   ├── core/                 # 核心计算引擎
│   │   ├── retention.py      # 留存率拟合模块（公式实现）
│   │   ├── dau.py            # DAU 计算模块（公式实现）
│   │   └── simulator.py      # 主模拟器（业务流程）
│   │
│   ├── api/                  # API 接口层
│   │   └── routes.py         # FastAPI 路由定义
│   │
│   └── utils/                # 工具函数
│       └── validation.py    # 参数校验
│
├── tests/                    # 测试用例
└── examples/                 # 示例配置和脚本
```

---

## 📄 文件详细说明

### 1. `main.py` - FastAPI 应用入口

**功能：**
- 创建 FastAPI 应用实例
- 配置 CORS 跨域支持
- 注册 API 路由
- 提供健康检查接口

**关键配置：**
- 端口：8000
- CORS 允许来源：`localhost:5173`, `localhost:3000`

---

### 2. `src/models/config.py` - API 输入配置模型

**功能：**
- 定义 API 输入的数据结构（Pydantic 模型）
- 实现三层参数覆盖逻辑（全局默认值 → 地区覆盖 → 月份覆盖）
- **定义所有缺省值**

#### 关键类和缺省值：

**`RetentionConfig` - 留存率配置**
```python
day1: float = 0.50    # 次日留存率
day2: float = 0.40    # 2日留存率
day3: float = 0.35    # 3日留存率
day7: float = 0.28    # 7日留存率
day14: float = 0.22   # 14日留存率
day30: float = 0.16   # 30日留存率
day60: float = 0.10   # 60日留存率
```

**`BudgetConfig` - 预算策略配置**
```python
base_ratio: float = 1.0  # 基准预算比例（占前日税后收入）
additional_by_month: Dict[str, float] = {}  # 额外投放预算（按月）
region_distribution: Dict[str, float] = {
    "JP": 0.25,      # 日本 25%
    "US": 0.25,      # 美国 25%
    "EMEA": 0.2,     # 英语T1+西欧 20%
    "LATAM": 0.1,    # 拉美 10%
    "CN": 0.1,       # 港澳台 10%
    "OTHER": 0.1,    # 其他 10%
}
```

**`DefaultParams` - 全局默认参数**
```python
initial_dau: int = 1000              # 初始 DAU
cpi: float = 2.0                     # CPI（用户获取成本）
arpu_iap: float = 0.01               # IAP ARPU
arpu_ad: float = 0.005               # 广告 ARPU
unit_cost_api: float = 0.006         # 单位 API 成本
unit_cost_machine: float = 0.00001    # 单位机器成本
organic_growth_rate: float = 0.01    # 自然量增长系数（1%）
retention: RetentionConfig = ...     # 留存率配置（见上）
```

**`SimulationConfig` - 模拟配置主结构**
```python
simulation_days: int = 180           # 模拟天数
start_date: Optional[date] = None     # 模拟开始日期
budget: BudgetConfig = ...           # 预算策略
defaults: DefaultParams = ...         # 全局默认参数
regions: Dict[str, RegionOverride] = {}  # 地区参数覆盖
monthly_overrides: Dict[str, Dict[str, RegionOverride]] = {}  # 月份覆盖
global_fixed_cost: float = 0.0       # 每日额外投放支出（已改名）
output_options: OutputOptions = ...   # 输出选项
```

#### 关键方法：

**`get_initial_dau(region: str) -> int`**
- **功能：** 获取指定地区的初始 DAU
- **逻辑：** 如果没有地区覆盖，按比例分配全局默认值
- **分配比例：**
  - JP: 20%
  - US: 20%
  - EMEA, LATAM, CN, OTHER: 各 15%

**`get_param(param_name: str, month: int, region: str) -> float`**
- **功能：** 获取指定参数值，支持三层覆盖
- **优先级：** 月份+地区 > 地区 > 全局默认值

---

### 3. `src/models/params.py` - 时空参数类

**功能：**
- 实现 `TimeRegionParam` 类，支持按月份和地区的参数覆盖
- 提供 `from_config()` 方法从配置创建参数对象

**注意：** 当前实现中，`TimeRegionParam` 类主要用于概念说明，实际使用中直接通过 `SimulationConfig` 的方法获取参数。

---

### 4. `src/models/results.py` - API 输出结果模型

**功能：**
- 定义 API 输出的数据结构（Pydantic 模型）
- 包含汇总信息、时序数据、留存率曲线等

**关键类：**
- `SimulationResult`: 完整的模拟结果
- `Summary`: 汇总信息（最终指标、累计指标、里程碑）
- `Timeseries`: 时序数据（每日明细）
- `RetentionCurve`: 留存率曲线（拟合参数）

---

### 5. `src/core/retention.py` - 留存率拟合模块 ⭐

**功能：**
- 根据 7 个关键留存点拟合参数
- 计算新用户和存量用户的留存率

#### 核心公式：

**1. 幂函数拟合（Day 1-30）**
```
R(d) = α × d^β
```
- `α` (alpha): 幂函数系数
- `β` (beta): 幂函数指数（通常为负数，表示衰减）
- `d`: 注册后天数

**2. 指数衰减（Day 31+）**
```
R(d) = R₃₀ × γ^(d-30)
```
- `R₃₀`: Day 30 的留存率（由幂函数计算）
- `γ` (gamma): 日衰减率（0.9 < γ < 1）
- `d`: 注册后天数

**3. 存量用户活跃率**
```
R_active(t) = γ^t
```
- `t`: 模拟天数（从 0 开始）
- `γ`: 日衰减率

#### 关键函数：

**`fit_retention_params(r1, r2, r3, r7, r14, r30, r60) -> (alpha, beta, gamma)`**
- **输入：** 7 个关键留存率节点
- **输出：** 拟合参数 (alpha, beta, gamma)
- **算法：**
  1. 使用 `scipy.optimize.curve_fit` 拟合 Day 1-30 的幂函数
  2. 根据 R30 和 R60 计算 gamma: `γ = (R60 / R30)^(1/30)`
  3. 如果拟合失败，使用简单估计作为后备

**`calc_retention_new(day, alpha, beta, gamma) -> float`**
- **功能：** 计算新用户在注册后第 `day` 天的留存率
- **逻辑：**
  - Day 0: 返回 1.0（注册当天）
  - Day 1-30: 使用幂函数 `α × d^β`
  - Day 31+: 使用指数衰减 `R30 × γ^(d-30)`

**`calc_retention_active(day, gamma) -> float`**
- **功能：** 计算初始存量用户在第 `day` 天的活跃率
- **公式：** `γ^day`

---

### 6. `src/core/dau.py` - DAU 计算模块 ⭐

**功能：**
- 实现 DAU 滚动预测公式
- 维护历史 DNU 队列

#### 核心公式：

**DAU 计算公式：**
```
DAU_t = DNU_total,t + Σ(DNU_total,t-i × R_new(i)) + (DAU_initial × R_active(t))
```

**分解：**
1. **今日新增用户：** `DNU_total,t`（第 0 天留存率 = 100%）
2. **历史新增用户贡献：** `Σ(DNU_total,t-i × R_new(i))`
   - `i`: 1 到 `retention_window`（默认 180 天）
   - `DNU_total,t-i`: i 天前的新增用户数
   - `R_new(i)`: 新用户第 i 天的留存率
3. **初始存量用户贡献：** `DAU_initial × R_active(t)`
   - `DAU_initial`: 初始活跃用户数
   - `R_active(t)`: 初始用户在第 t 天的活跃率

#### 关键类：

**`DAUCalculator`**
- **功能：** DAU 计算器，维护状态
- **属性：**
  - `initial_dau`: 初始活跃用户数
  - `dnu_history`: 历史 DNU 队列（deque，最大长度 180）
  - `current_day`: 当前模拟天数
  - `_retention_cache`: 预计算的留存率表（性能优化）

**`calculate_dau(dnu_today, dnu_history, alpha, beta, gamma, initial_dau, current_day) -> int`**
- **功能：** 函数式接口，计算当日 DAU
- **参数：** 所有必要的输入参数
- **返回：** 当日 DAU

---

### 7. `src/core/simulator.py` - 主模拟器 ⭐

**功能：**
- 按天循环执行模拟
- 计算预算、DNU、DAU、财务指标
- 聚合输出结果

#### 业务流程：

**按天循环（Day 0 到 simulation_days-1）：**

1. **预算计算**
   ```
   additional_budget = additional_by_month.get(month, 0)
   total_budget = (prev_revenue_after_tax × base_ratio) + additional_budget
   ```
   - `prev_revenue_after_tax`: 前一日税后收入
   - 税后收入 = IAP收入 × 0.7 + 广告收入 × 1.0

2. **各地区预算分配**
   ```
   region_budget = total_budget × region_distribution[region]
   ```

3. **DNU 计算**
   ```
   dnu_paid = region_budget / cpi
   dnu_organic = prev_dau × organic_growth_rate
   dnu_total = dnu_paid + dnu_organic
   ```

4. **DAU 计算**
   - 使用 `DAUCalculator.calculate_dau(dnu_total)`

5. **财务计算**
   ```
   revenue_iap = dau × arpu_iap
   revenue_ad = dau × arpu_ad
   revenue_total = revenue_iap + revenue_ad
   
   cost_marketing = region_budget
   cost_api = dau × unit_cost_api
   cost_machine = dau × unit_cost_machine
   cost_fixed = global_fixed_cost
   
   gross_profit = revenue_total - (cost_marketing + cost_api + cost_machine + cost_fixed)
   ```

6. **累计指标更新**
   - 累加收入、成本、利润等指标

7. **里程碑检查**
   - 盈亏平衡日：累计利润首次 >= 0
   - 首次盈利日：当日利润首次 > 0
   - DAU 峰值：记录最高 DAU 及其日期

#### 关键类：

**`RegionSimulator`**
- **功能：** 单地区模拟器
- **属性：**
  - `dau_calculator`: DAU 计算器实例
  - `prev_dau`: 前一日 DAU
  - `dnu_history`: 历史 DNU 列表

**`run_simulation(config: SimulationConfig) -> SimulationResult`**
- **功能：** 主入口函数，运行完整模拟
- **返回：** 完整的模拟结果

---

### 8. `src/api/routes.py` - FastAPI 路由

**功能：**
- 定义 API 端点
- 处理请求和响应

**端点：**
- `POST /api/simulate`: 运行模拟
- `POST /api/validate`: 校验配置
- `POST /api/export`: 导出数据（CSV/JSON）
- `GET /api/default-config`: 获取默认配置
- `GET /api/regions`: 获取支持的地区列表

---

### 9. `src/utils/validation.py` - 参数校验

**功能：**
- 校验模拟配置的有效性
- 检查参数范围和逻辑一致性

**校验项：**
- 模拟天数范围（1-730）
- 地区预算分配比例之和是否为 100%
- 留存率单调性检查
- CPI 和 ARPU 合理性检查
- 初始 DAU 检查

---

## 🔍 关键公式总结

### 1. 留存率拟合
- **Day 1-30:** `R(d) = α × d^β`
- **Day 31+:** `R(d) = R₃₀ × γ^(d-30)`
- **存量用户:** `R(t) = γ^t`

### 2. DAU 计算
```
DAU_t = DNU_t + Σ(DNU_t-i × R_new(i)) + (DAU_initial × R_active(t))
```

### 3. 预算计算
```
Budget_t = (Revenue_after_tax,t-1 × base_ratio) + additional_budget
```

### 4. DNU 计算
```
DNU_paid = Budget / CPI
DNU_organic = DAU_prev × organic_growth_rate
DNU_total = DNU_paid + DNU_organic
```

### 5. 财务计算
```
Revenue = DAU × (ARPU_IAP + ARPU_Ad)
Cost = Marketing + (DAU × (Cost_API + Cost_Machine)) + Fixed_Cost
Profit = Revenue - Cost
```

---

## 📊 缺省值总结

| 参数 | 缺省值 | 说明 |
|------|--------|------|
| `simulation_days` | 180 | 模拟天数 |
| `initial_dau` | 1000 | 初始 DAU（全局） |
| `cpi` | 2.0 | 用户获取成本 |
| `arpu_iap` | 0.01 | IAP ARPU |
| `arpu_ad` | 0.005 | 广告 ARPU |
| `unit_cost_api` | 0.006 | 单位 API 成本 |
| `unit_cost_machine` | 0.00001 | 单位机器成本 |
| `organic_growth_rate` | 0.01 | 自然量增长系数（1%） |
| `base_ratio` | 1.0 | 基准预算比例（100%） |
| `global_fixed_cost` | 0.0 | 每日额外投放支出 |
| `retention.day1` | 0.50 | 次日留存率 |
| `retention.day7` | 0.28 | 7日留存率 |
| `retention.day30` | 0.16 | 30日留存率 |
| `retention.day60` | 0.10 | 60日留存率 |

---

## 🧪 测试和示例

- **`tests/`**: 单元测试
  - `test_retention.py`: 留存率拟合测试
  - `test_simulator.py`: 模拟器测试

- **`examples/`**: 示例
  - `sample_config.json`: 示例配置
  - `basic_example.py`: 基础使用示例

---

## 📝 注意事项

1. **初始 DAU 分配：** 如果没有地区覆盖，全局初始 DAU 会按比例分配到 6 个地区
2. **留存率窗口：** DAU 计算考虑最近 180 天的新增用户
3. **税后收入计算：** IAP 收入按 70% 计算，广告收入按 100% 计算
4. **预算计算：** 基于前一日税后收入，加上额外投放支出

---

## 🔧 修改建议

如果需要修改公式或缺省值，主要关注以下文件：
- **缺省值：** `src/models/config.py`
- **留存率公式：** `src/core/retention.py`
- **DAU 公式：** `src/core/dau.py`
- **财务计算：** `src/core/simulator.py`
