"""
用户选择优先级属性测试
Property-Based Tests for User Selection Priority

使用 hypothesis 进行属性测试，验证用户选择优先级
Requirements: 5.5

**Property 13: 用户选择优先级**
*For any* 用户主动选择的疗愈方案，系统 SHALL 执行用户选择的方案而非自动匹配的方案。
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
from services.plan_manager import PlanManager, UserPreferences, TherapyPlanSelector


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
# Property Tests - Property 13: 用户选择优先级
# ============================================================================

class TestUserSelectionPriority:
    """
    Property 13: 用户选择优先级
    
    **Feature: healing-pod-system, Property 13: 用户选择优先级**
    **Validates: Requirements 5.5**
    
    *For any* 用户主动选择的疗愈方案，系统 SHALL 执行用户选择的方案而非自动匹配的方案。
    """
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_user_selection_overrides_auto_match(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        For any valid EmotionState, when a user manually selects a plan,
        get_effective_plan() SHALL return the user-selected plan, not the auto-matched plan.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 2)  # Need at least 2 plans to test selection
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Get the auto-matched plan first
        auto_matched_plan = plan_manager.match(emotion_state)
        
        # Select a different plan manually (pick one that's not the auto-matched one)
        available_plans = plan_manager.get_all_plans()
        different_plan = None
        for plan in available_plans:
            if plan.id != auto_matched_plan.id:
                different_plan = plan
                break
        
        assume(different_plan is not None)  # Ensure we found a different plan
        
        # User manually selects the different plan
        selected = selector.select_plan(different_plan.id)
        assert selected is not None, "select_plan should return the selected plan"
        assert selected.id == different_plan.id, "select_plan should return the correct plan"
        
        # Get effective plan - should be user selection, not auto-match
        effective_plan = selector.get_effective_plan(emotion_state)
        
        assert effective_plan.id == different_plan.id, \
            f"User selection should override auto-match: expected {different_plan.id}, got {effective_plan.id}"
        assert effective_plan.id != auto_matched_plan.id or different_plan.id == auto_matched_plan.id, \
            "Effective plan should be user selection, not auto-match"
    
    @given(
        emotion_state=valid_emotion_state(),
        style=valid_therapy_style(),
        preferences=valid_user_preferences()
    )
    @settings(max_examples=100)
    def test_user_selection_overrides_with_all_params(
        self,
        emotion_state: EmotionState,
        style: Optional[TherapyStyle],
        preferences: Optional[UserPreferences]
    ):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        For any valid combination of EmotionState, style, and preferences,
        user selection SHALL always override auto-matching regardless of parameters.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 2)
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Get all available plans
        available_plans = plan_manager.get_all_plans()
        
        # Pick a random plan to select
        plan_index = hash(str(emotion_state.category) + str(emotion_state.intensity)) % len(available_plans)
        user_selected_plan = available_plans[plan_index]
        
        # User manually selects the plan
        selector.select_plan(user_selected_plan.id)
        
        # Get effective plan with all parameters
        effective_plan = selector.get_effective_plan(emotion_state, style=style, preferences=preferences)
        
        assert effective_plan.id == user_selected_plan.id, \
            f"User selection should override auto-match with all params: expected {user_selected_plan.id}, got {effective_plan.id}"
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_clear_selection_restores_auto_match(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        After clearing user selection, get_effective_plan() SHALL return
        the auto-matched plan.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 2)
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Get the auto-matched plan
        auto_matched_plan = plan_manager.match(emotion_state)
        
        # Select a different plan
        available_plans = plan_manager.get_all_plans()
        different_plan = None
        for plan in available_plans:
            if plan.id != auto_matched_plan.id:
                different_plan = plan
                break
        
        assume(different_plan is not None)
        
        # User selects a different plan
        selector.select_plan(different_plan.id)
        
        # Verify user selection is active
        effective_before_clear = selector.get_effective_plan(emotion_state)
        assert effective_before_clear.id == different_plan.id, \
            "Before clear, effective plan should be user selection"
        
        # Clear the selection
        selector.clear_selection()
        
        # Verify auto-match is restored
        effective_after_clear = selector.get_effective_plan(emotion_state)
        assert effective_after_clear.id == auto_matched_plan.id, \
            f"After clear, effective plan should be auto-match: expected {auto_matched_plan.id}, got {effective_after_clear.id}"
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_has_user_selection_flag(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        The has_user_selection property SHALL correctly reflect whether
        a user has manually selected a plan.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 1)
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Initially, no user selection
        assert not selector.has_user_selection, \
            "Initially, has_user_selection should be False"
        
        # Select a plan
        plan = plan_manager.get_all_plans()[0]
        selector.select_plan(plan.id)
        
        assert selector.has_user_selection, \
            "After selection, has_user_selection should be True"
        
        # Clear selection
        selector.clear_selection()
        
        assert not selector.has_user_selection, \
            "After clear, has_user_selection should be False"
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_invalid_plan_selection_returns_none(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        Selecting an invalid plan ID SHALL return None and not affect
        the effective plan.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 1)
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Try to select an invalid plan
        result = selector.select_plan("invalid_plan_id_that_does_not_exist")
        
        assert result is None, "Selecting invalid plan should return None"
        assert not selector.has_user_selection, \
            "Invalid selection should not set has_user_selection"
        
        # Effective plan should be auto-matched
        effective_plan = selector.get_effective_plan(emotion_state)
        auto_matched = plan_manager.match(emotion_state)
        
        assert effective_plan.id == auto_matched.id, \
            "After invalid selection, effective plan should be auto-matched"
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_selection_info_reflects_source(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        get_selection_info() SHALL correctly indicate whether the effective
        plan comes from user selection or auto-matching.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 1)
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Get effective plan (auto-match)
        selector.get_effective_plan(emotion_state)
        info = selector.get_selection_info()
        
        assert not info["has_user_selection"], \
            "Info should show no user selection initially"
        if "effective_plan" in info:
            assert info["effective_plan"]["source"] == "auto_match", \
                "Source should be auto_match when no user selection"
        
        # Select a plan
        plan = plan_manager.get_all_plans()[0]
        selector.select_plan(plan.id)
        selector.get_effective_plan(emotion_state)
        info = selector.get_selection_info()
        
        assert info["has_user_selection"], \
            "Info should show user selection after select_plan"
        assert info["user_selected_plan_id"] == plan.id, \
            "Info should show correct user selected plan ID"
        if "effective_plan" in info:
            assert info["effective_plan"]["source"] == "user_selection", \
                "Source should be user_selection after select_plan"
    
    @given(
        emotion_state1=valid_emotion_state(),
        emotion_state2=valid_emotion_state()
    )
    @settings(max_examples=100)
    def test_user_selection_persists_across_emotion_changes(
        self,
        emotion_state1: EmotionState,
        emotion_state2: EmotionState
    ):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        User selection SHALL persist even when the emotion state changes.
        The selected plan should be returned regardless of new emotion states.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 1)
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Select a plan
        plan = plan_manager.get_all_plans()[0]
        selector.select_plan(plan.id)
        
        # Get effective plan with first emotion state
        effective1 = selector.get_effective_plan(emotion_state1)
        assert effective1.id == plan.id, \
            "User selection should be returned for first emotion state"
        
        # Get effective plan with second emotion state
        effective2 = selector.get_effective_plan(emotion_state2)
        assert effective2.id == plan.id, \
            "User selection should persist across emotion state changes"
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_multiple_selections_use_latest(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        When user makes multiple selections, the latest selection SHALL
        be the effective plan.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 3)
        
        selector = TherapyPlanSelector(plan_manager)
        plans = plan_manager.get_all_plans()
        
        # Select first plan
        selector.select_plan(plans[0].id)
        effective1 = selector.get_effective_plan(emotion_state)
        assert effective1.id == plans[0].id, "First selection should be effective"
        
        # Select second plan
        selector.select_plan(plans[1].id)
        effective2 = selector.get_effective_plan(emotion_state)
        assert effective2.id == plans[1].id, "Second selection should override first"
        
        # Select third plan
        selector.select_plan(plans[2].id)
        effective3 = selector.get_effective_plan(emotion_state)
        assert effective3.id == plans[2].id, "Third selection should override second"


class TestUserSelectionWithAvailablePlans:
    """
    Additional tests for user selection with available plans list.
    """
    
    @given(emotion_state=valid_emotion_state())
    @settings(max_examples=100)
    def test_available_plans_marks_selected(self, emotion_state: EmotionState):
        """
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        
        get_available_plans_for_selection() SHALL correctly mark the
        currently selected plan.
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        assume(len(plan_manager.plans) >= 2)
        
        selector = TherapyPlanSelector(plan_manager)
        
        # Select a plan
        plans = plan_manager.get_all_plans()
        selected_plan = plans[0]
        selector.select_plan(selected_plan.id)
        
        # Get available plans
        available = selector.get_available_plans_for_selection(emotion_state)
        
        # Find the selected plan in the list
        selected_in_list = None
        for plan_info in available:
            if plan_info["id"] == selected_plan.id:
                selected_in_list = plan_info
                break
        
        assert selected_in_list is not None, "Selected plan should be in available list"
        assert selected_in_list["is_selected"], \
            "Selected plan should be marked as is_selected=True"
        
        # Other plans should not be marked as selected
        for plan_info in available:
            if plan_info["id"] != selected_plan.id:
                assert not plan_info["is_selected"], \
                    f"Non-selected plan {plan_info['id']} should have is_selected=False"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
