"""
API 输出结果模型
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class FinalMetrics(BaseModel):
    """最终指标"""
    total_dau: int = Field(description="总 DAU")
    dau_by_region: Dict[str, int] = Field(description="各地区 DAU")
    dau_growth_rate: float = Field(description="DAU 增长率（相对初始值）")


class CumulativeMetrics(BaseModel):
    """累计指标"""
    total_revenue: float = Field(description="总收入")
    revenue_iap: float = Field(description="IAP 收入")
    revenue_ad: float = Field(description="广告收入")
    total_cost: float = Field(description="总成本")
    cost_marketing: float = Field(description="营销成本")
    cost_api: float = Field(description="API 成本（已合并到运营成本，保留用于向后兼容）")
    cost_machine: float = Field(description="机器成本（已合并到运营成本，保留用于向后兼容）")
    cost_fixed: float = Field(description="固定成本")
    net_profit: float = Field(description="净利润")
    roi: float = Field(description="投资回报率")


class Milestones(BaseModel):
    """里程碑"""
    break_even_day: Optional[int] = Field(default=None, description="盈亏平衡日")
    first_profitable_day: Optional[int] = Field(default=None, description="首次盈利日")
    peak_dau_day: int = Field(description="DAU 峰值日")
    peak_dau_value: int = Field(description="DAU 峰值")


class Summary(BaseModel):
    """汇总信息"""
    simulation_days: int = Field(description="模拟天数")
    active_regions: List[str] = Field(description="活跃地区")
    final_metrics: FinalMetrics = Field(description="最终指标")
    cumulative_metrics: CumulativeMetrics = Field(description="累计指标")
    milestones: Milestones = Field(description="里程碑")


class RegionTimeseries(BaseModel):
    """单地区时序数据"""
    dau: List[int] = Field(description="每日 DAU")
    dnu_organic: List[int] = Field(description="每日自然新增")
    dnu_paid: List[int] = Field(description="每日付费新增")
    revenue: List[float] = Field(description="每日收入")
    cost: List[float] = Field(description="每日成本")
    profit: List[float] = Field(description="每日利润")


class Timeseries(BaseModel):
    """时序数据"""
    dates: List[str] = Field(description="日期列表")
    days: List[int] = Field(description="天数列表")
    
    # 汇总时序
    totals: RegionTimeseries = Field(description="汇总数据")
    
    # 分地区时序（可选）
    by_region: Optional[Dict[str, RegionTimeseries]] = Field(default=None, description="分地区数据")


class RetentionCurve(BaseModel):
    """留存率曲线"""
    alpha: float = Field(description="幂函数参数 α")
    beta: float = Field(description="幂函数参数 β")
    gamma: float = Field(description="指数衰减率 γ")
    fitted_values: Dict[str, float] = Field(description="拟合后的留存率值")


class SimulationResult(BaseModel):
    """模拟结果 - API 输出主结构"""
    status: str = Field(default="success", description="状态")
    execution_time_ms: int = Field(description="执行时间（毫秒）")
    config_hash: Optional[str] = Field(default=None, description="配置哈希值")
    
    summary: Summary = Field(description="汇总信息")
    timeseries: Timeseries = Field(description="时序数据")
    retention_curves: Dict[str, RetentionCurve] = Field(description="各地区留存率曲线")


class ValidationResult(BaseModel):
    """参数校验结果"""
    valid: bool = Field(description="是否有效")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")


class DailyMetrics(BaseModel):
    """每日指标（用于内部计算）"""
    day: int
    date: str
    region: str
    dau: int
    dnu_organic: int
    dnu_paid: int
    dnu_total: int
    revenue_iap: float
    revenue_ad: float
    revenue_total: float
    cost_marketing: float
    cost_operational: float
    gross_profit: float
