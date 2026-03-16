"""
轻互动限制属性测试
Property-Based Tests for Light Interaction Limitation

使用 hypothesis 进行属性测试，验证虚拟社区轻互动限制
Requirements: 12.5

**Property 25: 轻互动限制**
*For any* 虚拟社区互动，系统 SHALL 仅支持点赞和送花操作，不支持评论和私信。
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
    InteractionType,
    Interaction
)
from services.virtual_community import VirtualCommunityService


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def valid_session_id(draw):
    """Generate a valid session ID."""
    return draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=5,
        max_size=50
    ))


@st.composite
def valid_character_id(draw):
    """Generate a valid character ID."""
    return draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=5,
        max_size=30
    ))


@st.composite
def valid_interaction_type(draw):
    """Generate a valid InteractionType (only LIKE and FLOWER)."""
    return draw(st.sampled_from([InteractionType.LIKE, InteractionType.FLOWER]))


@st.composite
def valid_comment_content(draw):
    """Generate comment content for testing disabled feature."""
    return draw(st.text(min_size=1, max_size=500))


@st.composite
def valid_message_content(draw):
    """Generate message content for testing disabled feature."""
    return draw(st.text(min_size=1, max_size=1000))


# ============================================================================
# Property Tests - Property 25: 轻互动限制
# ============================================================================

class TestLightInteractionLimitation:
    """
    Property 25: 轻互动限制
    
    **Feature: healing-pod-system, Property 25: 轻互动限制**
    **Validates: Requirements 12.5**
    
    *For any* 虚拟社区互动，系统 SHALL 仅支持点赞和送花操作，不支持评论和私信。
    """
    
    @pytest.fixture(autouse=True)
    def setup_service(self):
        """Setup virtual community service for tests."""
        self.service = VirtualCommunityService()
        # Ensure we have characters loaded
        assume(len(self.service.characters) > 0)
    
    @given(session_id=valid_session_id())
    @settings(max_examples=100)
    def test_like_interaction_allowed(
        self,
        session_id: str
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any session, like interaction SHALL be allowed and return valid Interaction.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        # 获取一个有效的角色ID
        character_id = list(service.characters.keys())[0]
        
        # 点赞应该成功
        interaction = service.like_character(session_id, character_id)
        
        assert interaction is not None, \
            "Like interaction should return a valid Interaction object"
        assert interaction.interaction_type == InteractionType.LIKE, \
            f"Interaction type should be LIKE, got {interaction.interaction_type}"
        assert interaction.session_id == session_id, \
            f"Session ID should match: expected {session_id}, got {interaction.session_id}"
        assert interaction.character_id == character_id, \
            f"Character ID should match: expected {character_id}, got {interaction.character_id}"
    
    @given(session_id=valid_session_id())
    @settings(max_examples=100)
    def test_flower_interaction_allowed(
        self,
        session_id: str
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any session, flower interaction SHALL be allowed and return valid Interaction.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        # 获取一个有效的角色ID
        character_id = list(service.characters.keys())[0]
        
        # 送花应该成功
        interaction = service.send_flower(session_id, character_id)
        
        assert interaction is not None, \
            "Flower interaction should return a valid Interaction object"
        assert interaction.interaction_type == InteractionType.FLOWER, \
            f"Interaction type should be FLOWER, got {interaction.interaction_type}"
        assert interaction.session_id == session_id, \
            f"Session ID should match: expected {session_id}, got {interaction.session_id}"
        assert interaction.character_id == character_id, \
            f"Character ID should match: expected {character_id}, got {interaction.character_id}"
    
    @given(
        session_id=valid_session_id(),
        character_id=valid_character_id(),
        comment=valid_comment_content()
    )
    @settings(max_examples=100)
    def test_comment_interaction_disabled(
        self,
        session_id: str,
        character_id: str,
        comment: str
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any session and character, comment interaction SHALL be disabled
        and raise NotImplementedError.
        """
        service = VirtualCommunityService()
        
        # 评论功能应该抛出 NotImplementedError
        with pytest.raises(NotImplementedError) as exc_info:
            service.comment(session_id, character_id, comment)
        
        # 验证错误消息包含正确的说明
        error_message = str(exc_info.value)
        assert "Comment" in error_message or "comment" in error_message, \
            f"Error message should mention 'comment': {error_message}"
        assert "disabled" in error_message.lower(), \
            f"Error message should mention 'disabled': {error_message}"
    
    @given(
        session_id=valid_session_id(),
        character_id=valid_character_id(),
        message=valid_message_content()
    )
    @settings(max_examples=100)
    def test_private_message_interaction_disabled(
        self,
        session_id: str,
        character_id: str,
        message: str
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any session and character, private message interaction SHALL be disabled
        and raise NotImplementedError.
        """
        service = VirtualCommunityService()
        
        # 私信功能应该抛出 NotImplementedError
        with pytest.raises(NotImplementedError) as exc_info:
            service.send_message(session_id, character_id, message)
        
        # 验证错误消息包含正确的说明
        error_message = str(exc_info.value)
        assert "message" in error_message.lower() or "Message" in error_message, \
            f"Error message should mention 'message': {error_message}"
        assert "disabled" in error_message.lower(), \
            f"Error message should mention 'disabled': {error_message}"
    
    @given(interaction_type=valid_interaction_type())
    @settings(max_examples=100)
    def test_interaction_type_only_like_or_flower(
        self,
        interaction_type: InteractionType
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        InteractionType enum SHALL only contain LIKE and FLOWER values.
        """
        # 验证 InteractionType 只有两个有效值
        valid_types = {InteractionType.LIKE, InteractionType.FLOWER}
        
        assert interaction_type in valid_types, \
            f"InteractionType should only be LIKE or FLOWER, got {interaction_type}"
        
        # 验证枚举只有两个成员
        all_types = list(InteractionType)
        assert len(all_types) == 2, \
            f"InteractionType should have exactly 2 members, got {len(all_types)}"
        assert set(all_types) == valid_types, \
            f"InteractionType should only contain LIKE and FLOWER"


class TestInteractionCountTracking:
    """
    测试互动计数追踪
    
    验证点赞和送花操作正确更新角色的互动计数
    """
    
    @given(
        session_id=valid_session_id(),
        num_likes=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_like_count_increments_correctly(
        self,
        session_id: str,
        num_likes: int
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any number of like interactions, character's likes_count SHALL
        increment by the correct amount.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        character_id = list(service.characters.keys())[0]
        initial_likes = service.characters[character_id].likes_count
        
        # 执行多次点赞
        for _ in range(num_likes):
            interaction = service.like_character(session_id, character_id)
            assert interaction is not None
        
        final_likes = service.characters[character_id].likes_count
        
        assert final_likes == initial_likes + num_likes, \
            f"Likes count should be {initial_likes + num_likes}, got {final_likes}"
    
    @given(
        session_id=valid_session_id(),
        num_flowers=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_flower_count_increments_correctly(
        self,
        session_id: str,
        num_flowers: int
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any number of flower interactions, character's flowers_count SHALL
        increment by the correct amount.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        character_id = list(service.characters.keys())[0]
        initial_flowers = service.characters[character_id].flowers_count
        
        # 执行多次送花
        for _ in range(num_flowers):
            interaction = service.send_flower(session_id, character_id)
            assert interaction is not None
        
        final_flowers = service.characters[character_id].flowers_count
        
        assert final_flowers == initial_flowers + num_flowers, \
            f"Flowers count should be {initial_flowers + num_flowers}, got {final_flowers}"


class TestInteractionRecordIntegrity:
    """
    测试互动记录完整性
    
    验证互动记录正确保存并可查询
    """
    
    @given(session_id=valid_session_id())
    @settings(max_examples=100)
    def test_interaction_records_saved_correctly(
        self,
        session_id: str
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any interaction, the record SHALL be saved and retrievable.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        character_id = list(service.characters.keys())[0]
        
        # 执行点赞和送花
        like_interaction = service.like_character(session_id, character_id)
        flower_interaction = service.send_flower(session_id, character_id)
        
        # 获取会话的所有互动记录
        session_interactions = service.get_session_interactions(session_id)
        
        # 验证记录已保存
        assert len(session_interactions) >= 2, \
            f"Should have at least 2 interactions, got {len(session_interactions)}"
        
        # 验证记录内容正确
        interaction_ids = [i.id for i in session_interactions]
        assert like_interaction.id in interaction_ids, \
            "Like interaction should be in session interactions"
        assert flower_interaction.id in interaction_ids, \
            "Flower interaction should be in session interactions"
    
    @given(
        session_id=valid_session_id(),
        interaction_type=valid_interaction_type()
    )
    @settings(max_examples=100)
    def test_interaction_has_valid_timestamp(
        self,
        session_id: str,
        interaction_type: InteractionType
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any interaction, the timestamp SHALL be set and valid.
        """
        service = VirtualCommunityService()
        assume(len(service.characters) > 0)
        
        character_id = list(service.characters.keys())[0]
        
        # 根据类型执行互动
        if interaction_type == InteractionType.LIKE:
            interaction = service.like_character(session_id, character_id)
        else:
            interaction = service.send_flower(session_id, character_id)
        
        assert interaction is not None
        assert interaction.timestamp is not None, \
            "Interaction should have a timestamp"
        
        # 验证时间戳是合理的（不是未来时间）
        from datetime import datetime
        assert interaction.timestamp <= datetime.now(), \
            "Interaction timestamp should not be in the future"


class TestInvalidCharacterInteraction:
    """
    测试无效角色互动
    
    验证对不存在的角色进行互动时的行为
    """
    
    @given(
        session_id=valid_session_id(),
        invalid_character_id=st.text(
            alphabet="xyz",  # 使用不太可能存在的字符
            min_size=20,
            max_size=30
        )
    )
    @settings(max_examples=100)
    def test_like_invalid_character_returns_none(
        self,
        session_id: str,
        invalid_character_id: str
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any invalid character ID, like interaction SHALL return None.
        """
        service = VirtualCommunityService()
        
        # 确保角色ID不存在
        assume(invalid_character_id not in service.characters)
        
        # 对不存在的角色点赞应该返回 None
        interaction = service.like_character(session_id, invalid_character_id)
        
        assert interaction is None, \
            f"Like on invalid character should return None, got {interaction}"
    
    @given(
        session_id=valid_session_id(),
        invalid_character_id=st.text(
            alphabet="xyz",
            min_size=20,
            max_size=30
        )
    )
    @settings(max_examples=100)
    def test_flower_invalid_character_returns_none(
        self,
        session_id: str,
        invalid_character_id: str
    ):
        """
        **Feature: healing-pod-system, Property 25: 轻互动限制**
        **Validates: Requirements 12.5**
        
        For any invalid character ID, flower interaction SHALL return None.
        """
        service = VirtualCommunityService()
        
        # 确保角色ID不存在
        assume(invalid_character_id not in service.characters)
        
        # 对不存在的角色送花应该返回 None
        interaction = service.send_flower(session_id, invalid_character_id)
        
        assert interaction is None, \
            f"Flower on invalid character should return None, got {interaction}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
