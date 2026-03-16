"""
虚拟社区 API 端点
Virtual Community API Endpoints

Requirements: 12.2, 12.3, 12.5
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

from models.emotion import EmotionCategory
from models.community import (
    HealingStage,
    InteractionType
)
from services.virtual_community import get_community_service

router = APIRouter(prefix="/api/community", tags=["community"])


# ===== Request/Response Models =====

class CharacterResponse(BaseModel):
    """角色响应模型"""
    id: str
    name: str
    age: int
    occupation: str
    personality: str
    story: str
    current_emotion: str
    current_stage: str
    artworks: List[str]
    likes_count: int
    flowers_count: int
    healing_journey: List[dict]


class MatchRequest(BaseModel):
    """匹配请求模型"""
    emotion: str
    limit: int = 5
    prefer_recovering: bool = True


class InteractionRequest(BaseModel):
    """互动请求模型"""
    session_id: str
    character_id: str


class InteractionResponse(BaseModel):
    """互动响应模型"""
    id: str
    session_id: str
    character_id: str
    interaction_type: str
    timestamp: str


class CharacterStatsResponse(BaseModel):
    """角色统计响应模型"""
    likes: int
    flowers: int


class ErrorResponse(BaseModel):
    """错误响应模型"""
    detail: str


# ===== Helper Functions =====

def character_to_response(char) -> CharacterResponse:
    """将角色对象转换为响应模型"""
    return CharacterResponse(
        id=char.id,
        name=char.name,
        age=char.age,
        occupation=char.occupation,
        personality=char.personality,
        story=char.story,
        current_emotion=char.current_emotion.value,
        current_stage=char.current_stage.value,
        artworks=char.artworks,
        likes_count=char.likes_count,
        flowers_count=char.flowers_count,
        healing_journey=[e.to_dict() for e in char.healing_journey]
    )


# ===== API Endpoints =====

@router.get("/characters", response_model=List[CharacterResponse])
async def get_all_characters():
    """获取所有虚拟角色
    
    Requirements: 12.2 - 包含至少30个预设虚拟角色
    """
    service = get_community_service()
    characters = service.get_all_characters()
    return [character_to_response(char) for char in characters]


@router.get("/characters/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str):
    """获取指定虚拟角色"""
    service = get_community_service()
    character = service.get_character(character_id)
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return character_to_response(character)


@router.post("/match", response_model=List[CharacterResponse])
async def match_characters(request: MatchRequest):
    """匹配虚拟角色
    
    Requirements: 12.3
    - 基于情绪相似度匹配
    - 优先匹配正在恢复中的角色
    """
    service = get_community_service()
    
    try:
        emotion = EmotionCategory(request.emotion)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid emotion: {request.emotion}"
        )
    
    matched = service.match_characters(
        user_emotion=emotion,
        limit=request.limit,
        prefer_recovering=request.prefer_recovering
    )
    
    return [character_to_response(char) for char in matched]


@router.get("/characters/stage/{stage}", response_model=List[CharacterResponse])
async def get_characters_by_stage(stage: str):
    """按疗愈阶段获取角色"""
    service = get_community_service()
    
    try:
        healing_stage = HealingStage(stage)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid stage: {stage}"
        )
    
    characters = service.get_characters_by_stage(healing_stage)
    return [character_to_response(char) for char in characters]


@router.get("/characters/emotion/{emotion}", response_model=List[CharacterResponse])
async def get_characters_by_emotion(emotion: str):
    """按情绪获取角色"""
    service = get_community_service()
    
    try:
        emotion_category = EmotionCategory(emotion)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid emotion: {emotion}"
        )
    
    characters = service.get_characters_by_emotion(emotion_category)
    return [character_to_response(char) for char in characters]


# ===== 轻互动功能 (Requirements: 12.5) =====

@router.post("/like", response_model=InteractionResponse)
async def like_character(request: InteractionRequest):
    """点赞角色
    
    Requirements: 12.5 - 仅支持点赞和送花
    """
    service = get_community_service()
    
    interaction = service.like_character(
        session_id=request.session_id,
        character_id=request.character_id
    )
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return InteractionResponse(
        id=interaction.id,
        session_id=interaction.session_id,
        character_id=interaction.character_id,
        interaction_type=interaction.interaction_type.value,
        timestamp=interaction.timestamp.isoformat()
    )


@router.post("/flower", response_model=InteractionResponse)
async def send_flower(request: InteractionRequest):
    """送花给角色
    
    Requirements: 12.5 - 仅支持点赞和送花
    """
    service = get_community_service()
    
    interaction = service.send_flower(
        session_id=request.session_id,
        character_id=request.character_id
    )
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return InteractionResponse(
        id=interaction.id,
        session_id=interaction.session_id,
        character_id=interaction.character_id,
        interaction_type=interaction.interaction_type.value,
        timestamp=interaction.timestamp.isoformat()
    )


@router.get("/characters/{character_id}/stats", response_model=CharacterStatsResponse)
async def get_character_stats(character_id: str):
    """获取角色互动统计"""
    service = get_community_service()
    stats = service.get_character_stats(character_id)
    return CharacterStatsResponse(**stats)


@router.get("/interactions/session/{session_id}", response_model=List[InteractionResponse])
async def get_session_interactions(session_id: str):
    """获取会话的所有互动记录"""
    service = get_community_service()
    interactions = service.get_session_interactions(session_id)
    
    return [
        InteractionResponse(
            id=i.id,
            session_id=i.session_id,
            character_id=i.character_id,
            interaction_type=i.interaction_type.value,
            timestamp=i.timestamp.isoformat()
        )
        for i in interactions
    ]


# ===== 禁用的功能 (Requirements: 12.5) =====

@router.post("/comment")
async def comment():
    """评论功能 - 已禁用
    
    Requirements: 12.5 - 不支持评论
    """
    raise HTTPException(
        status_code=403,
        detail="Comment feature is disabled. Only like and flower interactions are supported."
    )


@router.post("/message")
async def send_message():
    """私信功能 - 已禁用
    
    Requirements: 12.5 - 不支持私信
    """
    raise HTTPException(
        status_code=403,
        detail="Private message feature is disabled. Only like and flower interactions are supported."
    )
