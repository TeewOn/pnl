"""
主模拟器模块

按天循环执行：预算计算 -> DNU 计算 -> DAU 计算 -> 财务计算
"""

import time
import hashlib
import json
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from ..models.config import SimulationConfig, RetentionConfig
from ..models.results import (
    SimulationResult,
    Summary,
    FinalMetrics,
    CumulativeMetrics,
    Milestones,
    Timeseries,
    RegionTimeseries,
    RetentionCurve,
    DailyMetrics,
)
from .retention import fit_retention_params, get_fitted_key_retentions
from .dau import DAUCalculator


class RegionSimulator:
    """单地区模拟器"""
    
    def __init__(
        self,
        region: str,
        initial_dau: int,
        retention_config: RetentionConfig,
    ):
        self.region = region
        self.initial_dau = initial_dau
        
        # 拟合留存率参数
        retention = retention_config.to_dict()
        self.alpha, self.beta, self.gamma = fit_retention_params(
            retention[1], retention[2], retention[3],
            retention[7], retention[14], retention[30], retention[60]
        )
        
        # 初始化 DAU 计算器
        self.dau_calculator = DAUCalculator(
            initial_dau=initial_dau,
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
        )
        
        # 状态跟踪
        self.prev_dau = initial_dau
        self.dnu_history: List[int] = []
    
    def simulate_day(
        self,
        day: int,
        budget: float,
        cpi: float,
        organic_growth_rate: float,
        arpu_iap: float,
        arpu_ad: float,
        unit_cost_operational: float,
    ) -> DailyMetrics:
        """
        模拟单天
        
        Returns:
            DailyMetrics 对象
        """
        # 1. 计算 DNU
        dnu_paid = int(budget / cpi) if cpi > 0 else 0
        
        # 自然量增长：基于前一日DAU，但需要限制增长幅度，防止指数爆炸
        # 限制：自然量增长系数不应超过2%（0.02），且每天自然量增长不应超过前一日DAU的2%
        safe_organic_rate = min(organic_growth_rate, 0.02)  # 上限2%
        dnu_organic = int(self.prev_dau * safe_organic_rate)
        
        # 额外安全限制：如果自然量增长超过前一日DAU的2%，则限制为2%
        max_organic_dnu = int(self.prev_dau * 0.02)
        dnu_organic = min(dnu_organic, max_organic_dnu)
        
        dnu_total = dnu_organic + dnu_paid
        
        # 2. 计算 DAU
        dau, _, _ = self.dau_calculator.calculate_dau(dnu_total)
        
        # 3. 计算财务指标
        revenue_iap = dau * arpu_iap
        revenue_ad = dau * arpu_ad
        revenue_total = revenue_iap + revenue_ad
        
        cost_marketing = budget
        cost_operational = dau * unit_cost_operational
        
        gross_profit = revenue_total - (cost_marketing + cost_operational)
        
        # 4. 更新状态
        self.prev_dau = dau
        self.dnu_history.append(dnu_total)
        
        return DailyMetrics(
            day=day,
            date="",  # 由外层填充
            region=self.region,
            dau=dau,
            dnu_organic=dnu_organic,
            dnu_paid=dnu_paid,
            dnu_total=dnu_total,
            revenue_iap=revenue_iap,
            revenue_ad=revenue_ad,
            revenue_total=revenue_total,
            cost_marketing=cost_marketing,
            cost_operational=cost_operational,
            gross_profit=gross_profit,
        )
    
    def get_retention_curve(self) -> RetentionCurve:
        """获取留存率曲线"""
        return RetentionCurve(
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            fitted_values=get_fitted_key_retentions(self.alpha, self.beta, self.gamma),
        )


def run_simulation(config: SimulationConfig) -> SimulationResult:
    """
    运行模拟
    
    Args:
        config: 模拟配置
        
    Returns:
        SimulationResult 对象
    """
    start_time = time.time()
    
    # 获取活跃地区
    active_regions = config.get_active_regions()
    
    # 确定开始日期
    start_date = config.start_date or date.today()
    
    # 初始化各地区模拟器
    region_simulators: Dict[str, RegionSimulator] = {}
    for region in active_regions:
        initial_dau = config.get_initial_dau(region)
        retention_config = config.get_retention(start_date.month, region)
        region_simulators[region] = RegionSimulator(
            region=region,
            initial_dau=initial_dau,
            retention_config=retention_config,
        )
    
    # 存储每日指标
    all_daily_metrics: List[DailyMetrics] = []
    
    # 初始化累计指标
    cumulative = {
        "revenue_iap": 0.0,
        "revenue_ad": 0.0,
        "cost_marketing": 0.0,
        "cost_operational": 0.0,
        "cost_fixed": 0.0,
    }
    
    # 初始化时序数据
    dates_list: List[str] = []
    days_list: List[int] = []
    
    totals_dau: List[int] = []
    totals_dnu_organic: List[int] = []
    totals_dnu_paid: List[int] = []
    totals_revenue: List[float] = []
    totals_cost: List[float] = []
    totals_profit: List[float] = []
    
    region_timeseries: Dict[str, Dict[str, List]] = {
        region: {
            "dau": [], "dnu_organic": [], "dnu_paid": [],
            "revenue": [], "cost": [], "profit": []
        }
        for region in active_regions
    }
    
    # 里程碑跟踪
    cumulative_profit = 0.0
    break_even_day: Optional[int] = None
    first_profitable_day: Optional[int] = None
    peak_dau = 0
    peak_dau_day = 0
    
    # 前一日税后收入（用于预算计算）
    prev_revenue_after_tax = sum(
        config.get_initial_dau(r) * (
            config.get_param("arpu_iap", start_date.month, r) * 0.7 +
            config.get_param("arpu_ad", start_date.month, r) * 1.0
        )
        for r in active_regions
    )
    
    # 按天模拟
    for day in range(config.simulation_days):
        current_date = start_date + timedelta(days=day)
        month = current_date.month
        date_str = current_date.isoformat()
        
        dates_list.append(date_str)
        days_list.append(day + 1)
        
        # 1. 计算当日总预算
        additional_budget = config.budget.additional_by_month.get(str(month), 0)
        base_ratio = config.budget.get_base_ratio(month)  # 支持按月配置
        total_budget = (prev_revenue_after_tax * base_ratio) + additional_budget
        
        # 2. 各地区模拟
        day_total_dau = 0
        day_total_dnu_organic = 0
        day_total_dnu_paid = 0
        day_total_revenue = 0.0
        day_total_cost = 0.0
        day_total_profit = 0.0
        
        # 获取当月的地区预算分配
        region_distribution = config.budget.get_region_distribution(month)
        
        for region in active_regions:
            # 预算分配
            region_budget = total_budget * region_distribution.get(region, 0)
            
            # 获取地区参数
            cpi = config.get_param("cpi", month, region)
            organic_rate = config.get_param("organic_growth_rate", month, region)
            arpu_iap = config.get_param("arpu_iap", month, region)
            arpu_ad = config.get_param("arpu_ad", month, region)
            unit_cost_operational = config.get_param("unit_cost_operational", month, region)
            
            # 执行模拟
            metrics = region_simulators[region].simulate_day(
                day=day + 1,
                budget=region_budget,
                cpi=cpi,
                organic_growth_rate=organic_rate,
                arpu_iap=arpu_iap,
                arpu_ad=arpu_ad,
                unit_cost_operational=unit_cost_operational,
            )
            metrics.date = date_str
            all_daily_metrics.append(metrics)
            
            # 汇总当日指标
            day_total_dau += metrics.dau
            day_total_dnu_organic += metrics.dnu_organic
            day_total_dnu_paid += metrics.dnu_paid
            day_total_revenue += metrics.revenue_total
            day_total_cost += metrics.cost_marketing + metrics.cost_operational
            
            # 更新地区时序
            region_timeseries[region]["dau"].append(metrics.dau)
            region_timeseries[region]["dnu_organic"].append(metrics.dnu_organic)
            region_timeseries[region]["dnu_paid"].append(metrics.dnu_paid)
            region_timeseries[region]["revenue"].append(metrics.revenue_total)
            region_timeseries[region]["cost"].append(
                metrics.cost_marketing + metrics.cost_operational
            )
            region_timeseries[region]["profit"].append(metrics.gross_profit)
            
            # 更新累计指标
            cumulative["revenue_iap"] += metrics.revenue_iap
            cumulative["revenue_ad"] += metrics.revenue_ad
            cumulative["cost_marketing"] += metrics.cost_marketing
            cumulative["cost_operational"] += metrics.cost_operational
        
        # 3. 固定成本
        day_total_cost += config.global_fixed_cost
        cumulative["cost_fixed"] += config.global_fixed_cost
        
        # 4. 计算当日利润
        day_total_profit = day_total_revenue - day_total_cost
        cumulative_profit += day_total_profit
        
        # 5. 更新时序数据
        totals_dau.append(day_total_dau)
        totals_dnu_organic.append(day_total_dnu_organic)
        totals_dnu_paid.append(day_total_dnu_paid)
        totals_revenue.append(day_total_revenue)
        totals_cost.append(day_total_cost)
        totals_profit.append(day_total_profit)
        
        # 6. 检查里程碑
        if day_total_profit > 0 and first_profitable_day is None:
            first_profitable_day = day + 1
        
        if cumulative_profit >= 0 and break_even_day is None:
            break_even_day = day + 1
        
        if day_total_dau > peak_dau:
            peak_dau = day_total_dau
            peak_dau_day = day + 1
        
        # 7. 更新前一日税后收入（用于下一天的预算计算）
        prev_revenue_after_tax = sum(
            region_simulators[r].prev_dau * (
                config.get_param("arpu_iap", month, r) * 0.7 +
                config.get_param("arpu_ad", month, r) * 1.0
            )
            for r in active_regions
        )
    
    # 计算执行时间
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    # 计算最终指标
    total_revenue = cumulative["revenue_iap"] + cumulative["revenue_ad"]
    total_cost = (
        cumulative["cost_marketing"] +
        cumulative["cost_operational"] +
        cumulative["cost_fixed"]
    )
    net_profit = total_revenue - total_cost
    # ROI = 收入/成本（不是净利润/成本），这样 ROI >= 1 表示盈利，ROI < 1 表示亏损
    roi = total_revenue / total_cost if total_cost > 0 else 0
    
    initial_total_dau = sum(config.get_initial_dau(r) for r in active_regions)
    final_dau = totals_dau[-1] if totals_dau else 0
    dau_growth_rate = (final_dau - initial_total_dau) / initial_total_dau * 100 if initial_total_dau > 0 else 0
    
    # 构建结果（为了向后兼容，保留 cost_api 和 cost_machine，但都设置为 cost_operational）
    cost_operational_value = cumulative["cost_operational"]
    result = SimulationResult(
        status="success",
        execution_time_ms=execution_time_ms,
        config_hash=hashlib.md5(config.model_dump_json().encode()).hexdigest()[:8],
        summary=Summary(
            simulation_days=config.simulation_days,
            active_regions=active_regions,
            final_metrics=FinalMetrics(
                total_dau=final_dau,
                dau_by_region={
                    r: region_timeseries[r]["dau"][-1] if region_timeseries[r]["dau"] else 0
                    for r in active_regions
                },
                dau_growth_rate=dau_growth_rate,
            ),
            cumulative_metrics=CumulativeMetrics(
                total_revenue=total_revenue,
                revenue_iap=cumulative["revenue_iap"],
                revenue_ad=cumulative["revenue_ad"],
                total_cost=total_cost,
                cost_marketing=cumulative["cost_marketing"],
                cost_api=cost_operational_value,  # 向后兼容
                cost_machine=0.0,  # 向后兼容，设为0
                cost_fixed=cumulative["cost_fixed"],
                net_profit=net_profit,
                roi=roi,
            ),
            milestones=Milestones(
                break_even_day=break_even_day,
                first_profitable_day=first_profitable_day,
                peak_dau_day=peak_dau_day,
                peak_dau_value=peak_dau,
            ),
        ),
        timeseries=Timeseries(
            dates=dates_list,
            days=days_list,
            totals=RegionTimeseries(
                dau=totals_dau,
                dnu_organic=totals_dnu_organic,
                dnu_paid=totals_dnu_paid,
                revenue=totals_revenue,
                cost=totals_cost,
                profit=totals_profit,
            ),
            by_region={
                region: RegionTimeseries(
                    dau=region_timeseries[region]["dau"],
                    dnu_organic=region_timeseries[region]["dnu_organic"],
                    dnu_paid=region_timeseries[region]["dnu_paid"],
                    revenue=region_timeseries[region]["revenue"],
                    cost=region_timeseries[region]["cost"],
                    profit=region_timeseries[region]["profit"],
                )
                for region in active_regions
            } if config.output_options.include_region_breakdown else None,
        ),
        retention_curves={
            region: region_simulators[region].get_retention_curve()
            for region in active_regions
        },
    )
    
    return result
