"""
表情分类范围约束属性测试
Property-Based Tests for Expression Classification Range Constraint

使用 hypothesis 进行属性测试，验证表情分类器输出的表情类别属于预定义的 7 类基础表情

**Feature: healing-pod-system, Property 5: 表情分类范围约束**
**Validates: Requirements 2.3**
"""
import os
import sys
from typing import List, Tuple, Dict

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import FacialExpression, FaceAnalysisResult
from services.expression_classifier import ExpressionClassifier


# ============================================================================
# Constants
# ============================================================================

# 7 basic expressions as defined in Requirements 2.3
VALID_EXPRESSIONS = [
    "angry",
    "disgusted",
    "fearful",
    "happy",
    "sad",
    "surprised",
    "neutral"
]

# FacialExpression enum values
VALID_EXPRESSION_ENUMS = [e for e in FacialExpression]

# MediaPipe Face Mesh outputs exactly 468 landmarks
EXPECTED_LANDMARK_COUNT = 468

# Suppress health checks for large data
SUPPRESS_CHECKS = [HealthCheck.large_base_example, HealthCheck.data_too_large]


# ============================================================================
# Strategies for generating test data
# ============================================================================

def generate_landmarks_from_seed(seed: int) -> List[Tuple[float, float, float]]:
    """
    Generate 468 landmarks deterministically from a seed.
    """
    rng = np.random.default_rng(seed)
    landmarks = []
    for _ in range(EXPECTED_LANDMARK_COUNT):
        x = rng.uniform(0.0, 640.0)
        y = rng.uniform(0.0, 480.0)
        z = rng.uniform(-50.0, 50.0)
        landmarks.append((float(x), float(y), float(z)))
    return landmarks


@st.composite
def valid_landmarks_list(draw):
    """
    Generate a valid list of 468 face landmarks using a seed.
    """
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    return generate_landmarks_from_seed(seed)


@st.composite
def valid_face_image(draw):
    """
    Generate a valid face image (grayscale or BGR numpy array).
    """
    height = draw(st.integers(min_value=48, max_value=256))
    width = draw(st.integers(min_value=48, max_value=256))
    channels = draw(st.sampled_from([1, 3]))  # Grayscale or BGR
    
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    rng = np.random.default_rng(seed)
    
    if channels == 1:
        image = rng.integers(0, 256, (height, width), dtype=np.uint8)
    else:
        image = rng.integers(0, 256, (height, width, channels), dtype=np.uint8)
    
    return image


@st.composite
def valid_expression_scores(draw):
    """
    Generate valid expression scores dictionary.
    Scores should sum to approximately 1.0 (normalized probabilities).
    """
    raw_scores = [draw(st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)) 
                  for _ in VALID_EXPRESSIONS]
    
    # Normalize scores
    total = sum(raw_scores)
    normalized = [s / total for s in raw_scores]
    
    scores = {}
    for expr, score in zip(VALID_EXPRESSIONS, normalized):
        scores[expr] = score
    
    return scores


# ============================================================================
# Property Tests
# ============================================================================

class TestExpressionClassificationRangeConstraint:
    """
    Property 5: 表情分类范围约束
    
    **Feature: healing-pod-system, Property 5: 表情分类范围约束**
    **Validates: Requirements 2.3**
    
    *For any* image frame where a face is detected,
    the expression classifier output SHALL belong to one of the 
    7 predefined basic expressions (happy, sad, angry, fearful, 
    surprised, disgusted, neutral).
    """
    
    @given(face_image=valid_face_image(), landmarks=valid_landmarks_list())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_classifier_output_in_valid_expression_range(
        self, 
        face_image: np.ndarray,
        landmarks: List[Tuple[float, float, float]]
    ):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        For any face image and landmarks, the expression classifier
        SHALL output an expression that belongs to the 7 basic expressions.
        """
        classifier = ExpressionClassifier()
        classifier.initialize()
        
        try:
            expression, confidence, scores = classifier.classify(face_image, landmarks)
            
            # Property: Expression must be a valid FacialExpression enum
            assert isinstance(expression, FacialExpression), \
                f"Expression should be FacialExpression enum, got {type(expression)}"
            
            # Property: Expression value must be in valid expressions list
            assert expression.value in VALID_EXPRESSIONS, \
                f"Expression '{expression.value}' not in valid expressions: {VALID_EXPRESSIONS}"
            
            # Property: Confidence must be in valid range [0, 1]
            assert 0 <= confidence <= 1, \
                f"Confidence should be between 0 and 1, got {confidence}"
            
            # Property: All score keys must be valid expressions
            for expr_key in scores.keys():
                assert expr_key in VALID_EXPRESSIONS, \
                    f"Score key '{expr_key}' not in valid expressions: {VALID_EXPRESSIONS}"
        finally:
            classifier.cleanup()
    
    @given(face_image=valid_face_image())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_classifier_output_without_landmarks(self, face_image: np.ndarray):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        For any face image without landmarks, the expression classifier
        SHALL still output a valid expression from the 7 basic expressions.
        """
        # Skip if cv2 is not available (required for image-based classification)
        try:
            import cv2
        except ImportError:
            pytest.skip("cv2 (OpenCV) not available for image-based classification test")
        
        classifier = ExpressionClassifier()
        classifier.initialize()
        
        try:
            expression, confidence, scores = classifier.classify(face_image, landmarks=None)
            
            # Property: Expression must be a valid FacialExpression enum
            assert isinstance(expression, FacialExpression), \
                f"Expression should be FacialExpression enum, got {type(expression)}"
            
            # Property: Expression value must be in valid expressions list
            assert expression.value in VALID_EXPRESSIONS, \
                f"Expression '{expression.value}' not in valid expressions: {VALID_EXPRESSIONS}"
        finally:
            classifier.cleanup()
    
    @given(scores=valid_expression_scores())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_parse_predictions_returns_valid_expression(self, scores: Dict[str, float]):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        For any valid prediction scores, _parse_predictions SHALL
        return an expression from the 7 basic expressions.
        """
        classifier = ExpressionClassifier()
        classifier.initialize()
        
        try:
            # Convert scores dict to predictions array in correct order
            predictions = [scores[label] for label in classifier.EXPRESSION_LABELS]
            
            expression, confidence, result_scores = classifier._parse_predictions(predictions)
            
            # Property: Expression must be a valid FacialExpression enum
            assert isinstance(expression, FacialExpression), \
                f"Expression should be FacialExpression enum, got {type(expression)}"
            
            # Property: Expression value must be in valid expressions list
            assert expression.value in VALID_EXPRESSIONS, \
                f"Expression '{expression.value}' not in valid expressions: {VALID_EXPRESSIONS}"
            
            # Property: All returned score keys must be valid expressions
            for expr_key in result_scores.keys():
                assert expr_key in VALID_EXPRESSIONS, \
                    f"Score key '{expr_key}' not in valid expressions: {VALID_EXPRESSIONS}"
        finally:
            classifier.cleanup()
    
    def test_expression_labels_match_valid_expressions(self):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        The classifier's EXPRESSION_LABELS SHALL exactly match
        the 7 basic expressions defined in Requirements 2.3.
        """
        classifier = ExpressionClassifier()
        
        # Property: Labels should match exactly
        assert set(classifier.EXPRESSION_LABELS) == set(VALID_EXPRESSIONS), \
            f"Classifier labels {classifier.EXPRESSION_LABELS} don't match valid expressions {VALID_EXPRESSIONS}"
        
        # Property: Should have exactly 7 expressions
        assert len(classifier.EXPRESSION_LABELS) == 7, \
            f"Expected 7 expression labels, got {len(classifier.EXPRESSION_LABELS)}"
    
    def test_expression_map_covers_all_valid_expressions(self):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        The classifier's EXPRESSION_MAP SHALL map all 7 basic
        expressions to valid FacialExpression enum values.
        """
        classifier = ExpressionClassifier()
        
        # Property: All valid expressions should be in the map
        for expr in VALID_EXPRESSIONS:
            assert expr in classifier.EXPRESSION_MAP, \
                f"Expression '{expr}' not in EXPRESSION_MAP"
            
            # Property: Mapped value should be a FacialExpression enum
            mapped_value = classifier.EXPRESSION_MAP[expr]
            assert isinstance(mapped_value, FacialExpression), \
                f"Mapped value for '{expr}' should be FacialExpression, got {type(mapped_value)}"


class TestFaceAnalysisResultExpressionConstraint:
    """
    Additional property tests for FaceAnalysisResult expression validation.
    
    These tests verify that FaceAnalysisResult correctly enforces
    the expression classification range constraint.
    """
    
    @given(scores=valid_expression_scores(), landmarks=valid_landmarks_list())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_face_analysis_result_expression_in_valid_range(
        self, 
        scores: Dict[str, float],
        landmarks: List[Tuple[float, float, float]]
    ):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        For any FaceAnalysisResult, the expression SHALL be
        one of the 7 basic FacialExpression enum values.
        """
        # Pick the expression with highest score
        primary_expression = max(scores, key=scores.get)
        confidence = scores[primary_expression]
        
        result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression(primary_expression),
            confidence=confidence,
            expression_scores=scores,
            landmarks=landmarks
        )
        
        # Property: Expression must be a valid FacialExpression enum
        assert isinstance(result.expression, FacialExpression), \
            f"Expression should be FacialExpression enum, got {type(result.expression)}"
        
        # Property: Expression value must be in valid expressions list
        assert result.expression.value in VALID_EXPRESSIONS, \
            f"Expression '{result.expression.value}' not in valid expressions: {VALID_EXPRESSIONS}"
    
    def test_facial_expression_enum_has_exactly_7_values(self):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        The FacialExpression enum SHALL have exactly 7 values
        corresponding to the 7 basic expressions.
        """
        # Property: Exactly 7 expressions
        assert len(FacialExpression) == 7, \
            f"Expected 7 FacialExpression values, got {len(FacialExpression)}"
        
        # Property: All enum values should be in valid expressions
        for expr in FacialExpression:
            assert expr.value in VALID_EXPRESSIONS, \
                f"FacialExpression '{expr.value}' not in valid expressions: {VALID_EXPRESSIONS}"
    
    def test_get_expression_labels_returns_valid_expressions(self):
        """
        **Feature: healing-pod-system, Property 5: 表情分类范围约束**
        **Validates: Requirements 2.3**
        
        FaceAnalysisResult.get_expression_labels() SHALL return
        exactly the 7 basic expression labels.
        """
        labels = FaceAnalysisResult.get_expression_labels()
        
        # Property: Should return exactly 7 labels
        assert len(labels) == 7, \
            f"Expected 7 expression labels, got {len(labels)}"
        
        # Property: All labels should be valid expressions
        assert set(labels) == set(VALID_EXPRESSIONS), \
            f"Labels {labels} don't match valid expressions {VALID_EXPRESSIONS}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
