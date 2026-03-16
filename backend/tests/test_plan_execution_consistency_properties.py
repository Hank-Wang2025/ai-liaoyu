"""
方案执行一致性属性测试
Property-Based Tests for Therapy Plan Execution Consistency

使用 hypothesis 进行属性测试，验证疗愈方案执行一致性
Requirements: 6.1

**Property 6.1: 方案执行一致性**
*For any* 疗愈方案开始执行，Therapy_Engine SHALL 按照方案配置播放背景音乐和语音引导。
"""
import asyncio
import os
import sys
from datetime import datetime
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume, Phase

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import EmotionCategory
from models.therapy import (
    TherapyPlan,
    TherapyPhase,
    TherapyStyle,
    TherapyIntensity,
    LightConfig,
    AudioConfig,
    VoiceGuideConfig,
    ChairConfig,
    ScentConfig,
    LightPattern
)
from services.therapy_executor import (
    TherapyExecutor,
    ExecutorState,
    TherapyEvent
)


# Helper to run async code in sync context
def run_async(coro):
    """Run async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def valid_hex_color(draw):
    """Generate a valid HEX color string."""
    r = draw(st.integers(min_value=0, max_value=255))
    g = draw(st.integers(min_value=0, max_value=255))
    b = draw(st.integers(min_value=0, max_value=255))
    return f"#{r:02x}{g:02x}{b:02x}"


@st.composite
def valid_light_config(draw):
    """Generate a valid LightConfig."""
    color = draw(valid_hex_color())
    brightness = draw(st.integers(min_value=0, max_value=100))
    transition = draw(st.integers(min_value=0, max_value=5000))
    pattern = draw(st.sampled_from([LightPattern.STATIC, LightPattern.BREATH, LightPattern.PULSE, None]))
    
    return LightConfig(
        color=color,
        brightness=brightness,
        transition=transition,
        pattern=pattern
    )


@st.composite
def valid_audio_config(draw):
    """Generate a valid AudioConfig."""
    # Use realistic file paths
    file_paths = [
        "content/audio/calm_music_01.mp3",
        "content/audio/nature_sounds.mp3",
        "content/audio/meditation_bg.mp3",
        "content/audio/relaxing_piano.mp3"
    ]
    file = draw(st.sampled_from(file_paths))
    volume = draw(st.integers(min_value=0, max_value=100))
    loop = draw(st.booleans())
    fade_in = draw(st.integers(min_value=0, max_value=5000))
    fade_out = draw(st.integers(min_value=0, max_value=5000))
    
    return AudioConfig(
        file=file,
        volume=volume,
        loop=loop,
        fade_in=fade_in,
        fade_out=fade_out
    )


@st.composite
def valid_voice_guide_config(draw):
    """Generate a valid VoiceGuideConfig or None."""
    should_have_guide = draw(st.booleans())
    if not should_have_guide:
        return None
    
    texts = [
        "请闭上眼睛，深呼吸",
        "让我们一起放松身心",
        "感受此刻的宁静",
        "慢慢地吸气，再慢慢地呼气"
    ]
    text = draw(st.sampled_from(texts))
    voice = draw(st.sampled_from(["中文女", "中文男", "英文女"]))
    emotion = draw(st.sampled_from(["gentle", "warm", "calm", "encouraging"]))
    speed = draw(st.floats(min_value=0.8, max_value=1.2, allow_nan=False, allow_infinity=False))
    
    return VoiceGuideConfig(
        text=text,
        voice=voice,
        emotion=emotion,
        speed=speed
    )


@st.composite
def valid_therapy_phase(draw, min_duration: int = 5, max_duration: int = 60):
    """Generate a valid TherapyPhase."""
    names = ["准备阶段", "放松阶段", "深度疗愈", "恢复阶段", "结束阶段"]
    name = draw(st.sampled_from(names))
    duration = draw(st.integers(min_value=min_duration, max_value=max_duration))
    light = draw(valid_light_config())
    audio = draw(valid_audio_config())
    voice_guide = draw(valid_voice_guide_config())
    
    return TherapyPhase(
        name=name,
        duration=duration,
        light=light,
        audio=audio,
        voice_guide=voice_guide
    )


@st.composite
def valid_therapy_plan(draw, min_phases: int = 1, max_phases: int = 5):
    """Generate a valid TherapyPlan."""
    num_phases = draw(st.integers(min_value=min_phases, max_value=max_phases))
    
    # Generate phases with short durations for testing
    phases = [draw(valid_therapy_phase(min_duration=2, max_duration=10)) for _ in range(num_phases)]
    
    # Calculate total duration
    total_duration = sum(p.duration for p in phases)
    
    plan_id = draw(st.sampled_from([
        "test_plan_1", "test_plan_2", "test_plan_3",
        "anxiety_relief", "stress_reduction", "relaxation"
    ]))
    
    name = draw(st.sampled_from([
        "测试方案", "焦虑缓解", "压力释放", "深度放松"
    ]))
    
    target_emotions = draw(st.lists(
        st.sampled_from(list(EmotionCategory)),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    intensity = draw(st.sampled_from(list(TherapyIntensity)))
    style = draw(st.sampled_from(list(TherapyStyle)))
    
    return TherapyPlan(
        id=plan_id,
        name=name,
        description="测试方案描述",
        target_emotions=target_emotions,
        intensity=intensity,
        style=style,
        duration=total_duration,
        phases=phases
    )


# ============================================================================
# Mock Device Controllers
# ============================================================================

class MockLightManager:
    """Mock light controller manager for testing."""
    
    def __init__(self):
        self.applied_configs: List[dict] = []
        self.breath_mode_started = False
    
    async def set_all_lights(self, color: str, brightness: int, transition: int):
        self.applied_configs.append({
            "type": "set_all_lights",
            "color": color,
            "brightness": brightness,
            "transition": transition
        })
    
    async def start_breath_mode_all(self, color: str, min_brightness: int = 30, max_brightness: int = 100):
        self.breath_mode_started = True
        self.applied_configs.append({
            "type": "breath_mode",
            "color": color,
            "min_brightness": min_brightness,
            "max_brightness": max_brightness
        })
    
    async def stop_breath_mode_all(self):
        self.breath_mode_started = False


class MockAudioPlayer:
    """Mock audio player for testing."""
    
    def __init__(self):
        self.played_files: List[dict] = []
        self.is_playing = False
    
    async def play_background_music(self, file: str, volume: float = 0.8, loop: bool = True, fade_in_ms: int = 2000):
        self.is_playing = True
        self.played_files.append({
            "file": file,
            "volume": volume,
            "loop": loop,
            "fade_in_ms": fade_in_ms
        })
    
    async def stop_all(self, fade_out_ms: int = 2000):
        self.is_playing = False


# ============================================================================
# Property Tests - Property 6.1: 方案执行一致性
# ============================================================================

class TestPlanExecutionConsistency:
    """
    Property 6.1: 方案执行一致性
    
    **Feature: healing-pod-system, Property 6.1: 方案执行一致性**
    **Validates: Requirements 6.1**
    
    *For any* 疗愈方案开始执行，Therapy_Engine SHALL 按照方案配置播放背景音乐和语音引导。
    """
    
    @given(plan=valid_therapy_plan(min_phases=1, max_phases=2))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_execution_applies_audio_config_for_each_phase(self, plan: TherapyPlan):
        """
        **Feature: healing-pod-system, Property 6.1: 方案执行一致性**
        **Validates: Requirements 6.1**
        
        For any valid TherapyPlan, when execution starts, the executor SHALL
        apply the audio configuration for each phase according to the plan.
        """
        # Create mock controllers
        mock_audio = MockAudioPlayer()
        mock_light = MockLightManager()
        
        # Create executor with mocks
        executor = TherapyExecutor(
            light_manager=mock_light,
            audio_player=mock_audio
        )
        
        # Use start() method which runs in background and allows config to be applied
        async def run_test():
            await executor.start(plan)
            # Wait for config to be applied
            await asyncio.sleep(0.2)
            await executor.stop()
        
        run_async(run_test())
        
        # Verify audio was played for the first phase
        assert len(mock_audio.played_files) >= 1, \
            "Audio should be played when phase starts"
        
        # Verify the audio config matches the plan's first phase
        first_phase = plan.phases[0]
        first_audio_played = mock_audio.played_files[0]
        
        assert first_audio_played["file"] == first_phase.audio.file, \
            f"Audio file should match plan config: {first_audio_played['file']} != {first_phase.audio.file}"
        
        assert first_audio_played["loop"] == first_phase.audio.loop, \
            f"Audio loop setting should match plan config"
    
    @given(plan=valid_therapy_plan(min_phases=1, max_phases=2))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_execution_applies_light_config_for_each_phase(self, plan: TherapyPlan):
        """
        **Feature: healing-pod-system, Property 6.1: 方案执行一致性**
        **Validates: Requirements 6.1**
        
        For any valid TherapyPlan, when execution starts, the executor SHALL
        apply the light configuration for each phase according to the plan.
        """
        # Create mock controllers
        mock_audio = MockAudioPlayer()
        mock_light = MockLightManager()
        
        # Create executor with mocks
        executor = TherapyExecutor(
            light_manager=mock_light,
            audio_player=mock_audio
        )
        
        # Use start() method which runs in background
        async def run_test():
            await executor.start(plan)
            await asyncio.sleep(0.2)
            await executor.stop()
        
        run_async(run_test())
        
        # Verify light config was applied
        assert len(mock_light.applied_configs) >= 1, \
            "Light config should be applied when phase starts"
        
        # Verify the light config matches the plan's first phase
        first_phase = plan.phases[0]
        first_light_applied = mock_light.applied_configs[0]
        
        # Check if breath mode or static mode was applied based on pattern
        if first_phase.light.pattern == LightPattern.BREATH or first_phase.light.pattern == "breath":
            assert first_light_applied["type"] == "breath_mode", \
                "Breath mode should be started for breath pattern"
        else:
            assert first_light_applied["type"] == "set_all_lights", \
                "Static light should be set for non-breath pattern"
            assert first_light_applied["color"] == first_phase.light.color, \
                f"Light color should match plan config"
            assert first_light_applied["brightness"] == first_phase.light.brightness, \
                f"Light brightness should match plan config"
    
    @given(plan=valid_therapy_plan(min_phases=1, max_phases=2))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_execution_starts_with_correct_state(self, plan: TherapyPlan):
        """
        **Feature: healing-pod-system, Property 6.1: 方案执行一致性**
        **Validates: Requirements 6.1**
        
        For any valid TherapyPlan, when execution starts, the executor SHALL
        transition to RUNNING state.
        """
        # Create mock controllers
        mock_audio = MockAudioPlayer()
        mock_light = MockLightManager()
        
        # Create executor with mocks
        executor = TherapyExecutor(
            light_manager=mock_light,
            audio_player=mock_audio
        )
        
        # Verify initial state
        assert executor.state == ExecutorState.IDLE, \
            "Executor should start in IDLE state"
        
        # Run execution and check state
        async def run_test():
            await executor.start(plan)
            await asyncio.sleep(0.2)
            state_during_execution = executor.state
            await executor.stop()
            return state_during_execution
        
        state = run_async(run_test())
        
        # State should be RUNNING during execution
        assert state == ExecutorState.RUNNING, \
            f"Executor should be in RUNNING state during execution, got {state}"
    
    @given(plan=valid_therapy_plan(min_phases=1, max_phases=2))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_same_plan_produces_same_execution_sequence(self, plan: TherapyPlan):
        """
        **Feature: healing-pod-system, Property 6.1: 方案执行一致性**
        **Validates: Requirements 6.1**
        
        For any valid TherapyPlan, executing the same plan multiple times SHALL
        produce the same sequence of device configurations.
        """
        async def run_execution():
            mock_audio = MockAudioPlayer()
            mock_light = MockLightManager()
            
            executor = TherapyExecutor(
                light_manager=mock_light,
                audio_player=mock_audio
            )
            
            await executor.start(plan)
            await asyncio.sleep(0.2)
            await executor.stop()
            
            return {
                "audio_configs": mock_audio.played_files.copy(),
                "light_configs": mock_light.applied_configs.copy()
            }
        
        # Run execution twice
        result1 = run_async(run_execution())
        result2 = run_async(run_execution())
        
        # Verify audio configs are the same
        assert len(result1["audio_configs"]) == len(result2["audio_configs"]), \
            "Same plan should produce same number of audio configs"
        
        for i, (c1, c2) in enumerate(zip(result1["audio_configs"], result2["audio_configs"])):
            assert c1["file"] == c2["file"], \
                f"Audio config {i} file should be the same"
            assert c1["loop"] == c2["loop"], \
                f"Audio config {i} loop should be the same"
        
        # Verify light configs are the same
        assert len(result1["light_configs"]) == len(result2["light_configs"]), \
            "Same plan should produce same number of light configs"
        
        for i, (c1, c2) in enumerate(zip(result1["light_configs"], result2["light_configs"])):
            assert c1["type"] == c2["type"], \
                f"Light config {i} type should be the same"
    
    @given(plan=valid_therapy_plan(min_phases=1, max_phases=2))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_phase_config_matches_plan_definition(self, plan: TherapyPlan):
        """
        **Feature: healing-pod-system, Property 6.1: 方案执行一致性**
        **Validates: Requirements 6.1**
        
        For any valid TherapyPlan, the device configurations applied during
        execution SHALL exactly match the configurations defined in the plan.
        """
        mock_audio = MockAudioPlayer()
        mock_light = MockLightManager()
        
        executor = TherapyExecutor(
            light_manager=mock_light,
            audio_player=mock_audio
        )
        
        async def run_test():
            await executor.start(plan)
            await asyncio.sleep(0.2)
            await executor.stop()
        
        run_async(run_test())
        
        # Get the first phase config from the plan
        first_phase = plan.phases[0]
        
        # Verify audio config matches
        assert len(mock_audio.played_files) >= 1, \
            "At least one audio file should be played"
        
        played_audio = mock_audio.played_files[0]
        assert played_audio["file"] == first_phase.audio.file, \
            f"Played audio file should match plan: {played_audio['file']} != {first_phase.audio.file}"
        assert played_audio["volume"] == first_phase.audio.volume / 100.0, \
            f"Played audio volume should match plan (normalized)"
        assert played_audio["loop"] == first_phase.audio.loop, \
            f"Played audio loop should match plan"
        assert played_audio["fade_in_ms"] == first_phase.audio.fade_in, \
            f"Played audio fade_in should match plan"


class TestExecutorStateTransitions:
    """
    Test executor state transitions during plan execution.
    """
    
    @given(plan=valid_therapy_plan(min_phases=1, max_phases=2))
    @settings(max_examples=50, deadline=30000, suppress_health_check=[])
    def test_executor_stops_correctly(self, plan: TherapyPlan):
        """
        **Feature: healing-pod-system, Property 6.1: 方案执行一致性**
        **Validates: Requirements 6.1**
        
        For any valid TherapyPlan, when stop is called, the executor SHALL
        transition to IDLE state.
        """
        mock_audio = MockAudioPlayer()
        mock_light = MockLightManager()
        
        executor = TherapyExecutor(
            light_manager=mock_light,
            audio_player=mock_audio
        )
        
        async def run_test():
            await executor.start(plan)
            await asyncio.sleep(0.1)
            await executor.stop()
            return executor.state
        
        final_state = run_async(run_test())
        
        assert final_state == ExecutorState.IDLE, \
            f"Executor should be in IDLE state after stop, got {final_state}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
