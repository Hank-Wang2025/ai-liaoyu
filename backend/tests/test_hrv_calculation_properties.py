"""
HRV 计算有效性属性测试
Property-Based Tests for HRV Calculation Validity

使用 hypothesis 进行属性测试，验证 HRV 计算有效性
Requirements: 3.2
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
def valid_rr_intervals_60s(draw):
    """
    Generate valid RR intervals for at least 60 seconds of data.
    
    A typical resting heart rate is 60-100 bpm, which means:
    - At 60 bpm: 1 beat per second, RR interval = 1000ms
    - At 100 bpm: ~1.67 beats per second, RR interval = 600ms
    
    For 60 seconds of data, we need approximately 60-100 RR intervals.
    We generate at least 70 intervals to ensure we have enough data.
    """
    # Base RR interval (typical resting heart rate)
    base_rr = draw(st.integers(min_value=TYPICAL_MIN_RR, max_value=TYPICAL_MAX_RR))
    
    # Number of intervals (enough for at least 60 seconds)
    # At 800ms average, 75 intervals = 60 seconds
    num_intervals = draw(st.integers(min_value=70, max_value=150))
    
    # Variability (standard deviation in ms)
    variability = draw(st.integers(min_value=10, max_value=100))
    
    # Generate RR intervals with normal distribution around base
    rr_intervals = []
    for _ in range(num_intervals):
        # Add some natural variability
        rr = base_rr + draw(st.integers(min_value=-variability, max_value=variability))
        # Clamp to valid range
        rr = max(MIN_RR_INTERVAL, min(MAX_RR_INTERVAL, rr))
        rr_intervals.append(rr)
    
    return rr_intervals


@st.composite
def valid_rr_intervals_with_duration(draw):
    """
    Generate valid RR intervals with explicit duration calculation.
    
    Ensures the total duration is at least 60 seconds.
    """
    # Target duration in seconds (at least 60)
    target_duration = draw(st.integers(min_value=60, max_value=120))
    
    # Base RR interval
    base_rr = draw(st.integers(min_value=TYPICAL_MIN_RR, max_value=TYPICAL_MAX_RR))
    
    # Calculate approximate number of intervals needed
    approx_intervals = int((target_duration * 1000) / base_rr) + 10
    
    # Variability
    variability = draw(st.integers(min_value=10, max_value=80))
    
    rr_intervals = []
    total_duration_ms = 0
    
    while total_duration_ms < target_duration * 1000:
        rr = base_rr + draw(st.integers(min_value=-variability, max_value=variability))
        rr = max(MIN_RR_INTERVAL, min(MAX_RR_INTERVAL, rr))
        rr_intervals.append(rr)
        total_duration_ms += rr
    
    return rr_intervals


@st.composite
def physiologically_realistic_rr_intervals(draw):
    """
    Generate physiologically realistic RR intervals.
    
    Models realistic heart rate variability patterns:
    - Respiratory sinus arrhythmia (RSA)
    - Random beat-to-beat variability
    """
    # Base heart rate (bpm)
    base_hr = draw(st.integers(min_value=55, max_value=90))
    base_rr = int(60000 / base_hr)  # Convert to RR interval in ms
    
    # Number of intervals (at least 60 seconds worth)
    num_intervals = draw(st.integers(min_value=80, max_value=120))
    
    # HRV parameters
    rmssd_target = draw(st.integers(min_value=20, max_value=80))  # Target RMSSD
    
    rr_intervals = []
    prev_rr = base_rr
    
    for i in range(num_intervals):
        # Add beat-to-beat variability based on target RMSSD
        # RMSSD is roughly the standard deviation of successive differences
        diff = draw(st.integers(min_value=-rmssd_target, max_value=rmssd_target))
        rr = prev_rr + diff
        
        # Add some drift back to base
        drift = int((base_rr - rr) * 0.1)
        rr += drift
        
        # Clamp to valid range
        rr = max(MIN_RR_INTERVAL, min(MAX_RR_INTERVAL, rr))
        rr_intervals.append(rr)
        prev_rr = rr
    
    return rr_intervals


# ============================================================================
# Property Tests
# ============================================================================

class TestHRVCalculationValidity:
    """
    Property 7: HRV 计算有效性
    
    **Feature: healing-pod-system, Property 7: HRV 计算有效性**
    **Validates: Requirements 3.2**
    
    *For any* heart rate data sequence of at least 60 seconds,
    the HRV analysis module SHALL output valid RMSSD and SDNN metrics.
    """
    
    @given(rr_intervals=valid_rr_intervals_60s())
    @settings(max_examples=100)
    def test_hrv_analysis_produces_valid_rmssd(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 7: HRV 计算有效性**
        **Validates: Requirements 3.2**
        
        For any valid RR interval sequence of at least 60 seconds,
        the HRV analyzer SHALL produce a valid (non-negative) RMSSD value.
        """
        analyzer = HRVAnalyzer()
        
        # Calculate duration
        duration_seconds = sum(rr_intervals) / 1000.0
        
        # Ensure we have at least 60 seconds of data
        assume(duration_seconds >= 60)
        assume(len(rr_intervals) >= analyzer.MIN_RR_COUNT)
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        # Property assertion: RMSSD must be valid (non-negative)
        assert metrics is not None, \
            f"HRV analysis should produce metrics for {len(rr_intervals)} intervals over {duration_seconds:.1f}s"
        assert metrics.rmssd >= 0, \
            f"RMSSD should be non-negative, got {metrics.rmssd}"
    
    @given(rr_intervals=valid_rr_intervals_60s())
    @settings(max_examples=100)
    def test_hrv_analysis_produces_valid_sdnn(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 7: HRV 计算有效性**
        **Validates: Requirements 3.2**
        
        For any valid RR interval sequence of at least 60 seconds,
        the HRV analyzer SHALL produce a valid (non-negative) SDNN value.
        """
        analyzer = HRVAnalyzer()
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        assume(duration_seconds >= 60)
        assume(len(rr_intervals) >= analyzer.MIN_RR_COUNT)
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        # Property assertion: SDNN must be valid (non-negative)
        assert metrics is not None, \
            f"HRV analysis should produce metrics for {len(rr_intervals)} intervals"
        assert metrics.sdnn >= 0, \
            f"SDNN should be non-negative, got {metrics.sdnn}"
    
    @given(rr_intervals=valid_rr_intervals_with_duration())
    @settings(max_examples=100)
    def test_hrv_metrics_are_complete(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 7: HRV 计算有效性**
        **Validates: Requirements 3.2**
        
        For any valid RR interval sequence of at least 60 seconds,
        the HRV analyzer SHALL output complete metrics including both RMSSD and SDNN.
        """
        analyzer = HRVAnalyzer()
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        assume(duration_seconds >= 60)
        assume(len(rr_intervals) >= analyzer.MIN_RR_COUNT)
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        # Property assertion: metrics must be complete
        assert metrics is not None, "HRV analysis should produce metrics"
        assert hasattr(metrics, 'rmssd'), "Metrics should have RMSSD"
        assert hasattr(metrics, 'sdnn'), "Metrics should have SDNN"
        assert metrics.rmssd >= 0, f"RMSSD should be non-negative, got {metrics.rmssd}"
        assert metrics.sdnn >= 0, f"SDNN should be non-negative, got {metrics.sdnn}"
    
    @given(rr_intervals=physiologically_realistic_rr_intervals())
    @settings(max_examples=100)
    def test_hrv_metrics_validity_flag(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 7: HRV 计算有效性**
        **Validates: Requirements 3.2**
        
        For any physiologically realistic RR interval sequence of at least 60 seconds,
        the HRV metrics SHALL pass the validity check.
        """
        analyzer = HRVAnalyzer()
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        assume(duration_seconds >= 60)
        assume(len(rr_intervals) >= analyzer.MIN_RR_COUNT)
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        # Property assertion: metrics should be valid
        assert metrics is not None, "HRV analysis should produce metrics"
        assert metrics.is_valid(), \
            f"Metrics should be valid: RMSSD={metrics.rmssd}, SDNN={metrics.sdnn}, " \
            f"sample_count={metrics.sample_count}, stress_index={metrics.stress_index}"
    
    @given(rr_intervals=valid_rr_intervals_60s())
    @settings(max_examples=100)
    def test_rmssd_calculation_mathematical_validity(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 7: HRV 计算有效性**
        **Validates: Requirements 3.2**
        
        For any valid RR interval sequence,
        the RMSSD calculation SHALL be mathematically correct:
        RMSSD = sqrt(mean(successive_differences^2))
        """
        analyzer = HRVAnalyzer()
        
        # Preprocess to get clean data
        processed_rr, _ = analyzer.preprocess_rr_intervals(rr_intervals)
        
        assume(len(processed_rr) >= 2)
        
        # Calculate RMSSD using the analyzer
        rmssd = analyzer.calculate_rmssd(processed_rr)
        
        # Verify mathematical correctness
        rr_array = np.array(processed_rr, dtype=np.float64)
        successive_diffs = np.diff(rr_array)
        expected_rmssd = np.sqrt(np.mean(successive_diffs ** 2))
        
        # Property assertion: calculated RMSSD should match expected
        assert abs(rmssd - expected_rmssd) < 0.001, \
            f"RMSSD calculation mismatch: got {rmssd}, expected {expected_rmssd}"
    
    @given(rr_intervals=valid_rr_intervals_60s())
    @settings(max_examples=100)
    def test_sdnn_calculation_mathematical_validity(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 7: HRV 计算有效性**
        **Validates: Requirements 3.2**
        
        For any valid RR interval sequence,
        the SDNN calculation SHALL be mathematically correct:
        SDNN = std(RR_intervals)
        """
        analyzer = HRVAnalyzer()
        
        # Preprocess to get clean data
        processed_rr, _ = analyzer.preprocess_rr_intervals(rr_intervals)
        
        assume(len(processed_rr) >= 2)
        
        # Calculate SDNN using the analyzer
        sdnn = analyzer.calculate_sdnn(processed_rr)
        
        # Verify mathematical correctness
        rr_array = np.array(processed_rr, dtype=np.float64)
        expected_sdnn = np.std(rr_array, ddof=1)  # Sample standard deviation
        
        # Property assertion: calculated SDNN should match expected
        assert abs(sdnn - expected_sdnn) < 0.001, \
            f"SDNN calculation mismatch: got {sdnn}, expected {expected_sdnn}"
    
    @given(rr_intervals=valid_rr_intervals_60s())
    @settings(max_examples=100)
    def test_hrv_metrics_sample_count_accurate(self, rr_intervals: List[int]):
        """
        **Feature: healing-pod-system, Property 7: HRV 计算有效性**
        **Validates: Requirements 3.2**
        
        For any valid RR interval sequence,
        the sample_count in metrics SHALL reflect the actual number of processed intervals.
        """
        analyzer = HRVAnalyzer()
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        assume(duration_seconds >= 60)
        assume(len(rr_intervals) >= analyzer.MIN_RR_COUNT)
        
        # Get processed count
        processed_rr, _ = analyzer.preprocess_rr_intervals(rr_intervals)
        
        assume(len(processed_rr) >= analyzer.MIN_RR_COUNT)
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        # Property assertion: sample count should match processed intervals
        assert metrics is not None, "HRV analysis should produce metrics"
        assert metrics.sample_count == len(processed_rr), \
            f"Sample count mismatch: got {metrics.sample_count}, expected {len(processed_rr)}"


class TestHRVCalculationEdgeCases:
    """
    Edge case tests for HRV calculation.
    These complement the property tests by testing specific edge cases.
    """
    
    def test_minimum_valid_data(self):
        """Test HRV calculation with minimum valid data (at least 60 seconds)"""
        analyzer = HRVAnalyzer()
        
        # Generate at least 60 seconds of data at ~75 bpm (800ms RR)
        # 使用固定的 RR 间隔确保总时长超过 60 秒
        base_rr = 800
        num_intervals = 80  # 80 * 800ms = 64 seconds，确保超过 60 秒
        rr_intervals = [base_rr + (i % 30 - 15) for i in range(num_intervals)]
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        # 确保时长足够
        assert duration_seconds >= 60.0, f"Duration {duration_seconds}s should be >= 60s"
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        assert metrics is not None
        assert metrics.rmssd >= 0
        assert metrics.sdnn >= 0
    
    def test_constant_rr_intervals(self):
        """Test HRV calculation with constant RR intervals (zero variability)"""
        analyzer = HRVAnalyzer()
        
        # All intervals are exactly 800ms
        rr_intervals = [800] * 100
        duration_seconds = 80.0
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        assert metrics is not None
        # With constant intervals, RMSSD and SDNN should be 0 or very close to 0
        assert metrics.rmssd < 1.0, f"RMSSD should be ~0 for constant intervals, got {metrics.rmssd}"
        assert metrics.sdnn < 1.0, f"SDNN should be ~0 for constant intervals, got {metrics.sdnn}"
    
    def test_high_variability_rr_intervals(self):
        """Test HRV calculation with high variability RR intervals"""
        analyzer = HRVAnalyzer()
        
        # Alternating high and low RR intervals
        rr_intervals = []
        for i in range(100):
            if i % 2 == 0:
                rr_intervals.append(700)
            else:
                rr_intervals.append(900)
        
        duration_seconds = sum(rr_intervals) / 1000.0
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=duration_seconds)
        
        assert metrics is not None
        # High variability should produce high RMSSD and SDNN
        assert metrics.rmssd > 100, f"RMSSD should be high for variable intervals, got {metrics.rmssd}"
        assert metrics.sdnn > 50, f"SDNN should be high for variable intervals, got {metrics.sdnn}"
    
    def test_insufficient_data_returns_none(self):
        """Test that insufficient data returns None"""
        analyzer = HRVAnalyzer()
        
        # Only 20 intervals (less than MIN_RR_COUNT of 30)
        rr_intervals = [800] * 20
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=16.0)
        
        assert metrics is None
    
    def test_insufficient_duration_returns_none(self):
        """Test that insufficient duration returns None"""
        analyzer = HRVAnalyzer()
        
        # 50 intervals but only 40 seconds duration
        rr_intervals = [800] * 50
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=40.0)
        
        assert metrics is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
