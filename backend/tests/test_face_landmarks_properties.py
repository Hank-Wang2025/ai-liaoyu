"""
面部关键点属性测试
Property-Based Tests for Face Landmarks

使用 hypothesis 进行属性测试，验证面部关键点数量约束

**Feature: healing-pod-system, Property 4: 面部关键点数量约束**
**Validates: Requirements 2.2**
"""
import os
import sys
from typing import List, Tuple, Optional

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume, HealthCheck

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import FaceAnalysisResult, FacialExpression


# ============================================================================
# Constants
# ============================================================================

# MediaPipe Face Mesh outputs exactly 468 landmarks
EXPECTED_LANDMARK_COUNT = 468

# Valid facial expressions (7 basic expressions)
VALID_EXPRESSIONS = [e.value for e in FacialExpression]

# Suppress health checks for large data since 468 landmarks is a fixed requirement
SUPPRESS_CHECKS = [HealthCheck.large_base_example, HealthCheck.data_too_large]


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def valid_landmark_coordinate(draw):
    """
    Generate a valid landmark coordinate (x, y, z).
    
    Coordinates are typically in pixel space for x, y
    and normalized depth for z.
    """
    x = draw(st.floats(min_value=0.0, max_value=1920.0, allow_nan=False, allow_infinity=False))
    y = draw(st.floats(min_value=0.0, max_value=1080.0, allow_nan=False, allow_infinity=False))
    z = draw(st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    return (x, y, z)


def generate_landmarks_from_seed(seed: int) -> List[Tuple[float, float, float]]:
    """
    Generate 468 landmarks deterministically from a seed.
    
    This is more efficient than using hypothesis to generate each landmark.
    """
    rng = np.random.default_rng(seed)
    landmarks = []
    for _ in range(EXPECTED_LANDMARK_COUNT):
        x = rng.uniform(0.0, 1920.0)
        y = rng.uniform(0.0, 1080.0)
        z = rng.uniform(-100.0, 100.0)
        landmarks.append((float(x), float(y), float(z)))
    return landmarks


@st.composite
def valid_landmarks_list(draw):
    """
    Generate a valid list of 468 face landmarks using a seed.
    
    MediaPipe Face Mesh always outputs exactly 468 landmarks
    when a face is detected.
    """
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    return generate_landmarks_from_seed(seed)


@st.composite
def valid_face_bbox(draw):
    """
    Generate a valid face bounding box (x, y, width, height).
    """
    x = draw(st.integers(min_value=0, max_value=1000))
    y = draw(st.integers(min_value=0, max_value=800))
    width = draw(st.integers(min_value=50, max_value=500))
    height = draw(st.integers(min_value=50, max_value=600))
    return (x, y, width, height)


@st.composite
def valid_expression_scores(draw):
    """
    Generate valid expression scores dictionary.
    
    Scores should sum to approximately 1.0 (normalized probabilities).
    """
    scores = {}
    raw_scores = [draw(st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)) 
                  for _ in VALID_EXPRESSIONS]
    
    # Normalize scores
    total = sum(raw_scores)
    normalized = [s / total for s in raw_scores]
    
    for expr, score in zip(VALID_EXPRESSIONS, normalized):
        scores[expr] = score
    
    return scores


@st.composite
def valid_face_analysis_result_with_detection(draw):
    """
    Generate a valid FaceAnalysisResult where a face was detected.
    
    This simulates the output from MediaPipe Face Mesh when
    a face is successfully detected in the image.
    """
    landmarks = draw(valid_landmarks_list())
    bbox = draw(valid_face_bbox())
    expression_scores = draw(valid_expression_scores())
    
    # Pick the expression with highest score
    primary_expression = max(expression_scores, key=expression_scores.get)
    confidence = expression_scores[primary_expression]
    
    return FaceAnalysisResult(
        detected=True,
        expression=FacialExpression(primary_expression),
        confidence=confidence,
        expression_scores=expression_scores,
        landmarks=landmarks,
        face_bbox=bbox
    )


@st.composite
def simulated_image_frame(draw):
    """
    Generate a simulated image frame (BGR format numpy array).
    
    This represents a typical camera frame that would be
    passed to the face analyzer.
    """
    height = draw(st.integers(min_value=240, max_value=480))
    width = draw(st.integers(min_value=320, max_value=640))
    
    # Generate random BGR image using seed for efficiency
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    rng = np.random.default_rng(seed)
    frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    return frame


# ============================================================================
# Property Tests
# ============================================================================

class TestFaceLandmarkCountConstraint:
    """
    Property 4: 面部关键点数量约束
    
    **Feature: healing-pod-system, Property 4: 面部关键点数量约束**
    **Validates: Requirements 2.2**
    
    *For any* image frame where a face is detected,
    MediaPipe SHALL output exactly 468 facial landmarks.
    """
    
    @given(result=valid_face_analysis_result_with_detection())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_detected_face_has_exactly_468_landmarks(self, result: FaceAnalysisResult):
        """
        **Feature: healing-pod-system, Property 4: 面部关键点数量约束**
        **Validates: Requirements 2.2**
        
        For any FaceAnalysisResult where a face is detected,
        the landmarks list SHALL contain exactly 468 points.
        """
        # Property: When face is detected, landmarks must be present
        assert result.detected is True, "Test precondition: face should be detected"
        
        # Property: Landmarks must not be None when face is detected
        assert result.landmarks is not None, \
            "landmarks should not be None when face is detected"
        
        # Property: Exactly 468 landmarks
        assert len(result.landmarks) == EXPECTED_LANDMARK_COUNT, \
            f"Expected {EXPECTED_LANDMARK_COUNT} landmarks, got {len(result.landmarks)}"
    
    @given(result=valid_face_analysis_result_with_detection())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_each_landmark_has_three_coordinates(self, result: FaceAnalysisResult):
        """
        **Feature: healing-pod-system, Property 4: 面部关键点数量约束**
        **Validates: Requirements 2.2**
        
        For any detected face, each landmark SHALL have exactly 3 coordinates (x, y, z).
        """
        assert result.landmarks is not None
        
        for i, landmark in enumerate(result.landmarks):
            assert len(landmark) == 3, \
                f"Landmark {i} should have 3 coordinates (x, y, z), got {len(landmark)}"
    
    @given(result=valid_face_analysis_result_with_detection())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_landmark_coordinates_are_numeric(self, result: FaceAnalysisResult):
        """
        **Feature: healing-pod-system, Property 4: 面部关键点数量约束**
        **Validates: Requirements 2.2**
        
        For any detected face, all landmark coordinates SHALL be numeric values.
        """
        assert result.landmarks is not None
        
        for i, landmark in enumerate(result.landmarks):
            x, y, z = landmark
            assert isinstance(x, (int, float)), \
                f"Landmark {i} x-coordinate should be numeric, got {type(x)}"
            assert isinstance(y, (int, float)), \
                f"Landmark {i} y-coordinate should be numeric, got {type(y)}"
            assert isinstance(z, (int, float)), \
                f"Landmark {i} z-coordinate should be numeric, got {type(z)}"
            
            # Coordinates should not be NaN or Inf
            assert not np.isnan(x) and not np.isinf(x), \
                f"Landmark {i} x-coordinate should not be NaN or Inf"
            assert not np.isnan(y) and not np.isinf(y), \
                f"Landmark {i} y-coordinate should not be NaN or Inf"
            assert not np.isnan(z) and not np.isinf(z), \
                f"Landmark {i} z-coordinate should not be NaN or Inf"
    
    @given(landmarks=valid_landmarks_list())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_landmarks_list_invariant(self, landmarks: List[Tuple[float, float, float]]):
        """
        **Feature: healing-pod-system, Property 4: 面部关键点数量约束**
        **Validates: Requirements 2.2**
        
        For any valid landmarks list, the count SHALL always be 468.
        This tests the invariant property of the landmark count.
        """
        assert len(landmarks) == EXPECTED_LANDMARK_COUNT, \
            f"Landmarks list should always have {EXPECTED_LANDMARK_COUNT} points"


class TestFaceAnalysisResultValidation:
    """
    Additional property tests for FaceAnalysisResult validation.
    
    These tests verify that the FaceAnalysisResult data model
    correctly enforces the landmark count constraint.
    """
    
    def test_face_analysis_result_rejects_wrong_landmark_count(self):
        """
        Test that FaceAnalysisResult raises ValueError for wrong landmark count.
        
        The data model should enforce the 468 landmark constraint.
        """
        # Test with too few landmarks
        wrong_landmarks = [(0.0, 0.0, 0.0)] * 100  # Only 100 landmarks
        
        with pytest.raises(ValueError) as exc_info:
            FaceAnalysisResult(
                detected=True,
                expression=FacialExpression.NEUTRAL,
                confidence=0.8,
                expression_scores={e.value: 0.1 for e in FacialExpression},
                landmarks=wrong_landmarks
            )
        
        assert "468" in str(exc_info.value), \
            "Error message should mention expected landmark count of 468"
    
    def test_face_analysis_result_accepts_correct_landmark_count(self):
        """
        Test that FaceAnalysisResult accepts exactly 468 landmarks.
        """
        correct_landmarks = [(0.0, 0.0, 0.0)] * EXPECTED_LANDMARK_COUNT
        
        result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.NEUTRAL,
            confidence=0.8,
            expression_scores={e.value: 0.1 for e in FacialExpression},
            landmarks=correct_landmarks
        )
        
        assert len(result.landmarks) == EXPECTED_LANDMARK_COUNT
    
    def test_no_face_detected_has_no_landmarks(self):
        """
        Test that when no face is detected, landmarks should be None.
        """
        result = FaceAnalysisResult.no_face_detected()
        
        assert result.detected is False
        assert result.landmarks is None
    
    @given(landmarks=valid_landmarks_list())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_face_analysis_result_preserves_landmark_count(
        self, 
        landmarks: List[Tuple[float, float, float]]
    ):
        """
        **Feature: healing-pod-system, Property 4: 面部关键点数量约束**
        **Validates: Requirements 2.2**
        
        For any valid landmarks list passed to FaceAnalysisResult,
        the stored landmarks SHALL preserve the exact count of 468.
        """
        result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.NEUTRAL,
            confidence=0.8,
            expression_scores={e.value: 0.1 for e in FacialExpression},
            landmarks=landmarks
        )
        
        assert len(result.landmarks) == EXPECTED_LANDMARK_COUNT, \
            f"FaceAnalysisResult should preserve {EXPECTED_LANDMARK_COUNT} landmarks"


class TestFaceAnalyzerLandmarkExtraction:
    """
    Property tests for FaceAnalyzer landmark extraction.
    
    These tests verify that the FaceAnalyzer correctly extracts
    468 landmarks from MediaPipe Face Mesh output.
    """
    
    @given(frame=simulated_image_frame())
    @settings(max_examples=10, suppress_health_check=SUPPRESS_CHECKS)
    def test_analyzer_extracts_correct_landmark_count_when_face_detected(
        self, 
        frame: np.ndarray
    ):
        """
        **Feature: healing-pod-system, Property 4: 面部关键点数量约束**
        **Validates: Requirements 2.2**
        
        For any image frame where a face is detected,
        FaceAnalyzer SHALL extract exactly 468 landmarks.
        
        Note: This test uses simulated frames. In real scenarios,
        face detection depends on actual face presence in the image.
        """
        from services.face_analyzer import FaceAnalyzer
        
        analyzer = FaceAnalyzer()
        
        # Try to initialize - may fail if MediaPipe not installed
        try:
            initialized = analyzer.initialize()
        except Exception:
            pytest.skip("MediaPipe not available for testing")
        
        if not initialized:
            pytest.skip("FaceAnalyzer could not be initialized")
        
        try:
            result = analyzer.analyze_sync(frame)
            
            # If a face was detected, verify landmark count
            if result.detected and result.landmarks is not None:
                assert len(result.landmarks) == EXPECTED_LANDMARK_COUNT, \
                    f"Expected {EXPECTED_LANDMARK_COUNT} landmarks, got {len(result.landmarks)}"
            
            # If no face detected, landmarks should be None
            if not result.detected:
                assert result.landmarks is None, \
                    "landmarks should be None when no face is detected"
        finally:
            analyzer.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
