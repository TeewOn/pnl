"""
DAU 计算模块

DAU 滚动预测公式：
DAU_t = DNU_total,t + Σ(DNU_total,t-i × R_new(i)) + (DAU_initial × R_active(t))

其中：
- DNU_total,t: 第 t 天的新增用户
- R_new(i): 新用户第 i 天的留存率
- R_active(t): 初始存量用户在第 t 天的活跃率
"""

from typing import List, Tuple
import numpy as np

from .retention import calc_retention_new, calc_retention_active


class DAUCalculator:
    """
    DAU 计算器
    
    维护历史 DNU 记录，用于计算每日的活跃用户数
    """
    
    def __init__(
        self,
        initial_dau: int,
        alpha: float,
        beta: float,
        gamma: float,
        retention_window: int = 180,  # 留存率计算窗口（用于性能优化，但保留所有历史数据）
    ):
        """
        初始化 DAU 计算器
        
        Args:
            initial_dau: 初始活跃用户数
            alpha, beta, gamma: 留存率拟合参数
            retention_window: 留存率预计算窗口（天数，用于性能优化）
        """
        self.initial_dau = initial_dau
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.retention_window = retention_window
        
        # 历史 DNU 列表（保留所有历史数据，不限制长度）
        # 修复：不使用固定长度的deque，避免超过180天后丢失数据导致DAU突然下降
        self.dnu_history: List[int] = []
        
        # 当前模拟天数（从 0 开始）
        self.current_day = 0
        
        # 预计算留存率表（提升性能）
        self._retention_cache = {}
        self._precompute_retentions()
    
    def _precompute_retentions(self):
        """预计算留存率表"""
        for day in range(1, self.retention_window + 1):
            self._retention_cache[day] = calc_retention_new(
                day, self.alpha, self.beta, self.gamma
            )
    
    def _get_retention(self, days_since_acquisition: int) -> float:
        """获取留存率（使用缓存）"""
        if days_since_acquisition <= 0:
            return 1.0
        if days_since_acquisition in self._retention_cache:
            return self._retention_cache[days_since_acquisition]
        return calc_retention_new(
            days_since_acquisition, self.alpha, self.beta, self.gamma
        )
    
    def calculate_dau(self, dnu_today: int) -> Tuple[int, int, int]:
        """
        计算当日 DAU
        
        Args:
            dnu_today: 今日新增用户数（organic + paid）
            
        Returns:
            (total_dau, dau_from_new, dau_from_initial)
            - total_dau: 总 DAU
            - dau_from_new: 来自新用户的 DAU
            - dau_from_initial: 来自初始用户的 DAU
        """
        # 1. 今日新增用户（第 0 天留存率 = 100%）
        dau_from_today = dnu_today
        
        # 2. 历史新增用户的贡献
        # 遍历所有历史DNU，计算它们的留存贡献
        # 注意：即使超过retention_window天，也要考虑这些用户的贡献（虽然留存率很低）
        dau_from_history = 0
        for i, historical_dnu in enumerate(reversed(self.dnu_history)):
            days_ago = i + 1  # 1 天前、2 天前、...
            # 对于超过retention_window天的用户，仍然计算留存率（虽然很低）
            retention = self._get_retention(days_ago)
            dau_from_history += int(historical_dnu * retention)
        
        # 3. 初始存量用户的贡献
        initial_retention = calc_retention_active(self.current_day, self.gamma)
        dau_from_initial = int(self.initial_dau * initial_retention)
        
        # 4. 更新状态
        self.dnu_history.append(dnu_today)
        self.current_day += 1
        
        # 5. 汇总
        dau_from_new = dau_from_today + dau_from_history
        total_dau = dau_from_new + dau_from_initial
        
        return total_dau, dau_from_new, dau_from_initial
    
    def reset(self):
        """重置计算器状态"""
        self.dnu_history.clear()
        self.current_day = 0


def calculate_dau(
    dnu_today: int,
    dnu_history: List[int],
    alpha: float,
    beta: float,
    gamma: float,
    initial_dau: int,
    current_day: int,
) -> int:
    """
    计算当日 DAU（函数式接口）
    
    DAU_t = DNU_today + Σ(DNU_t-i × R_new(i)) + (DAU_initial × R_active(t))
    
    Args:
        dnu_today: 今日新增用户
        dnu_history: 历史新增用户列表（按时间顺序，最早的在前）
        alpha, beta, gamma: 留存率参数
        initial_dau: 初始活跃用户数
        current_day: 当前模拟天数（从 0 开始）
        
    Returns:
        当日 DAU
    """
    # 1. 今日新增用户
    dau = dnu_today
    
    # 2. 历史新增用户贡献
    for i, historical_dnu in enumerate(reversed(dnu_history)):
        days_ago = i + 1
        retention = calc_retention_new(days_ago, alpha, beta, gamma)
        dau += int(historical_dnu * retention)
    
    # 3. 初始存量用户贡献
    initial_retention = calc_retention_active(current_day, gamma)
    dau += int(initial_dau * initial_retention)
    
    return dau
