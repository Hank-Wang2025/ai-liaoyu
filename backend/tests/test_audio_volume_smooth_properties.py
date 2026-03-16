"""
音频音量平滑过渡属性测试
Audio Volume Smooth Transition Property Tests

**Feature: healing-pod-system, Property: 音量平滑过渡**
**Validates: Requirements 6.5**

测试音量变化是否平滑，避免突兀变化
"""
import asyncio
import sys
import os

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pytest
from hypothesis import given, strategies as st, settings, assume

from services.audio_controller import (
    AudioFader,
    MockAudioController,
    AudioConfig,
)


class TestVolumeSmoothTransitionProperties:
    """
    音量平滑过渡属性测试
    
    **Feature: healing-pod-system, Property: 音量平滑过渡**
    **Validates: Requirements 6.5**
    
    测试音量变化是否平滑，确保没有突兀的音量跳变
    """
    
    @given(
        start_volume=st.floats(min_value=0.0, max_value=1.0),
        end_volume=st.floats(min_value=0.0, max_value=1.0),
        duration_ms=st.integers(min_value=100, max_value=5000)
    )
    @settings(max_examples=100)
    def test_volume_transition_curve_is_monotonic(
        self,
        start_volume: float,
        end_volume: float,
        duration_ms: int
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 起始音量和目标音量，音量过渡曲线应该是单调的（递增或递减），
        不应该出现音量跳变或非单调变化。
        """
        # Skip if start and end are the same (no transition needed)
        assume(abs(start_volume - end_volume) > 0.01)
        
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_volume_transition(start_volume, end_volume, duration_ms)
        
        # 验证曲线起点和终点
        assert curve[0] == pytest.approx(start_volume, abs=0.01), \
            f"Curve should start at {start_volume}, got {curve[0]}"
        assert curve[-1] == pytest.approx(end_volume, abs=0.01), \
            f"Curve should end at {end_volume}, got {curve[-1]}"
        
        # 验证曲线是单调的
        if start_volume < end_volume:
            # 递增：每个值应该 >= 前一个值
            for i in range(len(curve) - 1):
                assert curve[i] <= curve[i + 1] + 1e-6, \
                    f"Volume curve should be monotonically increasing at index {i}: {curve[i]} > {curve[i+1]}"
        else:
            # 递减：每个值应该 <= 前一个值
            for i in range(len(curve) - 1):
                assert curve[i] >= curve[i + 1] - 1e-6, \
                    f"Volume curve should be monotonically decreasing at index {i}: {curve[i]} < {curve[i+1]}"
    
    @given(
        start_volume=st.floats(min_value=0.0, max_value=1.0),
        end_volume=st.floats(min_value=0.0, max_value=1.0),
        duration_ms=st.integers(min_value=100, max_value=5000)
    )
    @settings(max_examples=100)
    def test_volume_transition_no_sudden_jumps(
        self,
        start_volume: float,
        end_volume: float,
        duration_ms: int
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 音量过渡，相邻采样点之间的音量变化不应超过合理阈值，
        确保没有突兀的音量跳变。
        """
        assume(abs(start_volume - end_volume) > 0.01)
        
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_volume_transition(start_volume, end_volume, duration_ms)
        
        # 计算总变化量
        total_change = abs(end_volume - start_volume)
        
        # 计算每个采样点的最大允许变化
        # 使用正弦曲线时，最大变化率在中点，约为 π/2 倍的平均变化率
        num_samples = len(curve)
        avg_change_per_sample = total_change / max(1, num_samples - 1)
        max_allowed_change = avg_change_per_sample * 2.0  # 允许2倍的平均变化率
        
        # 验证相邻采样点之间没有突兀跳变
        for i in range(len(curve) - 1):
            actual_change = abs(curve[i + 1] - curve[i])
            assert actual_change <= max_allowed_change + 1e-6, \
                f"Volume jump too large at index {i}: {actual_change} > {max_allowed_change}"
    
    @given(
        volume=st.floats(min_value=0.0, max_value=1.0),
        duration_ms=st.integers(min_value=100, max_value=2000)
    )
    @settings(max_examples=100)
    def test_volume_transition_curve_stays_in_range(
        self,
        volume: float,
        duration_ms: int
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 音量过渡曲线，所有采样点的音量值应该在 [0, 1] 范围内。
        """
        fader = AudioFader(sample_rate=44100)
        
        # 测试从0到目标音量
        curve_up = fader.create_volume_transition(0.0, volume, duration_ms)
        assert all(0.0 <= v <= 1.0 for v in curve_up), \
            "All volume values should be in [0, 1] range"
        
        # 测试从目标音量到0
        curve_down = fader.create_volume_transition(volume, 0.0, duration_ms)
        assert all(0.0 <= v <= 1.0 for v in curve_down), \
            "All volume values should be in [0, 1] range"
    
    @given(
        start_volume=st.floats(min_value=0.0, max_value=1.0),
        end_volume=st.floats(min_value=0.0, max_value=1.0),
        duration_ms=st.integers(min_value=100, max_value=2000)
    )
    @settings(max_examples=100)
    def test_volume_transition_intermediate_values(
        self,
        start_volume: float,
        end_volume: float,
        duration_ms: int
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 音量过渡，中间值应该在起始和目标音量之间，
        不应该出现超调或下冲。
        """
        assume(abs(start_volume - end_volume) > 0.01)
        
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_volume_transition(start_volume, end_volume, duration_ms)
        
        min_vol = min(start_volume, end_volume)
        max_vol = max(start_volume, end_volume)
        
        # 所有中间值应该在起始和目标音量之间（允许小误差）
        for i, v in enumerate(curve):
            assert min_vol - 1e-6 <= v <= max_vol + 1e-6, \
                f"Volume at index {i} ({v}) should be between {min_vol} and {max_vol}"


class TestFadeInOutSmoothProperties:
    """
    淡入淡出平滑性属性测试
    
    **Feature: healing-pod-system, Property: 音量平滑过渡**
    **Validates: Requirements 6.5**
    """
    
    @given(
        duration_ms=st.integers(min_value=100, max_value=5000),
        fade_type=st.sampled_from(["linear", "exponential", "logarithmic", "sine"])
    )
    @settings(max_examples=100)
    def test_fade_in_curve_starts_at_zero(
        self,
        duration_ms: int,
        fade_type: str
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 淡入曲线，应该从0开始，到1结束。
        """
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_fade_curve(duration_ms, fade_type, "in")
        
        assert curve[0] == pytest.approx(0.0, abs=0.01), \
            f"Fade-in curve should start at 0, got {curve[0]}"
        assert curve[-1] == pytest.approx(1.0, abs=0.01), \
            f"Fade-in curve should end at 1, got {curve[-1]}"
    
    @given(
        duration_ms=st.integers(min_value=100, max_value=5000),
        fade_type=st.sampled_from(["linear", "exponential", "logarithmic", "sine"])
    )
    @settings(max_examples=100)
    def test_fade_out_curve_ends_at_zero(
        self,
        duration_ms: int,
        fade_type: str
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 淡出曲线，应该从1开始，到0结束。
        """
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_fade_curve(duration_ms, fade_type, "out")
        
        assert curve[0] == pytest.approx(1.0, abs=0.01), \
            f"Fade-out curve should start at 1, got {curve[0]}"
        assert curve[-1] == pytest.approx(0.0, abs=0.01), \
            f"Fade-out curve should end at 0, got {curve[-1]}"
    
    @given(
        duration_ms=st.integers(min_value=100, max_value=5000),
        fade_type=st.sampled_from(["linear", "exponential", "logarithmic", "sine"])
    )
    @settings(max_examples=100)
    def test_fade_curve_is_monotonic(
        self,
        duration_ms: int,
        fade_type: str
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 淡入淡出曲线，应该是单调的（淡入递增，淡出递减）。
        """
        fader = AudioFader(sample_rate=44100)
        
        # 测试淡入曲线（应该单调递增）
        curve_in = fader.create_fade_curve(duration_ms, fade_type, "in")
        for i in range(len(curve_in) - 1):
            assert curve_in[i] <= curve_in[i + 1] + 1e-6, \
                f"Fade-in curve should be monotonically increasing at index {i}"
        
        # 测试淡出曲线（应该单调递减）
        curve_out = fader.create_fade_curve(duration_ms, fade_type, "out")
        for i in range(len(curve_out) - 1):
            assert curve_out[i] >= curve_out[i + 1] - 1e-6, \
                f"Fade-out curve should be monotonically decreasing at index {i}"


class TestMockControllerVolumeSmoothProperties:
    """
    模拟控制器音量平滑过渡属性测试
    
    **Feature: healing-pod-system, Property: 音量平滑过渡**
    **Validates: Requirements 6.5**
    """
    
    @given(
        start_volume=st.floats(min_value=0.1, max_value=0.9),
        end_volume=st.floats(min_value=0.1, max_value=0.9),
        transition_ms=st.integers(min_value=100, max_value=500)
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_controller_volume_transition_reaches_target(
        self,
        start_volume: float,
        end_volume: float,
        transition_ms: int
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 音量过渡，控制器应该最终达到目标音量。
        """
        assume(abs(start_volume - end_volume) > 0.05)
        
        controller = MockAudioController()
        await controller.initialize()
        await controller.play("test.wav", volume=start_volume)
        
        # 执行音量过渡
        result = await controller.set_volume(end_volume, transition_ms=transition_ms)
        
        assert result is True, "Volume transition should succeed"
        assert controller.current_state.volume == pytest.approx(end_volume, abs=0.02), \
            f"Final volume should be {end_volume}, got {controller.current_state.volume}"
        
        await controller.cleanup()
    
    @given(
        volume=st.floats(min_value=-0.5, max_value=1.5)
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_controller_volume_clamping(
        self,
        volume: float
    ):
        """
        **Feature: healing-pod-system, Property: 音量平滑过渡**
        **Validates: Requirements 6.5**
        
        *For any* 设置的音量值，控制器应该将其限制在 [0, 1] 范围内。
        """
        controller = MockAudioController()
        await controller.initialize()
        await controller.play("test.wav", volume=0.5)
        
        await controller.set_volume(volume)
        
        actual_volume = controller.current_state.volume
        assert 0.0 <= actual_volume <= 1.0, \
            f"Volume should be clamped to [0, 1], got {actual_volume}"
        
        expected = max(0.0, min(1.0, volume))
        assert actual_volume == pytest.approx(expected, abs=0.01), \
            f"Volume should be clamped to {expected}, got {actual_volume}"
        
        await controller.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
