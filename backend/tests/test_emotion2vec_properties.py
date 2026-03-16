"""
emotion2vec+ 属性测试
Property-Based Tests for emotion2vec+ Analyzer

使用 hypothesis 进行属性测试，验证情绪分类范围约束
"""
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import EmotionCategory, Emotion2VecResult
from services.emotion2vec_analyzer import Emotion2VecAnalyzer


# ============================================================================
# Strategies for generating test data
# ============================================================================

# Valid emotion2vec+ emotion labels (9 classes)
VALID_EMOTION_LABELS = [
    "angry",      # 生气
    "happy",      # 开心
    "neutral",    # 中立
    "sad",        # 难过
    "surprised",  # 惊讶
    "fearful",    # 恐惧
    "disgusted",  # 厌恶
    "anxious",    # 焦虑
    "tired"       # 疲惫
]


@st.composite
def emotion_scores_dict(draw):
    """
    Generate valid emotion scores dictionary.
    
    Scores are floats between 0 and 1, and will be normalized.
    """
    scores = {}
    for label in VALID_EMOTION_LABELS:
        scores[label] = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    # Ensure at least one score is non-zero
    total = sum(scores.values())
    if total == 0:
        # Set a random emotion to have a non-zero score
        random_label = draw(st.sampled_from(VALID_EMOTION_LABELS))
        scores[random_label] = draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return scores


@st.composite
def emotion2vec_raw_output(draw):
    """
    Generate valid emotion2vec+ model raw output format.
    
    emotion2vec+ output format:
    [{'key': 'audio_path', 'scores': [0.1, 0.2, ...], 'labels': ['angry', 'happy', ...]}]
    """
    # Generate scores for each emotion
    scores = [draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)) 
              for _ in VALID_EMOTION_LABELS]
    
    # Ensure at least one score is non-zero
    if sum(scores) == 0:
        idx = draw(st.integers(min_value=0, max_value=len(VALID_EMOTION_LABELS) - 1))
        scores[idx] = draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return [{
        "key": "test_audio",
        "scores": scores,
        "labels": VALID_EMOTION_LABELS.copy()
    }]


@st.composite
def emotion2vec_raw_output_with_nested_scores(draw):
    """
    Generate emotion2vec+ output with nested scores (alternative format).
    """
    scores = [draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)) 
              for _ in VALID_EMOTION_LABELS]
    
    if sum(scores) == 0:
        idx = draw(st.integers(min_value=0, max_value=len(VALID_EMOTION_LABELS) - 1))
        scores[idx] = draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    # Nested scores format
    return [{
        "key": "test_audio",
        "scores": [scores],  # Nested list
        "labels": VALID_EMOTION_LABELS.copy()
    }]


# ============================================================================
# Property Tests
# ============================================================================

class TestEmotion2VecEmotionClassificationRange:
    """
    Property 2: 情绪分类范围约束
    
    **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
    **Validates: Requirements 1.3**
    
    *For any* audio input, the emotion2vec+ model output emotion category 
    SHALL belong to one of the predefined 9 emotion classes:
    (angry, happy, neutral, sad, surprised, fearful, disgusted, anxious, tired)
    """
    
    @given(raw_output=emotion2vec_raw_output())
    @settings(max_examples=100)
    def test_parsed_emotion_in_valid_categories(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any valid emotion2vec+ raw output,
        the parsed emotion category SHALL be one of the 9 predefined emotion classes.
        """
        analyzer = Emotion2VecAnalyzer()
        
        # Parse the raw output
        result = analyzer._parse_result(raw_output)
        
        # Property assertion: emotion must be a valid EmotionCategory
        assert isinstance(result.emotion, EmotionCategory), \
            f"Expected EmotionCategory, got {type(result.emotion)}"
        
        # Verify it's one of the 9 valid categories
        valid_categories = list(EmotionCategory)
        assert result.emotion in valid_categories, \
            f"emotion '{result.emotion}' should be one of {[c.value for c in valid_categories]}"
    
    @given(raw_output=emotion2vec_raw_output())
    @settings(max_examples=100)
    def test_emotion_value_in_valid_labels(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any valid emotion2vec+ raw output,
        the emotion value (string) SHALL be one of the 9 predefined labels.
        """
        analyzer = Emotion2VecAnalyzer()
        
        result = analyzer._parse_result(raw_output)
        
        # Get the string value of the emotion
        emotion_value = result.emotion.value
        
        # Verify it's one of the valid labels
        assert emotion_value in VALID_EMOTION_LABELS, \
            f"emotion value '{emotion_value}' should be one of {VALID_EMOTION_LABELS}"
    
    @given(raw_output=emotion2vec_raw_output_with_nested_scores())
    @settings(max_examples=100)
    def test_nested_scores_emotion_in_valid_categories(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any emotion2vec+ output with nested scores format,
        the parsed emotion category SHALL still be one of the 9 predefined classes.
        """
        analyzer = Emotion2VecAnalyzer()
        
        result = analyzer._parse_result(raw_output)
        
        assert isinstance(result.emotion, EmotionCategory), \
            f"Expected EmotionCategory, got {type(result.emotion)}"
        
        assert result.emotion.value in VALID_EMOTION_LABELS, \
            f"emotion '{result.emotion.value}' should be one of {VALID_EMOTION_LABELS}"
    
    @given(scores=emotion_scores_dict())
    @settings(max_examples=100)
    def test_primary_emotion_from_scores_in_valid_labels(self, scores: Dict[str, float]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any valid emotion scores dictionary,
        the primary emotion extracted SHALL be one of the 9 predefined labels.
        """
        analyzer = Emotion2VecAnalyzer()
        
        primary_emotion = analyzer._get_primary_emotion(scores)
        
        assert primary_emotion in VALID_EMOTION_LABELS, \
            f"primary emotion '{primary_emotion}' should be one of {VALID_EMOTION_LABELS}"
    
    @given(scores=emotion_scores_dict())
    @settings(max_examples=100)
    def test_emotion_category_mapping_valid(self, scores: Dict[str, float]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any primary emotion label,
        the mapping to EmotionCategory SHALL produce a valid category.
        """
        analyzer = Emotion2VecAnalyzer()
        
        primary_emotion = analyzer._get_primary_emotion(scores)
        mapped_category = analyzer.EMOTION_CATEGORY_MAP.get(primary_emotion, EmotionCategory.NEUTRAL)
        
        assert isinstance(mapped_category, EmotionCategory), \
            f"Expected EmotionCategory, got {type(mapped_category)}"
        
        valid_categories = list(EmotionCategory)
        assert mapped_category in valid_categories, \
            f"mapped category '{mapped_category}' should be one of {valid_categories}"
    
    @given(raw_output=emotion2vec_raw_output())
    @settings(max_examples=100)
    def test_result_scores_contain_all_labels(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any valid emotion2vec+ raw output,
        the result scores dictionary SHALL contain all 9 emotion labels.
        """
        analyzer = Emotion2VecAnalyzer()
        
        result = analyzer._parse_result(raw_output)
        
        # Verify all labels are present in scores
        for label in VALID_EMOTION_LABELS:
            assert label in result.scores, \
                f"label '{label}' should be present in scores"
    
    @given(raw_output=emotion2vec_raw_output())
    @settings(max_examples=100)
    def test_scores_values_in_valid_range(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any valid emotion2vec+ raw output,
        all score values SHALL be in the range [0, 1].
        """
        analyzer = Emotion2VecAnalyzer()
        
        result = analyzer._parse_result(raw_output)
        
        for label, score in result.scores.items():
            assert 0 <= score <= 1, \
                f"score for '{label}' should be in [0, 1], got {score}"
    
    @given(raw_output=emotion2vec_raw_output())
    @settings(max_examples=100)
    def test_intensity_in_valid_range(self, raw_output: List[Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 2: 情绪分类范围约束**
        **Validates: Requirements 1.3**
        
        For any valid emotion2vec+ raw output,
        the intensity value SHALL be in the range [0, 1].
        """
        analyzer = Emotion2VecAnalyzer()
        
        result = analyzer._parse_result(raw_output)
        
        assert 0 <= result.intensity <= 1, \
            f"intensity should be in [0, 1], got {result.intensity}"


class TestEmotion2VecEdgeCases:
    """
    Edge case tests for emotion2vec+ output parsing.
    These complement the property tests by testing specific edge cases.
    """
    
    def test_empty_result_returns_neutral(self):
        """Test that empty result returns neutral emotion"""
        analyzer = Emotion2VecAnalyzer()
        
        result = analyzer._parse_result([])
        
        assert isinstance(result, Emotion2VecResult)
        assert result.emotion == EmotionCategory.NEUTRAL
        assert result.emotion.value in VALID_EMOTION_LABELS
    
    def test_none_result_returns_neutral(self):
        """Test that None result returns neutral emotion"""
        analyzer = Emotion2VecAnalyzer()
        
        result = analyzer._parse_result(None)
        
        assert isinstance(result, Emotion2VecResult)
        assert result.emotion == EmotionCategory.NEUTRAL
        assert result.emotion.value in VALID_EMOTION_LABELS
    
    def test_all_zero_scores_returns_valid_emotion(self):
        """Test that all-zero scores still return a valid emotion"""
        analyzer = Emotion2VecAnalyzer()
        
        raw_output = [{
            "key": "test",
            "scores": [0.0] * 9,
            "labels": VALID_EMOTION_LABELS.copy()
        }]
        
        result = analyzer._parse_result(raw_output)
        
        assert isinstance(result.emotion, EmotionCategory)
        assert result.emotion.value in VALID_EMOTION_LABELS
    
    def test_single_high_score_returns_correct_emotion(self):
        """Test that a single high score returns the correct emotion"""
        analyzer = Emotion2VecAnalyzer()
        
        # Set happy to 1.0, all others to 0.0
        scores = [0.0] * 9
        happy_idx = VALID_EMOTION_LABELS.index("happy")
        scores[happy_idx] = 1.0
        
        raw_output = [{
            "key": "test",
            "scores": scores,
            "labels": VALID_EMOTION_LABELS.copy()
        }]
        
        result = analyzer._parse_result(raw_output)
        
        assert result.emotion == EmotionCategory.HAPPY
        assert result.emotion.value == "happy"
    
    def test_analyzer_emotion_labels_match_valid_labels(self):
        """Test that analyzer's EMOTION_LABELS match our valid labels"""
        analyzer = Emotion2VecAnalyzer()
        
        assert set(analyzer.EMOTION_LABELS) == set(VALID_EMOTION_LABELS), \
            "Analyzer EMOTION_LABELS should match VALID_EMOTION_LABELS"
    
    def test_all_emotion_categories_have_mapping(self):
        """Test that all emotion labels have a category mapping"""
        analyzer = Emotion2VecAnalyzer()
        
        for label in VALID_EMOTION_LABELS:
            assert label in analyzer.EMOTION_CATEGORY_MAP, \
                f"label '{label}' should have a category mapping"
            assert isinstance(analyzer.EMOTION_CATEGORY_MAP[label], EmotionCategory), \
                f"mapping for '{label}' should be EmotionCategory"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
