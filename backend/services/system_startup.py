"""
系统启动与初始化模块
System Startup and Initialization Module

实现 AI 模型并行加载、设备自动检测和容错启动
Requirements: 16.1, 16.2, 16.3
"""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Coroutine
from loguru import logger


class LoadingStatus(str, Enum):
    """加载状态"""
    PENDING = "pending"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ComponentType(str, Enum):
    """组件类型"""
    AI_MODEL = "ai_model"
    DEVICE = "device"
    SERVICE = "service"
    DATABASE = "database"


@dataclass
class LoadingProgress:
    """加载进度"""
    component_name: str
    component_type: ComponentType
    status: LoadingStatus = LoadingStatus.PENDING
    progress: float = 0.0  # 0.0 - 1.0
    message: str = ""
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """加载耗时（毫秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    @property
    def is_complete(self) -> bool:
        """是否完成（成功或失败）"""
        return self.status in (LoadingStatus.LOADED, LoadingStatus.FAILED, LoadingStatus.SKIPPED)


@dataclass
class SystemStartupResult:
    """系统启动结果"""
    success: bool
    total_time_ms: float
    components: Dict[str, LoadingProgress]
    failed_components: List[str] = field(default_factory=list)
    degraded_mode: bool = False
    degraded_features: List[str] = field(default_factory=list)
    
    @property
    def loaded_count(self) -> int:
        """成功加载的组件数"""
        return sum(1 for p in self.components.values() if p.status == LoadingStatus.LOADED)
    
    @property
    def failed_count(self) -> int:
        """加载失败的组件数"""
        return sum(1 for p in self.components.values() if p.status == LoadingStatus.FAILED)


class ComponentLoader(ABC):
    """组件加载器基类"""
    
    def __init__(
        self,
        name: str,
        component_type: ComponentType,
        required: bool = True,
        timeout_seconds: float = 60.0
    ):
        self.name = name
        self.component_type = component_type
        self.required = required
        self.timeout_seconds = timeout_seconds
        self._progress = LoadingProgress(
            component_name=name,
            component_type=component_type
        )
    
    @property
    def progress(self) -> LoadingProgress:
        """获取加载进度"""
        return self._progress
    
    @abstractmethod
    async def load(self) -> bool:
        """加载组件
        
        Returns:
            是否加载成功
        """
        pass
    
    def update_progress(
        self,
        progress: float = None,
        message: str = None,
        status: LoadingStatus = None
    ) -> None:
        """更新加载进度"""
        if progress is not None:
            self._progress.progress = min(1.0, max(0.0, progress))
        if message is not None:
            self._progress.message = message
        if status is not None:
            self._progress.status = status


class AIModelLoader(ComponentLoader):
    """AI 模型加载器
    
    用于加载 SenseVoice、emotion2vec、CosyVoice、Qwen3 等 AI 模型
    """
    
    def __init__(
        self,
        name: str,
        load_func: Callable[[], Coroutine[Any, Any, bool]],
        required: bool = True,
        timeout_seconds: float = 60.0
    ):
        """初始化 AI 模型加载器
        
        Args:
            name: 模型名称
            load_func: 异步加载函数
            required: 是否必需
            timeout_seconds: 超时时间
        """
        super().__init__(name, ComponentType.AI_MODEL, required, timeout_seconds)
        self._load_func = load_func
    
    async def load(self) -> bool:
        """加载 AI 模型"""
        self._progress.start_time = datetime.now()
        self._progress.status = LoadingStatus.LOADING
        self.update_progress(0.1, f"开始加载 {self.name} 模型...")
        
        try:
            # 使用超时控制
            result = await asyncio.wait_for(
                self._load_func(),
                timeout=self.timeout_seconds
            )
            
            if result:
                self._progress.status = LoadingStatus.LOADED
                self._progress.progress = 1.0
                self._progress.message = f"{self.name} 模型加载成功"
                logger.info(f"AI model '{self.name}' loaded successfully")
            else:
                self._progress.status = LoadingStatus.FAILED
                self._progress.error = "加载函数返回失败"
                logger.error(f"AI model '{self.name}' load function returned False")
            
            return result
            
        except asyncio.TimeoutError:
            self._progress.status = LoadingStatus.FAILED
            self._progress.error = f"加载超时 ({self.timeout_seconds}s)"
            logger.error(f"AI model '{self.name}' loading timed out")
            return False
            
        except Exception as e:
            self._progress.status = LoadingStatus.FAILED
            self._progress.error = str(e)
            logger.error(f"AI model '{self.name}' loading failed: {e}")
            return False
            
        finally:
            self._progress.end_time = datetime.now()


class DeviceLoader(ComponentLoader):
    """设备加载器
    
    用于连接和初始化硬件设备（灯光、音频、座椅、香薰等）
    """
    
    def __init__(
        self,
        name: str,
        connect_func: Callable[[], Coroutine[Any, Any, bool]],
        required: bool = False,  # 设备默认非必需，支持降级
        timeout_seconds: float = 10.0
    ):
        """初始化设备加载器
        
        Args:
            name: 设备名称
            connect_func: 异步连接函数
            required: 是否必需
            timeout_seconds: 超时时间
        """
        super().__init__(name, ComponentType.DEVICE, required, timeout_seconds)
        self._connect_func = connect_func
    
    async def load(self) -> bool:
        """连接设备"""
        self._progress.start_time = datetime.now()
        self._progress.status = LoadingStatus.LOADING
        self.update_progress(0.1, f"正在连接 {self.name}...")
        
        try:
            result = await asyncio.wait_for(
                self._connect_func(),
                timeout=self.timeout_seconds
            )
            
            if result:
                self._progress.status = LoadingStatus.LOADED
                self._progress.progress = 1.0
                self._progress.message = f"{self.name} 连接成功"
                logger.info(f"Device '{self.name}' connected successfully")
            else:
                self._progress.status = LoadingStatus.FAILED
                self._progress.error = "连接失败"
                logger.warning(f"Device '{self.name}' connection failed")
            
            return result
            
        except asyncio.TimeoutError:
            self._progress.status = LoadingStatus.FAILED
            self._progress.error = f"连接超时 ({self.timeout_seconds}s)"
            logger.warning(f"Device '{self.name}' connection timed out")
            return False
            
        except Exception as e:
            self._progress.status = LoadingStatus.FAILED
            self._progress.error = str(e)
            logger.warning(f"Device '{self.name}' connection error: {e}")
            return False
            
        finally:
            self._progress.end_time = datetime.now()




class ProgressMonitor:
    """加载进度监控器
    
    监控所有组件的加载进度，提供实时状态更新
    """
    
    def __init__(self):
        self._loaders: Dict[str, ComponentLoader] = {}
        self._callbacks: List[Callable[[Dict[str, LoadingProgress]], None]] = []
        self._start_time: Optional[datetime] = None
    
    def register_loader(self, loader: ComponentLoader) -> None:
        """注册组件加载器"""
        self._loaders[loader.name] = loader
    
    def register_callback(
        self,
        callback: Callable[[Dict[str, LoadingProgress]], None]
    ) -> None:
        """注册进度回调函数"""
        self._callbacks.append(callback)
    
    def get_all_progress(self) -> Dict[str, LoadingProgress]:
        """获取所有组件的加载进度"""
        return {name: loader.progress for name, loader in self._loaders.items()}
    
    def get_overall_progress(self) -> float:
        """获取总体加载进度 (0.0 - 1.0)"""
        if not self._loaders:
            return 1.0
        
        total_progress = sum(loader.progress.progress for loader in self._loaders.values())
        return total_progress / len(self._loaders)
    
    def get_elapsed_time_ms(self) -> float:
        """获取已用时间（毫秒）"""
        if not self._start_time:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds() * 1000
    
    def _notify_callbacks(self) -> None:
        """通知所有回调函数"""
        progress = self.get_all_progress()
        for callback in self._callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    async def monitor_progress(self, interval_ms: int = 500) -> None:
        """持续监控进度并通知回调
        
        Args:
            interval_ms: 更新间隔（毫秒）
        """
        while True:
            self._notify_callbacks()
            
            # 检查是否所有组件都已完成
            all_complete = all(
                loader.progress.is_complete
                for loader in self._loaders.values()
            )
            
            if all_complete:
                break
            
            await asyncio.sleep(interval_ms / 1000)


class ModelPreloader:
    """AI 模型预加载器
    
    实现 AI 模型的并行加载，确保在 60 秒内完成
    Requirements: 16.1
    """
    
    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 60.0
    
    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT):
        """初始化模型预加载器
        
        Args:
            timeout_seconds: 总超时时间（秒）
        """
        self.timeout_seconds = timeout_seconds
        self._loaders: List[AIModelLoader] = []
        self._monitor = ProgressMonitor()
        self._loaded_models: Dict[str, Any] = {}
    
    def add_model(
        self,
        name: str,
        load_func: Callable[[], Coroutine[Any, Any, bool]],
        required: bool = True,
        timeout_seconds: float = None
    ) -> None:
        """添加要加载的模型
        
        Args:
            name: 模型名称
            load_func: 异步加载函数
            required: 是否必需
            timeout_seconds: 单个模型超时时间
        """
        loader = AIModelLoader(
            name=name,
            load_func=load_func,
            required=required,
            timeout_seconds=timeout_seconds or self.timeout_seconds
        )
        self._loaders.append(loader)
        self._monitor.register_loader(loader)
    
    def register_progress_callback(
        self,
        callback: Callable[[Dict[str, LoadingProgress]], None]
    ) -> None:
        """注册进度回调"""
        self._monitor.register_callback(callback)
    
    async def load_all(self) -> Dict[str, LoadingProgress]:
        """并行加载所有模型
        
        Returns:
            各模型的加载进度
        """
        if not self._loaders:
            logger.info("No models to load")
            return {}
        
        logger.info(f"Starting parallel model loading ({len(self._loaders)} models)...")
        self._monitor._start_time = datetime.now()
        
        # 启动进度监控任务
        monitor_task = asyncio.create_task(self._monitor.monitor_progress())
        
        try:
            # 并行加载所有模型
            load_tasks = [loader.load() for loader in self._loaders]
            
            # 使用总超时时间
            await asyncio.wait_for(
                asyncio.gather(*load_tasks, return_exceptions=True),
                timeout=self.timeout_seconds
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Model loading timed out after {self.timeout_seconds}s")
            # 标记未完成的模型为超时
            for loader in self._loaders:
                if not loader.progress.is_complete:
                    loader._progress.status = LoadingStatus.FAILED
                    loader._progress.error = "总体加载超时"
                    loader._progress.end_time = datetime.now()
        
        finally:
            # 停止监控任务
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        # 最终通知
        self._monitor._notify_callbacks()
        
        elapsed = self._monitor.get_elapsed_time_ms()
        logger.info(f"Model loading completed in {elapsed:.0f}ms")
        
        return self._monitor.get_all_progress()
    
    def get_loading_summary(self) -> Dict[str, Any]:
        """获取加载摘要"""
        progress = self._monitor.get_all_progress()
        
        loaded = [name for name, p in progress.items() if p.status == LoadingStatus.LOADED]
        failed = [name for name, p in progress.items() if p.status == LoadingStatus.FAILED]
        
        return {
            "total": len(progress),
            "loaded": len(loaded),
            "failed": len(failed),
            "loaded_models": loaded,
            "failed_models": failed,
            "elapsed_ms": self._monitor.get_elapsed_time_ms()
        }


class DeviceScanner:
    """设备扫描器
    
    自动检测和连接硬件设备
    Requirements: 16.2
    """
    
    def __init__(self):
        self._loaders: List[DeviceLoader] = []
        self._monitor = ProgressMonitor()
        self._connected_devices: Dict[str, Any] = {}
    
    def add_device(
        self,
        name: str,
        connect_func: Callable[[], Coroutine[Any, Any, bool]],
        required: bool = False,
        timeout_seconds: float = 10.0
    ) -> None:
        """添加要连接的设备
        
        Args:
            name: 设备名称
            connect_func: 异步连接函数
            required: 是否必需
            timeout_seconds: 连接超时时间
        """
        loader = DeviceLoader(
            name=name,
            connect_func=connect_func,
            required=required,
            timeout_seconds=timeout_seconds
        )
        self._loaders.append(loader)
        self._monitor.register_loader(loader)
    
    def register_progress_callback(
        self,
        callback: Callable[[Dict[str, LoadingProgress]], None]
    ) -> None:
        """注册进度回调"""
        self._monitor.register_callback(callback)
    
    async def scan_and_connect(self) -> Dict[str, LoadingProgress]:
        """扫描并连接所有设备
        
        Returns:
            各设备的连接状态
        """
        if not self._loaders:
            logger.info("No devices to connect")
            return {}
        
        logger.info(f"Starting device scan ({len(self._loaders)} devices)...")
        self._monitor._start_time = datetime.now()
        
        # 启动进度监控
        monitor_task = asyncio.create_task(self._monitor.monitor_progress())
        
        try:
            # 并行连接所有设备
            connect_tasks = [loader.load() for loader in self._loaders]
            await asyncio.gather(*connect_tasks, return_exceptions=True)
            
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        self._monitor._notify_callbacks()
        
        elapsed = self._monitor.get_elapsed_time_ms()
        logger.info(f"Device scan completed in {elapsed:.0f}ms")
        
        return self._monitor.get_all_progress()
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """获取连接摘要"""
        progress = self._monitor.get_all_progress()
        
        connected = [name for name, p in progress.items() if p.status == LoadingStatus.LOADED]
        failed = [name for name, p in progress.items() if p.status == LoadingStatus.FAILED]
        
        return {
            "total": len(progress),
            "connected": len(connected),
            "failed": len(failed),
            "connected_devices": connected,
            "failed_devices": failed,
            "elapsed_ms": self._monitor.get_elapsed_time_ms()
        }




class DegradedModeManager:
    """降级模式管理器
    
    管理系统在设备连接失败时的降级运行
    Requirements: 16.3
    """
    
    # 设备到功能的映射
    DEVICE_FEATURE_MAP = {
        "light_controller": ["ambient_lighting", "emotion_lighting", "breath_mode"],
        "audio_controller": ["background_music", "voice_guide", "surround_sound"],
        "chair_controller": ["massage", "vibration"],
        "scent_controller": ["aromatherapy"],
        "camera": ["face_analysis", "expression_recognition"],
        "microphone": ["voice_input", "speech_recognition"],
        "heart_rate_monitor": ["hrv_analysis", "stress_monitoring"],
        "display": ["visual_content", "video_playback"]
    }
    
    def __init__(self):
        self._failed_devices: List[str] = []
        self._disabled_features: List[str] = []
        self._is_degraded: bool = False
    
    def process_device_failures(
        self,
        device_progress: Dict[str, LoadingProgress]
    ) -> None:
        """处理设备连接失败
        
        Args:
            device_progress: 设备连接状态
        """
        self._failed_devices = []
        self._disabled_features = []
        
        for name, progress in device_progress.items():
            if progress.status == LoadingStatus.FAILED:
                self._failed_devices.append(name)
                
                # 查找受影响的功能
                for device_key, features in self.DEVICE_FEATURE_MAP.items():
                    if device_key in name.lower():
                        self._disabled_features.extend(features)
                        break
        
        # 去重
        self._disabled_features = list(set(self._disabled_features))
        self._is_degraded = len(self._failed_devices) > 0
        
        if self._is_degraded:
            logger.warning(
                f"System running in degraded mode. "
                f"Failed devices: {self._failed_devices}. "
                f"Disabled features: {self._disabled_features}"
            )
    
    @property
    def is_degraded(self) -> bool:
        """是否处于降级模式"""
        return self._is_degraded
    
    @property
    def failed_devices(self) -> List[str]:
        """获取失败的设备列表"""
        return self._failed_devices.copy()
    
    @property
    def disabled_features(self) -> List[str]:
        """获取禁用的功能列表"""
        return self._disabled_features.copy()
    
    def is_feature_available(self, feature: str) -> bool:
        """检查功能是否可用
        
        Args:
            feature: 功能名称
            
        Returns:
            功能是否可用
        """
        return feature not in self._disabled_features
    
    def get_status(self) -> Dict[str, Any]:
        """获取降级模式状态"""
        return {
            "is_degraded": self._is_degraded,
            "failed_devices": self._failed_devices,
            "disabled_features": self._disabled_features
        }


class SystemStartupManager:
    """系统启动管理器
    
    协调 AI 模型加载、设备连接和容错启动
    Requirements: 16.1, 16.2, 16.3
    """
    
    def __init__(
        self,
        model_timeout: float = 60.0,
        device_timeout: float = 30.0
    ):
        """初始化系统启动管理器
        
        Args:
            model_timeout: 模型加载总超时时间（秒）
            device_timeout: 设备连接总超时时间（秒）
        """
        self.model_timeout = model_timeout
        self.device_timeout = device_timeout
        
        self._model_preloader = ModelPreloader(timeout_seconds=model_timeout)
        self._device_scanner = DeviceScanner()
        self._degraded_manager = DegradedModeManager()
        
        self._startup_result: Optional[SystemStartupResult] = None
        self._progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    def add_model(
        self,
        name: str,
        load_func: Callable[[], Coroutine[Any, Any, bool]],
        required: bool = True,
        timeout_seconds: float = None
    ) -> None:
        """添加 AI 模型"""
        self._model_preloader.add_model(
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
        self._device_scanner.add_device(
            name, connect_func, required, timeout_seconds
        )
    
    def register_progress_callback(
        self,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """注册启动进度回调"""
        self._progress_callbacks.append(callback)
        
        # 转发到子组件
        def model_callback(progress):
            self._notify_progress("models", progress)
        
        def device_callback(progress):
            self._notify_progress("devices", progress)
        
        self._model_preloader.register_progress_callback(model_callback)
        self._device_scanner.register_progress_callback(device_callback)
    
    def _notify_progress(self, phase: str, progress: Dict[str, LoadingProgress]) -> None:
        """通知进度更新"""
        status = {
            "phase": phase,
            "progress": {
                name: {
                    "status": p.status.value,
                    "progress": p.progress,
                    "message": p.message,
                    "error": p.error
                }
                for name, p in progress.items()
            }
        }
        
        for callback in self._progress_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    async def startup(self) -> SystemStartupResult:
        """执行系统启动
        
        Returns:
            启动结果
        """
        start_time = time.time()
        all_components: Dict[str, LoadingProgress] = {}
        failed_components: List[str] = []
        
        logger.info("=" * 50)
        logger.info("Starting Healing Pod System...")
        logger.info("=" * 50)
        
        # 阶段 1: 加载 AI 模型
        logger.info("Phase 1: Loading AI models...")
        model_progress = await self._model_preloader.load_all()
        all_components.update(model_progress)
        
        # 检查必需模型是否加载成功
        for loader in self._model_preloader._loaders:
            if loader.required and loader.progress.status == LoadingStatus.FAILED:
                failed_components.append(loader.name)
                logger.error(f"Required model '{loader.name}' failed to load")
        
        model_summary = self._model_preloader.get_loading_summary()
        logger.info(
            f"Model loading: {model_summary['loaded']}/{model_summary['total']} loaded, "
            f"{model_summary['failed']} failed"
        )
        
        # 如果必需模型加载失败，返回失败结果
        required_model_failed = any(
            loader.required and loader.progress.status == LoadingStatus.FAILED
            for loader in self._model_preloader._loaders
        )
        
        if required_model_failed:
            total_time = (time.time() - start_time) * 1000
            logger.error("System startup failed: Required models could not be loaded")
            
            return SystemStartupResult(
                success=False,
                total_time_ms=total_time,
                components=all_components,
                failed_components=failed_components,
                degraded_mode=False,
                degraded_features=[]
            )
        
        # 阶段 2: 连接设备
        logger.info("Phase 2: Connecting devices...")
        device_progress = await self._device_scanner.scan_and_connect()
        all_components.update(device_progress)
        
        # 处理设备连接失败（降级模式）
        self._degraded_manager.process_device_failures(device_progress)
        
        for loader in self._device_scanner._loaders:
            if loader.progress.status == LoadingStatus.FAILED:
                if loader.required:
                    failed_components.append(loader.name)
                else:
                    logger.warning(f"Optional device '{loader.name}' not available")
        
        device_summary = self._device_scanner.get_connection_summary()
        logger.info(
            f"Device connection: {device_summary['connected']}/{device_summary['total']} connected, "
            f"{device_summary['failed']} failed"
        )
        
        # 检查必需设备
        required_device_failed = any(
            loader.required and loader.progress.status == LoadingStatus.FAILED
            for loader in self._device_scanner._loaders
        )
        
        total_time = (time.time() - start_time) * 1000
        
        # 构建启动结果
        self._startup_result = SystemStartupResult(
            success=not required_device_failed,
            total_time_ms=total_time,
            components=all_components,
            failed_components=failed_components,
            degraded_mode=self._degraded_manager.is_degraded,
            degraded_features=self._degraded_manager.disabled_features
        )
        
        # 记录启动结果
        if self._startup_result.success:
            if self._startup_result.degraded_mode:
                logger.warning(
                    f"System started in DEGRADED MODE in {total_time:.0f}ms. "
                    f"Disabled features: {self._startup_result.degraded_features}"
                )
            else:
                logger.info(f"System started successfully in {total_time:.0f}ms")
        else:
            logger.error(f"System startup FAILED after {total_time:.0f}ms")
        
        logger.info("=" * 50)
        
        return self._startup_result
    
    @property
    def startup_result(self) -> Optional[SystemStartupResult]:
        """获取启动结果"""
        return self._startup_result
    
    @property
    def is_degraded(self) -> bool:
        """是否处于降级模式"""
        return self._degraded_manager.is_degraded
    
    def is_feature_available(self, feature: str) -> bool:
        """检查功能是否可用"""
        return self._degraded_manager.is_feature_available(feature)
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "started": self._startup_result is not None,
            "success": self._startup_result.success if self._startup_result else False,
            "degraded_mode": self._degraded_manager.get_status(),
            "model_summary": self._model_preloader.get_loading_summary(),
            "device_summary": self._device_scanner.get_connection_summary()
        }


# 全局启动管理器实例
_startup_manager: Optional[SystemStartupManager] = None


def get_startup_manager() -> SystemStartupManager:
    """获取全局启动管理器实例"""
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = SystemStartupManager()
    return _startup_manager


def init_startup_manager(
    model_timeout: float = 60.0,
    device_timeout: float = 30.0
) -> SystemStartupManager:
    """初始化全局启动管理器
    
    Args:
        model_timeout: 模型加载超时时间
        device_timeout: 设备连接超时时间
        
    Returns:
        启动管理器实例
    """
    global _startup_manager
    _startup_manager = SystemStartupManager(
        model_timeout=model_timeout,
        device_timeout=device_timeout
    )
    return _startup_manager


async def cleanup_startup_manager() -> None:
    """清理启动管理器"""
    global _startup_manager
    _startup_manager = None
