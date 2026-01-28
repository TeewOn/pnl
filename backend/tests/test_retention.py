"""
留存率模块测试
"""

import pytest
import numpy as np
from src.core.retention import (
    fit_retention_params,
    calc_retention_new,
    calc_retention_active,
    generate_retention_curve,
)


class TestRetentionFitting:
    """留存率拟合测试"""
    
    def test_fit_retention_params_basic(self):
        """测试基本拟合功能"""
        # 典型留存率数据
        r1, r2, r3, r7, r14, r30, r60 = 0.50, 0.40, 0.35, 0.28, 0.22, 0.16, 0.10
        
        alpha, beta, gamma = fit_retention_params(r1, r2, r3, r7, r14, r30, r60)
        
        # 检查参数范围
        assert 0 < alpha < 1, "alpha 应该在 0-1 之间"
        assert beta < 0, "beta 应该为负数（衰减）"
        assert 0.9 < gamma < 1, "gamma 应该在 0.9-1 之间"
    
    def test_calc_retention_new_day0(self):
        """测试 Day 0 留存率（应为 100%）"""
        retention = calc_retention_new(0, 0.5, -0.3, 0.98)
        assert retention == 1.0
    
    def test_calc_retention_new_monotonic(self):
        """测试留存率单调递减"""
        alpha, beta, gamma = 0.5, -0.3, 0.98
        
        prev_retention = 1.0
        for day in range(1, 100):
            retention = calc_retention_new(day, alpha, beta, gamma)
            assert retention < prev_retention, f"Day {day} 应该低于 Day {day-1}"
            assert retention >= 0, f"Day {day} 留存率不应为负"
            prev_retention = retention
    
    def test_calc_retention_active(self):
        """测试存量用户留存率"""
        gamma = 0.98
        
        # Day 0 应为 100%
        assert calc_retention_active(0, gamma) == 1.0
        
        # 应该单调递减
        prev = 1.0
        for day in range(1, 100):
            current = calc_retention_active(day, gamma)
            assert current < prev
            prev = current
    
    def test_generate_retention_curve(self):
        """测试生成完整留存率曲线"""
        alpha, beta, gamma = 0.5, -0.3, 0.98
        
        curve = generate_retention_curve(alpha, beta, gamma, max_day=60)
        
        assert len(curve) == 60
        assert 1 in curve
        assert 60 in curve
        assert curve[1] > curve[60]


class TestEdgeCases:
    """边界情况测试"""
    
    def test_very_high_retention(self):
        """测试高留存率场景"""
        r1, r2, r3, r7, r14, r30, r60 = 0.80, 0.70, 0.65, 0.55, 0.48, 0.40, 0.30
        
        alpha, beta, gamma = fit_retention_params(r1, r2, r3, r7, r14, r30, r60)
        
        # 高留存时 beta 绝对值应该较小
        assert alpha > 0
        assert beta < 0
    
    def test_very_low_retention(self):
        """测试低留存率场景"""
        r1, r2, r3, r7, r14, r30, r60 = 0.20, 0.12, 0.08, 0.05, 0.03, 0.02, 0.01
        
        alpha, beta, gamma = fit_retention_params(r1, r2, r3, r7, r14, r30, r60)
        
        # 应该能正常拟合
        assert alpha > 0
        assert beta < 0
