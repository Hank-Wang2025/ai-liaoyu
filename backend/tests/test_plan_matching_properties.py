"""
疗愈方案匹配一致性属性测试
Property-Based Tests for Therapy Plan Matching Consistency

使用 hypothesis 进行属性测试，验证疗愈方案匹配一致性
Requirements: 5.1

**Property 12: 疗愈方案匹配一致性**
*For any* 相同的 EmotionState 输入，疗愈方案匹配器 SHALL 返回相同的 TherapyPlan（在配置不变的情况下）。
"""
import os
import sys
from datetime import datetime
from typing import Optional

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import EmotionCategory, EmotionState
from models.therapy import TherapyStyle, TherapyIntensity
from services.plan_manager import PlanManager, UserPreferences


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def valid_emotion_category(draw):
    """Generate a valid EmotionCategory."""
    return draw(st.sampled_from(list(EmotionCategory)))


@st.composite
def valid_emotion_state(draw):
    """
    Generate a valid EmotionState with all required fields.
    """
    category = draw(valid_emotion_category())
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
def valid_therapy_style(draw):
    """Generate a valid TherapyStyle or None."""
    return draw(st.sampled_from([None, TherapyStyle.CHINESE, TherapyStyle.MODERN]))


@st.composite
def valid_user_preferences(draw):
    """Generate valid UserPreferences or None."""
    should_have_prefs = draw(st.booleans())
    if not should_have_prefs:
        return None
    
    preferred_style = draw(st.sampled_from([None, TherapyStyle.CHINESE, TherapyStyle.MODERN]))
    preferred_intensity = draw(st.sampled_from([None, TherapyIntensity.LOW, TherapyIntensity.MEDIUM, TherapyIntensity.HIGH]))
    
    return UserPreferences(
        preferred_style=preferred_style,
        preferred_intensity=preferred_intensity,
        history_plan_ids=[],
        effectiveness_scores={}
    )


# ============================================================================
# Property Tests - Property 12: 疗愈方案匹配一致性
# ============================================================================

class TestTherapyPlanMatchingConsistency:
    """
    Property 12: 疗愈方案匹配一致性
    
    **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
    **Validates: Requirements 5.1**
    
    *For any* 相同的 EmotionState 输入，疗愈方案匹配器 SHALL 返回相同的 TherapyPlan（在配置不变的情况下）。
    """
    
    @pytest.fixture(autouse=True)
    def setup_plan_manager(self):
        """Setup plan manager for tests."""
        self.plan_manager = PlanManager(plans_dir="content/plans")
        # Ensure we have plans loaded
        assume(len(self.plan_manager.plans) > 0)
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_same_emotion_returns_same_plan(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid EmotionState, calling match() multiple times with the same
        input SHALL return the same TherapyPlan.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        # Call match multiple times with the same emotion state
        plan1 = manager.match(emotion_state)
        plan2 = manager.match(emotion_state)
        plan3 = manager.match(emotion_state)
        
        # All results should be the same plan
        assert plan1 is not None, "First match should return a plan"
        assert plan2 is not None, "Second match should return a plan"
        assert plan3 is not None, "Third match should return a plan"
        
        assert plan1.id == plan2.id, \
            f"First and second match should return same plan: {plan1.id} != {plan2.id}"
        assert plan2.id == plan3.id, \
            f"Second and third match should return same plan: {plan2.id} != {plan3.id}"
    
    @given(
        emotion_state=valid_emotion_state(),
        style=valid_therapy_style()
    )
    @settings(max_examples=100)
    def test_same_emotion_and_style_returns_same_plan(
        self,
        emotion_state: EmotionState,
        style: Optional[TherapyStyle]
    ):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid EmotionState and style combination, calling match() multiple
        times with the same inputs SHALL return the same TherapyPlan.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        # Call match multiple times with the same emotion state and style
        plan1 = manager.match(emotion_state, style=style)
        plan2 = manager.match(emotion_state, style=style)
        
        assert plan1 is not None, "First match should return a plan"
        assert plan2 is not None, "Second match should return a plan"
        
        assert plan1.id == plan2.id, \
            f"Same emotion and style should return same plan: {plan1.id} != {plan2.id}"
    
    @given(
        emotion_state=valid_emotion_state(),
        preferences=valid_user_preferences()
    )
    @settings(max_examples=100)
    def test_same_emotion_and_preferences_returns_same_plan(
        self,
        emotion_state: EmotionState,
        preferences: Optional[UserPreferences]
    ):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid EmotionState and UserPreferences combination, calling match()
        multiple times with the same inputs SHALL return the same TherapyPlan.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        # Call match multiple times with the same emotion state and preferences
        plan1 = manager.match(emotion_state, preferences=preferences)
        plan2 = manager.match(emotion_state, preferences=preferences)
        
        assert plan1 is not None, "First match should return a plan"
        assert plan2 is not None, "Second match should return a plan"
        
        assert plan1.id == plan2.id, \
            f"Same emotion and preferences should return same plan: {plan1.id} != {plan2.id}"
    
    @given(
        emotion_state=valid_emotion_state(),
        style=valid_therapy_style(),
        preferences=valid_user_preferences()
    )
    @settings(max_examples=100)
    def test_same_full_input_returns_same_plan(
        self,
        emotion_state: EmotionState,
        style: Optional[TherapyStyle],
        preferences: Optional[UserPreferences]
    ):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid combination of EmotionState, style, and UserPreferences,
        calling match() multiple times with the same inputs SHALL return the same
        TherapyPlan.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        # Call match multiple times with all the same inputs
        plan1 = manager.match(emotion_state, style=style, preferences=preferences)
        plan2 = manager.match(emotion_state, style=style, preferences=preferences)
        plan3 = manager.match(emotion_state, style=style, preferences=preferences)
        
        assert plan1 is not None, "First match should return a plan"
        assert plan2 is not None, "Second match should return a plan"
        assert plan3 is not None, "Third match should return a plan"
        
        assert plan1.id == plan2.id == plan3.id, \
            f"All matches with same inputs should return same plan: {plan1.id}, {plan2.id}, {plan3.id}"
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_match_returns_valid_plan(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid EmotionState, match() SHALL return a valid TherapyPlan
        with all required fields.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        plan = manager.match(emotion_state)
        
        # Plan should be valid and have all required fields
        assert plan is not None, "Match should return a plan"
        assert plan.id is not None and len(plan.id) > 0, "Plan should have an id"
        assert plan.name is not None and len(plan.name) > 0, "Plan should have a name"
        assert plan.target_emotions is not None and len(plan.target_emotions) > 0, \
            "Plan should have target emotions"
        assert plan.intensity is not None, "Plan should have intensity"
        assert plan.style is not None, "Plan should have style"
        assert plan.duration > 0, "Plan should have positive duration"
        assert plan.phases is not None and len(plan.phases) > 0, "Plan should have phases"
    
    @given(
        emotion_state=valid_emotion_state(),
        num_calls=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=50)
    def test_match_consistency_over_many_calls(
        self,
        emotion_state: EmotionState,
        num_calls: int
    ):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid EmotionState, calling match() many times SHALL always
        return the same TherapyPlan.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        # Get the first result as reference
        reference_plan = manager.match(emotion_state)
        assert reference_plan is not None, "Reference match should return a plan"
        
        # Call match many times and verify consistency
        for i in range(num_calls):
            plan = manager.match(emotion_state)
            assert plan is not None, f"Match {i+1} should return a plan"
            assert plan.id == reference_plan.id, \
                f"Match {i+1} returned different plan: {plan.id} != {reference_plan.id}"


class TestMatchWithDetailsConsistency:
    """
    Additional consistency tests for match_with_details method.
    """
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_match_with_details_returns_consistent_order(
        self,
        emotion_state: EmotionState
    ):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid EmotionState, match_with_details() SHALL return results
        in the same order when called multiple times.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        # Call match_with_details multiple times
        results1 = manager.match_with_details(emotion_state, top_n=5)
        results2 = manager.match_with_details(emotion_state, top_n=5)
        
        # Results should have the same length
        assert len(results1) == len(results2), \
            f"Results should have same length: {len(results1)} != {len(results2)}"
        
        # Results should be in the same order
        for i, (r1, r2) in enumerate(zip(results1, results2)):
            assert r1.plan.id == r2.plan.id, \
                f"Result {i} should have same plan: {r1.plan.id} != {r2.plan.id}"
            # Scores should be equal (within floating point tolerance)
            assert abs(r1.score - r2.score) < 1e-9, \
                f"Result {i} should have same score: {r1.score} != {r2.score}"
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_match_and_match_with_details_return_same_top_plan(
        self,
        emotion_state: EmotionState
    ):
        """
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        
        For any valid EmotionState, match() and match_with_details()[0] SHALL
        return the same TherapyPlan.
        """
        manager = PlanManager(plans_dir="content/plans")
        assume(len(manager.plans) > 0)
        
        # Get plan from match()
        plan = manager.match(emotion_state)
        
        # Get top plan from match_with_details()
        results = manager.match_with_details(emotion_state, top_n=1)
        assume(len(results) > 0)
        
        top_plan = results[0].plan
        
        assert plan.id == top_plan.id, \
            f"match() and match_with_details() should return same top plan: {plan.id} != {top_plan.id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
