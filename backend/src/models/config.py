"""
API 输入配置模型

采用"全局默认值 + 地区覆盖 + 月份覆盖"的三层结构
"""

from typing import Dict, List, Optional
from datetime import date
from pydantic import BaseModel, Field, field_validator


class RetentionConfig(BaseModel):
    """留存率配置 - 7 个关键节点"""
    day1: float = Field(ge=0, le=1, default=0.3103, description="次日留存率")
    day2: float = Field(ge=0, le=1, default=0.4144, description="2日留存率")
    day3: float = Field(ge=0, le=1, default=0.3369, description="3日留存率")
    day7: float = Field(ge=0, le=1, default=0.2221, description="7日留存率")
    day14: float = Field(ge=0, le=1, default=0.1538, description="14日留存率")
    day30: float = Field(ge=0, le=1, default=0.0915, description="30日留存率")
    day60: float = Field(ge=0, le=1, default=0.0755, description="60日留存率")
    
    def to_list(self) -> List[float]:
        """返回留存率列表"""
        return [self.day1, self.day2, self.day3, self.day7, self.day14, self.day30, self.day60]
    
    def to_dict(self) -> Dict[int, float]:
        """返回留存率字典 {day: retention}"""
        return {
            1: self.day1,
            2: self.day2,
            3: self.day3,
            7: self.day7,
            14: self.day14,
            30: self.day30,
            60: self.day60,
        }


class BudgetConfig(BaseModel):
    """预算策略配置"""
    base_ratio: float = Field(ge=0, default=1.0, description="基准预算比例（占前日税后收入）- 默认值")
    base_ratio_by_month: Dict[str, float] = Field(default_factory=dict, description="按月基准预算比例覆盖")
    additional_by_month: Dict[str, float] = Field(default_factory=dict, description="额外投放预算（按月）")
    region_distribution: Dict[str, float] = Field(
        default_factory=lambda: {"JP": 0.25, "US": 0.25, "EMEA": 0.2, "LATAM": 0.1, "CN": 0.1, "OTHER": 0.1},
        description="各地区预算分配比例 - 默认值"
    )
    region_distribution_by_month: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="按月地区预算分配比例覆盖，如 {'1': {'JP': 0.3, 'US': 0.2, ...}}"
    )
    
    @field_validator("region_distribution")
    @classmethod
    def validate_distribution(cls, v: Dict[str, float]) -> Dict[str, float]:
        """校验地区分配比例之和为 100%"""
        total = sum(v.values())
        if not (0.999 <= total <= 1.001):
            raise ValueError(f"地区分配比例之和必须为 100%，当前为 {total*100:.2f}%")
        return v
    
    @field_validator("region_distribution_by_month")
    @classmethod
    def validate_monthly_distribution(cls, v: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """校验按月地区分配比例之和"""
        for month, dist in v.items():
            total = sum(dist.values())
            if not (0.999 <= total <= 1.001):
                raise ValueError(f"{month}月地区分配比例之和必须为 100%，当前为 {total*100:.2f}%")
        return v
    
    def get_base_ratio(self, month: int) -> float:
        """获取指定月份的基准预算比例"""
        month_key = str(month)
        return self.base_ratio_by_month.get(month_key, self.base_ratio)
    
    def get_region_distribution(self, month: int) -> Dict[str, float]:
        """获取指定月份的地区预算分配比例"""
        month_key = str(month)
        return self.region_distribution_by_month.get(month_key, self.region_distribution)


class DefaultParams(BaseModel):
    """全局默认参数"""
    initial_dau: int = Field(ge=0, default=300000, description="初始 DAU")
    cpi: float = Field(gt=0, default=1.1, description="CPI（用户获取成本）")
    arpu_iap: float = Field(ge=0, default=0.06, description="IAP ARPU")
    arpu_ad: float = Field(ge=0, default=0.0015, description="广告 ARPU")
    unit_cost_operational: float = Field(ge=0, default=0.01901, description="单位运营成本（API + 机器成本，每DAU每天）")
    organic_growth_rate: float = Field(ge=0, le=1, default=0.01, description="自然量增长系数")
    retention: RetentionConfig = Field(default_factory=RetentionConfig, description="留存率配置")


class RegionOverride(BaseModel):
    """地区参数覆盖"""
    initial_dau: Optional[int] = Field(default=None, ge=0)
    cpi: Optional[float] = Field(default=None, gt=0)
    arpu_iap: Optional[float] = Field(default=None, ge=0)
    arpu_ad: Optional[float] = Field(default=None, ge=0)
    organic_growth_rate: Optional[float] = Field(default=None, ge=0, le=1)
    retention: Optional[Dict[str, float]] = Field(default=None, description="部分覆盖留存率，如 {'day1': 0.55}")


class OutputOptions(BaseModel):
    """输出选项"""
    include_daily_details: bool = Field(default=True, description="是否包含每日明细")
    include_region_breakdown: bool = Field(default=True, description="是否包含地区细分")
    aggregate_by: str = Field(default="day", pattern="^(day|week|month)$", description="聚合粒度")


class SimulationConfig(BaseModel):
    """模拟配置 - API 输入主结构"""
    simulation_days: int = Field(ge=1, le=730, default=180, description="模拟天数")
    start_date: Optional[date] = Field(default=None, description="模拟开始日期")
    
    budget: BudgetConfig = Field(default_factory=BudgetConfig, description="预算策略")
    defaults: DefaultParams = Field(default_factory=DefaultParams, description="全局默认参数")
    regions: Dict[str, RegionOverride] = Field(default_factory=dict, description="地区参数覆盖")
    monthly_overrides: Dict[str, Dict[str, RegionOverride]] = Field(
        default_factory=dict, 
        description="月份参数覆盖，如 {'2025-01': {'JP': {...}}}"
    )
    
    global_fixed_cost: float = Field(ge=0, default=0.0, description="每日额外投放支出")
    output_options: OutputOptions = Field(default_factory=OutputOptions, description="输出选项")
    
    def get_active_regions(self) -> List[str]:
        """获取活跃地区列表（预算分配比例大于 0 的地区）"""
        return [r for r, ratio in self.budget.region_distribution.items() if ratio > 0]
    
    def get_param(self, param_name: str, month: int, region: str) -> float:
        """
        获取指定参数值，支持三层覆盖
        
        优先级: 月份+地区 > 地区 > 全局默认值
        """
        # 检查月份+地区覆盖
        month_key = f"{month:02d}" if isinstance(month, int) else str(month)
        if month_key in self.monthly_overrides and region in self.monthly_overrides[month_key]:
            region_override = self.monthly_overrides[month_key][region]
            value = getattr(region_override, param_name, None)
            if value is not None:
                return value
        
        # 检查地区覆盖
        if region in self.regions:
            value = getattr(self.regions[region], param_name, None)
            if value is not None:
                return value
        
        # 返回全局默认值
        return getattr(self.defaults, param_name)
    
    def get_retention(self, month: int, region: str) -> RetentionConfig:
        """获取指定月份和地区的留存率配置"""
        base_retention = self.defaults.retention.model_copy()
        
        # 应用地区覆盖
        if region in self.regions and self.regions[region].retention:
            for key, value in self.regions[region].retention.items():
                setattr(base_retention, key, value)
        
        # 应用月份+地区覆盖
        month_key = f"{month:02d}" if isinstance(month, int) else str(month)
        if month_key in self.monthly_overrides and region in self.monthly_overrides[month_key]:
            region_override = self.monthly_overrides[month_key][region]
            if region_override.retention:
                for key, value in region_override.retention.items():
                    setattr(base_retention, key, value)
        
        return base_retention
    
    def get_initial_dau(self, region: str) -> int:
        """
        获取指定地区的初始 DAU
        
        如果没有地区覆盖，则按比例分配全局默认值：
        - JP: 20%
        - US: 20%
        - EMEA, LATAM, CN, OTHER: 各 15%
        """
        if region in self.regions and self.regions[region].initial_dau is not None:
            return self.regions[region].initial_dau
        
        # 按比例分配全局默认值
        distribution = {
            "JP": 0.20,
            "US": 0.20,
            "EMEA": 0.15,
            "LATAM": 0.15,
            "CN": 0.15,
            "OTHER": 0.15,
        }
        ratio = distribution.get(region, 0.15)
        return int(self.defaults.initial_dau * ratio)
