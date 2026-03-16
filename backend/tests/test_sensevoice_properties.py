"""
SenseVoice 属性测试
Property-Based Tests for SenseVoice Analyzer

使用 hypothesis 进行属性测试，验证语音识别输出完整性
"""
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import AudioAnalysisResult, AudioEvent
from services.sensevoice_analyzer import SenseVoiceAnalyzer


# ============================================================================
# Strategies for generating test data
# ============================================================================

# Valid SenseVoice emotion tags
VALID_EMOTIONS = ["HAPPY", "SAD", "ANGRY", "NEUTRAL", "FEARFUL", "DISGUSTED", "SURPRISED"]

# Valid SenseVoice audio events
VALID_EVENTS = ["Laughter", "Crying", "Cough", "Sigh", "Applause", "BGM", "Speech"]

# Valid language codes
VALID_LANGUAGES = ["zh", "en", "yue", "ja", "ko"]


@st.composite
def sensevoice_raw_output(draw):
    """
    Generate valid SenseVoice model raw output format.
    
    SenseVoice output format: <|language|><|EMOTION|><|Event|>text content
    """
    language = draw(st.sampled_from(VALID_LANGUAGES))
    emotion = draw(st.sampled_from(VALID_EMOTIONS))
    event = draw(st.sampled_from(VALID_EVENTS))
    
    # Generate non-empty text content (Chinese or English)
    text_content = draw(st.one_of(
        # Chinese text
        st.text(
            alphabet="你好世界测试文本内容情绪分析语音识别今天天气很好我感到开心难过生气",
            min_size=1,
            max_size=100
        ),
        # English text
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ",
            min_size=1,
            max_size=100
        )
    ))
    
    # Ensure text is not just whitespace
    assume(text_content.strip())
    
    # Build the tagged output string
    tagged_text = f"<|{language}|><|{emotion}|><|{event}|>{text_content}"
    
    return [{"text": tagged_text}]


@st.composite
def sensevoice_partial_output(draw):
    """
    Generate SenseVoice output with partial tags (some tags may be missing).
    This tests the robustness of parsing.
    """
    include_language = draw(st.booleans())
    include_emotion = draw(st.booleans())
    include_event = draw(st.booleans())
    
    # At least one tag should be present for this to be a valid partial output
    assume(include_language or include_emotion or include_event)
    
    parts = []
    if include_language:
        language = draw(st.sampled_from(VALID_LANGUAGES))
        parts.append(f"<|{language}|>")
    if include_emotion:
        emotion = draw(st.sampled_from(VALID_EMOTIONS))
        parts.append(f"<|{emotion}|>")
    if include_event:
        event = draw(st.sampled_from(VALID_EVENTS))
        parts.append(f"<|{event}|>")
    
    # Generate text content
    text_content = draw(st.text(
        alphabet="测试文本内容abcdefghijklmnopqrstuvwxyz ",
        min_size=1,
        max_size=50
    ))
    assume(text_content.strip())
    
    tagged_text = "".join(parts) + text_content
    
    return [{"text": tagged_text}]


# ============================================================================
# Property Tests
# ============================================================================

class TestSenseVoiceOutputCompleteness:
    """
    Property 1: 语音识别输出完整性
    
    **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
    **Validates: Requirements 1.2**
    
    *For any* valid audio input, the SenseVoice model output SHALL contain:
    - text content (文本内容)
    - emotion label (情感标签)
    - audio event detection result (音频事件检测结果)
    
    All fields SHALL not be empty.
    """
    
    @given(raw_output=sensevoice_raw_output())
    @settings(max_examples=100)
    def test_parse_result_contains_all_required_fields(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any valid SenseVoice raw output with complete tags,
        the parsed AudioAnalysisResult SHALL contain:
        1. Non-empty text field
        2. Non-empty emotion field
        3. Non-empty event field
        """
        analyzer = SenseVoiceAnalyzer()
        duration_ms = 1000  # Arbitrary duration for testing
        
        # Parse the raw output
        result = analyzer._parse_result(raw_output, duration_ms)
        
        # Property assertions
        # 1. Result should be an AudioAnalysisResult
        assert isinstance(result, AudioAnalysisResult), \
            f"Expected AudioAnalysisResult, got {type(result)}"
        
        # 2. Text field should not be empty
        assert result.text is not None, "text field should not be None"
        assert isinstance(result.text, str), f"text should be str, got {type(result.text)}"
        assert len(result.text.strip()) > 0, \
            f"text field should not be empty, got: '{result.text}'"
        
        # 3. Emotion field should not be empty
        assert result.emotion is not None, "emotion field should not be None"
        assert isinstance(result.emotion, str), f"emotion should be str, got {type(result.emotion)}"
        assert len(result.emotion) > 0, \
            f"emotion field should not be empty, got: '{result.emotion}'"
        
        # 4. Event field should not be empty
        assert result.event is not None, "event field should not be None"
        assert isinstance(result.event, str), f"event should be str, got {type(result.event)}"
        assert len(result.event) > 0, \
            f"event field should not be empty, got: '{result.event}'"
        
        # 5. Language field should be present (additional completeness check)
        assert result.language is not None, "language field should not be None"
        assert isinstance(result.language, str), f"language should be str, got {type(result.language)}"
    
    @given(raw_output=sensevoice_raw_output())
    @settings(max_examples=100)
    def test_emotion_is_valid_category(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any valid SenseVoice raw output,
        the parsed emotion SHALL be one of the valid emotion categories.
        """
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result(raw_output, 1000)
        
        valid_emotions = analyzer.get_emotion_labels()
        assert result.emotion in valid_emotions, \
            f"emotion '{result.emotion}' should be one of {valid_emotions}"
    
    @given(raw_output=sensevoice_raw_output())
    @settings(max_examples=100)
    def test_event_is_valid_type(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any valid SenseVoice raw output,
        the parsed event SHALL be one of the valid audio event types.
        """
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result(raw_output, 1000)
        
        valid_events = analyzer.get_audio_events()
        # Also include 'none' as a valid event (when no special event detected)
        valid_events_with_none = valid_events + [AudioEvent.NONE.value]
        
        assert result.event in valid_events_with_none, \
            f"event '{result.event}' should be one of {valid_events_with_none}"
    
    @given(raw_output=sensevoice_raw_output())
    @settings(max_examples=100)
    def test_language_is_valid(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any valid SenseVoice raw output,
        the parsed language SHALL be one of the supported languages.
        """
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result(raw_output, 1000)
        
        valid_languages = analyzer.get_supported_languages()
        # Map to actual language values
        language_values = [analyzer.LANGUAGE_MAP.get(lang, lang) for lang in valid_languages]
        language_values.append("unknown")  # Unknown is also valid for edge cases
        
        assert result.language in language_values, \
            f"language '{result.language}' should be one of {language_values}"
    
    @given(raw_output=sensevoice_partial_output())
    @settings(max_examples=100)
    def test_partial_output_still_produces_valid_result(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any SenseVoice output with partial tags,
        the parser SHALL still produce a valid AudioAnalysisResult
        with default values for missing fields.
        """
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result(raw_output, 1000)
        
        # Result should always be valid AudioAnalysisResult
        assert isinstance(result, AudioAnalysisResult)
        
        # All fields should have values (even if defaults)
        assert result.text is not None
        assert result.emotion is not None
        assert result.event is not None
        assert result.language is not None
        
        # Emotion should be valid (defaults to 'neutral' if not detected)
        valid_emotions = analyzer.get_emotion_labels()
        assert result.emotion in valid_emotions
        
        # Event should be valid (defaults to 'none' if not detected)
        valid_events = analyzer.get_audio_events() + [AudioEvent.NONE.value]
        assert result.event in valid_events
    
    @given(duration_ms=st.integers(min_value=0, max_value=600000))
    @settings(max_examples=100)
    def test_duration_preserved_in_result(self, duration_ms: int):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any valid duration value,
        the parsed result SHALL preserve the duration_ms value.
        """
        analyzer = SenseVoiceAnalyzer()
        raw_output = [{"text": "<|zh|><|NEUTRAL|><|Speech|>测试文本"}]
        
        result = analyzer._parse_result(raw_output, duration_ms)
        
        assert result.duration_ms == duration_ms, \
            f"duration_ms should be {duration_ms}, got {result.duration_ms}"
    
    @given(raw_output=sensevoice_raw_output())
    @settings(max_examples=100)
    def test_confidence_in_valid_range(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any valid SenseVoice raw output,
        the confidence score SHALL be in the range [0, 1].
        """
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result(raw_output, 1000)
        
        assert 0 <= result.confidence <= 1, \
            f"confidence should be in [0, 1], got {result.confidence}"
    
    @given(raw_output=sensevoice_raw_output())
    @settings(max_examples=100)
    def test_timestamp_is_present(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 1: 语音识别输出完整性**
        **Validates: Requirements 1.2**
        
        For any valid SenseVoice raw output,
        the result SHALL include a timestamp.
        """
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result(raw_output, 1000)
        
        assert result.timestamp is not None, "timestamp should not be None"
        assert isinstance(result.timestamp, datetime), \
            f"timestamp should be datetime, got {type(result.timestamp)}"


class TestSenseVoiceEdgeCases:
    """
    Edge case tests for SenseVoice output parsing.
    These complement the property tests by testing specific edge cases.
    """
    
    def test_empty_result_handling(self):
        """Test handling of empty model output"""
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result([], 1000)
        
        assert isinstance(result, AudioAnalysisResult)
        assert result.text == ""
        assert result.emotion == "neutral"
        assert result.event == AudioEvent.NONE.value
        assert result.confidence == 0.0
    
    def test_none_result_handling(self):
        """Test handling of None model output"""
        analyzer = SenseVoiceAnalyzer()
        
        result = analyzer._parse_result(None, 1000)
        
        assert isinstance(result, AudioAnalysisResult)
        assert result.text == ""
        assert result.emotion == "neutral"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
