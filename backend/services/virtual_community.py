"""
虚拟社区服务
Virtual Community Service

Requirements: 12.2, 12.3, 12.5
"""
import os
import yaml
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.community import (
    VirtualCharacter,
    HealingStage,
    HealingJourneyEntry,
    InteractionType,
    Interaction
)
from models.emotion import EmotionCategory

logger = logging.getLogger(__name__)


class VirtualCommunityService:
    """虚拟社区服务
    
    Requirements:
    - 12.2: 包含至少30个预设虚拟角色
    - 12.3: 基于情绪相似度匹配，优先匹配正在恢复中的角色
    - 12.5: 仅支持点赞和送花，不支持评论和私信
    """
    
    def __init__(self, characters_file: str = None):
        """初始化虚拟社区服务
        
        Args:
            characters_file: 预设角色配置文件路径
        """
        self.characters: Dict[str, VirtualCharacter] = {}
        self.interactions: List[Interaction] = []
        
        # 默认配置文件路径
        if characters_file is None:
            characters_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "content", "community", "preset_characters.yaml"
            )
        
        self.characters_file = characters_file
        self._load_preset_characters()
    
    def _load_preset_characters(self) -> None:
        """加载预设角色"""
        if not os.path.exists(self.characters_file):
            logger.warning(f"Characters file not found: {self.characters_file}")
            return
        
        try:
            with open(self.characters_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or 'characters' not in data:
                logger.warning("No characters found in config file")
                return
            
            for char_data in data['characters']:
                character = self._parse_character(char_data)
                if character:
                    self.characters[character.id] = character
            
            logger.info(f"Loaded {len(self.characters)} preset characters")
        
        except Exception as e:
            logger.error(f"Failed to load preset characters: {e}")
    
    def _parse_character(self, data: Dict[str, Any]) -> Optional[VirtualCharacter]:
        """解析角色数据"""
        try:
            # 解析疗愈旅程
            healing_journey = []
            for entry in data.get('healing_journey', []):
                journey_entry = HealingJourneyEntry(
                    date=entry['date'],
                    stage=HealingStage(entry['stage']),
                    emotion=EmotionCategory(entry['emotion']),
                    description=entry['description'],
                    artwork=entry.get('artwork')
                )
                healing_journey.append(journey_entry)
            
            # 解析目标情绪
            target_emotions = [
                EmotionCategory(e) 
                for e in data.get('target_emotions', [])
            ]
            
            return VirtualCharacter(
                id=data['id'],
                name=data['name'],
                age=data['age'],
                occupation=data['occupation'],
                personality=data['personality'],
                story=data['story'],
                healing_journey=healing_journey,
                artworks=data.get('artworks', []),
                current_emotion=EmotionCategory(data['current_emotion']),
                current_stage=HealingStage(data['current_stage']),
                target_emotions=target_emotions
            )
        except Exception as e:
            logger.error(f"Failed to parse character: {e}")
            return None

    def match_characters(
        self, 
        user_emotion: EmotionCategory,
        limit: int = 5,
        prefer_recovering: bool = True
    ) -> List[VirtualCharacter]:
        """匹配虚拟角色
        
        Requirements: 12.3
        - 基于情绪相似度匹配
        - 优先匹配正在恢复中的角色
        
        Args:
            user_emotion: 用户当前情绪
            limit: 返回角色数量限制
            prefer_recovering: 是否优先匹配恢复中的角色
        
        Returns:
            匹配的角色列表，按相关性排序
        """
        if not self.characters:
            return []
        
        # 计算每个角色的匹配分数
        scored_characters = []
        for character in self.characters.values():
            score = self._calculate_match_score(
                character, 
                user_emotion, 
                prefer_recovering
            )
            scored_characters.append((character, score))
        
        # 按分数降序排序
        scored_characters.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前N个角色
        return [char for char, _ in scored_characters[:limit]]
    
    def _calculate_match_score(
        self,
        character: VirtualCharacter,
        user_emotion: EmotionCategory,
        prefer_recovering: bool
    ) -> float:
        """计算角色匹配分数
        
        Requirements: 12.3
        - 情绪相似度最高或处于恢复阶段的角色优先
        
        Args:
            character: 虚拟角色
            user_emotion: 用户情绪
            prefer_recovering: 是否优先恢复中角色
        
        Returns:
            匹配分数 (0-1)
        """
        score = 0.0
        
        # 情绪相似度 (权重: 0.6)
        emotion_similarity = character.get_emotion_similarity(user_emotion)
        score += emotion_similarity * 0.6
        
        # 恢复阶段加分 (权重: 0.3)
        if prefer_recovering and character.is_recovering:
            score += 0.3
        elif character.current_stage == HealingStage.IMPROVING:
            score += 0.2
        elif character.current_stage == HealingStage.THRIVING:
            score += 0.1
        
        # 目标情绪匹配加分 (权重: 0.1)
        if user_emotion in character.target_emotions:
            score += 0.1
        
        return min(1.0, score)

    def get_character(self, character_id: str) -> Optional[VirtualCharacter]:
        """获取指定角色
        
        Args:
            character_id: 角色ID
        
        Returns:
            角色对象，不存在则返回None
        """
        return self.characters.get(character_id)
    
    def get_all_characters(self) -> List[VirtualCharacter]:
        """获取所有角色
        
        Returns:
            所有角色列表
        """
        return list(self.characters.values())
    
    def get_characters_by_stage(
        self, 
        stage: HealingStage
    ) -> List[VirtualCharacter]:
        """按疗愈阶段获取角色
        
        Args:
            stage: 疗愈阶段
        
        Returns:
            该阶段的角色列表
        """
        return [
            char for char in self.characters.values()
            if char.current_stage == stage
        ]
    
    def get_characters_by_emotion(
        self, 
        emotion: EmotionCategory
    ) -> List[VirtualCharacter]:
        """按情绪获取角色
        
        Args:
            emotion: 情绪类别
        
        Returns:
            该情绪的角色列表
        """
        return [
            char for char in self.characters.values()
            if char.current_emotion == emotion
        ]
    
    # ===== 轻互动功能 (Requirements: 12.5) =====
    
    def like_character(
        self, 
        session_id: str, 
        character_id: str
    ) -> Optional[Interaction]:
        """点赞角色
        
        Requirements: 12.5 - 仅支持点赞和送花
        
        Args:
            session_id: 会话ID
            character_id: 角色ID
        
        Returns:
            互动记录，角色不存在则返回None
        """
        character = self.characters.get(character_id)
        if not character:
            logger.warning(f"Character not found: {character_id}")
            return None
        
        # 创建互动记录
        interaction = Interaction.create(
            session_id=session_id,
            character_id=character_id,
            interaction_type=InteractionType.LIKE
        )
        
        # 更新角色点赞数
        character.likes_count += 1
        
        # 保存互动记录
        self.interactions.append(interaction)
        
        logger.info(f"Session {session_id} liked character {character_id}")
        return interaction
    
    def send_flower(
        self, 
        session_id: str, 
        character_id: str
    ) -> Optional[Interaction]:
        """送花给角色
        
        Requirements: 12.5 - 仅支持点赞和送花
        
        Args:
            session_id: 会话ID
            character_id: 角色ID
        
        Returns:
            互动记录，角色不存在则返回None
        """
        character = self.characters.get(character_id)
        if not character:
            logger.warning(f"Character not found: {character_id}")
            return None
        
        # 创建互动记录
        interaction = Interaction.create(
            session_id=session_id,
            character_id=character_id,
            interaction_type=InteractionType.FLOWER
        )
        
        # 更新角色送花数
        character.flowers_count += 1
        
        # 保存互动记录
        self.interactions.append(interaction)
        
        logger.info(f"Session {session_id} sent flower to character {character_id}")
        return interaction

    def get_session_interactions(
        self, 
        session_id: str
    ) -> List[Interaction]:
        """获取会话的所有互动记录
        
        Args:
            session_id: 会话ID
        
        Returns:
            互动记录列表
        """
        return [
            i for i in self.interactions 
            if i.session_id == session_id
        ]
    
    def get_character_interactions(
        self, 
        character_id: str
    ) -> List[Interaction]:
        """获取角色的所有互动记录
        
        Args:
            character_id: 角色ID
        
        Returns:
            互动记录列表
        """
        return [
            i for i in self.interactions 
            if i.character_id == character_id
        ]
    
    def get_character_stats(
        self, 
        character_id: str
    ) -> Dict[str, int]:
        """获取角色互动统计
        
        Args:
            character_id: 角色ID
        
        Returns:
            统计数据 {likes: int, flowers: int}
        """
        character = self.characters.get(character_id)
        if not character:
            return {"likes": 0, "flowers": 0}
        
        return {
            "likes": character.likes_count,
            "flowers": character.flowers_count
        }
    
    # ===== 禁用的功能 (Requirements: 12.5) =====
    
    def comment(self, *args, **kwargs) -> None:
        """评论功能 - 已禁用
        
        Requirements: 12.5 - 不支持评论
        
        Raises:
            NotImplementedError: 评论功能已禁用
        """
        raise NotImplementedError(
            "Comment feature is disabled. "
            "Only like and flower interactions are supported."
        )
    
    def send_message(self, *args, **kwargs) -> None:
        """私信功能 - 已禁用
        
        Requirements: 12.5 - 不支持私信
        
        Raises:
            NotImplementedError: 私信功能已禁用
        """
        raise NotImplementedError(
            "Private message feature is disabled. "
            "Only like and flower interactions are supported."
        )


# 全局服务实例
_community_service: Optional[VirtualCommunityService] = None


def get_community_service() -> VirtualCommunityService:
    """获取虚拟社区服务实例（单例）"""
    global _community_service
    if _community_service is None:
        _community_service = VirtualCommunityService()
    return _community_service
