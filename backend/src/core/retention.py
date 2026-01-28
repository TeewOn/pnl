"""
留存率拟合模块

拟合逻辑：
1. Day 1-30（早期留存）: 幂函数拟合 R(d) = α * d^β
2. Day 31-60（长期留存）: 指数衰减 R(d) = R30 * γ^(d-30)
3. Day 61+: 继续使用 γ 进行指数衰减
"""

from typing import Tuple, List, Dict
import numpy as np
from scipy.optimize import curve_fit


def _power_func(d: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """幂函数: R(d) = α * d^β"""
    return alpha * np.power(d, beta)


def fit_retention_params(
    r1: float, r2: float, r3: float, r7: float, r14: float, r30: float, r60: float
) -> Tuple[float, float, float]:
    """
    根据 7 个关键留存点拟合参数
    
    Args:
        r1-r60: 7 个关键留存率节点
        
    Returns:
        (alpha, beta, gamma): 拟合参数
        - alpha, beta: 幂函数参数，用于 Day 1-30
        - gamma: 日衰减率，用于 Day 31+
    """
    # 1. 拟合 Day 1-30 的幂函数参数
    days_early = np.array([1, 2, 3, 7, 14, 30], dtype=float)
    retentions_early = np.array([r1, r2, r3, r7, r14, r30])
    
    try:
        # 使用最小二乘拟合
        (alpha, beta), _ = curve_fit(
            _power_func, 
            days_early, 
            retentions_early,
            p0=[0.5, -0.3],  # 初始猜测值
            bounds=([0.01, -2], [2, 0]),  # alpha > 0, beta < 0（衰减）
            maxfev=5000
        )
    except Exception:
        # 如果拟合失败，使用简单估计
        alpha = r1
        beta = np.log(r30 / r1) / np.log(30) if r1 > 0 and r30 > 0 else -0.3
    
    # 2. 计算 Day 31+ 的指数衰减率
    # γ = (R60 / R30)^(1/30)
    if r30 > 0 and r60 > 0:
        gamma = np.power(r60 / r30, 1.0 / 30.0)
    else:
        gamma = 0.98  # 默认衰减率
    
    # 确保 gamma 在合理范围内
    gamma = np.clip(gamma, 0.9, 0.999)
    
    return float(alpha), float(beta), float(gamma)


def calc_retention_new(day: int, alpha: float, beta: float, gamma: float) -> float:
    """
    计算新用户在注册后第 day 天的留存率
    
    Args:
        day: 注册后天数（1 = 次日留存, 2 = 第3日留存, ...）
        alpha, beta, gamma: 由 fit_retention_params() 拟合得到的参数
        
    Returns:
        留存率（0-1 之间）
    """
    if day <= 0:
        return 1.0  # Day 0 = 注册当天，留存率 100%
    
    if day <= 30:
        # Day 1-30: 幂函数
        retention = alpha * np.power(day, beta)
    else:
        # Day 31+: 从 Day 30 的值开始指数衰减
        r_day30 = alpha * np.power(30, beta)
        retention = r_day30 * np.power(gamma, day - 30)
    
    # 确保留存率在合理范围内
    return float(np.clip(retention, 0.0, 1.0))


def calc_retention_active(day: int, gamma: float) -> float:
    """
    计算初始 DAU（存量老用户）在模拟第 day 天的留存率
    
    存量用户从模拟第 1 天开始按 γ 衰减
    
    Args:
        day: 模拟天数（0 = 模拟第1天, 1 = 模拟第2天, ...）
        gamma: 日衰减率
        
    Returns:
        活跃率（0-1 之间）
    """
    if day < 0:
        return 1.0
    
    retention = np.power(gamma, day)
    return float(np.clip(retention, 0.0, 1.0))


def generate_retention_curve(
    alpha: float, beta: float, gamma: float, max_day: int = 180
) -> Dict[int, float]:
    """
    生成完整的留存率曲线
    
    Args:
        alpha, beta, gamma: 拟合参数
        max_day: 最大天数
        
    Returns:
        {day: retention} 字典
    """
    curve = {}
    for day in range(1, max_day + 1):
        curve[day] = calc_retention_new(day, alpha, beta, gamma)
    return curve


def get_fitted_key_retentions(alpha: float, beta: float, gamma: float) -> Dict[str, float]:
    """
    获取关键节点的拟合留存率值
    
    Returns:
        包含 day1, day7, day30, day60 等关键节点的字典
    """
    return {
        "day1": calc_retention_new(1, alpha, beta, gamma),
        "day2": calc_retention_new(2, alpha, beta, gamma),
        "day3": calc_retention_new(3, alpha, beta, gamma),
        "day7": calc_retention_new(7, alpha, beta, gamma),
        "day14": calc_retention_new(14, alpha, beta, gamma),
        "day30": calc_retention_new(30, alpha, beta, gamma),
        "day60": calc_retention_new(60, alpha, beta, gamma),
        "day90": calc_retention_new(90, alpha, beta, gamma),
        "day120": calc_retention_new(120, alpha, beta, gamma),
        "day180": calc_retention_new(180, alpha, beta, gamma),
    }
