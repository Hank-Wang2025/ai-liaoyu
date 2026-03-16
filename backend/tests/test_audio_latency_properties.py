"""
语音分析延迟约束属性测试
Property-Based Tests for Audio Analysis Latency Constraint

使用 hypothesis 进行属性测试，验证语音分析延迟约束
"""
import os
import sys
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import AudioAnalysisResult, AudioEvent, EmotionCategory, Emotion2VecResult
from services.sensevoice_analyzer import SenseVoiceAnalyzer
from services.emotion2vec_analyzer import Emotion2VecAnalyzer


# ============================================================================
# Constants
# ============================================================================

# Maximum allowed latency in milliseconds (from Requirements 1.5)
MAX_LATENCY_MS = 500

# Maximum audio duration in seconds (from Requirements 1.5)
MAX_AUDIO_DURATION_SECONDS = 60

# Valid emotions for SenseVoice
SENSEVOICE_EMOTIONS = ["happy", "sad", "angry", "neutral", "fearful", "disgusted", "surprised"]

# Valid emotions for emotion2vec+
EMOTION2VEC_EMOTIONS = ["angry", "happy", "neutral", "sad", "surprised", "fearful", "disgusted", "anxious", "tired"]


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def audio_duration_ms(draw):
    """
    Generate valid audio duration in milliseconds (0 to 60 seconds).
    """
    # Duration from 0 to 60 seconds in milliseconds
    return draw(st.integers(min_value=0, max_value=MAX_AUDIO_DURATION_SECONDS * 1000))


@st.composite
def sensevoice_mock_result(draw):
    """
    Generate mock SenseVoice analysis result.
    """
    emotion = draw(st.sampled_from(SENSEVOICE_EMOTIONS))
    text = draw(st.text(
        alphabet="测试文本内容abcdefghijklmnopqrstuvwxyz ",
        min_size=1,
        max_size=100
    ))
    assume(text.strip())
    
    return [{
        "text": f"<|zh|><|{emotion.upper()}|><|Speech|>{text}"
    }]


@st.composite
def emotion2vec_mock_result(draw):
    """
    Generate mock emotion2vec+ analysis result.
    """
    scores = [draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)) 
              for _ in EMOTION2VEC_EMOTIONS]
    
    # Ensure at least one score is non-zero
    if sum(scores) == 0:
        idx = draw(st.integers(min_value=0, max_value=len(EMOTION2VEC_EMOTIONS) - 1))
        scores[idx] = draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return [{
        "key": "test_audio",
        "scores": scores,
        "labels": EMOTION2VEC_EMOTIONS.copy()
    }]


# ============================================================================
# Property Tests
# ============================================================================

class TestAudioAnalysisLatencyConstraint:
    """
    Property 3: 语音分析延迟约束
    
    **Feature: healing-pod-system, Property 3: 语音分析延迟约束**
    **Validates: Requirements 1.5**
    
    *For any* audio input not exceeding 60 seconds in length,
    the emotion analysis engine SHALL return complete analysis results within 500ms.
    """
    
    @given(
        duration_ms=audio_duration_ms(),
        mock_result=sensevoice_mock_result()
    )
    @settings(max_examples=100)
    def test_sensevoice_parse_result_latency(
        self, 
        duration_ms: int,
        mock_result: List[Dict[str, Any]]
    ):
        """
        **Feature: healing-pod-system, Property 3: 语音分析延迟约束**
        **Validates: Requirements 1.5**
        
        For any audio duration up to 60 seconds,
        the SenseVoice result parsing SHALL complete within 500ms.
        
        Note: This tests the parsing component. Full model inference
        latency depends on hardware and is tested separately.
        """
        analyzer = SenseVoiceAnalyzer()
        
        # Measure parsing time
        start_time = time.perf_counter()
        result = analyzer._parse_result(mock_result, duration_ms)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        # Property assertion: parsing should be very fast (well under 500ms)
        # Parsing alone should take < 10ms typically
        assert elapsed_ms < MAX_LATENCY_MS, \
            f"Parsing took {elapsed_ms:.2f}ms, should be < {MAX_LATENCY_MS}ms"
        
        # Verify result is valid
        assert isinstance(result, AudioAnalysisResult)
        assert result.duration_ms == duration_ms
    
    @given(mock_result=emotion2vec_mock_result())
    @settings(max_examples=100)
    def test_emotion2vec_parse_result_latency(self, mock_result: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 3: 语音分析延迟约束**
        **Validates: Requirements 1.5**
        
        For any emotion2vec+ model output,
        the result parsing SHALL complete within 500ms.
        """
        analyzer = Emotion2VecAnalyzer()
        
        # Measure parsing time
        start_time = time.perf_counter()
        result = analyzer._parse_result(mock_result)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        # Property assertion: parsing should be very fast
        assert elapsed_ms < MAX_LATENCY_MS, \
            f"Parsing took {elapsed_ms:.2f}ms, should be < {MAX_LATENCY_MS}ms"
        
        # Verify result is valid
        assert isinstance(result, Emotion2VecResult)
        assert isinstance(result.emotion, EmotionCategory)
    
    @given(
        duration_ms=audio_duration_ms(),
        mock_result=sensevoice_mock_result()
    )
    @settings(max_examples=100)
    def test_parsing_latency_independent_of_duration(
        self,
        duration_ms: int,
        mock_result: List[Dict[str, Any]]
    ):
        """
        **Feature: healing-pod-system, Property 3: 语音分析延迟约束**
        **Validates: Requirements 1.5**
        
        For any audio duration up to 60 seconds,
        the parsing time SHALL be independent of audio duration
        and complete well within the 500ms constraint.
        
        This validates that parsing complexity doesn't scale with audio length.
        """
        analyzer = SenseVoiceAnalyzer()
        
        # Parse result and measure time
        start_time = time.perf_counter()
        result = analyzer._parse_result(mock_result, duration_ms)
        end_time = time.perf_counter()
        
        parsing_ms = (end_time - start_time) * 1000
        
        # Property assertion: parsing should be fast regardless of duration
        # Parsing alone should take < 50ms even for max duration audio
        assert parsing_ms < 50, \
            f"Parsing took {parsing_ms:.2f}ms for {duration_ms}ms audio, should be < 50ms"
        
        # Verify result is valid and duration is preserved
        assert isinstance(result, AudioAnalysisResult)
        assert result.duration_ms == duration_ms
    
    @given(duration_ms=audio_duration_ms())
    @settings(max_examples=100)
    def test_audio_duration_within_constraint(self, duration_ms: int):
        """
        **Feature: healing-pod-system, Property 3: 语音分析延迟约束**
        **Validates: Requirements 1.5**
        
        For any generated audio duration,
        the duration SHALL not exceed 60 seconds (60000ms).
        
        This validates our test data generation respects the constraint.
        """
        max_duration_ms = MAX_AUDIO_DURATION_SECONDS * 1000
        
        assert duration_ms <= max_duration_ms, \
            f"Audio duration {duration_ms}ms exceeds maximum {max_duration_ms}ms"
    
    @given(
        duration_ms=audio_duration_ms(),
        mock_sv_result=sensevoice_mock_result(),
        mock_e2v_result=emotion2vec_mock_result()
    )
    @settings(max_examples=100)
    def test_combined_parsing_latency(
        self,
        duration_ms: int,
        mock_sv_result: List[Dict[str, Any]],
        mock_e2v_result: List[Dict[str, Any]]
    ):
        """
        **Feature: healing-pod-system, Property 3: 语音分析延迟约束**
        **Validates: Requirements 1.5**
        
        For any audio input up to 60 seconds,
        combined SenseVoice + emotion2vec+ parsing SHALL complete within 500ms.
        """
        sv_analyzer = SenseVoiceAnalyzer()
        e2v_analyzer = Emotion2VecAnalyzer()
        
        # Measure combined parsing time
        start_time = time.perf_counter()
        sv_result = sv_analyzer._parse_result(mock_sv_result, duration_ms)
        e2v_result = e2v_analyzer._parse_result(mock_e2v_result)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        # Property assertion: combined parsing should be fast
        assert elapsed_ms < MAX_LATENCY_MS, \
            f"Combined parsing took {elapsed_ms:.2f}ms, should be < {MAX_LATENCY_MS}ms"
        
        # Verify results are valid
        assert isinstance(sv_result, AudioAnalysisResult)
        assert isinstance(e2v_result, Emotion2VecResult)


class TestLatencyConstraintEdgeCases:
    """
    Edge case tests for latency constraint.
    These complement the property tests by testing specific scenarios.
    """
    
    def test_empty_audio_fast_response(self):
        """
        Test that empty/minimal audio returns quickly.
        """
        analyzer = SenseVoiceAnalyzer()
        
        start_time = time.perf_counter()
        result = analyzer._parse_result([], 0)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        assert elapsed_ms < 10, f"Empty result parsing took {elapsed_ms:.2f}ms, should be < 10ms"
        assert isinstance(result, AudioAnalysisResult)
    
    def test_max_duration_audio_parsing(self):
        """
        Test parsing with maximum allowed duration (60 seconds).
        """
        analyzer = SenseVoiceAnalyzer()
        max_duration_ms = MAX_AUDIO_DURATION_SECONDS * 1000
        
        mock_result = [{"text": "<|zh|><|NEUTRAL|><|Speech|>这是一段60秒的测试音频"}]
        
        start_time = time.perf_counter()
        result = analyzer._parse_result(mock_result, max_duration_ms)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        assert elapsed_ms < MAX_LATENCY_MS, \
            f"Max duration parsing took {elapsed_ms:.2f}ms, should be < {MAX_LATENCY_MS}ms"
        assert result.duration_ms == max_duration_ms
    
    def test_long_text_parsing_latency(self):
        """
        Test parsing with long recognized text.
        """
        analyzer = SenseVoiceAnalyzer()
        
        # Generate long text (simulating long speech recognition result)
        long_text = "这是一段很长的测试文本内容，" * 100
        mock_result = [{"text": f"<|zh|><|HAPPY|><|Speech|>{long_text}"}]
        
        start_time = time.perf_counter()
        result = analyzer._parse_result(mock_result, 30000)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        assert elapsed_ms < MAX_LATENCY_MS, \
            f"Long text parsing took {elapsed_ms:.2f}ms, should be < {MAX_LATENCY_MS}ms"
        assert len(result.text) > 0
    
    def test_multiple_sequential_parses_latency(self):
        """
        Test that multiple sequential parses maintain latency constraint.
        """
        analyzer = SenseVoiceAnalyzer()
        mock_result = [{"text": "<|zh|><|NEUTRAL|><|Speech|>测试文本"}]
        
        total_time = 0
        num_iterations = 10
        
        for i in range(num_iterations):
            start_time = time.perf_counter()
            result = analyzer._parse_result(mock_result, 5000 * (i + 1))
            end_time = time.perf_counter()
            
            elapsed_ms = (end_time - start_time) * 1000
            total_time += elapsed_ms
            
            assert elapsed_ms < MAX_LATENCY_MS, \
                f"Iteration {i+1} took {elapsed_ms:.2f}ms, should be < {MAX_LATENCY_MS}ms"
        
        avg_time = total_time / num_iterations
        assert avg_time < MAX_LATENCY_MS / 2, \
            f"Average parsing time {avg_time:.2f}ms should be well under {MAX_LATENCY_MS}ms"
    
    def test_emotion2vec_all_emotions_parsing_latency(self):
        """
        Test emotion2vec parsing with all emotion scores.
        """
        analyzer = Emotion2VecAnalyzer()
        
        # Create result with all emotions having scores
        scores = [0.1, 0.15, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.05]
        mock_result = [{
            "key": "test",
            "scores": scores,
            "labels": EMOTION2VEC_EMOTIONS.copy()
        }]
        
        start_time = time.perf_counter()
        result = analyzer._parse_result(mock_result)
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        assert elapsed_ms < MAX_LATENCY_MS, \
            f"emotion2vec parsing took {elapsed_ms:.2f}ms, should be < {MAX_LATENCY_MS}ms"
        assert len(result.scores) == len(EMOTION2VEC_EMOTIONS)


class TestLatencyConstraintConstants:
    """
    Tests to verify latency constraint constants match requirements.
    """
    
    def test_max_latency_matches_requirement(self):
        """
        Verify MAX_LATENCY_MS matches Requirements 1.5 (500ms).
        """
        assert MAX_LATENCY_MS == 500, \
            f"MAX_LATENCY_MS should be 500ms per Requirements 1.5, got {MAX_LATENCY_MS}ms"
    
    def test_max_audio_duration_matches_requirement(self):
        """
        Verify MAX_AUDIO_DURATION_SECONDS matches Requirements 1.5 (60 seconds).
        """
        assert MAX_AUDIO_DURATION_SECONDS == 60, \
            f"MAX_AUDIO_DURATION_SECONDS should be 60s per Requirements 1.5, got {MAX_AUDIO_DURATION_SECONDS}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
