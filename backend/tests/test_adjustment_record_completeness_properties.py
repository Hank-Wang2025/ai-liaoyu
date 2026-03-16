"""
调整记录完整性属性测试
Property-Based Tests for Adjustment Record Completeness

使用 hypothesis 进行属性测试，验证调整记录完整性
Requirements: 10.4

**Property 21: 调整记录完整性**
*For any* 疗愈过程中的方案调整，系统 SHALL 记录调整时间、原因和调整内容。
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume, Phase

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.session import Session, SessionStatus, AdjustmentRecord
from models.emotion import EmotionState, EmotionCategory


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def valid_adjustment_reason(draw):
    """Generate a valid adjustment reason string."""
    reasons = [
        "情绪改善检测",
        "情绪恶化检测",
        "情绪无变化超过180秒",
        "用户手动调整",
        "自动切换方案: emotion_worsening",
        "自动切换方案: no_change_timeout",
        "阶段跳过",
        "强度调整",
        "方案切换"
    ]
    return draw(st.sampled_from(reasons))


@st.composite
def valid_adjustment_type(draw):
    """Generate a valid adjustment type string."""
    types = [
        "emotion_improvement",
        "emotion_worsening",
        "no_change_timeout",
        "plan_switch",
        "phase_skip",
        "intensity_change",
        "user_request"
    ]
    return draw(st.sampled_from(types))


@st.composite
def valid_adjustment_details(draw):
    """Generate valid adjustment details dictionary."""
    valence_change = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    intensity_change = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    current_emotion = draw(st.sampled_from([e.value for e in EmotionCategory]))
    
    return {
        "valence_change": valence_change,
        "intensity_change": intensity_change,
        "current_emotion": current_emotion
    }


@st.composite
def valid_state_dict(draw):
    """Generate a valid state dictionary."""
    plan_id = draw(st.text(min_size=1, max_size=36, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    phase_index = draw(st.integers(min_value=0, max_value=10))
    
    return {
        "plan_id": plan_id,
        "phase_index": phase_index
    }


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


# ============================================================================
# Property Tests - Property 21: 调整记录完整性
# ============================================================================

class TestAdjustmentRecordCompleteness:
    """
    Property 21: 调整记录完整性
    
    **Feature: healing-pod-system, Property 21: 调整记录完整性**
    **Validates: Requirements 10.4**
    
    *For any* 疗愈过程中的方案调整，系统 SHALL 记录调整时间、原因和调整内容。
    """
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_adjustment_record_has_timestamp(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment, the record SHALL contain a valid timestamp.
        """
        # Create an adjustment record
        record = AdjustmentRecord(
            timestamp=datetime.now(),
            reason=reason,
            adjustment_type=adjustment_type,
            details=details
        )
        
        # Verify timestamp is present and valid
        assert record.timestamp is not None, \
            "Adjustment record must have a timestamp"
        assert isinstance(record.timestamp, datetime), \
            "Timestamp must be a datetime object"
        
        # Verify timestamp is reasonable (not in the future, not too old)
        now = datetime.now()
        assert record.timestamp <= now + timedelta(seconds=1), \
            "Timestamp should not be in the future"
        assert record.timestamp >= now - timedelta(hours=1), \
            "Timestamp should not be too old"
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_adjustment_record_has_reason(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment, the record SHALL contain a non-empty reason.
        """
        # Create an adjustment record
        record = AdjustmentRecord(
            timestamp=datetime.now(),
            reason=reason,
            adjustment_type=adjustment_type,
            details=details
        )
        
        # Verify reason is present and non-empty
        assert record.reason is not None, \
            "Adjustment record must have a reason"
        assert isinstance(record.reason, str), \
            "Reason must be a string"
        assert len(record.reason) > 0, \
            "Reason must not be empty"
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_adjustment_record_has_details(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment, the record SHALL contain adjustment details (content).
        """
        # Create an adjustment record
        record = AdjustmentRecord(
            timestamp=datetime.now(),
            reason=reason,
            adjustment_type=adjustment_type,
            details=details
        )
        
        # Verify details is present
        assert record.details is not None, \
            "Adjustment record must have details"
        assert isinstance(record.details, dict), \
            "Details must be a dictionary"
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_adjustment_record_has_type(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment, the record SHALL contain an adjustment type.
        """
        # Create an adjustment record
        record = AdjustmentRecord(
            timestamp=datetime.now(),
            reason=reason,
            adjustment_type=adjustment_type,
            details=details
        )
        
        # Verify adjustment_type is present and non-empty
        assert record.adjustment_type is not None, \
            "Adjustment record must have an adjustment_type"
        assert isinstance(record.adjustment_type, str), \
            "Adjustment type must be a string"
        assert len(record.adjustment_type) > 0, \
            "Adjustment type must not be empty"
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details(),
        previous_state=valid_state_dict(),
        new_state=valid_state_dict()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_adjustment_record_to_dict_completeness(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any],
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment record, to_dict() SHALL produce a dictionary
        containing all required fields: timestamp, reason, adjustment_type, details.
        """
        # Create an adjustment record with all fields
        record = AdjustmentRecord(
            timestamp=datetime.now(),
            reason=reason,
            adjustment_type=adjustment_type,
            details=details,
            previous_state=previous_state,
            new_state=new_state
        )
        
        # Convert to dict
        record_dict = record.to_dict()
        
        # Verify all required fields are present
        assert "timestamp" in record_dict, \
            "to_dict() must include timestamp"
        assert "reason" in record_dict, \
            "to_dict() must include reason"
        assert "adjustment_type" in record_dict, \
            "to_dict() must include adjustment_type"
        assert "details" in record_dict, \
            "to_dict() must include details"
        
        # Verify optional fields are present when provided
        assert "previous_state" in record_dict, \
            "to_dict() must include previous_state"
        assert "new_state" in record_dict, \
            "to_dict() must include new_state"
        
        # Verify values match
        assert record_dict["reason"] == reason, \
            "Reason in dict should match original"
        assert record_dict["adjustment_type"] == adjustment_type, \
            "Adjustment type in dict should match original"
        assert record_dict["details"] == details, \
            "Details in dict should match original"
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_adjustment_record_roundtrip(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment record, converting to dict and back SHALL
        preserve all required fields (timestamp, reason, details).
        """
        # Create an adjustment record
        original = AdjustmentRecord(
            timestamp=datetime.now(),
            reason=reason,
            adjustment_type=adjustment_type,
            details=details
        )
        
        # Convert to dict and back
        record_dict = original.to_dict()
        restored = AdjustmentRecord.from_dict(record_dict)
        
        # Verify required fields are preserved
        assert restored.reason == original.reason, \
            "Reason should be preserved after roundtrip"
        assert restored.adjustment_type == original.adjustment_type, \
            "Adjustment type should be preserved after roundtrip"
        assert restored.details == original.details, \
            "Details should be preserved after roundtrip"
        
        # Verify timestamp is preserved (within tolerance for serialization)
        time_diff = abs((restored.timestamp - original.timestamp).total_seconds())
        assert time_diff < 1, \
            "Timestamp should be preserved after roundtrip (within 1 second tolerance)"


class TestSessionAdjustmentRecording:
    """
    Test adjustment recording through Session model.
    """
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_session_add_adjustment_creates_complete_record(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment added to a session, the session SHALL create
        a complete AdjustmentRecord with timestamp, reason, and details.
        """
        # Create a session
        session = Session.create()
        
        # Add an adjustment
        session.add_adjustment(
            reason=reason,
            adjustment_type=adjustment_type,
            details=details
        )
        
        # Verify adjustment was added
        assert len(session.adjustments) == 1, \
            "Session should have one adjustment"
        
        # Verify the adjustment record is complete
        record = session.adjustments[0]
        assert record.timestamp is not None, \
            "Adjustment must have timestamp"
        assert record.reason == reason, \
            "Adjustment must have correct reason"
        assert record.adjustment_type == adjustment_type, \
            "Adjustment must have correct type"
        assert record.details == details, \
            "Adjustment must have correct details"
    
    @given(
        num_adjustments=st.integers(min_value=1, max_value=10),
        adjustment_type=valid_adjustment_type()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_session_multiple_adjustments_all_complete(
        self, 
        num_adjustments: int,
        adjustment_type: str
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any number of adjustments added to a session, ALL adjustment
        records SHALL be complete with timestamp, reason, and details.
        """
        # Create a session
        session = Session.create()
        
        # Add multiple adjustments
        for i in range(num_adjustments):
            session.add_adjustment(
                reason=f"调整原因 {i}",
                adjustment_type=adjustment_type,
                details={"index": i, "value": i * 0.1}
            )
        
        # Verify all adjustments were added
        assert len(session.adjustments) == num_adjustments, \
            f"Session should have {num_adjustments} adjustments"
        
        # Verify each adjustment is complete
        for i, record in enumerate(session.adjustments):
            assert record.timestamp is not None, \
                f"Adjustment {i} must have timestamp"
            assert record.reason is not None and len(record.reason) > 0, \
                f"Adjustment {i} must have non-empty reason"
            assert record.adjustment_type is not None and len(record.adjustment_type) > 0, \
                f"Adjustment {i} must have non-empty type"
            assert record.details is not None, \
                f"Adjustment {i} must have details"
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details(),
        previous_state=valid_state_dict(),
        new_state=valid_state_dict()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_session_adjustment_with_state_changes(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any],
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any adjustment with state changes, the record SHALL include
        both previous_state and new_state in addition to required fields.
        """
        # Create a session
        session = Session.create()
        
        # Add an adjustment with state changes
        session.add_adjustment(
            reason=reason,
            adjustment_type=adjustment_type,
            details=details,
            previous_state=previous_state,
            new_state=new_state
        )
        
        # Verify adjustment was added with all fields
        assert len(session.adjustments) == 1, \
            "Session should have one adjustment"
        
        record = session.adjustments[0]
        
        # Verify required fields
        assert record.timestamp is not None, \
            "Adjustment must have timestamp"
        assert record.reason == reason, \
            "Adjustment must have correct reason"
        assert record.adjustment_type == adjustment_type, \
            "Adjustment must have correct type"
        assert record.details == details, \
            "Adjustment must have correct details"
        
        # Verify state change fields
        assert record.previous_state == previous_state, \
            "Adjustment must have correct previous_state"
        assert record.new_state == new_state, \
            "Adjustment must have correct new_state"


class TestAdjustmentRecordSerialization:
    """
    Test adjustment record serialization for database storage.
    """
    
    @given(
        reason=valid_adjustment_reason(),
        adjustment_type=valid_adjustment_type(),
        details=valid_adjustment_details()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_session_to_dict_includes_adjustments(
        self, 
        reason: str, 
        adjustment_type: str, 
        details: Dict[str, Any]
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any session with adjustments, to_dict() SHALL include
        all adjustment records in serialized form.
        """
        # Create a session and add adjustment
        session = Session.create()
        session.add_adjustment(
            reason=reason,
            adjustment_type=adjustment_type,
            details=details
        )
        
        # Convert to dict
        session_dict = session.to_dict()
        
        # Verify adjustments field exists
        assert "adjustments" in session_dict, \
            "Session dict must include adjustments field"
        
        # Parse adjustments JSON
        import json
        adjustments_data = json.loads(session_dict["adjustments"])
        
        # Verify adjustment data is complete
        assert len(adjustments_data) == 1, \
            "Should have one adjustment in serialized data"
        
        adj = adjustments_data[0]
        assert "timestamp" in adj, \
            "Serialized adjustment must have timestamp"
        assert "reason" in adj, \
            "Serialized adjustment must have reason"
        assert "adjustment_type" in adj, \
            "Serialized adjustment must have adjustment_type"
        assert "details" in adj, \
            "Serialized adjustment must have details"
    
    @given(
        num_adjustments=st.integers(min_value=1, max_value=5),
        adjustment_type=valid_adjustment_type()
    )
    @settings(max_examples=100, deadline=30000, suppress_health_check=[])
    def test_session_roundtrip_preserves_adjustments(
        self, 
        num_adjustments: int,
        adjustment_type: str
    ):
        """
        **Feature: healing-pod-system, Property 21: 调整记录完整性**
        **Validates: Requirements 10.4**
        
        For any session with adjustments, converting to dict and back
        SHALL preserve all adjustment records with complete data.
        """
        # Create a session and add adjustments
        session = Session.create()
        for i in range(num_adjustments):
            session.add_adjustment(
                reason=f"测试原因 {i}",
                adjustment_type=adjustment_type,
                details={"test_index": i}
            )
        
        # Convert to dict and back
        session_dict = session.to_dict()
        restored = Session.from_dict(session_dict)
        
        # Verify adjustments count is preserved
        assert len(restored.adjustments) == num_adjustments, \
            f"Should have {num_adjustments} adjustments after roundtrip"
        
        # Verify each adjustment is complete
        for i, record in enumerate(restored.adjustments):
            assert record.timestamp is not None, \
                f"Restored adjustment {i} must have timestamp"
            assert record.reason == f"测试原因 {i}", \
                f"Restored adjustment {i} must have correct reason"
            assert record.adjustment_type == adjustment_type, \
                f"Restored adjustment {i} must have correct type"
            assert record.details == {"test_index": i}, \
                f"Restored adjustment {i} must have correct details"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
