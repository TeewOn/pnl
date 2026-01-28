"""
FastAPI 路由定义
"""

import io
import csv
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..models.config import SimulationConfig
from ..models.results import SimulationResult, ValidationResult
from ..core.simulator import run_simulation
from ..utils.validation import validate_config

router = APIRouter()


@router.post("/simulate", response_model=SimulationResult)
async def simulate(config: SimulationConfig) -> SimulationResult:
    """
    运行 P&L 模拟
    
    Args:
        config: 模拟配置
        
    Returns:
        SimulationResult 对象
    """
    try:
        # 先校验配置
        validation = validate_config(config)
        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "配置校验失败",
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                }
            )
        
        # 运行模拟
        result = run_simulation(config)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": f"模拟执行失败: {str(e)}"}
        )


@router.post("/validate", response_model=ValidationResult)
async def validate(config: SimulationConfig) -> ValidationResult:
    """
    校验模拟配置
    
    仅校验配置有效性，不执行计算
    
    Returns:
        ValidationResult 对象
    """
    return validate_config(config)


@router.post("/export")
async def export_data(
    config: SimulationConfig,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
):
    """
    导出模拟数据
    
    Args:
        config: 模拟配置
        format: 导出格式 (csv/json)
        
    Returns:
        文件下载
    """
    try:
        # 运行模拟
        result = run_simulation(config)
        
        if format == "json":
            # JSON 格式
            return result.model_dump()
        
        else:
            # CSV 格式
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow([
                "Day", "Date", "DAU", "DNU_Organic", "DNU_Paid",
                "Revenue", "Cost", "Profit", "Cumulative_Profit"
            ])
            
            # 写入数据
            cumulative_profit = 0.0
            for i, day in enumerate(result.timeseries.days):
                profit = result.timeseries.totals.profit[i]
                cumulative_profit += profit
                writer.writerow([
                    day,
                    result.timeseries.dates[i],
                    result.timeseries.totals.dau[i],
                    result.timeseries.totals.dnu_organic[i],
                    result.timeseries.totals.dnu_paid[i],
                    round(result.timeseries.totals.revenue[i], 2),
                    round(result.timeseries.totals.cost[i], 2),
                    round(profit, 2),
                    round(cumulative_profit, 2),
                ])
            
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=pl_simulation.csv"
                }
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": f"导出失败: {str(e)}"}
        )


@router.get("/default-config", response_model=SimulationConfig)
async def get_default_config() -> SimulationConfig:
    """
    获取默认配置
    
    Returns:
        默认的 SimulationConfig
    """
    return SimulationConfig()


@router.get("/regions")
async def get_regions():
    """
    获取支持的地区列表
    """
    return {
        "regions": [
            {"code": "JP", "name": "日本"},
            {"code": "US", "name": "美国"},
            {"code": "EMEA", "name": "英语T1+西欧"},
            {"code": "LATAM", "name": "拉美"},
            {"code": "CN", "name": "港澳台"},
            {"code": "OTHER", "name": "其他"},
        ]
    }
