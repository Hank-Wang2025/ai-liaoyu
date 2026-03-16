"""
实时反馈调整模块
Real-time Feedback Adjustment Module

实现持续情绪监测、情绪改善检测和自动方案切换
Requirements: 10.1, 10.2, 10.3
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from loguru import logger

from models.emotion import EmotionState, EmotionCategory
from models.therapy import TherapyPlan
from services.session_manager import SessionManager
from services.therapy_executor import TherapyExecutor
from services.plan_manager import PlanManager


class EmotionTrend(str, Enum):
    """情绪趋势"""
    IMPROVING = "improving"      # 改善中
    STABLE = "stable"            # 稳定
    WORSENING = "worsening"      # 恶化中
    NO_CHANGE = "no_change"      # 无变化


@dataclass
class EmotionChangeDetection:
    """情绪变化检测结果"""
    trend: EmotionTrend
    valence_change: float  # 效价变化
    intensity_change: float  # 强度变化
    duration_seconds: int  # 检测时间窗口
    confidence: float  # 检测置信度
    
    @property
    def is_significant(self) -> bool:
        """是否为显著变化"""
        return abs(self.valence_change) > 0.1 or abs(self.intensity_change) > 0.15


@dataclass
class FeedbackConfig:
    """反馈配置"""
    # 监测间隔（秒）
    monitoring_interval: int = 10
    
    # 情绪无变化阈值（秒）- 超过此时间无变化则触发切换
    no_change_threshold: int = 180  # 3分钟
    
    # 情绪变化检测阈值
    improvement_threshold: float = 0.1  # 效价提升超过此值视为改善
    worsening_threshold: float = -0.1  # 效价下降超过此值视为恶化
    
    # 自动切换开关
    auto_switch_enabled: bool = True
    
    # 最小监测数据点数
    min_data_points: int = 3


class RealtimeFeedbackMonitor:
    """
    实时反馈监测器
    
    负责持续监测情绪状态并触发相应调整
    Requirements: 10.1, 10.2, 10.3
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        therapy_executor: TherapyExecutor,
        plan_manager: PlanManager,
        config: Optional[FeedbackConfig] = None
    ):
        """初始化监测器
        
        Args:
            session_manager: 会话管理器
            therapy_executor: 疗愈执行器
            plan_manager: 方案管理器
            config: 反馈配置
        """
        self._session_manager = session_manager
        self._therapy_executor = therapy_executor
        self._plan_manager = plan_manager
        self._config = config or FeedbackConfig()
        
        self._is_monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._emotion_buffer: List[EmotionState] = []
        self._last_change_time: Optional[datetime] = None
        self._last_emotion: Optional[EmotionState] = None
        
        self._adjustment_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
    
    @property
    def is_monitoring(self) -> bool:
        """是否正在监测"""
        return self._is_monitoring
    
    def add_adjustment_callback(
        self, 
        callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """添加调整回调
        
        Args:
            callback: 回调函数，接收 (adjustment_type, details) 参数
        """
        self._adjustment_callbacks.append(callback)
    
    def remove_adjustment_callback(
        self, 
        callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """移除调整回调"""
        if callback in self._adjustment_callbacks:
            self._adjustment_callbacks.remove(callback)
    
    def _notify_adjustment(self, adjustment_type: str, details: Dict[str, Any]) -> None:
        """通知调整"""
        for callback in self._adjustment_callbacks:
            try:
                callback(adjustment_type, details)
            except Exception as e:
                logger.error(f"Error in adjustment callback: {e}")
    
    async def start_monitoring(
        self, 
        emotion_source: Callable[[], Optional[EmotionState]]
    ) -> None:
        """开始监测
        
        Args:
            emotion_source: 情绪数据源函数，返回当前情绪状态
        """
        if self._is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self._is_monitoring = True
        self._emotion_buffer.clear()
        self._last_change_time = datetime.now()
        
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(emotion_source)
        )
        
        logger.info("Real-time feedback monitoring started")
    
    async def stop_monitoring(self) -> None:
        """停止监测"""
        self._is_monitoring = False
        
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self._monitoring_task = None
        logger.info("Real-time feedback monitoring stopped")
    
    async def _monitoring_loop(
        self, 
        emotion_source: Callable[[], Optional[EmotionState]]
    ) -> None:
        """监测循环
        
        Requirements: 10.1 - 持续监测用户的情绪和生理状态
        """
        while self._is_monitoring:
            try:
                # 获取当前情绪状态
                current_emotion = emotion_source()
                
                if current_emotion:
                    # 添加到缓冲区
                    self._emotion_buffer.append(current_emotion)
                    
                    # 保持缓冲区大小合理
                    max_buffer_size = 60  # 保留最近60个数据点
                    if len(self._emotion_buffer) > max_buffer_size:
                        self._emotion_buffer = self._emotion_buffer[-max_buffer_size:]
                    
                    # 记录到会话
                    if self._session_manager.has_active_session:
                        phase_name = None
                        if self._therapy_executor.current_phase:
                            phase_name = self._therapy_executor.current_phase.name
                        await self._session_manager.record_emotion(
                            current_emotion, 
                            phase_name
                        )
                    
                    # 检测情绪变化
                    if len(self._emotion_buffer) >= self._config.min_data_points:
                        await self._check_emotion_change(current_emotion)
                    
                    self._last_emotion = current_emotion
                
                # 等待下一个监测周期
                await asyncio.sleep(self._config.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self._config.monitoring_interval)
    
    async def _check_emotion_change(self, current_emotion: EmotionState) -> None:
        """检查情绪变化并触发相应动作
        
        Requirements: 10.2, 10.3
        """
        # 检测情绪趋势
        detection = self._detect_emotion_trend()
        
        if detection.trend == EmotionTrend.IMPROVING:
            # 情绪改善
            await self._handle_improvement(detection, current_emotion)
            self._last_change_time = datetime.now()
            
        elif detection.trend == EmotionTrend.WORSENING:
            # 情绪恶化
            await self._handle_worsening(detection, current_emotion)
            self._last_change_time = datetime.now()
            
        elif detection.trend == EmotionTrend.NO_CHANGE:
            # 检查是否超过无变化阈值
            if self._last_change_time:
                no_change_duration = (datetime.now() - self._last_change_time).total_seconds()
                if no_change_duration >= self._config.no_change_threshold:
                    # 超过3分钟无变化，触发自动切换
                    await self._handle_no_change(detection, current_emotion, no_change_duration)
                    self._last_change_time = datetime.now()
    
    def _detect_emotion_trend(self) -> EmotionChangeDetection:
        """检测情绪趋势
        
        分析情绪缓冲区中的数据，判断情绪变化趋势
        """
        if len(self._emotion_buffer) < self._config.min_data_points:
            return EmotionChangeDetection(
                trend=EmotionTrend.STABLE,
                valence_change=0.0,
                intensity_change=0.0,
                duration_seconds=0,
                confidence=0.0
            )
        
        # 取最近的数据点进行分析
        recent_emotions = self._emotion_buffer[-self._config.min_data_points:]
        
        # 计算效价变化
        first_valence = recent_emotions[0].valence
        last_valence = recent_emotions[-1].valence
        valence_change = last_valence - first_valence
        
        # 计算强度变化（对于负面情绪，强度降低是改善）
        first_intensity = recent_emotions[0].intensity
        last_intensity = recent_emotions[-1].intensity
        intensity_change = last_intensity - first_intensity
        
        # 考虑情绪类别的效价
        first_is_negative = first_valence < 0
        
        # 判断趋势
        if valence_change > self._config.improvement_threshold:
            trend = EmotionTrend.IMPROVING
        elif valence_change < self._config.worsening_threshold:
            trend = EmotionTrend.WORSENING
        elif abs(valence_change) < 0.05 and abs(intensity_change) < 0.1:
            trend = EmotionTrend.NO_CHANGE
        else:
            trend = EmotionTrend.STABLE
        
        # 计算置信度
        confidence = min(1.0, len(self._emotion_buffer) / 10)
        
        duration = int(
            (recent_emotions[-1].timestamp - recent_emotions[0].timestamp).total_seconds()
        )
        
        return EmotionChangeDetection(
            trend=trend,
            valence_change=valence_change,
            intensity_change=intensity_change,
            duration_seconds=duration,
            confidence=confidence
        )
    
    async def _handle_improvement(
        self, 
        detection: EmotionChangeDetection,
        current_emotion: EmotionState
    ) -> None:
        """处理情绪改善
        
        Requirements: 10.2 - 检测到用户情绪明显改善时的处理
        """
        logger.info(
            f"Emotion improvement detected: valence change={detection.valence_change:.2f}"
        )
        
        # 记录调整
        if self._session_manager.has_active_session:
            await self._session_manager.record_adjustment(
                reason="情绪改善检测",
                adjustment_type="emotion_improvement",
                details={
                    "valence_change": detection.valence_change,
                    "intensity_change": detection.intensity_change,
                    "current_emotion": current_emotion.category.value
                }
            )
        
        # 通知回调
        self._notify_adjustment("emotion_improvement", {
            "detection": {
                "trend": detection.trend.value,
                "valence_change": detection.valence_change,
                "intensity_change": detection.intensity_change
            },
            "current_emotion": {
                "category": current_emotion.category.value,
                "intensity": current_emotion.intensity,
                "valence": current_emotion.valence
            }
        })
    
    async def _handle_worsening(
        self, 
        detection: EmotionChangeDetection,
        current_emotion: EmotionState
    ) -> None:
        """处理情绪恶化"""
        logger.warning(
            f"Emotion worsening detected: valence change={detection.valence_change:.2f}"
        )
        
        # 记录调整
        if self._session_manager.has_active_session:
            await self._session_manager.record_adjustment(
                reason="情绪恶化检测",
                adjustment_type="emotion_worsening",
                details={
                    "valence_change": detection.valence_change,
                    "intensity_change": detection.intensity_change,
                    "current_emotion": current_emotion.category.value
                }
            )
        
        # 如果启用自动切换，尝试切换到更合适的方案
        if self._config.auto_switch_enabled:
            await self._try_switch_plan(current_emotion, "emotion_worsening")
        
        # 通知回调
        self._notify_adjustment("emotion_worsening", {
            "detection": {
                "trend": detection.trend.value,
                "valence_change": detection.valence_change,
                "intensity_change": detection.intensity_change
            },
            "current_emotion": {
                "category": current_emotion.category.value,
                "intensity": current_emotion.intensity,
                "valence": current_emotion.valence
            }
        })
    
    async def _handle_no_change(
        self, 
        detection: EmotionChangeDetection,
        current_emotion: EmotionState,
        no_change_duration: float
    ) -> None:
        """处理情绪无变化
        
        Requirements: 10.3 - 情绪恶化或无变化超过3分钟时自动切换到备选方案
        """
        logger.info(
            f"No emotion change for {no_change_duration:.0f}s, triggering auto-switch"
        )
        
        # 记录调整
        if self._session_manager.has_active_session:
            await self._session_manager.record_adjustment(
                reason=f"情绪无变化超过{int(no_change_duration)}秒",
                adjustment_type="no_change_timeout",
                details={
                    "no_change_duration": no_change_duration,
                    "current_emotion": current_emotion.category.value,
                    "threshold": self._config.no_change_threshold
                }
            )
        
        # 自动切换方案
        if self._config.auto_switch_enabled:
            await self._try_switch_plan(current_emotion, "no_change_timeout")
        
        # 通知回调
        self._notify_adjustment("no_change_timeout", {
            "no_change_duration": no_change_duration,
            "threshold": self._config.no_change_threshold,
            "current_emotion": {
                "category": current_emotion.category.value,
                "intensity": current_emotion.intensity,
                "valence": current_emotion.valence
            }
        })
    
    async def _try_switch_plan(
        self, 
        current_emotion: EmotionState,
        reason: str
    ) -> bool:
        """尝试切换到备选方案
        
        Args:
            current_emotion: 当前情绪状态
            reason: 切换原因
            
        Returns:
            是否成功切换
        """
        if not self._therapy_executor.is_running:
            return False
        
        try:
            # 获取当前方案
            current_plan_id = self._therapy_executor._current_plan.id if self._therapy_executor._current_plan else None
            
            # 匹配新方案
            match_results = self._plan_manager.match_with_details(
                current_emotion,
                top_n=3
            )
            
            # 选择一个不同于当前方案的备选方案
            new_plan = None
            for result in match_results:
                if result.plan.id != current_plan_id:
                    new_plan = result.plan
                    break
            
            if new_plan:
                # 记录切换
                if self._session_manager.has_active_session:
                    await self._session_manager.record_adjustment(
                        reason=f"自动切换方案: {reason}",
                        adjustment_type="plan_switch",
                        details={
                            "old_plan_id": current_plan_id,
                            "new_plan_id": new_plan.id,
                            "new_plan_name": new_plan.name,
                            "trigger": reason
                        },
                        previous_state={"plan_id": current_plan_id},
                        new_state={"plan_id": new_plan.id}
                    )
                
                # 执行切换
                await self._therapy_executor.switch_plan(new_plan)
                
                logger.info(f"Switched to plan: {new_plan.name}")
                return True
            else:
                logger.warning("No alternative plan available for switching")
                return False
                
        except Exception as e:
            logger.error(f"Failed to switch plan: {e}")
            return False
    
    def get_current_trend(self) -> Optional[EmotionChangeDetection]:
        """获取当前情绪趋势"""
        if len(self._emotion_buffer) < self._config.min_data_points:
            return None
        return self._detect_emotion_trend()
    
    def get_emotion_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """获取情绪历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            情绪历史列表
        """
        recent = self._emotion_buffer[-limit:] if limit else self._emotion_buffer
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "category": e.category.value,
                "intensity": e.intensity,
                "valence": e.valence,
                "arousal": e.arousal
            }
            for e in recent
        ]
    
    def update_config(self, **kwargs) -> None:
        """更新配置
        
        Args:
            **kwargs: 配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.info(f"Feedback config updated: {key}={value}")
