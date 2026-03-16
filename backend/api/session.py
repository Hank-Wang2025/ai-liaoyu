"""会话管理 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from loguru import logger

from services.session_manager import session_manager
from services.report_generator import report_generator
from models.emotion import EmotionCategory, EmotionState
from datetime import datetime

router = APIRouter()


class StartSessionResponse(BaseModel):
    """开始会话响应"""
    session_id: str
    status: str
    message: str


class EndSessionRequest(BaseModel):
    """结束会话请求"""
    final_emotion_category: Optional[str] = None
    final_emotion_intensity: Optional[float] = None
    final_emotion_valence: Optional[float] = None
    final_emotion_arousal: Optional[float] = None


class SessionSummaryResponse(BaseModel):
    """会话摘要响应"""
    has_active_session: bool
    session: Optional[Dict[str, Any]] = None


@router.get("/", response_model=SessionSummaryResponse)
async def get_session_status():
    """获取当前会话状态"""
    summary = session_manager.get_session_summary()
    return SessionSummaryResponse(
        has_active_session=session_manager.has_active_session,
        session=summary
    )


@router.post("/start", response_model=StartSessionResponse)
async def start_session():
    """开始新的疗愈会话"""
    try:
        session = await session_manager.create_session()
        return StartSessionResponse(
            session_id=session.id,
            status=session.status.value,
            message="会话已创建"
        )
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {e}")


@router.post("/end")
async def end_session(request: Optional[EndSessionRequest] = None):
    """结束当前疗愈会话"""
    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="没有活跃的会话")

    try:
        # 构建最终情绪状态（如果提供）
        final_emotion = None
        if request and request.final_emotion_category:
            try:
                category = EmotionCategory(request.final_emotion_category)
                final_emotion = EmotionState(
                    category=category,
                    intensity=request.final_emotion_intensity or 0.5,
                    valence=request.final_emotion_valence or 0.0,
                    arousal=request.final_emotion_arousal or 0.5,
                    confidence=0.8,
                    timestamp=datetime.now()
                )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的情绪类别: {request.final_emotion_category}"
                )

        session = await session_manager.end_session(final_emotion)
        return {
            "session_id": session.id,
            "status": session.status.value,
            "duration_seconds": session.duration_seconds,
            "message": "会话已结束"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"结束会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"结束会话失败: {e}")


@router.get("/recent")
async def get_recent_sessions(limit: int = 10):
    """获取最近的会话列表"""
    try:
        sessions = await session_manager.get_recent_sessions(limit)
        return {
            "sessions": [
                {
                    "id": s.id,
                    "status": s.status.value,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_seconds": s.duration_seconds,
                    "plan_name": s.plan_name,
                    "initial_emotion": s.initial_emotion.category.value if s.initial_emotion else None,
                }
                for s in sessions
            ],
            "total": len(sessions)
        }
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {e}")


@router.post("/{session_id}/pause")
async def pause_session(session_id: str):
    """暂停指定会话的疗愈"""
    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="没有活跃的会话")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"会话不匹配: {session_id}")

    try:
        await session_manager.pause_session()
        return {
            "session_id": session_id,
            "status": "paused",
            "message": "会话已暂停"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"暂停会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"暂停会话失败: {e}")


@router.post("/{session_id}/resume")
async def resume_session(session_id: str):
    """恢复指定会话的疗愈"""
    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="没有活跃的会话")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"会话不匹配: {session_id}")

    try:
        await session_manager.resume_session()
        return {
            "session_id": session_id,
            "status": "in_therapy",
            "message": "会话已恢复"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"恢复会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复会话失败: {e}")


@router.post("/{session_id}/end")
async def end_session_by_id(session_id: str, request: Optional[EndSessionRequest] = None):
    """结束指定会话的疗愈"""
    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="没有活跃的会话")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"会话不匹配: {session_id}")

    try:
        final_emotion = None
        if request and request.final_emotion_category:
            try:
                category = EmotionCategory(request.final_emotion_category)
                final_emotion = EmotionState(
                    category=category,
                    intensity=request.final_emotion_intensity or 0.5,
                    valence=request.final_emotion_valence or 0.0,
                    arousal=request.final_emotion_arousal or 0.5,
                    confidence=0.8,
                    timestamp=datetime.now()
                )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的情绪类别: {request.final_emotion_category}"
                )

        session = await session_manager.end_session(final_emotion)
        return {
            "session_id": session.id,
            "status": session.status.value,
            "duration_seconds": session.duration_seconds,
            "message": "会话已结束"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"结束会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"结束会话失败: {e}")


@router.get("/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    try:
        session = await session_manager.get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

        return {
            "id": session.id,
            "status": session.status.value,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_seconds": session.duration_seconds,
            "plan_id": session.plan_id,
            "plan_name": session.plan_name,
            "current_phase_index": session.current_phase_index,
            "initial_emotion": {
                "category": session.initial_emotion.category.value,
                "intensity": session.initial_emotion.intensity,
                "valence": session.initial_emotion.valence,
                "arousal": session.initial_emotion.arousal,
            } if session.initial_emotion else None,
            "final_emotion": {
                "category": session.final_emotion.category.value,
                "intensity": session.final_emotion.intensity,
                "valence": session.final_emotion.valence,
                "arousal": session.final_emotion.arousal,
            } if session.final_emotion else None,
            "emotion_history_count": len(session.emotion_history),
            "adjustment_count": len(session.adjustments),
            "user_feedback": session.user_feedback,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {e}")


@router.get("/{session_id}/report")
async def get_session_report(session_id: str):
    """获取会话疗愈报告"""
    try:
        session = await session_manager.get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

        # 生成报告
        report = await report_generator.generate_report(session)

        return {
            "session_id": session_id,
            "report_id": report.id,
            "status": report.status.value,
            "therapy_start_time": report.therapy_start_time.isoformat() if report.therapy_start_time else None,
            "therapy_end_time": report.therapy_end_time.isoformat() if report.therapy_end_time else None,
            "duration_minutes": report.duration_minutes,
            "plan_name": report.plan_name,
            "initial_emotion": {
                "category": report.initial_emotion_category.value,
                "intensity": report.initial_emotion_intensity,
                "valence": report.initial_emotion_valence,
            } if report.initial_emotion_category else None,
            "final_emotion": {
                "category": report.final_emotion_category.value,
                "intensity": report.final_emotion_intensity,
                "valence": report.final_emotion_valence,
            } if report.final_emotion_category else None,
            "effectiveness": {
                "rating": report.effectiveness_metrics.effectiveness_rating,
                "emotion_improvement": report.effectiveness_metrics.emotion_improvement,
                "valence_change": report.effectiveness_metrics.valence_change,
                "stability_index": report.effectiveness_metrics.stability_index,
            } if report.effectiveness_metrics else None,
            "summary_text": report.summary_text,
            "recommendations": report.recommendations,
            "emotion_curve": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "category": p.category.value,
                    "intensity": p.intensity,
                    "valence": p.valence,
                    "phase_name": p.phase_name,
                }
                for p in (report.emotion_curve or [])
            ],
            "adjustment_count": report.adjustment_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成报告失败: {e}")
