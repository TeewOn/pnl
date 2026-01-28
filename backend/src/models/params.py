"""
时空参数类 - 支持按月份和地区的三层覆盖逻辑

参数查询优先级: 月份+地区 > 地区 > 月份 > 全局缺省值
"""

from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field


class TimeRegionParam:
    """
    支持时空维度的参数类
    
    三层覆盖结构：
    1. default: 全局默认值
    2. by_region: 按地区覆盖
    3. by_month_region: 按月份+地区覆盖（优先级最高）
    """
    
    def __init__(
        self,
        default: float,
        by_region: Optional[Dict[str, float]] = None,
        by_month_region: Optional[Dict[Tuple[int, str], float]] = None,
    ):
        self.default = default
        self.by_region = by_region or {}
        self.by_month_region = by_month_region or {}
    
    def get(self, month: int, region: str) -> float:
        """
        获取指定月份和地区的参数值
        
        优先级: 月份+地区 > 地区 > 全局缺省值
        """
        # 最高优先级：月份+地区组合
        if (month, region) in self.by_month_region:
            return self.by_month_region[(month, region)]
        
        # 次优先级：地区
        if region in self.by_region:
            return self.by_region[region]
        
        # 默认值
        return self.default
    
    @classmethod
    def from_config(
        cls,
        default: float,
        regions: Optional[Dict[str, float]] = None,
        monthly_overrides: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> "TimeRegionParam":
        """
        从配置创建 TimeRegionParam
        
        Args:
            default: 全局默认值
            regions: 地区覆盖，如 {"JP": 3.5, "US": 2.8}
            monthly_overrides: 月份覆盖，如 {"2025-01": {"JP": 4.0}}
        """
        by_region = regions or {}
        by_month_region = {}
        
        if monthly_overrides:
            for month_str, region_values in monthly_overrides.items():
                # 解析月份字符串，如 "2025-01" -> 1
                month = int(month_str.split("-")[1]) if "-" in month_str else int(month_str)
                for region, value in region_values.items():
                    by_month_region[(month, region)] = value
        
        return cls(default=default, by_region=by_region, by_month_region=by_month_region)


# 地区枚举
REGIONS = ["JP", "US", "EMEA", "LATAM", "CN", "OTHER"]
