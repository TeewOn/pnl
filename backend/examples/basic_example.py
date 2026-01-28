"""
基础示例脚本

演示如何使用 P&L 模型进行模拟
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.config import SimulationConfig
from src.core.simulator import run_simulation
from src.utils.validation import validate_config


def main():
    # 1. 从 JSON 文件加载配置
    config_path = Path(__file__).parent / "sample_config.json"
    with open(config_path, "r") as f:
        config_dict = json.load(f)
    
    config = SimulationConfig(**config_dict)
    print("=" * 60)
    print("P&L 模拟器示例")
    print("=" * 60)
    
    # 2. 校验配置
    print("\n[1] 配置校验...")
    validation = validate_config(config)
    print(f"    有效: {validation.valid}")
    if validation.warnings:
        print(f"    警告: {validation.warnings}")
    if validation.errors:
        print(f"    错误: {validation.errors}")
        return
    
    # 3. 运行模拟
    print("\n[2] 运行模拟...")
    print(f"    模拟天数: {config.simulation_days}")
    print(f"    活跃地区: {config.get_active_regions()}")
    
    result = run_simulation(config)
    
    # 4. 输出结果
    print(f"\n[3] 模拟结果 (耗时 {result.execution_time_ms}ms)")
    print("-" * 60)
    
    summary = result.summary
    final = summary.final_metrics
    cumulative = summary.cumulative_metrics
    milestones = summary.milestones
    
    print(f"\n📊 最终指标:")
    print(f"    总 DAU: {final.total_dau:,}")
    print(f"    DAU 增长率: {final.dau_growth_rate:.1f}%")
    print(f"    各地区 DAU: {final.dau_by_region}")
    
    print(f"\n💰 累计财务指标:")
    print(f"    总收入: ${cumulative.total_revenue:,.2f}")
    print(f"      - IAP 收入: ${cumulative.revenue_iap:,.2f}")
    print(f"      - 广告收入: ${cumulative.revenue_ad:,.2f}")
    print(f"    总成本: ${cumulative.total_cost:,.2f}")
    print(f"      - 营销成本: ${cumulative.cost_marketing:,.2f}")
    print(f"      - API 成本: ${cumulative.cost_api:,.2f}")
    print(f"      - 机器成本: ${cumulative.cost_machine:,.2f}")
    print(f"      - 固定成本: ${cumulative.cost_fixed:,.2f}")
    print(f"    净利润: ${cumulative.net_profit:,.2f}")
    print(f"    ROI: {cumulative.roi*100:.2f}%")
    
    print(f"\n🏆 里程碑:")
    print(f"    盈亏平衡日: Day {milestones.break_even_day or 'N/A'}")
    print(f"    首次盈利日: Day {milestones.first_profitable_day or 'N/A'}")
    print(f"    DAU 峰值: {milestones.peak_dau_value:,} (Day {milestones.peak_dau_day})")
    
    print(f"\n📈 留存率拟合参数 (JP):")
    jp_curve = result.retention_curves.get("JP")
    if jp_curve:
        print(f"    α (alpha): {jp_curve.alpha:.4f}")
        print(f"    β (beta): {jp_curve.beta:.4f}")
        print(f"    γ (gamma): {jp_curve.gamma:.4f}")
        print(f"    拟合 Day7: {jp_curve.fitted_values.get('day7', 0)*100:.1f}%")
        print(f"    拟合 Day30: {jp_curve.fitted_values.get('day30', 0)*100:.1f}%")
    
    print("\n" + "=" * 60)
    print("模拟完成!")


if __name__ == "__main__":
    main()
