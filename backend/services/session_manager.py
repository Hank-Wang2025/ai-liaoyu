"""
疗愈会话管理器
Therapy Session Manager

实现会话生命周期管理、情绪历史记录和调整记录
Requirements: 13.1, 10.4
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from loguru import logger

from models.session import (
    Session,
    SessionStatus,
    EmotionHistoryEntry,
    AdjustmentRecord
)
from models.emotion import EmotionState, EmotionCategory
from models.therapy import TherapyPlan
from db.crud import session_crud, emotion_history_crud, adjustment_record_crud


class SessionManager:
    """
    疗愈会话管理器
    
    负责会话的创建、更新、结束和情绪历史记录
    Requirements: 13.1
    """
    
    def __init__(self):
        """初始化会话管理器"""
        self._current_session: Optional[Session] = None
        self._session_listeners: List[Callable[[Session, str], None]] = []
    
    @property
    def current_session(self) -> Optional[Session]:
        """获取当前会话"""
        return self._current_session
    
    @property
    def has_active_session(self) -> bool:
        """是否有活跃会话"""
        return self._current_session is not None and self._current_session.is_active
    
    def add_listener(self, listener: Callable[[Session, str], None]) -> None:
        """添加会话状态监听器
        
        Args:
            listener: 回调函数，接收 (session, event_type) 参数
        """
        self._session_listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[Session, str], None]) -> None:
        """移除会话状态监听器"""
        if listener in self._session_listeners:
            self._session_listeners.remove(listener)
    
    def _notify_listeners(self, event_type: str) -> None:
        """通知所有监听器"""
        if self._current_session:
            for listener in self._session_listeners:
                try:
                    listener(self._current_session, event_type)
                except Exception as e:
                    logger.error(f"Error notifying session listener: {e}")
    
    async def create_session(self) -> Session:
        """创建新会话
        
        Returns:
            新创建的会话
        """
        # 如果有活跃会话，先结束它
        if self.has_active_session:
            logger.warning("Ending existing active session before creating new one")
            await self.end_session()
        
        # 创建新会话
        session = Session.create()
        self._current_session = session
        
        # 保存到数据库
        await self._save_session(session)
        
        logger.info(f"Created new session: {session.id}")
        self._notify_listeners("created")
        
        return session
    
    async def set_initial_emotion(self, emotion: EmotionState) -> None:
        """设置初始情绪状态
        
        Args:
            emotion: 初始情绪状态
        """
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.set_initial_emotion(emotion)
        
        # 保存情绪历史到数据库
        await self._save_emotion_history(emotion)
        await self._update_session()
        
        logger.info(
            f"Session {self._current_session.id}: Initial emotion set to "
            f"{emotion.category.value} (intensity: {emotion.intensity:.2f})"
        )
        self._notify_listeners("emotion_set")
    
    async def set_plan(self, plan: TherapyPlan) -> None:
        """设置疗愈方案
        
        Args:
            plan: 疗愈方案
        """
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.set_plan(plan)
        await self._update_session()
        
        logger.info(f"Session {self._current_session.id}: Plan set to {plan.name}")
        self._notify_listeners("plan_set")
    
    async def start_therapy(self) -> None:
        """开始疗愈"""
        if not self._current_session:
            raise ValueError("No active session")
        
        if not self._current_session.plan_id:
            raise ValueError("No plan selected")
        
        self._current_session.start_therapy()
        await self._update_session()
        
        logger.info(f"Session {self._current_session.id}: Therapy started")
        self._notify_listeners("therapy_started")
    
    async def pause_session(self) -> None:
        """暂停会话"""
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.pause()
        await self._update_session()
        
        logger.info(f"Session {self._current_session.id}: Paused")
        self._notify_listeners("paused")
    
    async def resume_session(self) -> None:
        """恢复会话"""
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.resume()
        await self._update_session()
        
        logger.info(f"Session {self._current_session.id}: Resumed")
        self._notify_listeners("resumed")
    
    async def advance_phase(self) -> bool:
        """进入下一阶段
        
        Returns:
            是否成功进入下一阶段
        """
        if not self._current_session:
            raise ValueError("No active session")
        
        result = self._current_session.advance_phase()
        await self._update_session()
        
        logger.info(
            f"Session {self._current_session.id}: "
            f"Advanced to phase {self._current_session.current_phase_index}"
        )
        self._notify_listeners("phase_advanced")
        
        return result
    
    async def record_emotion(
        self, 
        emotion: EmotionState, 
        phase_name: Optional[str] = None
    ) -> None:
        """记录情绪状态
        
        Args:
            emotion: 情绪状态
            phase_name: 当前阶段名称
        """
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.add_emotion_history(emotion, phase_name)
        await self._save_emotion_history(emotion, phase_name)
        
        logger.debug(
            f"Session {self._current_session.id}: Emotion recorded - "
            f"{emotion.category.value} (intensity: {emotion.intensity:.2f})"
        )
    
    async def record_adjustment(
        self,
        reason: str,
        adjustment_type: str,
        details: Dict[str, Any],
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录调整
        
        Requirements: 10.4 - 记录每次调整的时间、原因、内容
        
        Args:
            reason: 调整原因
            adjustment_type: 调整类型
            details: 调整详情
            previous_state: 调整前状态
            new_state: 调整后状态
        """
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.add_adjustment(
            reason=reason,
            adjustment_type=adjustment_type,
            details=details,
            previous_state=previous_state,
            new_state=new_state
        )
        
        # 保存到数据库
        await self._save_adjustment(
            reason=reason,
            adjustment_type=adjustment_type,
            details=details,
            previous_state=previous_state,
            new_state=new_state
        )
        
        await self._update_session()
        
        logger.info(
            f"Session {self._current_session.id}: Adjustment recorded - "
            f"{adjustment_type}: {reason}"
        )
        self._notify_listeners("adjustment_recorded")
    
    async def end_session(
        self, 
        final_emotion: Optional[EmotionState] = None
    ) -> Session:
        """结束会话
        
        Args:
            final_emotion: 最终情绪状态
            
        Returns:
            结束的会话
        """
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.complete(final_emotion)
        await self._update_session()
        
        completed_session = self._current_session
        self._current_session = None
        
        logger.info(
            f"Session {completed_session.id}: Completed "
            f"(duration: {completed_session.duration_seconds}s)"
        )
        self._notify_listeners("completed")
        
        return completed_session
    
    async def cancel_session(self) -> Optional[Session]:
        """取消会话
        
        Returns:
            取消的会话
        """
        if not self._current_session:
            return None
        
        self._current_session.cancel()
        await self._update_session()
        
        cancelled_session = self._current_session
        self._current_session = None
        
        logger.info(f"Session {cancelled_session.id}: Cancelled")
        self._notify_listeners("cancelled")
        
        return cancelled_session
    
    async def set_user_feedback(self, feedback: Dict[str, Any]) -> None:
        """设置用户反馈
        
        Args:
            feedback: 用户反馈数据
        """
        if not self._current_session:
            raise ValueError("No active session")
        
        self._current_session.set_user_feedback(feedback)
        await self._update_session()
        
        logger.info(f"Session {self._current_session.id}: User feedback recorded")
    
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """根据ID获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话对象
        """
        data = await session_crud.get_by_id(session_id)
        if data:
            return Session.from_dict(data)
        return None
    
    async def get_recent_sessions(self, limit: int = 10) -> List[Session]:
        """获取最近的会话
        
        Args:
            limit: 返回数量限制
            
        Returns:
            会话列表
        """
        data_list = await session_crud.get_recent(limit)
        return [Session.from_dict(data) for data in data_list]
    
    async def get_session_emotion_history(
        self, 
        session_id: str
    ) -> List[EmotionHistoryEntry]:
        """获取会话的情绪历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            情绪历史列表
        """
        data_list = await emotion_history_crud.get_by_session(session_id)
        entries = []
        for data in data_list:
            emotion_state = EmotionState(
                category=EmotionCategory(data["category"]),
                intensity=data["intensity"],
                valence=data["valence"],
                arousal=data["arousal"],
                confidence=0.8,
                timestamp=datetime.fromisoformat(data["timestamp"])
            )
            entries.append(EmotionHistoryEntry(
                timestamp=datetime.fromisoformat(data["timestamp"]),
                emotion_state=emotion_state,
                phase_name=data.get("phase_name")
            ))
        return entries
    
    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """获取当前会话摘要
        
        Returns:
            会话摘要字典
        """
        if not self._current_session:
            return None
        
        session = self._current_session
        return {
            "id": session.id,
            "status": session.status.value,
            "duration_seconds": session.duration_seconds,
            "initial_emotion": {
                "category": session.initial_emotion.category.value,
                "intensity": session.initial_emotion.intensity
            } if session.initial_emotion else None,
            "current_emotion": {
                "category": session.emotion_history[-1].emotion_state.category.value,
                "intensity": session.emotion_history[-1].emotion_state.intensity
            } if session.emotion_history else None,
            "plan_name": session.plan_name,
            "current_phase_index": session.current_phase_index,
            "emotion_history_count": len(session.emotion_history),
            "adjustment_count": len(session.adjustments)
        }
    
    async def _save_session(self, session: Session) -> None:
        """保存会话到数据库"""
        try:
            data = session.to_dict()
            await session_crud.create(data)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def _update_session(self) -> None:
        """更新会话到数据库"""
        if not self._current_session:
            return
        
        try:
            data = self._current_session.to_dict()
            await session_crud.update(self._current_session.id, data)
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
    
    async def _save_emotion_history(
        self, 
        emotion: EmotionState,
        phase_name: Optional[str] = None
    ) -> None:
        """保存情绪历史到数据库"""
        if not self._current_session:
            return
        
        try:
            data = {
                "session_id": self._current_session.id,
                "timestamp": datetime.now().isoformat(),
                "category": emotion.category.value,
                "intensity": emotion.intensity,
                "valence": emotion.valence,
                "arousal": emotion.arousal,
                "audio_data": json.dumps(emotion.audio_emotion) if emotion.audio_emotion else None,
                "face_data": json.dumps(emotion.face_emotion) if emotion.face_emotion else None,
                "bio_data": json.dumps({"stress": emotion.bio_stress}) if emotion.bio_stress else None
            }
            await emotion_history_crud.create(data)
        except Exception as e:
            logger.error(f"Failed to save emotion history: {e}")
    
    async def _save_adjustment(
        self,
        reason: str,
        adjustment_type: str,
        details: Dict[str, Any],
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None
    ) -> None:
        """保存调整记录到数据库
        
        Requirements: 10.4 - 保存到数据库
        """
        if not self._current_session:
            return
        
        try:
            await adjustment_record_crud.create_adjustment(
                session_id=self._current_session.id,
                reason=reason,
                adjustment_type=adjustment_type,
                details=details,
                previous_state=previous_state,
                new_state=new_state
            )
        except Exception as e:
            logger.error(f"Failed to save adjustment record: {e}")
    
    async def get_session_adjustments(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的调整记录
        
        Args:
            session_id: 会话ID
            
        Returns:
            调整记录列表
        """
        return await adjustment_record_crud.get_by_session(session_id)


# 单例实例
session_manager = SessionManager()
