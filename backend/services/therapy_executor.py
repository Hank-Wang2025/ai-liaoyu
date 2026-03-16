"""
疗愈方案执行器
Therapy Plan Executor

实现方案阶段调度、设备联动控制和时序同步
Requirements: 6.1
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, AsyncGenerator
from loguru import logger

from models.therapy import (
    TherapyPlan,
    TherapyPhase,
    LightConfig,
    AudioConfig,
    ChairConfig,
    ScentConfig,
    VoiceGuideConfig
)
from models.session import Session
from services.light_controller import (
    LightControllerManager,
    RGBColor,
    LightPattern
)
from services.audio_controller import (
    TherapyAudioPlayer,
    AudioConfig as AudioControllerConfig
)
from services.chair_controller import (
    ChairControllerManager,
    MassageMode,
    ChairConfig as ChairControllerConfig
)
from services.scent_controller import (
    ScentControllerManager,
    ScentType,
    ScentConfig as ScentControllerConfig
)


class ExecutorState(str, Enum):
    """执行器状态"""
    IDLE = "idle"              # 空闲
    PREPARING = "preparing"    # 准备中
    RUNNING = "running"        # 运行中
    PAUSED = "paused"          # 已暂停
    TRANSITIONING = "transitioning"  # 阶段过渡中
    COMPLETED = "completed"    # 已完成
    ERROR = "error"            # 错误


@dataclass
class PhaseProgress:
    """阶段进度"""
    phase_index: int
    phase_name: str
    elapsed_seconds: int
    total_seconds: int
    progress_percent: float
    
    @property
    def remaining_seconds(self) -> int:
        """剩余秒数"""
        return max(0, self.total_seconds - self.elapsed_seconds)


@dataclass
class ExecutorStatus:
    """执行器状态"""
    state: ExecutorState
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    current_phase: Optional[PhaseProgress] = None
    total_phases: int = 0
    elapsed_seconds: int = 0
    total_seconds: int = 0
    error_message: Optional[str] = None
    
    @property
    def overall_progress(self) -> float:
        """总体进度 (0-1)"""
        if self.total_seconds == 0:
            return 0.0
        return min(1.0, self.elapsed_seconds / self.total_seconds)


@dataclass
class TherapyEvent:
    """疗愈事件"""
    event_type: str  # phase_start, phase_end, device_update, voice_guide, etc.
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)


class TherapyExecutor:
    """
    疗愈方案执行器
    
    负责执行疗愈方案，协调各设备的联动控制
    Requirements: 6.1
    """
    
    # 阶段过渡时间（毫秒）
    PHASE_TRANSITION_MS = 3000
    
    # 设备控制超时（秒）
    DEVICE_TIMEOUT = 5.0
    
    def __init__(
        self,
        light_manager: Optional[LightControllerManager] = None,
        audio_player: Optional[TherapyAudioPlayer] = None,
        chair_manager: Optional[ChairControllerManager] = None,
        scent_manager: Optional[ScentControllerManager] = None
    ):
        """初始化执行器
        
        Args:
            light_manager: 灯光控制器管理器
            audio_player: 音频播放器
            chair_manager: 座椅控制器管理器
            scent_manager: 香薰控制器管理器
        """
        self._light_manager = light_manager
        self._audio_player = audio_player
        self._chair_manager = chair_manager
        self._scent_manager = scent_manager
        
        self._state = ExecutorState.IDLE
        self._current_plan: Optional[TherapyPlan] = None
        self._current_phase_index: int = 0
        self._phase_start_time: Optional[datetime] = None
        self._plan_start_time: Optional[datetime] = None
        
        self._execution_task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        
        self._event_listeners: List[Callable[[TherapyEvent], None]] = []
        
        # 初始化时设置暂停事件为已设置状态（未暂停）
        self._pause_event.set()
        
        # 跳过阶段标志
        self._skip_current_phase = False
    
    @property
    def state(self) -> ExecutorState:
        """获取执行器状态"""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._state in (ExecutorState.RUNNING, ExecutorState.TRANSITIONING)
    
    @property
    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._state == ExecutorState.PAUSED
    
    @property
    def current_phase(self) -> Optional[TherapyPhase]:
        """获取当前阶段"""
        if self._current_plan and 0 <= self._current_phase_index < len(self._current_plan.phases):
            return self._current_plan.phases[self._current_phase_index]
        return None
    
    def add_event_listener(self, listener: Callable[[TherapyEvent], None]) -> None:
        """添加事件监听器"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[TherapyEvent], None]) -> None:
        """移除事件监听器"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """发送事件"""
        event = TherapyEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data or {}
        )
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
    
    def get_status(self) -> ExecutorStatus:
        """获取执行器状态"""
        current_phase_progress = None
        
        if self._current_plan and self._phase_start_time:
            phase = self.current_phase
            if phase:
                elapsed = int((datetime.now() - self._phase_start_time).total_seconds())
                current_phase_progress = PhaseProgress(
                    phase_index=self._current_phase_index,
                    phase_name=phase.name,
                    elapsed_seconds=elapsed,
                    total_seconds=phase.duration,
                    progress_percent=min(1.0, elapsed / phase.duration) * 100
                )
        
        total_elapsed = 0
        if self._plan_start_time:
            total_elapsed = int((datetime.now() - self._plan_start_time).total_seconds())
        
        return ExecutorStatus(
            state=self._state,
            plan_id=self._current_plan.id if self._current_plan else None,
            plan_name=self._current_plan.name if self._current_plan else None,
            current_phase=current_phase_progress,
            total_phases=len(self._current_plan.phases) if self._current_plan else 0,
            elapsed_seconds=total_elapsed,
            total_seconds=self._current_plan.duration if self._current_plan else 0
        )
    
    async def execute(self, plan: TherapyPlan) -> AsyncGenerator[TherapyEvent, None]:
        """执行疗愈方案
        
        Args:
            plan: 疗愈方案
            
        Yields:
            TherapyEvent: 疗愈事件
        """
        if self._state not in (ExecutorState.IDLE, ExecutorState.COMPLETED, ExecutorState.ERROR):
            raise RuntimeError(f"Cannot start execution in state: {self._state}")
        
        self._current_plan = plan
        self._current_phase_index = 0
        self._plan_start_time = datetime.now()
        self._state = ExecutorState.PREPARING
        self._stop_event.clear()
        self._pause_event.set()
        
        logger.info(f"Starting therapy execution: {plan.name}")
        
        yield TherapyEvent(
            event_type="execution_start",
            timestamp=datetime.now(),
            data={"plan_id": plan.id, "plan_name": plan.name}
        )
        
        try:
            # 执行每个阶段
            for phase_index, phase in enumerate(plan.phases):
                if self._stop_event.is_set():
                    break
                
                self._current_phase_index = phase_index
                self._phase_start_time = datetime.now()
                self._state = ExecutorState.RUNNING
                
                # 发送阶段开始事件
                yield TherapyEvent(
                    event_type="phase_start",
                    timestamp=datetime.now(),
                    data={
                        "phase_index": phase_index,
                        "phase_name": phase.name,
                        "duration": phase.duration
                    }
                )
                
                # 应用阶段配置到设备
                await self._apply_phase_config(phase)
                
                # 等待阶段完成
                async for event in self._wait_phase_duration(phase):
                    yield event
                
                if self._stop_event.is_set():
                    break
                
                # 发送阶段结束事件
                yield TherapyEvent(
                    event_type="phase_end",
                    timestamp=datetime.now(),
                    data={
                        "phase_index": phase_index,
                        "phase_name": phase.name
                    }
                )
                
                # 阶段过渡
                if phase_index < len(plan.phases) - 1:
                    self._state = ExecutorState.TRANSITIONING
                    await asyncio.sleep(self.PHASE_TRANSITION_MS / 1000)
            
            # 执行完成
            self._state = ExecutorState.COMPLETED
            await self._stop_all_devices()
            
            yield TherapyEvent(
                event_type="execution_complete",
                timestamp=datetime.now(),
                data={
                    "plan_id": plan.id,
                    "total_duration": int((datetime.now() - self._plan_start_time).total_seconds())
                }
            )
            
            logger.info(f"Therapy execution completed: {plan.name}")
            
        except asyncio.CancelledError:
            self._state = ExecutorState.IDLE
            await self._stop_all_devices()
            yield TherapyEvent(
                event_type="execution_cancelled",
                timestamp=datetime.now(),
                data={"plan_id": plan.id}
            )
            logger.info(f"Therapy execution cancelled: {plan.name}")
            
        except Exception as e:
            self._state = ExecutorState.ERROR
            await self._stop_all_devices()
            yield TherapyEvent(
                event_type="execution_error",
                timestamp=datetime.now(),
                data={"plan_id": plan.id, "error": str(e)}
            )
            logger.error(f"Therapy execution error: {e}")
            raise
    
    async def start(self, plan: TherapyPlan) -> None:
        """启动疗愈方案执行（非生成器模式）
        
        Args:
            plan: 疗愈方案
        """
        if self._execution_task and not self._execution_task.done():
            raise RuntimeError("Execution already in progress")
        
        async def run_execution():
            async for event in self.execute(plan):
                self._emit_event(event.event_type, event.data)
        
        self._execution_task = asyncio.create_task(run_execution())
    
    async def stop(self) -> None:
        """停止执行"""
        self._stop_event.set()
        self._pause_event.set()  # 确保不会卡在暂停状态
        
        if self._execution_task and not self._execution_task.done():
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass
        
        await self._stop_all_devices()
        self._state = ExecutorState.IDLE
        logger.info("Therapy execution stopped")
    
    async def pause(self) -> None:
        """暂停执行"""
        if self._state == ExecutorState.RUNNING:
            self._pause_event.clear()
            self._state = ExecutorState.PAUSED
            
            # 暂停设备
            if self._audio_player:
                # 降低音量而不是完全停止
                pass
            
            logger.info("Therapy execution paused")
            self._emit_event("execution_paused", {})
    
    async def resume(self) -> None:
        """恢复执行"""
        if self._state == ExecutorState.PAUSED:
            self._pause_event.set()
            self._state = ExecutorState.RUNNING
            logger.info("Therapy execution resumed")
            self._emit_event("execution_resumed", {})
    
    async def skip_phase(self) -> None:
        """跳过当前阶段"""
        if self._state in (ExecutorState.RUNNING, ExecutorState.PAUSED):
            # 设置一个标志让等待循环提前结束
            self._skip_current_phase = True
            if self._state == ExecutorState.PAUSED:
                self._pause_event.set()
            logger.info(f"Skipping phase {self._current_phase_index}")
    
    async def _apply_phase_config(self, phase: TherapyPhase) -> None:
        """应用阶段配置到设备
        
        实现设备联动控制
        """
        tasks = []
        
        # 灯光控制
        if phase.light and self._light_manager:
            tasks.append(self._apply_light_config(phase.light))
        
        # 音频控制
        if phase.audio and self._audio_player:
            tasks.append(self._apply_audio_config(phase.audio))
        
        # 语音引导
        if phase.voice_guide and self._audio_player:
            tasks.append(self._apply_voice_guide(phase.voice_guide))
        
        # 座椅控制
        if phase.chair and self._chair_manager:
            tasks.append(self._apply_chair_config(phase.chair))
        
        # 香薰控制
        if phase.scent and self._scent_manager:
            tasks.append(self._apply_scent_config(phase.scent))
        
        # 并行执行所有设备控制
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.DEVICE_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning("Device control timeout, continuing execution")
    
    async def _apply_light_config(self, config: LightConfig) -> None:
        """应用灯光配置"""
        try:
            if config.pattern == "breath":
                await self._light_manager.start_breath_mode_all(
                    config.color,
                    min_brightness=30,
                    max_brightness=config.brightness
                )
            else:
                await self._light_manager.set_all_lights(
                    config.color,
                    config.brightness,
                    config.transition
                )
            logger.debug(f"Light config applied: {config.color}, brightness={config.brightness}")
        except Exception as e:
            logger.error(f"Failed to apply light config: {e}")
    
    async def _apply_audio_config(self, config: AudioConfig) -> None:
        """应用音频配置"""
        try:
            await self._audio_player.play_background_music(
                config.file,
                volume=config.volume / 100.0,
                loop=config.loop,
                fade_in_ms=config.fade_in
            )
            logger.debug(f"Audio config applied: {config.file}")
        except Exception as e:
            logger.error(f"Failed to apply audio config: {e}")
    
    async def _apply_voice_guide(self, config: VoiceGuideConfig) -> None:
        """应用语音引导配置"""
        # 语音引导需要先合成再播放
        # 这里假设已经有预生成的语音文件
        logger.debug(f"Voice guide: {config.text[:50]}...")
    
    async def _apply_chair_config(self, config: ChairConfig) -> None:
        """应用座椅配置"""
        try:
            chair_config = ChairControllerConfig(
                mode=config.mode,
                intensity=config.intensity
            )
            await self._chair_manager.apply_therapy_config(chair_config)
            logger.debug(f"Chair config applied: mode={config.mode}, intensity={config.intensity}")
        except Exception as e:
            logger.error(f"Failed to apply chair config: {e}")
    
    async def _apply_scent_config(self, config: ScentConfig) -> None:
        """应用香薰配置"""
        try:
            scent_config = ScentControllerConfig(
                scent_type=config.scent_type,
                intensity=config.intensity
            )
            await self._scent_manager.apply_therapy_config(scent_config)
            logger.debug(f"Scent config applied: type={config.scent_type}, intensity={config.intensity}")
        except Exception as e:
            logger.error(f"Failed to apply scent config: {e}")
    
    async def _wait_phase_duration(self, phase: TherapyPhase) -> AsyncGenerator[TherapyEvent, None]:
        """等待阶段持续时间
        
        实现时序同步
        """
        self._skip_current_phase = False
        elapsed = 0
        check_interval = 1  # 每秒检查一次
        
        while elapsed < phase.duration:
            if self._stop_event.is_set() or self._skip_current_phase:
                break
            
            # 等待暂停事件
            await self._pause_event.wait()
            
            # 等待一个检查间隔
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=check_interval
                )
                break  # 收到停止信号
            except asyncio.TimeoutError:
                pass  # 正常超时，继续
            
            elapsed += check_interval
            
            # 每10秒发送一次进度事件
            if elapsed % 10 == 0:
                yield TherapyEvent(
                    event_type="phase_progress",
                    timestamp=datetime.now(),
                    data={
                        "phase_index": self._current_phase_index,
                        "phase_name": phase.name,
                        "elapsed": elapsed,
                        "total": phase.duration,
                        "progress": elapsed / phase.duration
                    }
                )
    
    async def _stop_all_devices(self) -> None:
        """停止所有设备"""
        tasks = []
        
        if self._light_manager:
            tasks.append(self._light_manager.stop_breath_mode_all())
        
        if self._audio_player:
            tasks.append(self._audio_player.stop_all(fade_out_ms=2000))
        
        if self._chair_manager and self._chair_manager.controller:
            tasks.append(self._chair_manager.controller.stop())
        
        if self._scent_manager and self._scent_manager.controller:
            tasks.append(self._scent_manager.controller.stop())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.debug("All devices stopped")
    
    async def switch_plan(self, new_plan: TherapyPlan) -> None:
        """切换到新方案
        
        用于实时反馈调整时切换方案
        
        Args:
            new_plan: 新的疗愈方案
        """
        if not self.is_running and not self.is_paused:
            raise RuntimeError("No active execution to switch")
        
        # 先保存旧方案信息，再停止执行
        old_plan_id = self._current_plan.id if self._current_plan else None
        old_plan_name = self._current_plan.name if self._current_plan else None
        
        logger.info(f"Switching plan from {old_plan_name} to {new_plan.name}")
        
        # 停止当前执行
        await self.stop()
        
        # 启动新方案
        await self.start(new_plan)
        
        self._emit_event("plan_switched", {
            "old_plan": old_plan_id,
            "new_plan": new_plan.id
        })
