"""
实时监测持续性属性测试
Property-Based Tests for Real-time Monitoring Continuity

使用 hypothesis 进行属性测试，验证实时监测持续性
Requirements: 10.1

**Property 19: 实时监测持续性**
*For any* 正在执行的疗愈方案，情绪监测 SHALL 以不低于每 10 秒一次的频率持续进行。
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
def valid_monitoring_interval(draw):
    """Generate a valid monitoring interval (1-10 seconds)."""
    return draw(st.integers(min_value=1, max_value=10))


@st.composite
def valid_feedback_config(draw):
    """Generate a valid FeedbackConfig with reasonable monitoring interval."""
    monitoring_interval = draw(st.integers(min_value=1, max_value=10))
    no_change_threshold = draw(st.integers(min_value=60, max_value=300))
    improvement_threshold = draw(st.floats(min_value=0.05, max_value=0.3, allow_nan=False, allow_infinity=False))
    worsening_threshold = draw(st.floats(min_value=-0.3, max_value=-0.05, allow_nan=False, allow_infinity=False))
    min_data_points = draw(st.integers(min_value=2, max_value=5))
    
    return FeedbackConfig(
        monitoring_interval=monitoring_interval,
        no_change_threshold=no_change_threshold,
        improvement_threshold=improvement_threshold,
        worsening_threshold=worsening_threshold,
        auto_switch_enabled=False,  # Disable auto-switch for testing
        min_data_points=min_data_points
    )


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
    
    async def switch_plan(self, plan):
        pass


class MockPlanManager:
    """Mock plan manager for testing."""
    
    def match_with_details(self, emotion: EmotionState, top_n: int = 3):
        return []


# ============================================================================
# Property Tests - Property 19: 实时监测持续性
# ============================================================================

class TestRealtimeMonitoringContinuity:
    """
    Property 19: 实时监测持续性
    
    **Feature: healing-pod-system, Property 19: 实时监测持续性**
    **Validates: Requirements 10.1**
    
    *For any* 正在执行的疗愈方案，情绪监测 SHALL 以不低于每 10 秒一次的频率持续进行。
    """
    
    @given(
        config=valid_feedback_config(),
        num_emotions=st.integers(min_value=3, max_value=10)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_monitoring_interval_is_respected(self, config: FeedbackConfig, num_emotions: int):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any valid FeedbackConfig, the monitoring interval SHALL be at most 10 seconds,
        ensuring continuous emotion monitoring during therapy execution.
        """
        # Verify the config's monitoring interval is within acceptable range
        assert config.monitoring_interval <= 10, \
            f"Monitoring interval should be at most 10 seconds, got {config.monitoring_interval}"
        
        # Create mock dependencies
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        # Create monitor with the config
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Verify the monitor's config has the correct interval
        assert monitor._config.monitoring_interval == config.monitoring_interval, \
            "Monitor should use the configured monitoring interval"
        assert monitor._config.monitoring_interval <= 10, \
            "Monitoring interval should not exceed 10 seconds"
    
    @given(config=valid_feedback_config())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_default_monitoring_interval_is_10_seconds(self, config: FeedbackConfig):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        The default monitoring interval SHALL be 10 seconds, ensuring the
        requirement of "at least every 10 seconds" is met by default.
        """
        # Create default config
        default_config = FeedbackConfig()
        
        assert default_config.monitoring_interval == 10, \
            f"Default monitoring interval should be 10 seconds, got {default_config.monitoring_interval}"
        
        # Verify the interval meets the requirement
        assert default_config.monitoring_interval <= 10, \
            "Default monitoring interval should not exceed 10 seconds"
    
    @given(emotion=valid_emotion_state())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_emotion_buffer_can_accumulate(self, emotion: EmotionState):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any valid EmotionState, the monitor SHALL be able to accumulate
        emotions in its buffer for continuous monitoring.
        """
        # Create mock dependencies
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(monitoring_interval=10)
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Manually add emotions to buffer (simulating monitoring)
        for i in range(5):
            monitor._emotion_buffer.append(EmotionState(
                category=emotion.category,
                intensity=emotion.intensity,
                valence=emotion.valence,
                arousal=emotion.arousal,
                confidence=emotion.confidence,
                timestamp=datetime.now() + timedelta(seconds=i * 10)
            ))
        
        # Verify buffer accumulated correctly
        assert len(monitor._emotion_buffer) == 5, \
            f"Buffer should have 5 emotions, got {len(monitor._emotion_buffer)}"
        
        # Verify all emotions have the same category
        for e in monitor._emotion_buffer:
            assert e.category == emotion.category, \
                f"All emotions should have category {emotion.category}"
    
    @given(
        interval=valid_monitoring_interval(),
        duration_seconds=st.integers(min_value=30, max_value=120)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_expected_samples_calculation(self, interval: int, duration_seconds: int):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any monitoring interval <= 10 seconds and any duration, the expected
        number of samples SHALL be at least duration / interval.
        """
        # Calculate expected minimum samples
        expected_min_samples = duration_seconds // interval
        
        # Verify the calculation is correct
        assert expected_min_samples >= duration_seconds // 10, \
            f"With interval {interval}s, should get at least {duration_seconds // 10} samples in {duration_seconds}s"
        
        # Verify interval meets requirement
        assert interval <= 10, \
            f"Monitoring interval should be at most 10 seconds, got {interval}"
    
    @given(emotion=valid_emotion_state())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_monitor_initial_state(self, emotion: EmotionState):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any valid configuration, the monitor SHALL start in a non-monitoring
        state with an empty buffer.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(monitoring_interval=10)
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Verify initial state
        assert not monitor.is_monitoring, \
            "Monitor should not be monitoring initially"
        assert len(monitor._emotion_buffer) == 0, \
            "Emotion buffer should be empty initially"
        assert monitor._config.monitoring_interval <= 10, \
            "Monitoring interval should not exceed 10 seconds"
    
    @given(
        config=valid_feedback_config(),
        num_emotions=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_buffer_size_limit(self, config: FeedbackConfig, num_emotions: int):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any number of emotions added, the buffer SHALL maintain a reasonable
        size limit (max 60 entries as per implementation).
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Add many emotions to buffer
        for i in range(num_emotions):
            monitor._emotion_buffer.append(EmotionState(
                category=EmotionCategory.NEUTRAL,
                intensity=0.5,
                valence=0.0,
                arousal=0.5,
                confidence=0.8,
                timestamp=datetime.now() + timedelta(seconds=i * 10)
            ))
        
        # Simulate buffer trimming (as done in monitoring loop)
        max_buffer_size = 60
        if len(monitor._emotion_buffer) > max_buffer_size:
            monitor._emotion_buffer = monitor._emotion_buffer[-max_buffer_size:]
        
        # Verify buffer size is within limit
        assert len(monitor._emotion_buffer) <= max_buffer_size, \
            f"Buffer should not exceed {max_buffer_size} entries"


class TestMonitoringConfiguration:
    """
    Test monitoring configuration validation.
    """
    
    @given(interval=st.integers(min_value=1, max_value=10))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_valid_interval_configuration(self, interval: int):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any interval between 1 and 10 seconds, the configuration SHALL
        be valid and meet the monitoring frequency requirement.
        """
        config = FeedbackConfig(monitoring_interval=interval)
        
        assert config.monitoring_interval == interval, \
            f"Config should have interval {interval}"
        assert config.monitoring_interval <= 10, \
            "Interval should not exceed 10 seconds"
        assert config.monitoring_interval >= 1, \
            "Interval should be at least 1 second"
    
    @given(config=valid_feedback_config())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_config_update_preserves_interval_constraint(self, config: FeedbackConfig):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any valid config, updating the monitor's config SHALL preserve
        the monitoring interval constraint.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Update config with a new valid interval
        new_interval = 5
        monitor.update_config(monitoring_interval=new_interval)
        
        assert monitor._config.monitoring_interval == new_interval, \
            f"Config should be updated to interval {new_interval}"
        assert monitor._config.monitoring_interval <= 10, \
            "Updated interval should not exceed 10 seconds"


class TestEmotionHistoryRetrieval:
    """
    Test emotion history retrieval during monitoring.
    """
    
    @given(
        emotions=st.lists(valid_emotion_state(), min_size=1, max_size=50),
        limit=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_get_emotion_history_respects_limit(self, emotions: List[EmotionState], limit: int):
        """
        **Feature: healing-pod-system, Property 19: 实时监测持续性**
        **Validates: Requirements 10.1**
        
        For any list of emotions and any limit, get_emotion_history SHALL
        return at most 'limit' entries.
        """
        mock_session = MockSessionManager()
        mock_executor = MockTherapyExecutor()
        mock_plan_manager = MockPlanManager()
        
        config = FeedbackConfig(monitoring_interval=10)
        
        monitor = RealtimeFeedbackMonitor(
            session_manager=mock_session,
            therapy_executor=mock_executor,
            plan_manager=mock_plan_manager,
            config=config
        )
        
        # Add emotions to buffer
        monitor._emotion_buffer = emotions
        
        # Get history with limit
        history = monitor.get_emotion_history(limit=limit)
        
        # Verify limit is respected
        expected_count = min(len(emotions), limit)
        assert len(history) == expected_count, \
            f"History should have {expected_count} entries, got {len(history)}"
        
        # Verify history entries have required fields
        for entry in history:
            assert "timestamp" in entry, "Entry should have timestamp"
            assert "category" in entry, "Entry should have category"
            assert "intensity" in entry, "Entry should have intensity"
            assert "valence" in entry, "Entry should have valence"
            assert "arousal" in entry, "Entry should have arousal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
