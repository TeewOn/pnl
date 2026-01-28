"""
主模拟器测试
"""

import pytest
from src.models.config import SimulationConfig, BudgetConfig, DefaultParams, RetentionConfig
from src.core.simulator import run_simulation


class TestSimulator:
    """模拟器测试"""
    
    @pytest.fixture
    def basic_config(self):
        """基础配置"""
        return SimulationConfig(
            simulation_days=30,
            budget=BudgetConfig(
                base_ratio=1.0,
                region_distribution={"JP": 0.5, "US": 0.5}
            ),
            defaults=DefaultParams(
                initial_dau=1000,
                cpi=2.0,
                arpu_iap=0.01,
                arpu_ad=0.005,
                retention=RetentionConfig(
                    day1=0.50,
                    day2=0.40,
                    day3=0.35,
                    day7=0.28,
                    day14=0.22,
                    day30=0.16,
                    day60=0.10,
                )
            ),
            global_fixed_cost=100.0,
        )
    
    def test_run_simulation_basic(self, basic_config):
        """测试基本模拟功能"""
        result = run_simulation(basic_config)
        
        assert result.status == "success"
        assert result.execution_time_ms >= 0
        assert len(result.timeseries.days) == 30
    
    def test_simulation_dau_growth(self, basic_config):
        """测试 DAU 增长"""
        result = run_simulation(basic_config)
        
        # 有投放的情况下 DAU 应该增长
        initial_dau = basic_config.defaults.initial_dau * 2  # JP + US
        final_dau = result.summary.final_metrics.total_dau
        
        # 由于有付费投放，DAU 应该有所增长
        assert final_dau > 0
    
    def test_simulation_timeseries_length(self, basic_config):
        """测试时序数据长度"""
        result = run_simulation(basic_config)
        
        ts = result.timeseries
        assert len(ts.dates) == basic_config.simulation_days
        assert len(ts.days) == basic_config.simulation_days
        assert len(ts.totals.dau) == basic_config.simulation_days
        assert len(ts.totals.revenue) == basic_config.simulation_days
    
    def test_simulation_retention_curves(self, basic_config):
        """测试留存率曲线输出"""
        result = run_simulation(basic_config)
        
        assert "JP" in result.retention_curves
        assert "US" in result.retention_curves
        
        jp_curve = result.retention_curves["JP"]
        assert jp_curve.alpha > 0
        assert jp_curve.beta < 0
        assert 0 < jp_curve.gamma < 1
    
    def test_simulation_cumulative_metrics(self, basic_config):
        """测试累计指标"""
        result = run_simulation(basic_config)
        
        cum = result.summary.cumulative_metrics
        
        # 收入应该为正
        assert cum.total_revenue > 0
        assert cum.revenue_iap >= 0
        assert cum.revenue_ad >= 0
        
        # 成本应该为正
        assert cum.total_cost > 0
        assert cum.cost_marketing >= 0
        assert cum.cost_fixed > 0
    
    def test_simulation_region_breakdown(self, basic_config):
        """测试地区细分"""
        result = run_simulation(basic_config)
        
        assert result.timeseries.by_region is not None
        assert "JP" in result.timeseries.by_region
        assert "US" in result.timeseries.by_region


class TestSimulatorEdgeCases:
    """边界情况测试"""
    
    def test_single_day_simulation(self):
        """测试单天模拟"""
        config = SimulationConfig(
            simulation_days=1,
            budget=BudgetConfig(
                base_ratio=1.0,
                region_distribution={"JP": 1.0}
            ),
            global_fixed_cost=100.0,
        )
        
        result = run_simulation(config)
        assert len(result.timeseries.days) == 1
    
    def test_no_budget_simulation(self):
        """测试零预算模拟"""
        config = SimulationConfig(
            simulation_days=10,
            budget=BudgetConfig(
                base_ratio=0.0,  # 零预算
                region_distribution={"JP": 1.0}
            ),
            global_fixed_cost=100.0,
        )
        
        result = run_simulation(config)
        
        # 无预算时，付费新增应该为 0
        assert all(dnu == 0 for dnu in result.timeseries.totals.dnu_paid)
