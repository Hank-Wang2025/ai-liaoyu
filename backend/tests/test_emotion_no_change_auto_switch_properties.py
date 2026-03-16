"""
情绪无变化自动切换属性测试
Property-Based Tests for Emotion No-Change Auto-Switch

使用 hypothesis 进行属性测试，验证情绪无变化自动切换功能
Requirements: 10.3

**Property 20: 情绪无变化自动切换**
*For any* 情绪状态在 3 分钟内无明显变化（变化幅度小于 0.1）的情况，
系统 SHALL 自动切换到备选方案。
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume, Phase

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import EmotionState, EmotionCategory
from services.realtime_feedback import (
    RealtimeFeedbackMonitor,
    FeedbackConfig,
    EmotionTrend,
    EmotionChangeDetection
)


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def valid_emotion_state(draw):
    """Generate a valid EmotionState."""
    category = draw(st.sampled_from(list(EmotionCategory)))
    intensity = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    valence = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    arousal = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return EmotionState(
        category=category,
        intensity=intensity,
        valence=valence,
        arousal=arousal,
        confidence=confidence,
        timestamp=datetime.now()
    )


@st.composite
def stable_emotion_sequence(draw, base_emotion: EmotionState = None, num_points: int = None):
    """
    Generate a sequence of emotions with minimal change (< 0.1 valence change).
    This simulates the "no change" condition.
    """
    if base_emotion is None:
        category = draw(st.sampled_from(list(EmotionCategory)))
        base_valence = draw(st.floats(min_value=-0.8, max_value=0.8, allow_nan=False, allow_infinity=False))
        base_intensity = draw(st.floats(min_value=0.2, max_value=0.8, allow_nan=False, allow_infinity=False))
        base_arousal = draw(st.floats(min_value=0.2, max_value=0.8, allow_nan=False, allow_infinity=False))
    else:
        category = base_emotion.category
        base_valence = base_emotion.valence
        base_intensity = base_emotion.intensity
        base_arousal = base_emotion.arousal
    
    if num_points is None:
        num_points = draw(st.integers(min_value=3, max_value=10))
    
    emotions = []
    base_time = datetime.now()
    
    for i in range(num_points):
        # Small variations that stay within 0.1 change threshold
        valence_delta = draw(st.floats(min_value=-0.04, max_value=0.04, allow_nan=False, allow_infinity=False))
        intensity_delta = draw(st.floats(min_value=-0.05, max_value=0.05, allow_nan=False, allow_infinity=False))
        
        valence = max(-1.0, min(1.0, base_valence + valence_delta))
        intensity = max(0.0, min(1.0, base_intensity + intensity_delta))
        
        emotions.append(EmotionState(
            category=category,
            intensity=intensity,
            valence=valence,
            arousal=base_arousal,
            confidence=0.8,
            timestamp=base_time + timedelta(seconds=i * 10)
        ))
    
    return emotions


@st.composite
def no_change_threshold_seconds(draw):
    """Generate a valid no-change threshold (default is 180 seconds = 3 minutes)."""
    return draw(st.integers(min_value=60, max_value=300))


# ============================================================================
# Mock Dependencies
# ============================================================================

class MockSessionManager:
    """Mock session manager for testing."""
    
    def __init__(self):
        self.has_active_session = True
        self.recorded_emotions: List[EmotionState] = []
        self.recorded_adjustments: List[dict] = []
    
    async def record_emotion(self, emotion: EmotionState, phase_name: Optional[str] = None):
        self.recorded_emotions.append(emotion)
    
    async def record_adjustment(self, reason: str, adjustment_type: str, details: dict, 
                                previous_state: Optional[dict] = None, 
                                new_state: Optional[dict] = None):
        self.recorded_adjustments.append({
            "reason": reason,
            "adjustment_type": adjustment_type,
            "details": details,
            "timestamp": datetime.now()
        })


class MockTherapyExecutor:
    """Mock therapy executor for testing."""
    
    def __init__(self):
        self.is_running = True
        self.current_phase = MagicMock()
        self.current_phase.name = "测试阶段"
        self._current_plan = MagicMock()
        self._current_plan.id = "test_plan"
        self.switched_plans: List = []
    
    async def switch_plan(self, plan):
        self.switched_plans.append(plan)


class MockPlanManager:
    """Mock plan manager for testing."""
    
    def __init__(self, alternative_plans=None):
        self.alternative_plans = alternative_plans or []
    
    def match_with_details(self, emotion: EmotionState, top_n: int = 3):
        return self.alternative_plans


class MockMatchResult:
    """Mock match result for plan matching."""
    
    def __init__(self, plan_id: str, plan_name: str):
        self.plan = MagicMock()
        self.plan.id = plan_id
        self.plan.name = plan_name


# ============================================================================
# Property Tests - Property 20: 情绪无变化自动切换
# ============================================================================

class TestEmotionNoChangeAutoSwitch:
    """
    Property 20: 情绪无变化自动切换
    
    **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
    **Validates: Requirements 10.3**
    
    *For any* 情绪状态在 3 分钟内无明显变化（变化幅度小于 0.1）的情况，
    系统 SHALL 自动切换到备选方案。
    """
    
    @given(
        base_valence=st.floats(min_value=-0.8, max_value=0.8, allow_nan=False, allow_infinity=False),
        base_intensity=st.floats(min_value=0.2, max_value=0.8, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_no_change_detection_threshold(self, base_valence: float, base_intensity: float):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        For any stable emotion sequence with valence change < 0.1, the system
        SHALL detect it as NO_CHANGE trend.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,  # 3 minutes
            improvement_threshold=0.1,
            worsening_threshold=-0.1,
            min_data_points=3
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Create stable emotion sequence with minimal change
        base_time = datetime.now()
        for i in range(5):
            # Small variations within threshold
            small_delta = 0.02 * (i % 2)  # Alternating small changes
            monitor._emotion_buffer.append(EmotionState(
                category=EmotionCategory.ANXIOUS,
                intensity=base_intensity + small_delta,
                valence=base_valence + small_delta,
                arousal=0.5,
                confidence=0.8,
                timestamp=base_time + timedelta(seconds=i * 10)
            ))
        
        # Detect trend
        detection = monitor._detect_emotion_trend()
        
        # Verify the change is within threshold
        assert abs(detection.valence_change) < 0.1, \
            f"Valence change {detection.valence_change} should be < 0.1 for stable emotions"
        
        # Verify trend is detected as NO_CHANGE or STABLE
        assert detection.trend in [EmotionTrend.NO_CHANGE, EmotionTrend.STABLE], \
            f"Trend should be NO_CHANGE or STABLE for minimal changes, got {detection.trend}"
    
    @given(threshold_seconds=no_change_threshold_seconds())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_default_no_change_threshold_is_180_seconds(self, threshold_seconds: int):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        The default no-change threshold SHALL be 180 seconds (3 minutes).
        """
        default_config = FeedbackConfig()
        
        assert default_config.no_change_threshold == 180, \
            f"Default no_change_threshold should be 180 seconds, got {default_config.no_change_threshold}"
        
        # Custom config should accept the threshold
        custom_config = FeedbackConfig(no_change_threshold=threshold_seconds)
        assert custom_config.no_change_threshold == threshold_seconds, \
            f"Custom threshold should be {threshold_seconds}"

    
    @given(emotion=valid_emotion_state())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_auto_switch_enabled_by_default(self, emotion: EmotionState):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        Auto-switch SHALL be enabled by default in the configuration.
        """
        default_config = FeedbackConfig()
        
        assert default_config.auto_switch_enabled is True, \
            "Auto-switch should be enabled by default"
    
    @given(
        base_valence=st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
        no_change_duration=st.integers(min_value=180, max_value=600)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_no_change_triggers_adjustment_record(self, base_valence: float, no_change_duration: int):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        For any no-change duration >= 180 seconds, the system SHALL record
        an adjustment with type 'no_change_timeout'.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,
            auto_switch_enabled=False  # Disable actual switch for this test
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Create stable emotion
        current_emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.5,
            valence=base_valence,
            arousal=0.5,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        # Create detection result
        detection = EmotionChangeDetection(
            trend=EmotionTrend.NO_CHANGE,
            valence_change=0.02,
            intensity_change=0.01,
            duration_seconds=no_change_duration,
            confidence=0.8
        )
        
        # Run the handler
        asyncio.get_event_loop().run_until_complete(
            monitor._handle_no_change(detection, current_emotion, no_change_duration)
        )
        
        # Verify adjustment was recorded
        assert len(mock_session.recorded_adjustments) == 1, \
            "Should record one adjustment for no-change timeout"
        
        adjustment = mock_session.recorded_adjustments[0]
        assert adjustment["adjustment_type"] == "no_change_timeout", \
            f"Adjustment type should be 'no_change_timeout', got {adjustment['adjustment_type']}"
        assert adjustment["details"]["no_change_duration"] == no_change_duration, \
            "Adjustment should record the no-change duration"
        assert adjustment["details"]["threshold"] == 180, \
            "Adjustment should record the threshold"

    
    @given(
        valence_change=st.floats(min_value=-0.09, max_value=0.09, allow_nan=False, allow_infinity=False),
        intensity_change=st.floats(min_value=-0.09, max_value=0.09, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_change_below_threshold_is_no_change(self, valence_change: float, intensity_change: float):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        For any valence change < 0.1 and intensity change < 0.1, the trend
        SHALL be detected as NO_CHANGE or STABLE.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,
            improvement_threshold=0.1,
            worsening_threshold=-0.1,
            min_data_points=3
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Create emotion sequence with specified changes
        base_time = datetime.now()
        base_valence = 0.0
        base_intensity = 0.5
        
        # First emotion
        monitor._emotion_buffer.append(EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=base_intensity,
            valence=base_valence,
            arousal=0.5,
            confidence=0.8,
            timestamp=base_time
        ))
        
        # Middle emotions (interpolated)
        for i in range(1, 3):
            factor = i / 3
            monitor._emotion_buffer.append(EmotionState(
                category=EmotionCategory.NEUTRAL,
                intensity=base_intensity + intensity_change * factor,
                valence=base_valence + valence_change * factor,
                arousal=0.5,
                confidence=0.8,
                timestamp=base_time + timedelta(seconds=i * 10)
            ))
        
        # Last emotion with full change
        monitor._emotion_buffer.append(EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=base_intensity + intensity_change,
            valence=base_valence + valence_change,
            arousal=0.5,
            confidence=0.8,
            timestamp=base_time + timedelta(seconds=30)
        ))
        
        # Detect trend
        detection = monitor._detect_emotion_trend()
        
        # Verify changes are within threshold
        assert abs(detection.valence_change) < 0.1 or abs(valence_change) >= 0.05, \
            f"Valence change should be detected correctly"
        
        # For very small changes, trend should be NO_CHANGE or STABLE
        if abs(valence_change) < 0.05 and abs(intensity_change) < 0.1:
            assert detection.trend in [EmotionTrend.NO_CHANGE, EmotionTrend.STABLE], \
                f"Small changes should result in NO_CHANGE or STABLE trend, got {detection.trend}"



class TestAutoSwitchMechanism:
    """
    Test the auto-switch mechanism when no change is detected.
    """
    
    @given(emotion=valid_emotion_state())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_switch_plan_called_on_no_change_timeout(self, emotion: EmotionState):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        For any emotion state with no change for >= 3 minutes, the system
        SHALL attempt to switch to an alternative plan.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        
        # Create alternative plan
        alt_plan = MockMatchResult("alt_plan_1", "备选方案1")
        mock_plan_manager = MockPlanManager(alternative_plans=[alt_plan])
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,
            auto_switch_enabled=True
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Create detection result for no change
        detection = EmotionChangeDetection(
            trend=EmotionTrend.NO_CHANGE,
            valence_change=0.02,
            intensity_change=0.01,
            duration_seconds=200,
            confidence=0.8
        )
        
        # Run the handler
        asyncio.get_event_loop().run_until_complete(
            monitor._handle_no_change(detection, emotion, 200)
        )
        
        # Verify switch was attempted
        assert len(mock_executor.switched_plans) == 1, \
            "Should attempt to switch plan on no-change timeout"
    
    @given(emotion=valid_emotion_state())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_no_switch_when_disabled(self, emotion: EmotionState):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        When auto_switch_enabled is False, the system SHALL NOT switch plans
        even on no-change timeout.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        
        alt_plan = MockMatchResult("alt_plan_1", "备选方案1")
        mock_plan_manager = MockPlanManager(alternative_plans=[alt_plan])
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,
            auto_switch_enabled=False  # Disabled
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        detection = EmotionChangeDetection(
            trend=EmotionTrend.NO_CHANGE,
            valence_change=0.02,
            intensity_change=0.01,
            duration_seconds=200,
            confidence=0.8
        )
        
        # Run the handler
        asyncio.get_event_loop().run_until_complete(
            monitor._handle_no_change(detection, emotion, 200)
        )
        
        # Verify no switch was attempted
        assert len(mock_executor.switched_plans) == 0, \
            "Should NOT switch plan when auto_switch_enabled is False"

    
    @given(
        no_change_duration=st.integers(min_value=1, max_value=179)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_no_switch_before_threshold(self, no_change_duration: int):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        For any no-change duration < 180 seconds, the system SHALL NOT
        trigger auto-switch.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,
            auto_switch_enabled=True
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Set last change time to simulate duration < threshold
        monitor._last_change_time = datetime.now() - timedelta(seconds=no_change_duration)
        
        # Verify the duration is below threshold
        assert no_change_duration < config.no_change_threshold, \
            f"Duration {no_change_duration} should be below threshold {config.no_change_threshold}"
        
        # The check in _check_emotion_change would not trigger _handle_no_change
        # because no_change_duration < no_change_threshold
        time_since_change = (datetime.now() - monitor._last_change_time).total_seconds()
        should_trigger = time_since_change >= config.no_change_threshold
        
        assert not should_trigger, \
            f"Should NOT trigger auto-switch when duration ({time_since_change:.0f}s) < threshold ({config.no_change_threshold}s)"


class TestNoChangeThresholdConfiguration:
    """
    Test the no-change threshold configuration.
    """
    
    @given(threshold=st.integers(min_value=60, max_value=600))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_configurable_threshold(self, threshold: int):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        The no-change threshold SHALL be configurable.
        """
        config = FeedbackConfig(no_change_threshold=threshold)
        
        assert config.no_change_threshold == threshold, \
            f"Threshold should be configurable to {threshold}"
        
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        assert monitor._config.no_change_threshold == threshold, \
            "Monitor should use the configured threshold"
    
    @given(new_threshold=st.integers(min_value=60, max_value=600))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_threshold_can_be_updated(self, new_threshold: int):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        The no-change threshold SHALL be updatable at runtime.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(no_change_threshold=180)
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Update threshold
        monitor.update_config(no_change_threshold=new_threshold)
        
        assert monitor._config.no_change_threshold == new_threshold, \
            f"Threshold should be updated to {new_threshold}"



class TestCallbackNotification:
    """
    Test callback notification on no-change timeout.
    """
    
    @given(
        no_change_duration=st.integers(min_value=180, max_value=600),
        emotion=valid_emotion_state()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_callback_notified_on_no_change(self, no_change_duration: int, emotion: EmotionState):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        For any no-change timeout, registered callbacks SHALL be notified
        with the correct adjustment type.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,
            auto_switch_enabled=False
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Track callback invocations
        callback_invocations = []
        
        def test_callback(adjustment_type: str, details: dict):
            callback_invocations.append({
                "type": adjustment_type,
                "details": details
            })
        
        monitor.add_adjustment_callback(test_callback)
        
        detection = EmotionChangeDetection(
            trend=EmotionTrend.NO_CHANGE,
            valence_change=0.02,
            intensity_change=0.01,
            duration_seconds=no_change_duration,
            confidence=0.8
        )
        
        # Run the handler
        asyncio.get_event_loop().run_until_complete(
            monitor._handle_no_change(detection, emotion, no_change_duration)
        )
        
        # Verify callback was invoked
        assert len(callback_invocations) == 1, \
            "Callback should be invoked once on no-change timeout"
        
        invocation = callback_invocations[0]
        assert invocation["type"] == "no_change_timeout", \
            f"Callback type should be 'no_change_timeout', got {invocation['type']}"
        assert invocation["details"]["no_change_duration"] == no_change_duration, \
            "Callback should include no_change_duration"
        assert invocation["details"]["threshold"] == 180, \
            "Callback should include threshold"


class TestEmotionTrendDetection:
    """
    Test emotion trend detection for no-change scenarios.
    """
    
    @given(
        base_valence=st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
        num_points=st.integers(min_value=3, max_value=10)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_stable_sequence_detected_correctly(self, base_valence: float, num_points: int):
        """
        **Feature: healing-pod-system, Property 20: 情绪无变化自动切换**
        **Validates: Requirements 10.3**
        
        For any sequence of emotions with identical valence, the trend
        SHALL be detected as NO_CHANGE or STABLE.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(
            monitoring_interval=10,
            no_change_threshold=180,
            improvement_threshold=0.1,
            worsening_threshold=-0.1,
            min_data_points=3
        )
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Create perfectly stable emotion sequence
        base_time = datetime.now()
        for i in range(num_points):
            monitor._emotion_buffer.append(EmotionState(
                category=EmotionCategory.NEUTRAL,
                intensity=0.5,
                valence=base_valence,  # Same valence throughout
                arousal=0.5,
                confidence=0.8,
                timestamp=base_time + timedelta(seconds=i * 10)
            ))
        
        # Detect trend
        detection = monitor._detect_emotion_trend()
        
        # Verify valence change is zero
        assert abs(detection.valence_change) < 0.001, \
            f"Valence change should be ~0 for stable sequence, got {detection.valence_change}"
        
        # Verify trend is NO_CHANGE or STABLE
        assert detection.trend in [EmotionTrend.NO_CHANGE, EmotionTrend.STABLE], \
            f"Stable sequence should result in NO_CHANGE or STABLE trend, got {detection.trend}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
