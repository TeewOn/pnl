"""
P&L 模拟器 - Streamlit 版本

实时更新，参数调整后立即看到结果
"""

import sys
import os
from pathlib import Path

# 添加后端代码路径
# 获取当前文件所在目录
current_dir = Path(__file__).parent.resolve()
# 获取项目根目录（streamlit_app 的父目录）
project_root = current_dir.parent
# 后端目录（包含 src 的父目录）
backend_dir = project_root / "backend"
backend_dir_str = str(backend_dir.resolve())

# 将 backend 目录添加到路径，这样可以从 src.models 导入
if backend_dir_str not in sys.path:
    sys.path.insert(0, backend_dir_str)

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
from calendar import month_name
import json

# 导入后端模块（使用 src.models 和 src.core）
# 强制重新加载模块（解决缓存问题）
import importlib
import src.models.config
import src.core.simulator
import src.core.retention
importlib.reload(src.models.config)
importlib.reload(src.core.simulator)
importlib.reload(src.core.retention)

from src.models.config import (
    SimulationConfig,
    DefaultParams,
    BudgetConfig,
    RetentionConfig,
    RegionOverride,
)
from src.core.simulator import run_simulation
from src.core.retention import fit_retention_params

# 加载默认配置
def load_default_config():
    """加载默认配置文件"""
    config_path = current_dir / "default_config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"配置文件未找到: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"配置文件格式错误: {e}")
        return {}

# 加载默认配置
default_config = load_default_config()

# 页面配置
st.set_page_config(
    page_title="P&L 模拟器",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# 标题
st.markdown('<div class="main-header">📊 P&L 模拟器</div>', unsafe_allow_html=True)

# 初始化 session_state 缓存
if "config_mode" not in st.session_state:
    st.session_state.config_mode = "global"  # "global" 或 "regional"
if "cached_global_config" not in st.session_state:
    st.session_state.cached_global_config = {}
if "cached_regional_config" not in st.session_state:
    st.session_state.cached_regional_config = {}

# ============ 左侧参数面板 ============
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # 配置方案选择
    st.subheader("📋 配置方案")
    config_mode = st.radio(
        "选择配置方案",
        ["方案1: 全局配置", "方案2: 分地区配置"],
        index=0 if st.session_state.config_mode == "global" else 1,
        help="方案1：输入全局参数，全球视作同一地区\n方案2：按地区分别输入参数"
    )
    config_mode_key = "global" if config_mode == "方案1: 全局配置" else "regional"
    
    # 如果切换了方案，更新session_state
    if config_mode_key != st.session_state.config_mode:
        st.session_state.config_mode = config_mode_key
    
    st.divider()
    
    # 基础设置
    st.subheader("基础设置")
    sim_default = default_config.get("simulation", {})
    simulation_days = st.number_input(
        "模拟天数",
        min_value=1,
        max_value=730,
        value=sim_default.get("simulation_days", 180),
        step=1,
        help="模拟的总天数"
    )
    
    start_date_default = sim_default.get("start_date")
    if start_date_default:
        # 如果配置中有日期，解析它
        if isinstance(start_date_default, str):
            start_date_default = date.fromisoformat(start_date_default)
        else:
            start_date_default = date.today()
    else:
        start_date_default = date.today()
    
    start_date = st.date_input(
        "开始日期",
        value=start_date_default,
        help="模拟开始的日期"
    )
    
    # 计算涉及的月份范围
    end_date = start_date + timedelta(days=simulation_days - 1)
    months_in_range = []
    current = start_date.replace(day=1)
    while current <= end_date:
        months_in_range.append((current.month, current.year))
        # 下一个月
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    st.divider()
    
    # 预算策略
    st.subheader("💰 预算策略")
    
    # 基准预算比例
    st.markdown("**基准预算比例**")
    budget_default = default_config.get("budget", {})
    base_ratio = st.number_input(
        "默认基准预算比例 (%)",
        min_value=0.0,
        max_value=200.0,
        value=budget_default.get("base_ratio", 100.0),
        step=1.0,
        format="%.1f",
        help="每日投放预算占前一日税后总收入的比例",
        key="base_ratio",
    ) / 100
    
    # 按月配置基准预算比例
    base_ratio_by_month = {}
    use_monthly_base_ratio = st.checkbox("启用按月配置基准预算比例", value=False, help="勾选后可以为每个月设置不同的基准预算比例")
    
    if use_monthly_base_ratio:
        with st.expander("按月配置基准预算比例", expanded=False):
            cols = st.columns(3)
            col_idx = 0
            for month_num, year in months_in_range:
                month_key = str(month_num)
                month_label = f"{year}年{month_num}月"
                input_key = f"base_ratio_month_{month_key}_{year}"
                
                with cols[col_idx % 3]:
                    # 获取当前值：如果 session_state 中有值就用它，否则用默认值
                    current_value = st.session_state.get(input_key, base_ratio * 100)
                    
                    # 创建 widget，如果 key 已存在则不设置 value
                    if input_key in st.session_state:
                        month_base_ratio = st.number_input(
                            f"{month_label} (%)",
                            min_value=0.0,
                            max_value=200.0,
                            step=1.0,
                            format="%.1f",
                            key=input_key,
                        )
                    else:
                        month_base_ratio = st.number_input(
                            f"{month_label} (%)",
                            min_value=0.0,
                            max_value=200.0,
                            value=current_value,
                            step=1.0,
                            format="%.1f",
                            key=input_key,
                        )
                    # 确保值被正确收集到字典中（使用当前 widget 的值）
                    base_ratio_by_month[month_key] = month_base_ratio / 100
                col_idx += 1
    else:
        # 如果未启用按月配置，清空已保存的值（可选）
        for month_num, year in months_in_range:
            month_key = str(month_num)
            input_key = f"base_ratio_month_{month_key}_{year}"
            if input_key in st.session_state:
                del st.session_state[input_key]
    
    # 按月额外投放预算
    st.markdown("**按月额外投放预算**")
    st.caption("可以为特定月份设置每日额外增加的投放预算金额（在基准预算基础上，该月的每一天都会增加此金额）")
    
    additional_by_month = {}
    use_monthly_budget = st.checkbox("启用按月额外预算", value=False, help="勾选后可以为每个月设置不同的每日额外预算金额")
    
    if use_monthly_budget:
        # 使用expander折叠，默认收起
        with st.expander("按月配置额外预算", expanded=False):
            st.info("💡 提示：这里输入的是该月**每日增加的投放预算金额**。例如输入 1000，表示该月的每一天都会在基准预算基础上额外增加 1000 美元的投放预算。")
            cols = st.columns(3)
            col_idx = 0
            for month_num, year in months_in_range:
                month_key = str(month_num)
                month_label = f"{year}年{month_num}月"
                with cols[col_idx % 3]:
                    additional_by_month[month_key] = st.number_input(
                        f"{month_label} (每日增加 $)",
                        min_value=0.0,
                        value=0.0,
                        step=100.0,
                        format="%.0f",
                        key=f"additional_budget_{month_key}_{year}",
                        help=f"{month_label} 每日额外增加的投放预算金额（美元）",
                    )
                col_idx += 1
    else:
        # 如果未启用，所有月份额外预算为0
        additional_by_month = {}
    
    # 地区预算分配（仅在方案2时显示）
    region_names = {
        "JP": "日本",
        "US": "美国",
        "EMEA": "英语T1+西欧",
        "LATAM": "拉美",
        "CN": "港澳台",
        "OTHER": "其他",
    }
    
    if config_mode_key == "regional":
        st.markdown("**地区预算分配**")
        
        # 是否按月配置地区预算分配
        use_monthly_region_distribution = st.checkbox(
            "启用按月配置地区预算分配",
            value=False,
            help="勾选后可以为每个月设置不同的地区预算分配比例"
        )
        
        region_distribution = {}
        region_distribution_by_month = {}
        
        if use_monthly_region_distribution:
            # 按月配置地区预算分配
            st.caption("默认分配比例（适用于未单独配置的月份）")
            
            # 默认分配
            total_ratio = 0
            region_dist_default = budget_default.get("region_distribution", {})
            for code, name in region_names.items():
                default_val = region_dist_default.get(code, 20.0 if code in ["JP", "US"] else 15.0)
                ratio = st.number_input(
                    f"{name} (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=default_val,
                    step=0.1,
                    format="%.1f",
                    key=f"region_default_{code}",
                ) / 100
                region_distribution[code] = ratio
                total_ratio += ratio
            
            if abs(total_ratio - 1.0) > 0.001:
                st.warning(f"⚠️ 默认地区分配总和: {total_ratio*100:.1f}% (应为 100%)")
            else:
                st.success(f"✅ 默认地区分配总和: {total_ratio*100:.1f}%")
            
            # 按月配置
            with st.expander("按月配置地区预算分配", expanded=False):
                for month_num, year in months_in_range:
                    month_key = str(month_num)
                    month_label = f"{year}年{month_num}月"
                    st.markdown(f"**{month_label}**")
                    
                    month_distribution = {}
                    month_total = 0
                    cols = st.columns(3)
                    col_idx = 0
                    for code, name in region_names.items():
                        with cols[col_idx % 3]:
                            ratio = st.number_input(
                                f"{name} (%)",
                                min_value=0.0,
                                max_value=100.0,
                                value=region_distribution.get(code, 0.15) * 100,
                                step=0.1,
                                format="%.1f",
                                key=f"region_month_{month_key}_{year}_{code}",
                            ) / 100
                            month_distribution[code] = ratio
                            month_total += ratio
                        col_idx += 1
                    
                    if abs(month_total - 1.0) > 0.001:
                        st.warning(f"⚠️ {month_label} 分配总和: {month_total*100:.1f}%")
                    else:
                        st.success(f"✅ {month_label} 分配总和: {month_total*100:.1f}%")
                    
                    region_distribution_by_month[month_key] = month_distribution
                    st.divider()
        else:
            # 不按月配置，使用统一分配
            total_ratio = 0
            region_dist_default = budget_default.get("region_distribution", {})
            
            for code, name in region_names.items():
                default_val = region_dist_default.get(code, 20.0 if code in ["JP", "US"] else 15.0)
                ratio = st.number_input(
                    f"{name} (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=default_val,
                    step=0.1,
                    format="%.1f",
                    key=f"region_{code}",
                ) / 100
                region_distribution[code] = ratio
                total_ratio += ratio
            
            # 显示分配总和
            if abs(total_ratio - 1.0) > 0.001:
                st.warning(f"⚠️ 地区分配总和: {total_ratio*100:.1f}% (应为 100%)")
            else:
                st.success(f"✅ 地区分配总和: {total_ratio*100:.1f}%")
            
            region_distribution_by_month = {}
    else:
        # 方案1：全局配置，不显示地区预算分配，使用默认均分
        region_distribution = {
            "JP": 1.0/6,
            "US": 1.0/6,
            "EMEA": 1.0/6,
            "LATAM": 1.0/6,
            "CN": 1.0/6,
            "OTHER": 1.0/6,
        }
        region_distribution_by_month = {}
    
    st.divider()
    
    # 根据选择的方案显示不同的参数输入界面
    if config_mode_key == "global":
        # ============ 方案1: 全局配置 ============
        st.subheader("🌍 全局默认参数")
        
        # 从缓存恢复或使用默认值
        cached = st.session_state.cached_global_config
        global_default = default_config.get("global", {})
        
        initial_dau = st.number_input(
            "初始 DAU",
            min_value=0,
            max_value=1000000,
            value=cached.get("initial_dau", global_default.get("initial_dau", 1000)),
            step=100,
            help="全局初始 DAU（全球视为统一地区）",
            key="global_initial_dau",
        )
        
        cpi = st.number_input(
            "CPI (用户获取成本)",
            min_value=0.1,
            max_value=10.0,
            value=cached.get("cpi", global_default.get("cpi", 2.0)),
            step=0.1,
            format="%.2f",
            help="每获取一个用户的成本",
            key="global_cpi",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            arpu_iap = st.number_input(
                "ARPU (IAP)",
                min_value=0.0,
                max_value=1.0,
                value=cached.get("arpu_iap", global_default.get("arpu_iap", 0.01)),
                step=0.001,
                format="%.3f",
                help="单用户日均内购收入",
                key="global_arpu_iap",
            )
        
        with col2:
            arpu_ad = st.number_input(
                "ARPU (Ad)",
                min_value=0.0,
                max_value=1.0,
                value=cached.get("arpu_ad", global_default.get("arpu_ad", 0.005)),
                step=0.001,
                format="%.3f",
                help="单用户日均广告收入",
                key="global_arpu_ad",
            )
        
        unit_cost_operational = st.number_input(
            "单位运营成本",
            min_value=0.0,
            max_value=0.1,
            value=cached.get("unit_cost_operational", global_default.get("unit_cost_operational", 0.01901)),
            step=0.0001,
            format="%.5f",
            help="每 DAU 每天的运营成本（API + 机器成本）",
            key="global_unit_cost",
        )
        
        # 自然量增长系数说明
        with st.expander("ℹ️ 自然量增长系数说明", expanded=False):
            st.markdown("""
            **什么是自然量增长系数？**
            
            自然量增长系数表示当前活跃用户（DAU）中每天自发带来新用户的比例。
            
            **计算公式：**
            ```
            每日自然新增用户数 = 前一日DAU × 自然量增长系数
            ```
            
            **示例：**
            - 如果前一日DAU = 10,000，自然量增长系数 = 1%（0.01）
            - 则当日自然新增用户 = 10,000 × 0.01 = 100人
            
            **生效方式：**
            1. 每天基于前一天的DAU计算自然新增用户数
            2. 自然新增用户会参与留存率计算，影响后续的DAU
            3. 系统会自动限制：自然量增长系数最大值为2%，防止指数级增长
            
            **建议值：**
            - 一般产品：0.5% - 1.5%
            - 高增长产品：1.5% - 2.0%
            """)
        
        organic_default = global_default.get("organic_growth_rate", 0.01)
        organic_growth_rate = st.number_input(
            "自然量增长系数 (%)",
            min_value=0.0,
            max_value=2.0,
            value=min(cached.get("organic_growth_rate", organic_default) * 100, 2.0),
            step=0.1,
            format="%.1f",
            help="每天自然新增用户占前一日DAU的比例（最大值2%）",
            key="global_organic",
        ) / 100
        
        st.divider()
        
        # 留存率配置
        st.subheader("📈 留存率配置")
        st.caption("输入 7 个关键留存率节点")
        
        cached_retention = cached.get("retention", {})
        retention_default = global_default.get("retention", {})
        
        retention_day1 = st.number_input("Day 1", 0.0, 1.0, cached_retention.get("day1", retention_default.get("day1", 0.50)), 0.01, format="%.2f", key="global_retention_day1")
        retention_day2 = st.number_input("Day 2", 0.0, 1.0, cached_retention.get("day2", retention_default.get("day2", 0.40)), 0.01, format="%.2f", key="global_retention_day2")
        retention_day3 = st.number_input("Day 3", 0.0, 1.0, cached_retention.get("day3", retention_default.get("day3", 0.35)), 0.01, format="%.2f", key="global_retention_day3")
        retention_day7 = st.number_input("Day 7", 0.0, 1.0, cached_retention.get("day7", retention_default.get("day7", 0.28)), 0.01, format="%.2f", key="global_retention_day7")
        retention_day14 = st.number_input("Day 14", 0.0, 1.0, cached_retention.get("day14", retention_default.get("day14", 0.22)), 0.01, format="%.2f", key="global_retention_day14")
        retention_day30 = st.number_input("Day 30", 0.0, 1.0, cached_retention.get("day30", retention_default.get("day30", 0.16)), 0.01, format="%.2f", key="global_retention_day30")
        retention_day60 = st.number_input("Day 60", 0.0, 1.0, cached_retention.get("day60", retention_default.get("day60", 0.10)), 0.01, format="%.2f", key="global_retention_day60")
        
        # 保存到缓存
        st.session_state.cached_global_config = {
            "initial_dau": initial_dau,
            "cpi": cpi,
            "arpu_iap": arpu_iap,
            "arpu_ad": arpu_ad,
            "unit_cost_operational": unit_cost_operational,
            "organic_growth_rate": organic_growth_rate,
            "retention": {
                "day1": retention_day1,
                "day2": retention_day2,
                "day3": retention_day3,
                "day7": retention_day7,
                "day14": retention_day14,
                "day30": retention_day30,
                "day60": retention_day60,
            }
        }
        
        # 显示拟合参数预览
        try:
            alpha, beta, gamma = fit_retention_params(
                retention_day1, retention_day2, retention_day3,
                retention_day7, retention_day14, retention_day30, retention_day60
            )
            with st.expander("📊 留存率拟合参数"):
                st.write(f"α (alpha): {alpha:.4f}")
                st.write(f"β (beta): {beta:.4f}")
                st.write(f"γ (gamma): {gamma:.4f}")
        except:
            pass
        
        # 方案1的全局参数变量
        global_params = {
            "initial_dau": initial_dau,
            "cpi": cpi,
            "arpu_iap": arpu_iap,
            "arpu_ad": arpu_ad,
            "unit_cost_operational": unit_cost_operational,
            "organic_growth_rate": organic_growth_rate,
            "retention": RetentionConfig(
                day1=retention_day1,
                day2=retention_day2,
                day3=retention_day3,
                day7=retention_day7,
                day14=retention_day14,
                day30=retention_day30,
                day60=retention_day60,
            )
        }
        regional_params = None
        
    else:
        # ============ 方案2: 分地区配置 ============
        st.subheader("🌍 分地区参数配置")
        
        # 自然量增长系数说明（方案2）
        with st.expander("ℹ️ 自然量增长系数说明", expanded=False):
            st.markdown("""
            **什么是自然量增长系数？**
            
            自然量增长系数表示当前活跃用户（DAU）中每天自发带来新用户的比例。
            
            **计算公式：**
            ```
            每日自然新增用户数 = 前一日DAU × 自然量增长系数
            ```
            
            **示例：**
            - 如果前一日DAU = 10,000，自然量增长系数 = 1%（0.01）
            - 则当日自然新增用户 = 10,000 × 0.01 = 100人
            
            **生效方式：**
            1. 每天基于前一天的DAU计算自然新增用户数
            2. 自然新增用户会参与留存率计算，影响后续的DAU
            3. 系统会自动限制：自然量增长系数最大值为2%，防止指数级增长
            
            **建议值：**
            - 一般产品：0.5% - 1.5%
            - 高增长产品：1.5% - 2.0%
            """)
        
        # 从缓存恢复或使用默认值
        cached = st.session_state.cached_regional_config
        regional_defaults = default_config.get("regional", {})
        
        # 为每个地区创建输入表单
        regional_params = {}
        regional_retentions = {}
        
        for code, name in region_names.items():
            with st.expander(f"📍 {name} ({code})", expanded=False):
                cached_region = cached.get(code, {})
                region_default = regional_defaults.get(code, {})
                
                regional_params[code] = {
                    "initial_dau": st.number_input(
                        f"初始 DAU",
                        min_value=0,
                        max_value=1000000,
                        value=cached_region.get("initial_dau", region_default.get("initial_dau", 0)),
                        step=100,
                        key=f"regional_{code}_dau"
                    ),
                    "cpi": st.number_input(
                        f"CPI (用户获取成本)",
                        min_value=0.1,
                        max_value=10.0,
                        value=cached_region.get("cpi", region_default.get("cpi", 2.0)),
                        step=0.1,
                        format="%.2f",
                        key=f"regional_{code}_cpi"
                    ),
                    "arpu_iap": st.number_input(
                        f"ARPU (IAP)",
                        min_value=0.0,
                        max_value=1.0,
                        value=cached_region.get("arpu_iap", region_default.get("arpu_iap", 0.01)),
                        step=0.001,
                        format="%.3f",
                        key=f"regional_{code}_arpu_iap"
                    ),
                    "arpu_ad": st.number_input(
                        f"ARPU (Ad)",
                        min_value=0.0,
                        max_value=1.0,
                        value=cached_region.get("arpu_ad", region_default.get("arpu_ad", 0.005)),
                        step=0.001,
                        format="%.3f",
                        key=f"regional_{code}_arpu_ad"
                    ),
                    "unit_cost_operational": st.number_input(
                        f"单位运营成本",
                        min_value=0.0,
                        max_value=0.1,
                        value=cached_region.get("unit_cost_operational", region_default.get("unit_cost_operational", 0.01901)),
                        step=0.0001,
                        format="%.5f",
                        key=f"regional_{code}_unit_cost"
                    ),
                    "organic_growth_rate": st.number_input(
                        f"自然量增长系数 (%)",
                        min_value=0.0,
                        max_value=2.0,
                        value=min(cached_region.get("organic_growth_rate", region_default.get("organic_growth_rate", 0.01)) * 100, 2.0),
                        step=0.1,
                        format="%.1f",
                        help="每天自然新增用户占前一日DAU的比例（最大值2%）",
                        key=f"regional_{code}_organic"
                    ) / 100,
                }
                
                # 留存率配置
                st.caption("留存率配置（7个关键节点）")
                cached_retention = cached_region.get("retention", {})
                retention_default = region_default.get("retention", {})
                regional_retentions[code] = {
                    "day1": st.number_input(f"Day 1", 0.0, 1.0, cached_retention.get("day1", retention_default.get("day1", 0.50)), 0.0001, format="%.4f", key=f"regional_{code}_retention_day1"),
                    "day2": st.number_input(f"Day 2", 0.0, 1.0, cached_retention.get("day2", retention_default.get("day2", 0.40)), 0.0001, format="%.4f", key=f"regional_{code}_retention_day2"),
                    "day3": st.number_input(f"Day 3", 0.0, 1.0, cached_retention.get("day3", retention_default.get("day3", 0.35)), 0.0001, format="%.4f", key=f"regional_{code}_retention_day3"),
                    "day7": st.number_input(f"Day 7", 0.0, 1.0, cached_retention.get("day7", retention_default.get("day7", 0.28)), 0.0001, format="%.4f", key=f"regional_{code}_retention_day7"),
                    "day14": st.number_input(f"Day 14", 0.0, 1.0, cached_retention.get("day14", retention_default.get("day14", 0.22)), 0.0001, format="%.4f", key=f"regional_{code}_retention_day14"),
                    "day30": st.number_input(f"Day 30", 0.0, 1.0, cached_retention.get("day30", retention_default.get("day30", 0.16)), 0.0001, format="%.4f", key=f"regional_{code}_retention_day30"),
                    "day60": st.number_input(f"Day 60", 0.0, 1.0, cached_retention.get("day60", retention_default.get("day60", 0.10)), 0.0001, format="%.4f", key=f"regional_{code}_retention_day60"),
                }
                
                # 保存到缓存
                cached[code] = {
                    **regional_params[code],
                    "organic_growth_rate": regional_params[code]["organic_growth_rate"],
                    "retention": regional_retentions[code]
                }
        
        st.session_state.cached_regional_config = cached
        global_params = None

# ============ 构建配置并运行模拟 ============
# 注意：由于 Streamlit 的重新运行机制，参数变化时会自动重新执行下面的代码

if config_mode_key == "global":
    # 方案1: 全局配置
    # 方案1下，将所有预算分配给一个虚拟的"全球"地区，或者保持原有分配但不显示地区对比
    budget_config = BudgetConfig(
        base_ratio=base_ratio,
        base_ratio_by_month=base_ratio_by_month,
        additional_by_month=additional_by_month,
        region_distribution=region_distribution,
        region_distribution_by_month=region_distribution_by_month,
    )
    
    config = SimulationConfig(
        simulation_days=simulation_days,
        start_date=start_date,
        budget=budget_config,
        defaults=DefaultParams(
            initial_dau=global_params["initial_dau"],
            cpi=global_params["cpi"],
            arpu_iap=global_params["arpu_iap"],
            arpu_ad=global_params["arpu_ad"],
            unit_cost_operational=global_params["unit_cost_operational"],
            organic_growth_rate=global_params["organic_growth_rate"],
            retention=global_params["retention"],
        ),
        regions={},  # 方案1不使用地区覆盖
        monthly_overrides={},
        global_fixed_cost=0.0,  # 不再使用global_fixed_cost，改用additional_by_month
        output_options={
            "include_daily_details": True,
            "include_region_breakdown": False,  # 方案1不包含地区细分
            "aggregate_by": "day",
        },
    )
else:
    # 方案2: 分地区配置
    # 构建地区覆盖配置
    regions_dict = {}
    for code, params in regional_params.items():
        retention_dict = {
            "day1": regional_retentions[code]["day1"],
            "day2": regional_retentions[code]["day2"],
            "day3": regional_retentions[code]["day3"],
            "day7": regional_retentions[code]["day7"],
            "day14": regional_retentions[code]["day14"],
            "day30": regional_retentions[code]["day30"],
            "day60": regional_retentions[code]["day60"],
        }
        
        regions_dict[code] = RegionOverride(
            initial_dau=params["initial_dau"] if params["initial_dau"] > 0 else None,
            cpi=params["cpi"],
            arpu_iap=params["arpu_iap"],
            arpu_ad=params["arpu_ad"],
            unit_cost_operational=params["unit_cost_operational"],
            organic_growth_rate=params["organic_growth_rate"],
            retention=retention_dict,
        )
    
    # 方案2使用默认值作为基础，但会被地区覆盖
    config = SimulationConfig(
        simulation_days=simulation_days,
        start_date=start_date,
        budget=BudgetConfig(
            base_ratio=base_ratio,
            base_ratio_by_month=base_ratio_by_month,
            additional_by_month=additional_by_month,
            region_distribution=region_distribution,
            region_distribution_by_month=region_distribution_by_month,
        ),
        defaults=DefaultParams(
            initial_dau=0,  # 方案2中各地区都有独立配置
            cpi=2.0,  # 默认值，会被地区覆盖
            arpu_iap=0.01,
            arpu_ad=0.005,
            unit_cost_operational=0.01901,
            organic_growth_rate=0.01,
            retention=RetentionConfig(),  # 默认值，会被地区覆盖
        ),
        regions=regions_dict,  # 方案2使用地区覆盖
        monthly_overrides={},
        global_fixed_cost=0.0,  # 不再使用global_fixed_cost，改用additional_by_month
        output_options={
            "include_daily_details": True,
            "include_region_breakdown": True,  # 方案2包含地区细分
            "aggregate_by": "day",
        },
    )

# 运行模拟
with st.spinner("🔄 正在运行模拟..."):
    result = run_simulation(config)

# ============ 显示结果 ============

# 关键指标卡片
st.subheader("📊 关键指标")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "最终 DAU",
        f"{result.summary.final_metrics.total_dau:,}",
        delta=f"{result.summary.final_metrics.dau_growth_rate:.1f}%",
        delta_color="normal" if result.summary.final_metrics.dau_growth_rate >= 0 else "inverse",
    )

with col2:
    st.metric(
        "累计收入",
        f"${result.summary.cumulative_metrics.total_revenue:,.0f}",
    )

with col3:
    st.metric(
        "累计成本",
        f"${result.summary.cumulative_metrics.total_cost:,.0f}",
    )

with col4:
    net_profit = result.summary.cumulative_metrics.net_profit
    roi = result.summary.cumulative_metrics.roi  # ROI = 收入/成本
    # ROI > 1 表示盈利（收入 > 成本），箭头向上（normal，绿色）
    # ROI < 1 表示亏损（收入 < 成本），箭头向下（inverse，红色）
    st.metric(
        "净利润",
        f"${net_profit:,.0f}",
        delta=f"ROI: {roi:.2f}",
        delta_color="normal" if roi > 1 else "inverse",
    )

# 详细指标
with st.expander("📋 详细指标"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**收入明细**")
        st.write(f"- IAP 收入: ${result.summary.cumulative_metrics.revenue_iap:,.2f}")
        st.write(f"- 广告收入: ${result.summary.cumulative_metrics.revenue_ad:,.2f}")
    
    with col2:
        st.write("**成本明细**")
        st.write(f"- 营销成本: ${result.summary.cumulative_metrics.cost_marketing:,.2f}")
        st.write(f"- 运营成本: ${result.summary.cumulative_metrics.cost_api:,.2f}")
        st.write(f"- 固定成本: ${result.summary.cumulative_metrics.cost_fixed:,.2f}")
    
    st.write("**里程碑**")
    milestones = result.summary.milestones
    st.write(f"- 盈亏平衡日: Day {milestones.break_even_day or 'N/A'}")
    st.write(f"- 首次盈利日: Day {milestones.first_profitable_day or 'N/A'}")
    st.write(f"- DAU 峰值: {milestones.peak_dau_value:,} (Day {milestones.peak_dau_day})")

st.divider()

# 图表展示
# 方案1不显示地区对比标签页
if config_mode_key == "global":
    tab1, tab2, tab3 = st.tabs(["📈 DAU & DNU 趋势", "💰 收入/成本/利润趋势", "📊 P&L 累计曲线"])
else:
    tab1, tab2, tab3, tab4 = st.tabs(["📈 DAU & DNU 趋势", "💰 收入/成本/利润趋势", "📊 P&L 累计曲线", "🌍 地区对比"])

with tab1:
    st.subheader("DAU & DNU 趋势")
    
    # DAU 和 DNU 趋势图（统一坐标轴）
    fig = go.Figure()
    
    # DAU
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=result.timeseries.totals.dau,
        name="DAU",
        mode="lines",
        line=dict(color="#1890ff", width=2),
        fill="tonexty",
        fillcolor="rgba(24, 144, 255, 0.1)",
    ))
    
    # DNU 自然
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=result.timeseries.totals.dnu_organic,
        name="DNU (自然)",
        mode="lines",
        line=dict(color="#52c41a", width=2, dash="dash"),
    ))
    
    # DNU 付费
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=result.timeseries.totals.dnu_paid,
        name="DNU (付费)",
        mode="lines",
        line=dict(color="#fa8c16", width=2, dash="dash"),
    ))
    
    # DNU 总计
    dnu_total = [o + p for o, p in zip(result.timeseries.totals.dnu_organic, result.timeseries.totals.dnu_paid)]
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=dnu_total,
        name="DNU (总计)",
        mode="lines",
        line=dict(color="#722ed1", width=2, dash="dot"),
    ))
    
    fig.update_layout(
        xaxis_title="天数",
        yaxis_title="用户数",
        hovermode="x unified",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("收入/成本/利润趋势")
    
    # 计算每日收入和成本
    daily_revenue = result.timeseries.totals.revenue
    daily_cost = result.timeseries.totals.cost
    daily_profit = result.timeseries.totals.profit
    
    fig = go.Figure()
    
    # 收入
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=daily_revenue,
        name="收入",
        mode="lines",
        line=dict(color="#52c41a", width=2),
        fill="tonexty",
        fillcolor="rgba(82, 196, 26, 0.1)",
    ))
    
    # 成本
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=daily_cost,
        name="成本",
        mode="lines",
        line=dict(color="#ff4d4f", width=2),
        fill="tonexty",
        fillcolor="rgba(255, 77, 79, 0.1)",
    ))
    
    # 利润
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=daily_profit,
        name="利润",
        mode="lines",
        line=dict(color="#1890ff", width=2, dash="dash"),
    ))
    
    # 零线
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        xaxis_title="天数",
        yaxis_title="金额 ($)",
        hovermode="x unified",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("P&L 累计曲线")
    
    # 计算累计利润
    cumulative_profit = []
    cumulative = 0
    for profit in result.timeseries.totals.profit:
        cumulative += profit
        cumulative_profit.append(cumulative)
    
    # P&L 曲线
    fig = go.Figure()
    
    # 累计利润曲线
    colors = ["#ff4d4f" if p < 0 else "#52c41a" for p in cumulative_profit]
    fig.add_trace(go.Scatter(
        x=result.timeseries.days,
        y=cumulative_profit,
        name="累计利润",
        mode="lines",
        line=dict(width=2),
        marker=dict(color=colors),
        fill="tonexty",
        fillcolor="rgba(82, 196, 26, 0.1)",
    ))
    
    # 盈亏平衡线
    if result.summary.milestones.break_even_day:
        be_day = result.summary.milestones.break_even_day
        fig.add_vline(
            x=be_day,
            line_dash="dash",
            line_color="#faad14",
            annotation_text=f"盈亏平衡 Day {be_day}",
        )
    
    # 零线
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    
    fig.update_layout(
        xaxis_title="天数",
        yaxis_title="累计利润 ($)",
        hovermode="x unified",
        height=400,
    )
    
    st.plotly_chart(fig, use_container_width=True)

if config_mode_key == "regional":
    with tab4:
        st.subheader("地区贡献度")
        
        if result.timeseries.by_region:
            # 选择指标
            metric_type = st.radio(
                "选择指标",
                ["DAU", "收入", "成本"],
                horizontal=True,
            )
            
            # 计算各地区数据
            region_data = []
            for region, data in result.timeseries.by_region.items():
                if metric_type == "DAU":
                    value = data.dau[-1] if data.dau else 0
                elif metric_type == "收入":
                    value = sum(data.revenue) if data.revenue else 0
                else:
                    value = sum(data.cost) if data.cost else 0
                
                region_data.append({
                    "地区": region_names.get(region, region),
                    "值": value,
                })
            
            # 饼图
            if region_data:
                fig = px.pie(
                    values=[d["值"] for d in region_data],
                    names=[d["地区"] for d in region_data],
                    title=f"各地区 {metric_type} 贡献度",
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 数据表
                st.dataframe(
                    region_data,
                    use_container_width=True,
                    hide_index=True,
                )

# 执行时间
st.caption(f"⏱️ 模拟执行时间: {result.execution_time_ms}ms")
