"""
香薰控制器模块
Scent Controller Module

实现 WiFi 智能香薰设备的连接和控制
Requirements: (可选功能)
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from loguru import logger

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp library not available. WiFi scent functionality will be limited.")


class ScentType(str, Enum):
    """香型类型"""
    LAVENDER = "lavender"          # 薰衣草 - 放松助眠
    EUCALYPTUS = "eucalyptus"      # 桉树 - 清新提神
    PEPPERMINT = "peppermint"      # 薄荷 - 清凉醒脑
    CHAMOMILE = "chamomile"        # 洋甘菊 - 舒缓镇静
    BERGAMOT = "bergamot"          # 佛手柑 - 减压愉悦
    SANDALWOOD = "sandalwood"      # 檀香 - 冥想静心
    JASMINE = "jasmine"            # 茉莉 - 温暖舒适
    ROSE = "rose"                  # 玫瑰 - 浪漫放松
    LEMON = "lemon"                # 柠檬 - 清新活力
    CEDAR = "cedar"                # 雪松 - 安定沉稳
    OFF = "off"                    # 关闭


@dataclass
class ScentConfig:
    """香薰配置"""
    scent_type: str  # 香型
    intensity: int  # 强度 1-10
    duration: Optional[int] = None  # 持续时间（秒），None表示持续运行


@dataclass
class ScentState:
    """香薰状态"""
    scent_type: ScentType = ScentType.OFF
    intensity: int = 0  # 0-10
    is_running: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """验证强度范围"""
        if not 0 <= self.intensity <= 10:
            raise ValueError(f"intensity must be between 0 and 10, got {self.intensity}")


# 情绪到香型的映射
EMOTION_SCENT_MAP: Dict[str, Dict[str, Any]] = {
    "anxious": {
        "scent": ScentType.LAVENDER,
        "intensity": 5,
        "description": "薰衣草有助于缓解焦虑"
    },
    "happy": {
        "scent": ScentType.BERGAMOT,
        "intensity": 6,
        "description": "佛手柑增强愉悦感"
    },
    "sad": {
        "scent": ScentType.JASMINE,
        "intensity": 5,
        "description": "茉莉提供温暖舒适"
    },
    "angry": {
        "scent": ScentType.CHAMOMILE,
        "intensity": 6,
        "description": "洋甘菊帮助平静"
    },
    "tired": {
        "scent": ScentType.PEPPERMINT,
        "intensity": 4,
        "description": "薄荷清凉醒脑"
    },
    "fearful": {
        "scent": ScentType.SANDALWOOD,
        "intensity": 5,
        "description": "檀香提供安全感"
    },
    "neutral": {
        "scent": ScentType.EUCALYPTUS,
        "intensity": 4,
        "description": "桉树清新自然"
    }
}


class BaseScentController(ABC):
    """香薰控制器基类
    
    定义香薰控制的抽象接口，所有具体的香薰适配器都需要继承此类。
    """
    
    def __init__(self, name: str = "scent"):
        self.name = name
        self._current_state: ScentState = ScentState()
        self._is_connected: bool = False
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected
    
    @property
    def current_state(self) -> ScentState:
        """当前香薰状态"""
        return self._current_state
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接设备
        
        Returns:
            是否连接成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def set_scent(self, scent_type: ScentType, intensity: int = 5) -> bool:
        """设置香型和强度
        
        Args:
            scent_type: 香型
            intensity: 强度 1-10
            
        Returns:
            是否设置成功
        """
        pass
    
    @abstractmethod
    async def set_intensity(self, intensity: int) -> bool:
        """设置强度
        
        Args:
            intensity: 强度 1-10
            
        Returns:
            是否设置成功
        """
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """开始散香"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止散香"""
        pass
    
    def _update_state(
        self,
        scent_type: ScentType,
        intensity: int,
        is_running: bool
    ) -> None:
        """更新内部状态"""
        self._current_state = ScentState(
            scent_type=scent_type,
            intensity=intensity,
            is_running=is_running
        )


class MockScentController(BaseScentController):
    """模拟香薰控制器（用于测试和开发）"""
    
    def __init__(self, name: str = "mock_scent"):
        super().__init__(name)
        self._command_history: List[Dict[str, Any]] = []
    
    @property
    def command_history(self) -> List[Dict[str, Any]]:
        """获取命令历史"""
        return self._command_history
    
    async def connect(self) -> bool:
        """模拟连接"""
        await asyncio.sleep(0.1)  # 模拟连接延迟
        self._is_connected = True
        self._command_history.append({
            "action": "connect",
            "timestamp": datetime.now()
        })
        logger.info(f"Mock scent controller '{self.name}' connected")
        return True
    
    async def disconnect(self) -> None:
        """模拟断开连接"""
        await self.stop()
        self._is_connected = False
        self._command_history.append({
            "action": "disconnect",
            "timestamp": datetime.now()
        })
        logger.info(f"Mock scent controller '{self.name}' disconnected")
    
    async def set_scent(self, scent_type: ScentType, intensity: int = 5) -> bool:
        """设置香型和强度"""
        if not self._is_connected:
            return False
        
        # 验证强度范围
        intensity = max(1, min(10, intensity))
        
        self._update_state(scent_type, intensity, scent_type != ScentType.OFF)
        self._command_history.append({
            "action": "set_scent",
            "scent_type": scent_type.value,
            "intensity": intensity,
            "timestamp": datetime.now()
        })
        
        logger.debug(f"Scent set to {scent_type.value} with intensity {intensity}")
        return True
    
    async def set_intensity(self, intensity: int) -> bool:
        """设置强度"""
        if not self._is_connected:
            return False
        
        # 验证强度范围
        intensity = max(1, min(10, intensity))
        
        self._current_state.intensity = intensity
        self._current_state.timestamp = datetime.now()
        
        self._command_history.append({
            "action": "set_intensity",
            "intensity": intensity,
            "timestamp": datetime.now()
        })
        
        logger.debug(f"Scent intensity set to {intensity}")
        return True
    
    async def start(self) -> bool:
        """开始散香"""
        if not self._is_connected:
            return False
        
        if self._current_state.scent_type == ScentType.OFF:
            # 如果没有设置香型，使用默认的薰衣草
            await self.set_scent(ScentType.LAVENDER)
        
        self._current_state.is_running = True
        self._current_state.timestamp = datetime.now()
        
        self._command_history.append({
            "action": "start",
            "scent_type": self._current_state.scent_type.value,
            "intensity": self._current_state.intensity,
            "timestamp": datetime.now()
        })
        
        logger.info(f"Scent diffuser started: {self._current_state.scent_type.value}")
        return True
    
    async def stop(self) -> bool:
        """停止散香"""
        if not self._is_connected:
            return False
        
        self._update_state(ScentType.OFF, 0, False)
        
        self._command_history.append({
            "action": "stop",
            "timestamp": datetime.now()
        })
        
        logger.info("Scent diffuser stopped")
        return True



class WiFiScentController(BaseScentController):
    """WiFi 智能香薰控制器
    
    通过 WiFi HTTP API 控制智能香薰设备。
    """
    
    def __init__(
        self,
        ip: str,
        port: int = 80,
        name: str = "wifi_scent",
        api_path: str = "/api"
    ):
        """初始化 WiFi 香薰控制器
        
        Args:
            ip: 设备 IP 地址
            port: 设备端口
            name: 设备名称
            api_path: API 路径前缀
        """
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp library is required for WiFi scent functionality")
        
        super().__init__(name)
        self.ip = ip
        self.port = port
        self.api_path = api_path
        self._base_url = f"http://{ip}:{port}{api_path}"
        self._session: Optional['aiohttp.ClientSession'] = None
    
    async def connect(self) -> bool:
        """连接设备（验证设备可达）"""
        try:
            self._session = aiohttp.ClientSession()
            
            # 尝试获取设备状态以验证连接
            async with self._session.get(
                f"{self._base_url}/status",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self._is_connected = True
                    logger.info(f"Connected to WiFi scent device at {self.ip}")
                    return True
                else:
                    logger.error(f"Device returned status {response.status}")
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"Connection error: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        await self.stop()
        
        if self._session:
            await self._session.close()
            self._session = None
        
        self._is_connected = False
        logger.info("Disconnected from WiFi scent device")
    
    async def _send_command(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """发送命令到设备
        
        Args:
            endpoint: API 端点
            data: 命令数据
            
        Returns:
            是否发送成功
        """
        if not self._session or not self._is_connected:
            return False
        
        try:
            async with self._session.post(
                f"{self._base_url}/{endpoint}",
                json=data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    async def set_scent(self, scent_type: ScentType, intensity: int = 5) -> bool:
        """设置香型和强度"""
        if not self._is_connected:
            return False
        
        # 验证强度范围
        intensity = max(1, min(10, intensity))
        
        success = await self._send_command("set", {
            "scent": scent_type.value,
            "intensity": intensity
        })
        
        if success:
            self._update_state(scent_type, intensity, scent_type != ScentType.OFF)
            logger.info(f"Scent set to {scent_type.value} with intensity {intensity}")
        
        return success
    
    async def set_intensity(self, intensity: int) -> bool:
        """设置强度"""
        if not self._is_connected:
            return False
        
        # 验证强度范围
        intensity = max(1, min(10, intensity))
        
        success = await self._send_command("intensity", {
            "intensity": intensity
        })
        
        if success:
            self._current_state.intensity = intensity
            self._current_state.timestamp = datetime.now()
            logger.info(f"Scent intensity set to {intensity}")
        
        return success
    
    async def start(self) -> bool:
        """开始散香"""
        if not self._is_connected:
            return False
        
        if self._current_state.scent_type == ScentType.OFF:
            await self.set_scent(ScentType.LAVENDER)
        
        success = await self._send_command("start", {})
        
        if success:
            self._current_state.is_running = True
            self._current_state.timestamp = datetime.now()
            logger.info("Scent diffuser started")
        
        return success
    
    async def stop(self) -> bool:
        """停止散香"""
        if not self._is_connected:
            return False
        
        success = await self._send_command("stop", {})
        
        if success:
            self._update_state(ScentType.OFF, 0, False)
            logger.info("Scent diffuser stopped")
        
        return success


class EmotionScentMapper:
    """情绪-香型映射器
    
    根据用户情绪状态选择合适的香型。
    """
    
    def __init__(self):
        self._custom_mappings: Dict[str, Dict[str, Any]] = {}
    
    def get_scent_config(self, emotion: str) -> ScentConfig:
        """根据情绪获取香薰配置
        
        Args:
            emotion: 情绪类别
            
        Returns:
            香薰配置
        """
        emotion_lower = emotion.lower()
        
        # 优先使用自定义映射
        if emotion_lower in self._custom_mappings:
            mapping = self._custom_mappings[emotion_lower]
        elif emotion_lower in EMOTION_SCENT_MAP:
            mapping = EMOTION_SCENT_MAP[emotion_lower]
        else:
            # 默认使用中性配置
            mapping = EMOTION_SCENT_MAP["neutral"]
        
        return ScentConfig(
            scent_type=mapping["scent"].value,
            intensity=mapping["intensity"]
        )
    
    def set_custom_mapping(
        self,
        emotion: str,
        scent_type: ScentType,
        intensity: int,
        description: str = ""
    ) -> None:
        """设置自定义情绪-香型映射
        
        Args:
            emotion: 情绪类别
            scent_type: 香型
            intensity: 强度 1-10
            description: 描述
        """
        self._custom_mappings[emotion.lower()] = {
            "scent": scent_type,
            "intensity": intensity,
            "description": description
        }
    
    def get_all_mappings(self) -> Dict[str, Dict[str, Any]]:
        """获取所有情绪-香型映射"""
        result = dict(EMOTION_SCENT_MAP)
        result.update(self._custom_mappings)
        return result


class ScentControllerManager:
    """香薰控制器管理器
    
    管理香薰设备，提供统一的控制接口。
    """
    
    def __init__(self):
        self.controller: Optional[BaseScentController] = None
        self.emotion_mapper = EmotionScentMapper()
        self._timed_task: Optional[asyncio.Task] = None
    
    def set_controller(self, controller: BaseScentController) -> None:
        """设置香薰控制器"""
        self.controller = controller
    
    async def connect(self) -> bool:
        """连接设备"""
        if self.controller:
            return await self.controller.connect()
        return False
    
    async def disconnect(self) -> None:
        """断开设备"""
        await self.stop_timed_scent()
        if self.controller:
            await self.controller.disconnect()
    
    async def apply_therapy_config(self, config: ScentConfig) -> bool:
        """应用疗愈配置
        
        Args:
            config: 香薰配置
            
        Returns:
            是否应用成功
        """
        if not self.controller or not self.controller.is_connected:
            return False
        
        # 解析香型
        try:
            scent_type = ScentType(config.scent_type.lower())
        except ValueError:
            scent_type = ScentType.LAVENDER
        
        # 设置香型和强度
        success = await self.controller.set_scent(scent_type, config.intensity)
        
        # 如果指定了持续时间，启动定时任务
        if success and config.duration:
            await self.start_timed_scent(config.duration)
        
        return success
    
    async def apply_emotion_scent(self, emotion: str) -> bool:
        """根据情绪应用香薰设置
        
        Args:
            emotion: 情绪类别
            
        Returns:
            是否应用成功
        """
        config = self.emotion_mapper.get_scent_config(emotion)
        return await self.apply_therapy_config(config)
    
    async def start_timed_scent(self, duration_seconds: int) -> None:
        """启动定时散香
        
        Args:
            duration_seconds: 持续时间（秒）
        """
        # 取消现有的定时任务
        await self.stop_timed_scent()
        
        async def timed_stop():
            await asyncio.sleep(duration_seconds)
            if self.controller:
                await self.controller.stop()
                logger.info(f"Timed scent completed after {duration_seconds} seconds")
        
        self._timed_task = asyncio.create_task(timed_stop())
    
    async def stop_timed_scent(self) -> None:
        """停止定时散香任务"""
        if self._timed_task and not self._timed_task.done():
            self._timed_task.cancel()
            try:
                await self._timed_task
            except asyncio.CancelledError:
                pass
        self._timed_task = None
    
    def get_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        if not self.controller:
            return {
                "connected": False,
                "state": None
            }
        
        state = self.controller.current_state
        return {
            "connected": self.controller.is_connected,
            "state": {
                "scent_type": state.scent_type.value,
                "intensity": state.intensity,
                "is_running": state.is_running
            }
        }
    
    def get_available_scents(self) -> List[Dict[str, str]]:
        """获取可用的香型列表"""
        scents = []
        for scent in ScentType:
            if scent != ScentType.OFF:
                scents.append({
                    "scent": scent.value,
                    "name": scent.name.replace("_", " ").title()
                })
        return scents


def create_scent_controller(
    controller_type: str = "mock",
    **kwargs
) -> BaseScentController:
    """创建香薰控制器实例
    
    Args:
        controller_type: 控制器类型 ("mock", "wifi")
        **kwargs: 控制器特定参数
        
    Returns:
        香薰控制器实例
    """
    if controller_type == "mock":
        return MockScentController(kwargs.get("name", "mock_scent"))
    elif controller_type == "wifi":
        ip = kwargs.get("ip")
        if not ip:
            raise ValueError("WiFi scent controller requires 'ip' parameter")
        return WiFiScentController(
            ip=ip,
            port=kwargs.get("port", 80),
            name=kwargs.get("name", "wifi_scent"),
            api_path=kwargs.get("api_path", "/api")
        )
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")
