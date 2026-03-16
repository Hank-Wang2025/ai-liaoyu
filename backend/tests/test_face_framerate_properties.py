"""
面部分析帧率约束属性测试
Property-Based Tests for Face Analysis Frame Rate Constraint

使用 hypothesis 进行属性测试，验证面部分析模块以不低于 30fps 的帧率处理图像

**Feature: healing-pod-system, Property 6: 面部分析帧率约束**
**Validates: Requirements 2.6**
"""
import os
import sys
import time
from typing import List, Tuple

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import FaceAnalysisResult


# ============================================================================
# Constants
# ============================================================================

# Target frame rate as defined in Requirements 2.6
TARGET_FPS = 30

# Maximum allowed time per frame (in seconds) to achieve 30fps
MAX_FRAME_TIME_SECONDS = 1.0 / TARGET_FPS  # ~33.33ms

# Tolerance for timing measurements (10% margin)
TIMING_TOLERANCE = 0.1

# Minimum number of frames to test for frame rate consistency
MIN_FRAMES_FOR_RATE_TEST = 10

# Suppress health checks for large data
SUPPRESS_CHECKS = [HealthCheck.large_base_example, HealthCheck.data_too_large, HealthCheck.too_slow]


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def simulated_video_frame(draw):
    """
    Generate a simulated video frame (BGR format numpy array).
    
    This represents a typical camera frame that would be
    passed to the face analyzer at 30fps.
    """
    # Common video resolutions
    resolution = draw(st.sampled_from([
        (480, 640),   # VGA
        (720, 1280),  # HD
        (480, 854),   # FWVGA
        (360, 640),   # nHD
    ]))
    height, width = resolution
    
    # Generate random BGR image using seed for efficiency
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    rng = np.random.default_rng(seed)
    frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    return frame


@st.composite
def frame_sequence_params(draw):
    """
    Generate parameters for a sequence of frames to test frame rate.
    """
    num_frames = draw(st.integers(min_value=MIN_FRAMES_FOR_RATE_TEST, max_value=30))
    resolution = draw(st.sampled_from([
        (480, 640),   # VGA - most common for real-time processing
        (360, 640),   # Lower resolution for faster processing
    ]))
    seed = draw(st.integers(min_value=0, max_value=2**32 - 1))
    return {
        'num_frames': num_frames,
        'resolution': resolution,
        'seed': seed
    }


def generate_frame_sequence(params: dict) -> List[np.ndarray]:
    """
    Generate a sequence of frames for frame rate testing.
    """
    num_frames = params['num_frames']
    height, width = params['resolution']
    seed = params['seed']
    
    rng = np.random.default_rng(seed)
    frames = []
    for _ in range(num_frames):
        frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
        frames.append(frame)
    return frames


# ============================================================================
# Property Tests
# ============================================================================

class TestFaceAnalysisFrameRateConstraint:
    """
    Property 6: 面部分析帧率约束
    
    **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
    **Validates: Requirements 2.6**
    
    *For any* continuous video stream input, the face analysis module
    SHALL process images at no less than 30fps frame rate.
    """
    
    @given(frame=simulated_video_frame())
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS, deadline=None)
    def test_single_frame_processing_time_within_budget(self, frame: np.ndarray):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        For any single video frame, the face analyzer SHALL process it
        within the time budget required for 30fps (~33.33ms).
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
            # Measure processing time
            start_time = time.perf_counter()
            result = analyzer.analyze_sync(frame)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            
            # Property: Processing time should be within budget for 30fps
            # Allow some tolerance for system variations
            max_allowed_time = MAX_FRAME_TIME_SECONDS * (1 + TIMING_TOLERANCE)
            
            assert processing_time <= max_allowed_time, \
                f"Frame processing took {processing_time*1000:.2f}ms, " \
                f"exceeds {max_allowed_time*1000:.2f}ms budget for 30fps"
            
            # Verify result is valid
            assert isinstance(result, FaceAnalysisResult), \
                f"Expected FaceAnalysisResult, got {type(result)}"
        finally:
            analyzer.cleanup()
    
    @given(params=frame_sequence_params())
    @settings(max_examples=20, suppress_health_check=SUPPRESS_CHECKS, deadline=None)
    def test_frame_sequence_achieves_target_fps(self, params: dict):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        For any sequence of video frames, the face analyzer SHALL
        achieve an average frame rate of at least 30fps.
        """
        from services.face_analyzer import FaceAnalyzer
        
        analyzer = FaceAnalyzer()
        
        # Try to initialize
        try:
            initialized = analyzer.initialize()
        except Exception:
            pytest.skip("MediaPipe not available for testing")
        
        if not initialized:
            pytest.skip("FaceAnalyzer could not be initialized")
        
        try:
            frames = generate_frame_sequence(params)
            num_frames = len(frames)
            
            # Process all frames and measure total time
            start_time = time.perf_counter()
            for frame in frames:
                result = analyzer.analyze_sync(frame)
                assert isinstance(result, FaceAnalysisResult)
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            achieved_fps = num_frames / total_time if total_time > 0 else float('inf')
            
            # Property: Average FPS should be at least 30
            # Allow some tolerance for system variations
            min_acceptable_fps = TARGET_FPS * (1 - TIMING_TOLERANCE)
            
            assert achieved_fps >= min_acceptable_fps, \
                f"Achieved {achieved_fps:.2f}fps processing {num_frames} frames, " \
                f"below minimum {min_acceptable_fps:.2f}fps (target: {TARGET_FPS}fps)"
        finally:
            analyzer.cleanup()
    
    @given(frame=simulated_video_frame())
    @settings(max_examples=50, suppress_health_check=SUPPRESS_CHECKS, deadline=None)
    def test_frame_processing_time_consistency(self, frame: np.ndarray):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        For any video frame processed multiple times, the processing time
        SHALL remain consistent and within the 30fps budget.
        """
        from services.face_analyzer import FaceAnalyzer
        
        analyzer = FaceAnalyzer()
        
        try:
            initialized = analyzer.initialize()
        except Exception:
            pytest.skip("MediaPipe not available for testing")
        
        if not initialized:
            pytest.skip("FaceAnalyzer could not be initialized")
        
        try:
            # Process the same frame multiple times
            num_iterations = 5
            processing_times = []
            
            for _ in range(num_iterations):
                start_time = time.perf_counter()
                result = analyzer.analyze_sync(frame)
                end_time = time.perf_counter()
                
                processing_times.append(end_time - start_time)
                assert isinstance(result, FaceAnalysisResult)
            
            # Calculate statistics
            avg_time = sum(processing_times) / len(processing_times)
            max_time = max(processing_times)
            
            # Property: Average processing time should be within budget
            max_allowed_avg = MAX_FRAME_TIME_SECONDS * (1 + TIMING_TOLERANCE)
            assert avg_time <= max_allowed_avg, \
                f"Average processing time {avg_time*1000:.2f}ms exceeds budget"
            
            # Property: Maximum processing time should not be excessively high
            # Allow 2x tolerance for occasional spikes
            max_allowed_spike = MAX_FRAME_TIME_SECONDS * 2
            assert max_time <= max_allowed_spike, \
                f"Maximum processing time {max_time*1000:.2f}ms indicates performance issue"
        finally:
            analyzer.cleanup()


class TestFrameRateCalculation:
    """
    Property tests for frame rate calculation utilities.
    
    These tests verify that frame rate calculations are correct
    and consistent with the 30fps requirement.
    """
    
    @given(num_frames=st.integers(min_value=1, max_value=1000),
           total_time=st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_fps_calculation_correctness(self, num_frames: int, total_time: float):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        For any number of frames and total processing time,
        the FPS calculation SHALL be mathematically correct.
        """
        calculated_fps = num_frames / total_time
        
        # Property: FPS should be positive
        assert calculated_fps > 0, "FPS should be positive"
        
        # Property: FPS calculation should be reversible
        reconstructed_time = num_frames / calculated_fps
        assert abs(reconstructed_time - total_time) < 1e-9, \
            "FPS calculation should be reversible"
    
    @given(fps=st.floats(min_value=1.0, max_value=120.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100, suppress_health_check=SUPPRESS_CHECKS)
    def test_frame_time_from_fps(self, fps: float):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        For any target FPS, the frame time calculation SHALL be correct.
        """
        frame_time = 1.0 / fps
        
        # Property: Frame time should be positive
        assert frame_time > 0, "Frame time should be positive"
        
        # Property: Frame time should be inversely proportional to FPS
        reconstructed_fps = 1.0 / frame_time
        assert abs(reconstructed_fps - fps) < 1e-9, \
            "Frame time calculation should be reversible"
    
    def test_target_fps_frame_time_budget(self):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        The frame time budget for 30fps SHALL be approximately 33.33ms.
        """
        expected_frame_time_ms = 1000.0 / TARGET_FPS  # ~33.33ms
        actual_frame_time_ms = MAX_FRAME_TIME_SECONDS * 1000
        
        # Property: Frame time budget should match 30fps requirement
        assert abs(actual_frame_time_ms - expected_frame_time_ms) < 0.01, \
            f"Frame time budget {actual_frame_time_ms:.2f}ms doesn't match " \
            f"expected {expected_frame_time_ms:.2f}ms for {TARGET_FPS}fps"


class TestFaceAnalyzerPerformanceInvariants:
    """
    Property tests for FaceAnalyzer performance invariants.
    
    These tests verify that the FaceAnalyzer maintains consistent
    performance characteristics required for 30fps operation.
    """
    
    def test_analyzer_initialization_does_not_affect_frame_rate(self):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        After initialization, the FaceAnalyzer SHALL maintain
        consistent frame processing performance.
        """
        from services.face_analyzer import FaceAnalyzer
        
        analyzer = FaceAnalyzer()
        
        try:
            initialized = analyzer.initialize()
        except Exception:
            pytest.skip("MediaPipe not available for testing")
        
        if not initialized:
            pytest.skip("FaceAnalyzer could not be initialized")
        
        try:
            # Generate test frame
            rng = np.random.default_rng(42)
            frame = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
            
            # Warm-up run (first frame may be slower due to JIT compilation)
            _ = analyzer.analyze_sync(frame)
            
            # Measure subsequent frames
            processing_times = []
            for _ in range(10):
                start_time = time.perf_counter()
                _ = analyzer.analyze_sync(frame)
                end_time = time.perf_counter()
                processing_times.append(end_time - start_time)
            
            # Property: All frames should be processed within budget
            max_allowed_time = MAX_FRAME_TIME_SECONDS * (1 + TIMING_TOLERANCE)
            for i, pt in enumerate(processing_times):
                assert pt <= max_allowed_time, \
                    f"Frame {i+1} took {pt*1000:.2f}ms, exceeds budget"
            
            # Property: Processing times should be relatively consistent
            avg_time = sum(processing_times) / len(processing_times)
            for pt in processing_times:
                # Allow 50% variance from average
                assert pt <= avg_time * 1.5, \
                    f"Processing time {pt*1000:.2f}ms varies too much from average {avg_time*1000:.2f}ms"
        finally:
            analyzer.cleanup()
    
    @given(resolution=st.sampled_from([(360, 640), (480, 640), (480, 854)]))
    @settings(max_examples=10, suppress_health_check=SUPPRESS_CHECKS, deadline=None)
    def test_different_resolutions_maintain_frame_rate(self, resolution: Tuple[int, int]):
        """
        **Feature: healing-pod-system, Property 6: 面部分析帧率约束**
        **Validates: Requirements 2.6**
        
        For any common video resolution, the FaceAnalyzer SHALL
        maintain at least 30fps processing rate.
        """
        from services.face_analyzer import FaceAnalyzer
        
        analyzer = FaceAnalyzer()
        
        try:
            initialized = analyzer.initialize()
        except Exception:
            pytest.skip("MediaPipe not available for testing")
        
        if not initialized:
            pytest.skip("FaceAnalyzer could not be initialized")
        
        try:
            height, width = resolution
            rng = np.random.default_rng(42)
            frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
            
            # Process multiple frames
            num_frames = 10
            start_time = time.perf_counter()
            for _ in range(num_frames):
                _ = analyzer.analyze_sync(frame)
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            achieved_fps = num_frames / total_time
            
            # Property: Should achieve at least 30fps (with tolerance)
            min_acceptable_fps = TARGET_FPS * (1 - TIMING_TOLERANCE)
            assert achieved_fps >= min_acceptable_fps, \
                f"Resolution {width}x{height}: achieved {achieved_fps:.2f}fps, " \
                f"below minimum {min_acceptable_fps:.2f}fps"
        finally:
            analyzer.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
