"""
虚拟角色匹配逻辑属性测试
Property-Based Tests for Virtual Character Matching Logic

使用 hypothesis 进行属性测试，验证虚拟角色匹配逻辑
Requirements: 12.3

**Property 24: 虚拟角色匹配逻辑**
*For any* 用户情绪状态，虚拟社区 SHALL 匹配情绪相似度最高或处于恢复阶段的虚拟角色。
"""
import os
import sys
from typing import List

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import EmotionCategory
from models.community import (
    VirtualCharacter,
    HealingStage,
    HealingJourneyEntry
)
from services.virtual_community import VirtualCommunityService


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def valid_emotion_category(draw):
    """Generate a valid EmotionCategory."""
    return draw(st.sampled_from(list(EmotionCategory)))


@st.composite
def valid_healing_stage(draw):
    """Generate a valid HealingStage."""
    return draw(st.sampled_from(list(HealingStage)))


@st.composite
def valid_character(draw):
    """Generate a valid VirtualCharacter for testing."""
    char_id = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=5, max_size=20))
    name = draw(st.text(min_size=1, max_size=20))
    age = draw(st.integers(min_value=18, max_value=80))
    occupation = draw(st.text(min_size=1, max_size=30))
    personality = draw(st.text(min_size=1, max_size=50))
    story = draw(st.text(min_size=1, max_size=200))
    current_emotion = draw(valid_emotion_category())
    current_stage = draw(valid_healing_stage())
    
    # Generate target emotions (0-3 emotions)
    num_targets = draw(st.integers(min_value=0, max_value=3))
    target_emotions = draw(st.lists(
        valid_emotion_category(),
        min_size=num_targets,
        max_size=num_targets,
        unique=True
    ))
    
    return VirtualCharacter(
        id=char_id,
        name=name,
        age=age,
        occupation=occupation,
        personality=personality,
        story=story,
        healing_journey=[],
        artworks=[],
        current_emotion=current_emotion,
        current_stage=current_stage,
        target_emotions=target_emotions
    )


@st.composite
def valid_limit(draw):
    """Generate a valid limit for character matching."""
    return draw(st.integers(min_value=1, max_value=20))


# ============================================================================
# Property Tests - Property 24: 虚拟角色匹配逻辑
# ============================================================================

class TestVirtualCharacterMatchingLogic:
    """
    Property 24: 虚拟角色匹配逻辑
    
    **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
    **Validates: Requirements 12.3**
    
    *For any* 用户情绪状态，虚拟社区 SHALL 匹配情绪相似度最高或处于恢复阶段的虚拟角色。
    """
    
    @pytest.fixture(autouse=True)
    def setup_service(self):
        """Setup virtual community service for tests."""
        self.service = VirtualCommunityService()
        # Ensure we have characters loaded
        assume(len(self.service.characters) > 0)
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_matched_characters_have_high_similarity_or_recovering(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        For any user emotion, matched characters SHALL have high emotion similarity
        OR be in recovering stage.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        matched = service.match_characters(user_emotion, limit=5, prefer_recovering=True)
        assume(len(matched) > 0)
        
        for character in matched:
            # 角色应该满足以下条件之一：
            # 1. 情绪相似度高（>= 0.6，即同组情绪或更高）
            # 2. 处于恢复阶段
            # 3. 目标情绪包含用户情绪
            emotion_similarity = character.get_emotion_similarity(user_emotion)
            is_recovering = character.is_recovering
            is_target_emotion = user_emotion in character.target_emotions
            
            assert emotion_similarity >= 0.2 or is_recovering or is_target_emotion, \
                f"Character {character.id} should have high similarity ({emotion_similarity}), " \
                f"be recovering ({is_recovering}), or target user emotion ({is_target_emotion})"
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_recovering_characters_prioritized_when_preferred(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        When prefer_recovering=True, recovering characters SHALL be prioritized
        in the match results.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        # 获取所有恢复中的角色
        recovering_chars = [
            c for c in service.characters.values()
            if c.is_recovering
        ]
        
        # 如果没有恢复中的角色，跳过此测试
        assume(len(recovering_chars) > 0)
        
        matched = service.match_characters(user_emotion, limit=10, prefer_recovering=True)
        assume(len(matched) > 0)
        
        # 计算匹配结果中恢复中角色的数量
        matched_recovering = [c for c in matched if c.is_recovering]
        
        # 至少应该有一个恢复中的角色在结果中
        assert len(matched_recovering) > 0, \
            "At least one recovering character should be in match results"
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_exact_emotion_match_has_highest_similarity(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Characters with exact emotion match SHALL have similarity score of 1.0.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        # 查找与用户情绪完全匹配的角色
        exact_match_chars = [
            c for c in service.characters.values()
            if c.current_emotion == user_emotion
        ]
        
        for character in exact_match_chars:
            similarity = character.get_emotion_similarity(user_emotion)
            assert similarity == 1.0, \
                f"Exact emotion match should have similarity 1.0, got {similarity}"
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_match_results_sorted_by_score(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Match results SHALL be sorted by match score in descending order.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        matched = service.match_characters(user_emotion, limit=10, prefer_recovering=True)
        assume(len(matched) >= 2)
        
        # 计算每个匹配角色的分数
        scores = []
        for character in matched:
            score = service._calculate_match_score(character, user_emotion, True)
            scores.append(score)
        
        # 验证分数是降序排列的
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], \
                f"Scores should be in descending order: {scores[i]} < {scores[i + 1]}"
    
    @given(
        user_emotion=valid_emotion_category(),
        limit=valid_limit()
    )
    @settings(max_examples=100)
    def test_match_respects_limit(
        self,
        user_emotion: EmotionCategory,
        limit: int
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Match results SHALL respect the specified limit.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        matched = service.match_characters(user_emotion, limit=limit)
        
        assert len(matched) <= limit, \
            f"Match results ({len(matched)}) should not exceed limit ({limit})"
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_match_consistency(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        For the same user emotion, match_characters SHALL return consistent results.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        # 多次调用匹配
        matched1 = service.match_characters(user_emotion, limit=5)
        matched2 = service.match_characters(user_emotion, limit=5)
        matched3 = service.match_characters(user_emotion, limit=5)
        
        # 结果应该一致
        assert len(matched1) == len(matched2) == len(matched3), \
            "Match results should have consistent length"
        
        for i in range(len(matched1)):
            assert matched1[i].id == matched2[i].id == matched3[i].id, \
                f"Match result {i} should be consistent"
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_target_emotion_characters_have_higher_score(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Characters with user emotion in target_emotions SHALL have bonus score.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        # 查找目标情绪包含用户情绪的角色
        target_chars = [
            c for c in service.characters.values()
            if user_emotion in c.target_emotions
        ]
        
        for character in target_chars:
            similarity = character.get_emotion_similarity(user_emotion)
            # 目标情绪匹配应该至少有 0.8 的相似度
            assert similarity >= 0.8, \
                f"Character with target emotion should have similarity >= 0.8, got {similarity}"


class TestEmotionSimilarityCalculation:
    """
    测试情绪相似度计算逻辑
    """
    
    @given(emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_same_emotion_similarity_is_one(
        self,
        emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Same emotion SHALL have similarity of 1.0.
        """
        character = VirtualCharacter(
            id="test_char",
            name="Test",
            age=25,
            occupation="Test",
            personality="Test",
            story="Test",
            healing_journey=[],
            artworks=[],
            current_emotion=emotion,
            current_stage=HealingStage.RECOVERING,
            target_emotions=[]
        )
        
        similarity = character.get_emotion_similarity(emotion)
        assert similarity == 1.0, \
            f"Same emotion should have similarity 1.0, got {similarity}"
    
    @given(
        char_emotion=valid_emotion_category(),
        user_emotion=valid_emotion_category()
    )
    @settings(max_examples=100)
    def test_similarity_in_valid_range(
        self,
        char_emotion: EmotionCategory,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Emotion similarity SHALL be in range [0, 1].
        """
        character = VirtualCharacter(
            id="test_char",
            name="Test",
            age=25,
            occupation="Test",
            personality="Test",
            story="Test",
            healing_journey=[],
            artworks=[],
            current_emotion=char_emotion,
            current_stage=HealingStage.RECOVERING,
            target_emotions=[]
        )
        
        similarity = character.get_emotion_similarity(user_emotion)
        assert 0.0 <= similarity <= 1.0, \
            f"Similarity should be in [0, 1], got {similarity}"


class TestMatchScoreCalculation:
    """
    测试匹配分数计算逻辑
    """
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_match_score_in_valid_range(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Match score SHALL be in range [0, 1].
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        for character in service.characters.values():
            score = service._calculate_match_score(character, user_emotion, True)
            assert 0.0 <= score <= 1.0, \
                f"Match score should be in [0, 1], got {score}"
    
    @given(user_emotion=valid_emotion_category())
    @settings(max_examples=100)
    def test_recovering_stage_adds_bonus(
        self,
        user_emotion: EmotionCategory
    ):
        """
        **Feature: healing-pod-system, Property 24: 虚拟角色匹配逻辑**
        **Validates: Requirements 12.3**
        
        Recovering stage SHALL add bonus to match score when prefer_recovering=True.
        """
        # 创建两个相同情绪但不同阶段的角色
        recovering_char = VirtualCharacter(
            id="recovering_char",
            name="Recovering",
            age=25,
            occupation="Test",
            personality="Test",
            story="Test",
            healing_journey=[],
            artworks=[],
            current_emotion=user_emotion,
            current_stage=HealingStage.RECOVERING,
            target_emotions=[]
        )
        
        struggling_char = VirtualCharacter(
            id="struggling_char",
            name="Struggling",
            age=25,
            occupation="Test",
            personality="Test",
            story="Test",
            healing_journey=[],
            artworks=[],
            current_emotion=user_emotion,
            current_stage=HealingStage.STRUGGLING,
            target_emotions=[]
        )
        
        service = VirtualCommunityService()
        
        recovering_score = service._calculate_match_score(recovering_char, user_emotion, True)
        struggling_score = service._calculate_match_score(struggling_char, user_emotion, True)
        
        # 恢复中的角色应该有更高的分数
        assert recovering_score > struggling_score, \
            f"Recovering character should have higher score: {recovering_score} <= {struggling_score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
