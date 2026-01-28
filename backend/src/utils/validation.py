"""
参数校验工具
"""

from typing import List, Tuple
from ..models.config import SimulationConfig
from ..models.results import ValidationResult


def validate_config(config: SimulationConfig) -> ValidationResult:
    """
    校验模拟配置
    
    Returns:
        ValidationResult 对象
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    # 1. 校验模拟天数
    if config.simulation_days < 1:
        errors.append("模拟天数必须大于 0")
    elif config.simulation_days > 730:
        warnings.append("模拟天数超过 2 年，计算可能较慢")
    
    # 2. 校验预算配置
    region_distribution = config.budget.region_distribution
    total_ratio = sum(region_distribution.values())
    if not (0.999 <= total_ratio <= 1.001):
        errors.append(f"地区预算分配比例之和必须为 100%，当前为 {total_ratio*100:.2f}%")
    
    # 3. 校验留存率
    retention = config.defaults.retention
    if retention.day1 < retention.day7:
        warnings.append("Day 1 留存率低于 Day 7，这通常不正常")
    if retention.day7 < retention.day30:
        warnings.append("Day 7 留存率低于 Day 30，这通常不正常")
    if retention.day30 < retention.day60:
        warnings.append("Day 30 留存率低于 Day 60，这通常不正常")
    if retention.day60 < 0.05:
        warnings.append("Day 60 留存率低于 5%，可能导致长期 DAU 快速下降")
    
    # 4. 校验 CPI 和 ARPU
    if config.defaults.cpi <= 0:
        errors.append("CPI 必须大于 0")
    
    daily_arpu = config.defaults.arpu_iap + config.defaults.arpu_ad
    daily_cost = config.defaults.unit_cost_operational
    if daily_arpu < daily_cost:
        warnings.append(f"单用户日均 ARPU ({daily_arpu:.4f}) 低于日均成本 ({daily_cost:.4f})，难以盈利")
    
    # 5. 校验初始 DAU
    if config.defaults.initial_dau <= 0:
        warnings.append("初始 DAU 为 0，建议设置初始用户基数")
    
    # 6. 校验预算策略
    if config.budget.base_ratio > 2.0:
        warnings.append("基准预算比例超过 200%，可能导致过度投放")
    if config.budget.base_ratio <= 0:
        warnings.append("基准预算比例为 0，将不会进行付费投放")
    
    # 7. 校验有效地区
    active_regions = [r for r, ratio in region_distribution.items() if ratio > 0]
    if len(active_regions) == 0:
        errors.append("至少需要一个有效地区（预算分配比例 > 0）")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
