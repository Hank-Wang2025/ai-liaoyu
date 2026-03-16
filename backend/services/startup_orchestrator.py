"""
启动编排器模块
Startup Orchestrator Module

协调系统启动流程，实现容错启动和降级模式
Requirements: 16.1, 16.2, 16.3
"""
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Coroutine
from loguru import logger

from .system_startup import (
    LoadingStatus,
    ComponentType,
    LoadingProgress,
    SystemStartupResult,
    SystemStartupManager,
    DegradedModeManager
)
from .device_manager import (
    DeviceType,
    ConnectionStatus,
    DeviceInfo,
    HardwareDeviceManager,
    init_device_manager
)
from .device_config import (
    DeviceConfiguration,
    get_device_config,
    reload_device_config,
    set_config_path,
)
from .device_initializer import (
    DeviceInitializer,
    get_device_initializer,
    init_devices_from_config,
    cleanup_devices,
)


class StartupPhase(str, Enum):
    """启动阶段"""
    INITIALIZING = "initializing"
    LOADING_MODELS = "loading_models"
    SCANNING_DEVICES = "scanning_devices"
    CONNECTING_DEVICES = "connecting_devices"
    STARTING_SERVICES = "starting_services"
    READY = "ready"
    FAILED = "failed"


@dataclass
class StartupError:
    """启动错误记录"""
    component: str
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    recoverable: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "recoverable": self.recoverable
        }


@dataclass
class StartupState:
    """启动状态"""
    phase: StartupPhase = StartupPhase.INITIALIZING
    progress: float = 0.0
    message: str = ""
    errors: List[StartupError] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def elapsed_ms(self) -> float:
        """已用时间（毫秒）"""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() * 1000
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    @property
    def has_critical_errors(self) -> bool:
        """是否有不可恢复的错误"""
        return any(not e.recoverable for e in self.errors)


class FaultTolerantStartup:
    """容错启动管理器
    
    实现设备连接失败处理、降级模式启动和错误日志记录
    Requirements: 16.3
    """
    
    def __init__(
        self,
        model_timeout: float = 60.0,
        device_timeout: float = 30.0,
        max_retries: int = 2,
        config_path: Optional[str] = None
    ):
        """初始化容错启动管理器
        
        Args:
            model_timeout: 模型加载超时时间（秒）
            device_timeout: 设备连接超时时间（秒）
            max_retries: 最大重试次数
            config_path: 设备配置文件路径（可选）
        """
        self.model_timeout = model_timeout
        self.device_timeout = device_timeout
        self.max_retries = max_retries
        
        # 加载设备配置
        if config_path:
            set_config_path(config_path)
        self._device_config = get_device_config()
        
        # 根据配置更新超时设置
        if self._device_config.global_config.connection_timeout:
            self.device_timeout = self._device_config.global_config.connection_timeout
        
        self._state = StartupState()
        self._startup_manager = SystemStartupManager(
            model_timeout=model_timeout,
            device_timeout=self.device_timeout
        )
        self._device_manager: Optional[HardwareDeviceManager] = None
        self._device_initializer: Optional[DeviceInitializer] = None
        self._degraded_manager = DegradedModeManager()
        
        self._progress_callbacks: List[Callable[[StartupState], None]] = []
        self._model_instances: Dict[str, Any] = {}
        self._service_instances: Dict[str, Any] = {}
    
    @property
    def state(self) -> StartupState:
        """获取启动状态"""
        return self._state
    
    @property
    def is_degraded(self) -> bool:
        """是否处于降级模式"""
        return self._degraded_manager.is_degraded
    
    def register_progress_callback(
        self,
        callback: Callable[[StartupState], None]
    ) -> None:
        """注册进度回调"""
        self._progress_callbacks.append(callback)
    
    def _notify_progress(self) -> None:
        """通知进度更新"""
        for callback in self._progress_callbacks:
            try:
                callback(self._state)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def _update_state(
        self,
        phase: StartupPhase = None,
        progress: float = None,
        message: str = None
    ) -> None:
        """更新启动状态"""
        if phase is not None:
            self._state.phase = phase
        if progress is not None:
            self._state.progress = progress
        if message is not None:
            self._state.message = message
        
        self._notify_progress()
    
    def _log_error(
        self,
        component: str,
        error_type: str,
        message: str,
        recoverable: bool = True
    ) -> None:
        """记录错误"""
        error = StartupError(
            component=component,
            error_type=error_type,
            message=message,
            recoverable=recoverable
        )
        self._state.errors.append(error)
        
        if recoverable:
            logger.warning(f"[{component}] {error_type}: {message}")
        else:
            logger.error(f"[{component}] CRITICAL {error_type}: {message}")
    
    def add_model(
        self,
        name: str,
        load_func: Callable[[], Coroutine[Any, Any, bool]],
        required: bool = True,
        timeout_seconds: float = None
    ) -> None:
        """添加 AI 模型"""
        self._startup_manager.add_model(
            name, load_func, required, timeout_seconds
        )
    
    def add_device(
        self,
        name: str,
        connect_func: Callable[[], Coroutine[Any, Any, bool]],
        required: bool = False,
        timeout_seconds: float = 10.0
    ) -> None:
        """添加硬件设备"""
        self._startup_manager.add_device(
            name, connect_func, required, timeout_seconds
        )
    
    async def _load_models_with_retry(self) -> Dict[str, LoadingProgress]:
        """带重试的模型加载"""
        self._update_state(
            phase=StartupPhase.LOADING_MODELS,
            progress=0.1,
            message="正在加载 AI 模型..."
        )
        
        result = await self._startup_manager._model_preloader.load_all()
        
        # 检查失败的模型并尝试重试
        for loader in self._startup_manager._model_preloader._loaders:
            if loader.progress.status == LoadingStatus.FAILED:
                if loader.required:
                    # 必需模型失败，尝试重试
                    for attempt in range(self.max_retries):
                        logger.info(
                            f"Retrying model '{loader.name}' "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        
                        # 重置状态
                        loader._progress.status = LoadingStatus.PENDING
                        loader._progress.error = None
                        
                        success = await loader.load()
                        if success:
                            break
                    
                    if loader.progress.status == LoadingStatus.FAILED:
                        self._log_error(
                            component=loader.name,
                            error_type="ModelLoadError",
                            message=loader.progress.error or "Unknown error",
                            recoverable=False
                        )
                else:
                    # 可选模型失败，记录警告
                    self._log_error(
                        component=loader.name,
                        error_type="ModelLoadWarning",
                        message=loader.progress.error or "Unknown error",
                        recoverable=True
                    )
        
        self._update_state(progress=0.4, message="AI 模型加载完成")
        return result
    
    async def _connect_devices_with_fallback(self) -> Dict[str, LoadingProgress]:
        """带降级的设备连接"""
        self._update_state(
            phase=StartupPhase.CONNECTING_DEVICES,
            progress=0.5,
            message="正在连接硬件设备..."
        )
        
        result = await self._startup_manager._device_scanner.scan_and_connect()
        
        # 处理设备连接失败
        for loader in self._startup_manager._device_scanner._loaders:
            if loader.progress.status == LoadingStatus.FAILED:
                if loader.required:
                    # 必需设备失败，尝试重试
                    for attempt in range(self.max_retries):
                        logger.info(
                            f"Retrying device '{loader.name}' "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        
                        loader._progress.status = LoadingStatus.PENDING
                        loader._progress.error = None
                        
                        success = await loader.load()
                        if success:
                            break
                    
                    if loader.progress.status == LoadingStatus.FAILED:
                        self._log_error(
                            component=loader.name,
                            error_type="DeviceConnectionError",
                            message=loader.progress.error or "Connection failed",
                            recoverable=False
                        )
                else:
                    # 可选设备失败，记录并进入降级模式
                    self._log_error(
                        component=loader.name,
                        error_type="DeviceConnectionWarning",
                        message=loader.progress.error or "Connection failed",
                        recoverable=True
                    )
        
        # 处理降级模式
        self._degraded_manager.process_device_failures(result)
        
        self._update_state(progress=0.7, message="设备连接完成")
        return result
    
    async def _start_services(self) -> bool:
        """启动后台服务"""
        self._update_state(
            phase=StartupPhase.STARTING_SERVICES,
            progress=0.8,
            message="正在启动后台服务..."
        )
        
        try:
            # 初始化设备管理器
            self._device_manager = init_device_manager()
            
            # 使用配置初始化设备
            logger.info("根据配置文件初始化设备...")
            self._device_initializer = get_device_initializer()
            init_results = await self._device_initializer.initialize_all()
            
            # 记录设备初始化结果
            for device_name, success in init_results.items():
                if not success:
                    self._log_error(
                        component=device_name,
                        error_type="DeviceInitError",
                        message=f"设备 {device_name} 初始化失败",
                        recoverable=True
                    )
            
            # 启动设备监控
            await self._device_manager.start_monitoring()
            
            self._update_state(progress=0.9, message="后台服务启动完成")
            return True
            
        except Exception as e:
            self._log_error(
                component="services",
                error_type="ServiceStartError",
                message=str(e),
                recoverable=True
            )
            return False
    
    async def startup(self) -> SystemStartupResult:
        """执行容错启动
        
        Returns:
            启动结果
        """
        self._state = StartupState(start_time=datetime.now())
        
        logger.info("=" * 60)
        logger.info("Starting Healing Pod System (Fault-Tolerant Mode)...")
        logger.info("=" * 60)
        
        self._update_state(
            phase=StartupPhase.INITIALIZING,
            progress=0.0,
            message="系统初始化中..."
        )
        
        all_components: Dict[str, LoadingProgress] = {}
        
        try:
            # 阶段 1: 加载 AI 模型
            model_progress = await self._load_models_with_retry()
            all_components.update(model_progress)
            
            # 检查是否有不可恢复的错误
            if self._state.has_critical_errors:
                self._update_state(
                    phase=StartupPhase.FAILED,
                    message="启动失败：必需组件加载失败"
                )
                self._state.end_time = datetime.now()
                
                return SystemStartupResult(
                    success=False,
                    total_time_ms=self._state.elapsed_ms,
                    components=all_components,
                    failed_components=[e.component for e in self._state.errors if not e.recoverable],
                    degraded_mode=False,
                    degraded_features=[]
                )
            
            # 阶段 2: 连接设备
            device_progress = await self._connect_devices_with_fallback()
            all_components.update(device_progress)
            
            # 阶段 3: 启动服务
            await self._start_services()
            
            # 完成启动
            self._state.end_time = datetime.now()
            
            if self._state.has_critical_errors:
                self._update_state(
                    phase=StartupPhase.FAILED,
                    progress=1.0,
                    message="启动失败"
                )
                success = False
            elif self._degraded_manager.is_degraded:
                self._update_state(
                    phase=StartupPhase.READY,
                    progress=1.0,
                    message="系统已启动（降级模式）"
                )
                success = True
            else:
                self._update_state(
                    phase=StartupPhase.READY,
                    progress=1.0,
                    message="系统已就绪"
                )
                success = True
            
            # 记录启动结果
            self._log_startup_summary()
            
            return SystemStartupResult(
                success=success,
                total_time_ms=self._state.elapsed_ms,
                components=all_components,
                failed_components=[e.component for e in self._state.errors if not e.recoverable],
                degraded_mode=self._degraded_manager.is_degraded,
                degraded_features=self._degraded_manager.disabled_features
            )
            
        except Exception as e:
            logger.exception(f"Startup failed with exception: {e}")
            
            self._log_error(
                component="system",
                error_type="StartupException",
                message=str(e),
                recoverable=False
            )
            
            self._state.end_time = datetime.now()
            self._update_state(
                phase=StartupPhase.FAILED,
                progress=1.0,
                message=f"启动异常: {e}"
            )
            
            return SystemStartupResult(
                success=False,
                total_time_ms=self._state.elapsed_ms,
                components=all_components,
                failed_components=["system"],
                degraded_mode=False,
                degraded_features=[]
            )
    
    def _log_startup_summary(self) -> None:
        """记录启动摘要"""
        logger.info("=" * 60)
        logger.info("Startup Summary")
        logger.info("=" * 60)
        logger.info(f"Total time: {self._state.elapsed_ms:.0f}ms")
        logger.info(f"Phase: {self._state.phase.value}")
        logger.info(f"Degraded mode: {self._degraded_manager.is_degraded}")
        
        if self._state.errors:
            logger.info(f"Errors: {len(self._state.errors)}")
            for error in self._state.errors:
                level = "WARNING" if error.recoverable else "ERROR"
                logger.info(f"  [{level}] {error.component}: {error.message}")
        
        if self._degraded_manager.disabled_features:
            logger.info(f"Disabled features: {self._degraded_manager.disabled_features}")
        
        logger.info("=" * 60)
    
    async def shutdown(self) -> None:
        """关闭系统"""
        logger.info("Shutting down Healing Pod System...")
        
        # 清理设备初始化器
        if self._device_initializer:
            await self._device_initializer.disconnect_all()
        
        if self._device_manager:
            await self._device_manager.stop_monitoring()
            await self._device_manager.disconnect_all()
        
        logger.info("System shutdown complete")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        device_init_results = {}
        if self._device_initializer:
            device_init_results = self._device_initializer.get_init_results()
        
        return {
            "phase": self._state.phase.value,
            "progress": self._state.progress,
            "message": self._state.message,
            "elapsed_ms": self._state.elapsed_ms,
            "errors": [e.to_dict() for e in self._state.errors],
            "degraded_mode": self._degraded_manager.get_status(),
            "is_ready": self._state.phase == StartupPhase.READY,
            "device_init_results": device_init_results,
        }
    
    def get_device_config(self) -> DeviceConfiguration:
        """获取设备配置"""
        return self._device_config
    
    def get_device_initializer(self) -> Optional[DeviceInitializer]:
        """获取设备初始化器"""
        return self._device_initializer
    
    def is_feature_available(self, feature: str) -> bool:
        """检查功能是否可用"""
        return self._degraded_manager.is_feature_available(feature)


# 全局容错启动管理器实例
_fault_tolerant_startup: Optional[FaultTolerantStartup] = None


def get_fault_tolerant_startup() -> FaultTolerantStartup:
    """获取全局容错启动管理器实例"""
    global _fault_tolerant_startup
    if _fault_tolerant_startup is None:
        _fault_tolerant_startup = FaultTolerantStartup()
    return _fault_tolerant_startup


def init_fault_tolerant_startup(
    model_timeout: float = 60.0,
    device_timeout: float = 30.0,
    max_retries: int = 2,
    config_path: Optional[str] = None
) -> FaultTolerantStartup:
    """初始化全局容错启动管理器
    
    Args:
        model_timeout: 模型加载超时时间
        device_timeout: 设备连接超时时间
        max_retries: 最大重试次数
        config_path: 设备配置文件路径（可选）
        
    Returns:
        容错启动管理器实例
    """
    global _fault_tolerant_startup
    _fault_tolerant_startup = FaultTolerantStartup(
        model_timeout=model_timeout,
        device_timeout=device_timeout,
        max_retries=max_retries,
        config_path=config_path
    )
    return _fault_tolerant_startup


async def cleanup_fault_tolerant_startup() -> None:
    """清理容错启动管理器"""
    global _fault_tolerant_startup
    if _fault_tolerant_startup:
        await _fault_tolerant_startup.shutdown()
    _fault_tolerant_startup = None
    
    # 同时清理设备
    await cleanup_devices()
