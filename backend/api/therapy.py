"""疗愈引擎 API 路由"""
import asyncio
import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from loguru import logger

from models.emotion import EmotionCategory, EmotionState
from models.therapy import TherapyStyle, TherapyIntensity
from services.plan_manager import (
    PlanManager,
    UserPreferences,
    TherapyPlanSelector
)
from services.audio_controller import get_shared_audio_player
from services.chair_controller import ChairControllerManager
from services.cosyvoice_synthesizer import (
    CosyVoiceSynthesizer,
    MockCosyVoiceSynthesizer,
    VoiceEmotion,
    VoiceSpeaker,
    VoiceSynthesisConfig,
    create_voice_synthesizer,
    TherapyVoiceSynthesizer,
    EmotionVoiceMapper
)
from services.qwen_dialog import (
    QwenDialogEngine,
    MockQwenDialogEngine,
    DialogMessage,
    DialogResponse,
    DialogRole,
    CrisisKeywordDetector,
    create_dialog_engine
)
from services.device_initializer import get_device_initializer

router = APIRouter()

# 全局实例
_plan_manager: Optional[PlanManager] = None
_plan_selector: Optional[TherapyPlanSelector] = None
_voice_synthesizer: Optional[CosyVoiceSynthesizer] = None
_therapy_voice_synthesizer: Optional[TherapyVoiceSynthesizer] = None
_dialog_engine: Optional[QwenDialogEngine] = None
_current_executor: Optional[Any] = None
_stop_finalize_tasks: dict[str, asyncio.Task] = {}
_stopping_session_ids: set[str] = set()
RUNTIME_INTENSITY_MIN = 1
RUNTIME_INTENSITY_MAX = 5


def get_plan_manager() -> PlanManager:
    """获取方案管理器单例"""
    global _plan_manager
    if _plan_manager is None:
        _plan_manager = PlanManager()
    return _plan_manager


def get_plan_selector() -> TherapyPlanSelector:
    """获取方案选择器单例"""
    global _plan_selector
    if _plan_selector is None:
        _plan_selector = TherapyPlanSelector(get_plan_manager())
    return _plan_selector


def get_voice_synthesizer():
    """获取语音合成器单例"""
    global _voice_synthesizer
    if _voice_synthesizer is None:
        # 默认使用 Mock 实现，生产环境可以设置 use_mock=False
        _voice_synthesizer = create_voice_synthesizer(use_mock=True)
    return _voice_synthesizer


def get_therapy_voice_synthesizer() -> TherapyVoiceSynthesizer:
    """获取疗愈语音合成器单例"""
    global _therapy_voice_synthesizer
    if _therapy_voice_synthesizer is None:
        _therapy_voice_synthesizer = TherapyVoiceSynthesizer(
            synthesizer=get_voice_synthesizer()
        )
    return _therapy_voice_synthesizer


def get_dialog_engine():
    """获取对话引擎单例"""
    global _dialog_engine
    if _dialog_engine is None:
        # 默认使用 Mock 实现，生产环境可以设置 use_mock=False
        _dialog_engine = create_dialog_engine(use_mock=True)
    return _dialog_engine


def get_current_executor() -> Optional[Any]:
    return _current_executor


def set_current_executor(executor: Optional[Any]) -> None:
    global _current_executor
    _current_executor = executor


def create_background_task(coro: Any) -> asyncio.Task:
    return asyncio.create_task(coro)


async def _build_therapy_executor() -> Any:
    from services.therapy_executor import TherapyExecutor

    audio_player = await get_shared_audio_player()

    chair_manager = None
    initializer = get_device_initializer()
    chair_controller = initializer.get_chair_controller()
    if chair_controller is None:
        try:
            await initializer.ensure_chair_controller()
        except Exception as exc:
            logger.warning(f"Device initialization failed while building therapy executor: {exc}")
        chair_controller = initializer.get_chair_controller()

    if chair_controller is not None:
        chair_manager = ChairControllerManager()
        chair_manager.set_controller(chair_controller)

    return TherapyExecutor(audio_player=audio_player, chair_manager=chair_manager)


def _coarse_intensity_to_runtime_level(intensity: TherapyIntensity) -> int:
    mapping = {
        TherapyIntensity.LOW: RUNTIME_INTENSITY_MIN,
        TherapyIntensity.MEDIUM: 3,
        TherapyIntensity.HIGH: RUNTIME_INTENSITY_MAX,
    }
    return mapping[intensity]


def _runtime_level_to_coarse_intensity(level: int) -> TherapyIntensity:
    if level <= 2:
        return TherapyIntensity.LOW
    if level == 3:
        return TherapyIntensity.MEDIUM
    return TherapyIntensity.HIGH


def _get_runtime_intensity_level(plan: Any) -> int:
    level = getattr(plan, "runtime_intensity_level", None)
    if isinstance(level, int):
        normalized_level = max(RUNTIME_INTENSITY_MIN, min(RUNTIME_INTENSITY_MAX, level))
        setattr(plan, "runtime_intensity_level", normalized_level)
        return normalized_level

    intensity = getattr(plan, "intensity", TherapyIntensity.MEDIUM)
    if not isinstance(intensity, TherapyIntensity):
        try:
            intensity = TherapyIntensity(intensity)
        except Exception:
            intensity = TherapyIntensity.MEDIUM

    setattr(plan, "intensity", intensity)
    fallback_level = _coarse_intensity_to_runtime_level(intensity)
    setattr(plan, "runtime_intensity_level", fallback_level)
    return fallback_level


def _get_adjustment_target_runtime_level(
    current_level: int,
    direction: str,
) -> tuple[int, bool]:
    if direction == "relax":
        target_level = max(RUNTIME_INTENSITY_MIN, current_level - 1)
    elif direction == "intensify":
        target_level = min(RUNTIME_INTENSITY_MAX, current_level + 1)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid adjustment direction: {direction}")

    return target_level, target_level == current_level


def _get_pending_stop_task(session_id: str) -> Optional[asyncio.Task]:
    task = _stop_finalize_tasks.get(session_id)
    if task is not None and task.done():
        _stop_finalize_tasks.pop(session_id, None)
        task = None
    return task


async def _finalize_stopped_session(session_id: str) -> None:
    from services.session_manager import session_manager

    try:
        executor = get_current_executor()
        if executor is not None:
            try:
                await executor.stop()
            finally:
                set_current_executor(None)

        active_session = session_manager.current_session
        if (
            active_session is not None
            and session_manager.has_active_session
            and active_session.id == session_id
        ):
            await session_manager.end_session()
    except Exception as exc:
        logger.error(f"Fast stop finalization failed for session {session_id}: {exc}")
    finally:
        _stop_finalize_tasks.pop(session_id, None)
        _stopping_session_ids.discard(session_id)


def _get_adjustment_target_intensity(
    current_intensity: TherapyIntensity,
    direction: str,
) -> tuple[TherapyIntensity, bool]:
    intensity_order = [
        TherapyIntensity.LOW,
        TherapyIntensity.MEDIUM,
        TherapyIntensity.HIGH,
    ]

    try:
        current_index = intensity_order.index(current_intensity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid current plan intensity") from exc

    if direction == "relax":
        target_index = max(0, current_index - 1)
    elif direction == "intensify":
        target_index = min(len(intensity_order) - 1, current_index + 1)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid adjustment direction: {direction}")

    return intensity_order[target_index], target_index == current_index


# Request/Response Models
class EmotionStateRequest(BaseModel):
    """情绪状态请求"""
    category: str
    intensity: float
    valence: float = 0.0
    arousal: float = 0.5
    confidence: float = 0.8


class MatchPlanRequest(BaseModel):
    """方案匹配请求"""
    emotion: EmotionStateRequest
    style: Optional[str] = None
    preferred_style: Optional[str] = None
    preferred_intensity: Optional[str] = None


class SelectPlanRequest(BaseModel):
    """方案选择请求"""
    plan_id: str


class AdjustIntensityRequest(BaseModel):
    direction: str = Field(..., description="Adjust direction: relax or intensify")


class PlanResponse(BaseModel):
    """方案响应"""
    id: str
    name: str
    description: str
    style: str
    intensity: str
    duration: int
    target_emotions: List[str]
    phase_count: int


class VoiceSynthesisRequest(BaseModel):
    """语音合成请求"""
    text: str = Field(..., min_length=1, max_length=5000, description="要合成的文本")
    emotion: Optional[str] = Field(default="gentle", description="情感类型: gentle/warm/calm/encouraging")
    speed: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="语速 (0.5-2.0)")
    speaker: Optional[str] = Field(default="中文女", description="语音角色")
    stream: Optional[bool] = Field(default=False, description="是否流式输出")


class VoiceSynthesisResponse(BaseModel):
    """语音合成响应"""
    success: bool
    duration_ms: int
    sample_rate: int
    text: str
    emotion: str
    speaker: str
    audio_base64: Optional[str] = None  # Base64 编码的音频数据
    message: Optional[str] = None


class EmotionBasedSynthesisRequest(BaseModel):
    """基于情绪状态的语音合成请求"""
    text: str = Field(..., min_length=1, max_length=5000, description="要合成的文本")
    emotion_category: str = Field(default="neutral", description="用户当前情绪类别")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="情绪强度 (0-1)")
    valence: float = Field(default=0.0, ge=-1.0, le=1.0, description="效价 (-1 到 1)")
    arousal: float = Field(default=0.5, ge=0.0, le=1.0, description="唤醒度 (0-1)")


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    check_crisis: bool = Field(default=True, description="是否检查危机关键词")


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool
    content: str
    is_first_response: bool = False
    contains_ai_disclosure: bool = False
    contains_crisis_warning: bool = False
    crisis_resources: Optional[List[str]] = None
    generation_time_ms: int = 0
    message: Optional[str] = None


@router.get("/")
async def get_therapy_status():
    """获取疗愈引擎状态"""
    manager = get_plan_manager()
    return {
        "status": "ready",
        "module": "therapy",
        "plans_loaded": len(manager.get_all_plans())
    }


@router.get("/plans")
async def list_plans():
    """获取疗愈方案列表"""
    manager = get_plan_manager()
    plans = manager.get_all_plans()

    return {
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "style": p.style.value,
                "intensity": p.intensity.value,
                "duration": p.duration,
                "target_emotions": [e.value for e in p.target_emotions],
                "phase_count": len(p.phases)
            }
            for p in plans
        ],
        "total": len(plans)
    }


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """获取指定方案详情"""
    manager = get_plan_manager()
    plan = manager.get_plan_by_id(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    payload = {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "style": plan.style.value,
        "intensity": plan.intensity.value,
        "duration": plan.duration,
        "target_emotions": [e.value for e in plan.target_emotions],
        "phases": [
            {
                "name": phase.name,
                "duration": phase.duration,
                "light": {
                    "color": phase.light.color,
                    "brightness": phase.light.brightness,
                    "pattern": phase.light.pattern.value if phase.light.pattern else None
                },
                "audio": {
                    "file": phase.audio.file,
                    "volume": phase.audio.volume
                },
                "has_voice_guide": phase.voice_guide is not None,
                "has_visual": phase.visual is not None,
                "has_chair": phase.chair is not None,
                "has_scent": phase.scent is not None
            }
            for phase in plan.phases
        ]
    }
    if plan.screen_prompts is not None:
        payload["screen_prompts"] = [
            {
                "start_second": prompt.start_second,
                "end_second": prompt.end_second,
                "title": prompt.title,
                "lines": list(prompt.lines),
            }
            for prompt in plan.screen_prompts
        ]

    return payload


@router.post("/match")
async def match_plan(request: MatchPlanRequest):
    """匹配疗愈方案"""
    manager = get_plan_manager()

    # 构建情绪状态
    try:
        emotion_category = EmotionCategory(request.emotion.category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid emotion category: {request.emotion.category}"
        )

    emotion = EmotionState(
        category=emotion_category,
        intensity=request.emotion.intensity,
        valence=request.emotion.valence,
        arousal=request.emotion.arousal,
        confidence=request.emotion.confidence,
        timestamp=datetime.now()
    )

    # 构建用户偏好
    preferences = None
    if request.preferred_style or request.preferred_intensity:
        preferences = UserPreferences(
            preferred_style=TherapyStyle(request.preferred_style) if request.preferred_style else None,
            preferred_intensity=TherapyIntensity(request.preferred_intensity) if request.preferred_intensity else None
        )

    # 解析风格参数
    style = None
    if request.style:
        try:
            style = TherapyStyle(request.style)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid style: {request.style}"
            )

    # 获取匹配结果
    matches = manager.match_with_details(emotion, style, preferences, top_n=3)

    return {
        "matched_plans": [
            {
                "id": m.plan.id,
                "name": m.plan.name,
                "score": round(m.score, 3),
                "match_reasons": m.match_reasons,
                "style": m.plan.style.value,
                "intensity": m.plan.intensity.value,
                "duration": m.plan.duration
            }
            for m in matches
        ],
        "best_match": {
            "id": matches[0].plan.id,
            "name": matches[0].plan.name
        } if matches else None
    }


@router.post("/select")
async def select_plan(request: SelectPlanRequest):
    """用户手动选择方案"""
    selector = get_plan_selector()
    plan = selector.select_plan(request.plan_id)

    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan not found: {request.plan_id}"
        )

    return {
        "success": True,
        "selected_plan": {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description
        },
        "message": "Plan selected successfully. User selection will override auto-matching."
    }


@router.delete("/select")
async def clear_selection():
    """清除用户选择"""
    selector = get_plan_selector()
    selector.clear_selection()

    return {
        "success": True,
        "message": "Selection cleared. Auto-matching will be used."
    }


@router.get("/selection")
async def get_selection_info():
    """获取当前选择信息"""
    selector = get_plan_selector()
    return selector.get_selection_info()


@router.post("/effective")
async def get_effective_plan(request: MatchPlanRequest):
    """
    获取有效方案（考虑用户选择优先级）

    如果用户已手动选择方案，返回用户选择的方案
    否则返回自动匹配的方案
    """
    selector = get_plan_selector()

    # 构建情绪状态
    try:
        emotion_category = EmotionCategory(request.emotion.category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid emotion category: {request.emotion.category}"
        )

    emotion = EmotionState(
        category=emotion_category,
        intensity=request.emotion.intensity,
        valence=request.emotion.valence,
        arousal=request.emotion.arousal,
        confidence=request.emotion.confidence,
        timestamp=datetime.now()
    )

    # 构建用户偏好
    preferences = None
    if request.preferred_style or request.preferred_intensity:
        preferences = UserPreferences(
            preferred_style=TherapyStyle(request.preferred_style) if request.preferred_style else None,
            preferred_intensity=TherapyIntensity(request.preferred_intensity) if request.preferred_intensity else None
        )

    # 解析风格参数
    style = None
    if request.style:
        try:
            style = TherapyStyle(request.style)
        except ValueError:
            pass

    # 获取有效方案
    plan = selector.get_effective_plan(emotion, style, preferences)
    selection_info = selector.get_selection_info()

    return {
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "style": plan.style.value,
            "intensity": plan.intensity.value,
            "duration": plan.duration
        },
        "source": "user_selection" if selector.has_user_selection else "auto_match",
        "selection_info": selection_info
    }


class ExecutePlanRequest(BaseModel):
    """执行疗愈方案请求"""
    plan_id: str = Field(..., description="疗愈方案 ID")
    emotion_category: Optional[str] = Field(default=None, description="当前情绪类别")
    emotion_intensity: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    emotion_valence: Optional[float] = Field(default=0.0, ge=-1.0, le=1.0)
    emotion_arousal: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)


@router.post("/execute")
async def execute_plan(request: ExecutePlanRequest):
    """
    执行疗愈方案

    创建会话、设置情绪状态和方案，然后启动执行器。
    """
    from services.session_manager import session_manager

    manager = get_plan_manager()
    plan = manager.get_plan_by_id(request.plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail=f"方案不存在: {request.plan_id}")

    try:
        # 创建会话
        session = await session_manager.create_session()

        # 设置初始情绪（如果提供）
        if request.emotion_category:
            try:
                emotion = EmotionState(
                    category=EmotionCategory(request.emotion_category),
                    intensity=request.emotion_intensity or 0.5,
                    valence=request.emotion_valence or 0.0,
                    arousal=request.emotion_arousal or 0.5,
                    confidence=0.8,
                    timestamp=datetime.now()
                )
                await session_manager.set_initial_emotion(emotion)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的情绪类别: {request.emotion_category}"
                )

        # 设置方案并开始疗愈
        plan.runtime_intensity_level = _get_runtime_intensity_level(plan)
        await session_manager.set_plan(plan)
        await session_manager.start_therapy()

        # 在后台启动执行器，避免首次设备/音频启动阻塞接口响应。
        executor = await _build_therapy_executor()
        set_current_executor(executor)

        async def start_executor() -> None:
            try:
                await executor.start(plan)
            except Exception as exc:
                if get_current_executor() is executor:
                    set_current_executor(None)
                logger.error(f"后台启动疗愈执行器失败: {exc}")

        create_background_task(start_executor())

        return {
            "success": True,
            "session_id": session.id,
            "plan_id": plan.id,
            "plan_name": plan.name,
            "duration": plan.duration,
            "phases": len(plan.phases),
            "message": f"疗愈方案「{plan.name}」已开始执行"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行疗愈方案失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行疗愈方案失败: {e}")


@router.post("/recommend")
async def recommend_plan(request: MatchPlanRequest):
    """推荐疗愈方案（match 的别名，供前端调用）"""
    return await match_plan(request)


@router.post("/start")
async def start_therapy(request: ExecutePlanRequest):
    """开始疗愈（execute 的别名，供前端调用）"""
    return await execute_plan(request)


@router.post("/pause/{session_id}")
async def pause_therapy(session_id: str):
    """暂停疗愈"""
    from services.session_manager import session_manager

    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="没有活跃的会话")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"会话不匹配: {session_id}")

    try:
        executor = get_current_executor()
        if executor is not None:
            await executor.pause()
        await session_manager.pause_session()
        return {"success": True, "session_id": session_id, "message": "疗愈已暂停"}
    except Exception as e:
        logger.error(f"暂停疗愈失败: {e}")
        raise HTTPException(status_code=500, detail=f"暂停疗愈失败: {e}")


@router.post("/resume/{session_id}")
async def resume_therapy(session_id: str):
    """恢复疗愈"""
    from services.session_manager import session_manager

    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="没有活跃的会话")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"会话不匹配: {session_id}")

    try:
        executor = get_current_executor()
        if executor is not None:
            await executor.resume()
        await session_manager.resume_session()
        return {"success": True, "session_id": session_id, "message": "疗愈已恢复"}
    except Exception as e:
        logger.error(f"恢复疗愈失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复疗愈失败: {e}")


@router.post("/adjust-intensity/{session_id}")
async def adjust_therapy_intensity(session_id: str, request: AdjustIntensityRequest):
    """Adjust therapy intensity while the session is running."""
    from services.session_manager import session_manager

    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="No active session")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"Session mismatch: {session_id}")

    executor = get_current_executor()
    current_plan = getattr(executor, "_current_plan", None) if executor is not None else None
    if executor is None or current_plan is None:
        raise HTTPException(status_code=400, detail="No active therapy executor")

    previous_plan_id = current_plan.id
    previous_intensity = current_plan.intensity.value
    previous_runtime_intensity_level = _get_runtime_intensity_level(current_plan)

    try:
        target_runtime_intensity_level, at_boundary = _get_adjustment_target_runtime_level(
            previous_runtime_intensity_level,
            request.direction,
        )
        target_intensity = _runtime_level_to_coarse_intensity(
            target_runtime_intensity_level
        )

        if at_boundary:
            return {
                "success": True,
                "changed": False,
                "atBoundary": True,
                "targetIntensity": target_intensity.value,
                "plan": current_plan.to_dict(),
                "message": "Already at intensity boundary",
            }

        changed = await executor.adjust_chair_intensity(target_runtime_intensity_level)
        if not changed:
            return {
                "success": True,
                "changed": False,
                "atBoundary": False,
                "targetIntensity": target_intensity.value,
                "plan": current_plan.to_dict(),
                "message": "Unable to adjust chair intensity",
            }

        await session_manager.set_plan(current_plan)
        await session_manager.record_adjustment(
            reason="runtime_intensity_adjustment",
            adjustment_type="intensity_adjustment",
            details={
                "direction": request.direction,
                "target_intensity": target_intensity.value,
                "old_plan_id": previous_plan_id,
                "new_plan_id": current_plan.id,
                "old_runtime_intensity_level": previous_runtime_intensity_level,
                "new_runtime_intensity_level": current_plan.runtime_intensity_level,
            },
            previous_state={
                "plan_id": previous_plan_id,
                "intensity": previous_intensity,
                "runtime_intensity_level": previous_runtime_intensity_level,
            },
            new_state={
                "plan_id": current_plan.id,
                "intensity": current_plan.intensity.value,
                "runtime_intensity_level": current_plan.runtime_intensity_level,
            },
        )
        return {
            "success": True,
            "changed": True,
            "atBoundary": False,
            "targetIntensity": current_plan.intensity.value,
            "plan": current_plan.to_dict(),
            "message": "Therapy intensity adjusted",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Adjust therapy intensity failed: {e}")
        raise HTTPException(status_code=500, detail=f"Adjust therapy intensity failed: {e}")


@router.post("/skip/{session_id}")
async def skip_therapy_phase(session_id: str):
    """Skip the current therapy phase."""
    from services.session_manager import session_manager

    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="No active session")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"Session mismatch: {session_id}")

    executor = get_current_executor()
    if executor is None:
        raise HTTPException(status_code=400, detail="No active therapy executor")

    try:
        await executor.skip_phase()
        return {"success": True, "session_id": session_id, "message": "Current phase skipped"}
    except Exception as e:
        logger.error(f"Skip therapy phase failed: {e}")
        raise HTTPException(status_code=500, detail=f"Skip therapy phase failed: {e}")


@router.post("/stop-now/{session_id}")
async def stop_now_therapy(session_id: str):
    """Stop device outputs immediately and finish session teardown in background."""
    from services.session_manager import session_manager

    pending_task = _get_pending_stop_task(session_id)
    if pending_task is not None:
        return {
            "success": True,
            "session_id": session_id,
            "already_stopping": True,
            "warnings": [],
        }

    if not session_manager.has_active_session:
        existing_session = None
        get_session_by_id = getattr(session_manager, "get_session_by_id", None)
        if callable(get_session_by_id):
            existing_session = await get_session_by_id(session_id)

        if existing_session is not None:
            return {
                "success": True,
                "session_id": session_id,
                "already_stopping": True,
                "warnings": [],
            }

        raise HTTPException(status_code=400, detail="No active session")

    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"Session mismatch: {session_id}")

    warnings: List[str] = []
    executor = get_current_executor()
    if executor is not None and hasattr(executor, "stop_outputs_now"):
        try:
            stop_result = await executor.stop_outputs_now()
            if isinstance(stop_result, list):
                warnings.extend(stop_result)
        except Exception as exc:
            logger.warning(f"Fast stop device output handling failed: {exc}")
            warnings.append("device_stop_failed")

    if hasattr(session_manager, "mark_stopping"):
        try:
            await session_manager.mark_stopping()
        except Exception as exc:
            logger.warning(f"Failed to mark session stopping: {exc}")
            warnings.append("session_mark_stopping_failed")

    _stopping_session_ids.add(session_id)
    _stop_finalize_tasks[session_id] = create_background_task(
        _finalize_stopped_session(session_id)
    )

    return {
        "success": True,
        "session_id": session_id,
        "already_stopping": False,
        "warnings": warnings,
    }


@router.post("/end/{session_id}")
async def end_therapy(session_id: str):
    """结束疗愈"""
    from services.session_manager import session_manager

    if not session_manager.has_active_session:
        raise HTTPException(status_code=400, detail="没有活跃的会话")
    if session_manager.current_session.id != session_id:
        raise HTTPException(status_code=404, detail=f"会话不匹配: {session_id}")

    try:
        executor = get_current_executor()
        if executor is not None:
            try:
                await executor.stop()
            finally:
                set_current_executor(None)
        session = await session_manager.end_session()
        return {
            "success": True,
            "session_id": session.id,
            "duration_seconds": session.duration_seconds,
            "message": "疗愈已结束"
        }
    except Exception as e:
        logger.error(f"结束疗愈失败: {e}")
        raise HTTPException(status_code=500, detail=f"结束疗愈失败: {e}")


@router.post("/voice/synthesize", response_model=VoiceSynthesisResponse)
async def synthesize_voice(request: VoiceSynthesisRequest):
    """
    语音合成

    使用 CosyVoice 3.0 模型将文本转换为语音
    支持情感控制和语速调节
    """
    import base64

    synthesizer = get_voice_synthesizer()

    # 验证情感类型
    try:
        emotion = VoiceEmotion(request.emotion)
    except ValueError:
        emotion = VoiceEmotion.GENTLE

    try:
        # 合成语音
        result = await synthesizer.synthesize_with_emotion(
            text=request.text,
            emotion=emotion,
            speed=request.speed,
            speaker=request.speaker
        )

        # 将音频数据编码为 Base64
        audio_base64 = base64.b64encode(result.audio_data).decode('utf-8')

        return VoiceSynthesisResponse(
            success=True,
            duration_ms=result.duration_ms,
            sample_rate=result.sample_rate,
            text=result.text,
            emotion=result.emotion,
            speaker=result.speaker,
            audio_base64=audio_base64
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice synthesis failed: {str(e)}"
        )


@router.post("/voice/synthesize/stream")
async def synthesize_voice_stream(request: VoiceSynthesisRequest):
    """
    流式语音合成

    返回音频流，适用于实时播放场景
    """
    synthesizer = get_voice_synthesizer()

    try:
        emotion = VoiceEmotion(request.emotion)
    except ValueError:
        emotion = VoiceEmotion.GENTLE

    config = VoiceSynthesisConfig(
        speaker=request.speaker or VoiceSpeaker.CHINESE_FEMALE.value,
        emotion=emotion,
        speed=request.speed,
        stream=True
    )

    async def audio_generator():
        async for chunk in synthesizer.synthesize_stream(request.text, config):
            yield chunk

    return StreamingResponse(
        audio_generator(),
        media_type="audio/raw",
        headers={
            "X-Sample-Rate": str(synthesizer.sample_rate),
            "X-Audio-Format": "float32"
        }
    )


@router.get("/voice/speakers")
async def get_available_speakers():
    """获取可用的语音角色列表"""
    synthesizer = get_voice_synthesizer()
    speakers = synthesizer.get_available_speakers()

    return {
        "speakers": speakers,
        "default": VoiceSpeaker.CHINESE_FEMALE.value,
        "emotions": [e.value for e in VoiceEmotion]
    }


@router.get("/voice/emotions")
async def get_available_emotions():
    """获取可用的情感类型列表"""
    return {
        "emotions": [
            {"value": e.value, "name": e.name}
            for e in VoiceEmotion
        ],
        "default": VoiceEmotion.GENTLE.value
    }


@router.post("/voice/synthesize/emotion-based", response_model=VoiceSynthesisResponse)
async def synthesize_voice_emotion_based(request: EmotionBasedSynthesisRequest):
    """
    基于用户情绪状态的语音合成

    根据用户当前的情绪状态（类别、强度、效价、唤醒度）
    动态调整语音的情感和语速，提供最适合当前情绪的语音输出
    """
    import base64

    therapy_synthesizer = get_therapy_voice_synthesizer()

    try:
        # 根据情绪状态合成语音
        result = await therapy_synthesizer.synthesize_for_emotion_state(
            text=request.text,
            emotion_category=request.emotion_category,
            intensity=request.intensity,
            valence=request.valence,
            arousal=request.arousal
        )

        # 将音频数据编码为 Base64
        audio_base64 = base64.b64encode(result.audio_data).decode('utf-8')

        return VoiceSynthesisResponse(
            success=True,
            duration_ms=result.duration_ms,
            sample_rate=result.sample_rate,
            text=result.text,
            emotion=result.emotion,
            speaker=result.speaker,
            audio_base64=audio_base64
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Emotion-based voice synthesis failed: {str(e)}"
        )


class GuideVoiceRequest(BaseModel):
    """引导语语音合成请求"""
    text: str = Field(..., min_length=1, max_length=5000)
    emotion: str = "gentle"
    speed: float = 0.95


@router.post("/voice/synthesize/guide")
async def synthesize_guide_voice(request: GuideVoiceRequest):
    """
    合成引导语语音

    专门用于疗愈引导语的合成，使用较慢、温柔的语速
    """
    import base64

    therapy_synthesizer = get_therapy_voice_synthesizer()

    try:
        voice_emotion = VoiceEmotion(request.emotion)
    except ValueError:
        voice_emotion = VoiceEmotion.GENTLE

    try:
        result = await therapy_synthesizer.synthesize_guide_text(
            guide_text=request.text,
            emotion=voice_emotion,
            speed=request.speed
        )

        audio_base64 = base64.b64encode(result.audio_data).decode('utf-8')

        return {
            "success": True,
            "duration_ms": result.duration_ms,
            "sample_rate": result.sample_rate,
            "text": result.text,
            "emotion": result.emotion,
            "speaker": result.speaker,
            "audio_base64": audio_base64
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Guide voice synthesis failed: {str(e)}"
        )


@router.get("/voice/emotion-mapping")
async def get_emotion_voice_mapping():
    """
    获取情绪到语音参数的映射关系

    返回不同情绪类别对应的语音情感和推荐语速
    """
    mappings = []

    for emotion_category in ["happy", "sad", "angry", "anxious", "tired",
                             "fearful", "surprised", "disgusted", "neutral"]:
        params = EmotionVoiceMapper.get_voice_params_for_emotion(
            emotion_category=emotion_category,
            intensity=0.5,
            valence=0.0,
            arousal=0.5
        )
        mappings.append({
            "emotion_category": emotion_category,
            "voice_emotion": params["emotion"].value,
            "recommended_speed": params["speed"],
            "speaker": params["speaker"]
        })

    return {
        "mappings": mappings,
        "description": "情绪类别到语音参数的映射关系"
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    AI 对话

    使用 Qwen3-8B 模型进行温暖、共情、非评判的对话
    支持危机关键词检测和 AI 身份声明
    """
    dialog_engine = get_dialog_engine()

    try:
        response = await dialog_engine.chat(
            message=request.message,
            check_crisis=request.check_crisis
        )

        return ChatResponse(
            success=True,
            content=response.content,
            is_first_response=response.is_first_response,
            contains_ai_disclosure=response.contains_ai_disclosure,
            contains_crisis_warning=response.contains_crisis_warning,
            crisis_resources=response.crisis_resources,
            generation_time_ms=response.generation_time_ms
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/chat/reset")
async def reset_chat():
    """
    重置对话会话

    清除对话历史并重置首次响应标志
    """
    dialog_engine = get_dialog_engine()
    dialog_engine.reset_session()

    return {
        "success": True,
        "message": "Chat session reset successfully"
    }


@router.get("/chat/history")
async def get_chat_history():
    """
    获取对话历史

    返回当前会话的所有对话消息
    """
    dialog_engine = get_dialog_engine()
    history = dialog_engine.get_history()

    return {
        "history": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in history
        ],
        "total": len(history)
    }


@router.get("/chat/crisis-keywords")
async def get_crisis_keywords():
    """
    获取危机关键词列表

    返回系统用于检测危机情况的关键词
    """
    return {
        "keywords_zh": CrisisKeywordDetector.CRISIS_KEYWORDS_ZH,
        "keywords_en": CrisisKeywordDetector.CRISIS_KEYWORDS_EN,
        "resources": CrisisKeywordDetector.get_crisis_resources()
    }


class CrisisCheckRequest(BaseModel):
    """危机检查请求"""
    message: str = Field(..., min_length=1)


@router.post("/chat/check-crisis")
async def check_crisis(request: CrisisCheckRequest):
    """
    检查消息是否包含危机关键词

    仅检测，不进行对话
    """
    is_crisis, matched_keywords = CrisisKeywordDetector.detect_crisis(request.message)

    return {
        "is_crisis": is_crisis,
        "matched_keywords": matched_keywords,
        "resources": CrisisKeywordDetector.get_crisis_resources() if is_crisis else None
    }
