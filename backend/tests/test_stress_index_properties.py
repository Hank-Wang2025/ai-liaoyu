"""
压力指数范围约束属性测试
Property-Based Tests for Stress Index Range Constraint

使用 hypothesis 进行属性测试，验证压力指数范围约束
Requirements: 3.3

**Property 8: 压力指数范围约束**
*For any* 有效的心率数据输入，压力指数计算结果 SHALL 在 0-100 范围内。
"""
import os
import sys
from typing import List

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.hrv_analyzer import HRVAnalyzer, HRVMetrics


# ============================================================================
# Strategies for generating test data
# ============================================================================

# Valid RR interval range (ms) - corresponds to heart rates of ~30-200 bpm
MIN_RR_INTERVAL = 300   # ~200 bpm
MAX_RR_INTERVAL = 2000  # ~30 bpm

# Typical resting heart rate RR interval range (ms) - 60-100 bpm
TYPICAL_MIN_RR = 600   # ~100 bpm
TYPICAL_MAX_RR = 1000  # ~60 bpm


@st.composite
def valid_rmssd_values(draw):
    """
    Generate valid RMSSD values.
    
    RMSSD typically ranges from 10ms (high stress) to 100ms+ (low stress).
    We test a wide range including edge cases.
    """
    return draw(st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False))


@st.composite
def valid_sdnn_values(draw):
    """
    Generate valid SDNN values.
    
    SDNN typically ranges from 30ms (high stress) to 150ms+ (low stress).
    We test a wide range including edge cases.
    """
    return draw(st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False))


@st.composite
def valid_mean_hr_values(draw):
    """
    Generate valid mean heart rate values.
    
    Heart rate typically ranges from 40 bpm to 180 bpm.
    """
    return draw(st.floats(min_value=30.0, max_value=200.0, allow_nan=False, allow_infinity=False))


@st.composite
def valid_rr_intervals_60s(draw):
    """
    Generate valid RR intervals for at least 60 seconds of data.
    """
    # Base RR interval (typical resting heart rate)
    base_rr = draw(st.integers(min_value=TYPICAL_MIN_RR, max_value=TYPICAL_MAX_RR))
    
    # Number of intervals (enough for at least 60 seconds)
    num_intervals = draw(st.integers(min_value=70, max_value=150))
    
    # Variability (standard deviation in ms)
    variability = draw(st.integers(min_value=10, max_value=100))
    
    # Generate RR intervals with normal distribution around base
    rr_intervals = []
    for _ in range(num_intervals):
        rr = base_rr + draw(st.integers(min_value=-variability, max_value=variability))
        rr = max(MIN_RR_INTERVAL, min(MAX_RR_INTERVAL, rr))
        rr_intervals.append(rr)
    
    return rr_intervals


@st.composite
def extreme_rr_intervals(draw):
    """
    Generate RR intervals with extreme variability to test edge cases.
    """
    # Choose between low variability (high stress) or high variability (low stress)
    variability_type = draw(st.sampled_from(["low", "high", "mixed"]))
    
    num_intervals = draw(st.integers(min_value=70, max_value=120))
    
    if variability_type == "low":
        # Very consistent intervals (low HRV, high stress)
        base_rr = draw(st.integers(min_value=600, max_value=900))
        variability = draw(st.integers(min_value=1, max_value=10))
    elif variability_type == "high":
        # Highly variable intervals (high HRV, low stress)
        base_rr = draw(st.integers(min_value=700, max_value=900))
        variability = draw(st.integers(min_value=80, max_value=150))
    else:
        # Mixed variability
        base_rr = draw(st.integers(min_value=600, max_value=1000))
        variability = draw(st.integers(min_value=30, max_value=80))
    
    rr_intervals = []
    for _ in range(num_intervals):
        rr = base_rr + draw(st.integers(min_value=-variability, max_value=variability))
        rr = max(MIN_RR_INTERVAL, min(MAX_RR_INTERVAL, rr))
        rr_intervals.append(rr)
    
    return rr_intervals


# ============================================================================
# Property Tests
# ============================================================================

class TestStressIndexRangeConstraint:
    """
    Property 8: 压力指数范围约束
    
    **Feature: healing-pod-system, Property 8: 压力指数范围约束**
    **Validates: Requirements 3.3**
    
    *For any* 有效的心率数据输入，压力指数计算结果 SHALL 在 0-100 范围内。
    """
    
    @given(rmssd=valid_rmssd_values(), sdnn=valid_sdnn_values())
    @settings(max_examples=100)
    def test_stress_index_range_from_hrv_metrics(self, rmssd: float, sdnn: float):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        
        For any valid RMSSD and SDNN values,
        the stress index SHALL be in the range [0, 100].
        """
        analyzer = HRVAnalyzer()
        
        stress_index = analyzer.calculate_stress_index(rmssd, sdnn)
        
        # Property assertion: stress index must be in [0, 100]
        assert 0 <= stress_index <= 100, \
            f"Stress index {stress_index} out of range [0, 100] for RMSSD={rmssd}, SDNN={sdnn}"
    
    @given(
        rmssd=valid_rmssd_values(),
        sdnn=valid_sdnn_values(),
        mean_hr=valid_mean_hr_values()
    )
    @settings(max_examples=100)
    def test_stress_index_range_with_heart_rate(
        self, rmssd: float, sdnn: float, mean_hr: float
    ):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        
        For any valid RMSSD, SDNN, and mean heart rate values,
        the stress index SHALL be in the range [0, 100].
        """
        analyzer = HRVAnalyzer()
        
        stress_index = analyzer.calculate_stress_index(rmssd, sdnn, mean_hr)
        
        # Property assertion: stress index must be in [0, 100]
        assert 0 <= stress_index <= 100, \
            f"Stress index {stress_index} out of range [0, 100] for " \
            f"RMSSD={rmssd}, SDNN={sdnn}, HR={mean_hr}"
    
    @given(rr_intervals=valid_rr_intervals_60s())
    @settings(max_examples=100)
    def test_stress_index_range_from_rr_intervals(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        
        For any valid RR interval sequence of at least 60 seconds,
        the stress index in the HRV metrics SHALL be in the range [0, 100].
        """
        analyzer = HRVAnalyzer()
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        # Ensure we have sufficient data
        assume(duration_seconds >= 60)
        assume(len(rr_intervals) >= analyzer.MIN_RR_COUNT)
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        # If analysis succeeds, stress index must be in range
        if metrics is not None:
            assert 0 <= metrics.stress_index <= 100, \
                f"Stress index {metrics.stress_index} out of range [0, 100]"
    
    @given(rr_intervals=extreme_rr_intervals())
    @settings(max_examples=100)
    def test_stress_index_range_extreme_variability(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        
        For any RR interval sequence with extreme variability (very low or very high HRV),
        the stress index SHALL still be in the range [0, 100].
        """
        analyzer = HRVAnalyzer()
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        assume(duration_seconds >= 60)
        assume(len(rr_intervals) >= analyzer.MIN_RR_COUNT)
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        if metrics is not None:
            assert 0 <= metrics.stress_index <= 100, \
                f"Stress index {metrics.stress_index} out of range [0, 100] " \
                f"for extreme variability data"
    
    @given(
        rmssd=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        sdnn=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_stress_index_range_boundary_values(self, rmssd: float, sdnn: float):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        
        For any RMSSD and SDNN values including extreme boundary values,
        the stress index SHALL be clamped to the range [0, 100].
        """
        analyzer = HRVAnalyzer()
        
        stress_index = analyzer.calculate_stress_index(rmssd, sdnn)
        
        # Property assertion: stress index must be clamped to [0, 100]
        assert 0 <= stress_index <= 100, \
            f"Stress index {stress_index} not clamped to [0, 100] for " \
            f"RMSSD={rmssd}, SDNN={sdnn}"
    
    @given(
        rmssd=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        sdnn=st.floats(min_value=0.0, max_value=30.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_stress_index_high_stress_scenario(self, rmssd: float, sdnn: float):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        
        For very low RMSSD and SDNN values (high stress scenario),
        the stress index SHALL be in the range [0, 100] (not exceed 100).
        """
        analyzer = HRVAnalyzer()
        
        stress_index = analyzer.calculate_stress_index(rmssd, sdnn)
        
        # Property assertion: even in high stress, index must not exceed 100
        assert 0 <= stress_index <= 100, \
            f"Stress index {stress_index} exceeds 100 for high stress scenario " \
            f"(RMSSD={rmssd}, SDNN={sdnn})"
    
    @given(
        rmssd=st.floats(min_value=100.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        sdnn=st.floats(min_value=150.0, max_value=400.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_stress_index_low_stress_scenario(self, rmssd: float, sdnn: float):
        """
        **Feature: healing-pod-system, Property 8: 压力指数范围约束**
        **Validates: Requirements 3.3**
        
        For very high RMSSD and SDNN values (low stress scenario),
        the stress index SHALL be in the range [0, 100] (not go below 0).
        """
        analyzer = HRVAnalyzer()
        
        stress_index = analyzer.calculate_stress_index(rmssd, sdnn)
        
        # Property assertion: even in low stress, index must not go below 0
        assert 0 <= stress_index <= 100, \
            f"Stress index {stress_index} below 0 for low stress scenario " \
            f"(RMSSD={rmssd}, SDNN={sdnn})"


class TestStressIndexEdgeCases:
    """
    Edge case tests for stress index calculation.
    These complement the property tests by testing specific edge cases.
    """
    
    def test_stress_index_zero_hrv(self):
        """Test stress index with zero HRV values (edge case)"""
        analyzer = HRVAnalyzer()
        
        stress_index = analyzer.calculate_stress_index(rmssd=0.0, sdnn=0.0)
        
        assert 0 <= stress_index <= 100
        # Zero HRV should indicate maximum stress
        assert stress_index == 100.0
    
    def test_stress_index_very_high_hrv(self):
        """Test stress index with very high HRV values (edge case)"""
        analyzer = HRVAnalyzer()
        
        stress_index = analyzer.calculate_stress_index(rmssd=200.0, sdnn=300.0)
        
        assert 0 <= stress_index <= 100
        # Very high HRV should indicate minimum stress
        assert stress_index == 0.0
    
    def test_stress_index_threshold_values(self):
        """Test stress index at threshold values"""
        analyzer = HRVAnalyzer()
        
        # At low stress thresholds
        stress_at_low = analyzer.calculate_stress_index(
            rmssd=analyzer.RMSSD_LOW_STRESS,
            sdnn=analyzer.SDNN_LOW_STRESS
        )
        assert 0 <= stress_at_low <= 100
        assert stress_at_low == 0.0
        
        # At high stress thresholds
        stress_at_high = analyzer.calculate_stress_index(
            rmssd=analyzer.RMSSD_HIGH_STRESS,
            sdnn=analyzer.SDNN_HIGH_STRESS
        )
        assert 0 <= stress_at_high <= 100
        assert stress_at_high == 100.0
    
    def test_stress_index_with_extreme_heart_rate(self):
        """Test stress index with extreme heart rate values"""
        analyzer = HRVAnalyzer()
        
        # Very high heart rate
        stress_high_hr = analyzer.calculate_stress_index(
            rmssd=35.0, sdnn=70.0, mean_hr=180.0
        )
        assert 0 <= stress_high_hr <= 100
        
        # Very low heart rate
        stress_low_hr = analyzer.calculate_stress_index(
            rmssd=35.0, sdnn=70.0, mean_hr=35.0
        )
        assert 0 <= stress_low_hr <= 100
    
    def test_stress_index_consistency(self):
        """Test that stress index is consistent for same inputs"""
        analyzer = HRVAnalyzer()
        
        rmssd, sdnn = 40.0, 80.0
        
        stress1 = analyzer.calculate_stress_index(rmssd, sdnn)
        stress2 = analyzer.calculate_stress_index(rmssd, sdnn)
        
        assert stress1 == stress2
        assert 0 <= stress1 <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
