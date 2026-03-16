"""
座椅控制器模块
Chair Controller Module

使用 bleak 库实现 BLE 连接和按摩座椅控制
Requirements: 9.1, 9.2, 9.3
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from loguru import logger

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.device import BLEDevice
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    logger.warning("bleak library not available. BLE chair functionality will be disabled.")


class MassageMode(str, Enum):
    """按摩模式
    
    Requirements: 9.2 - 支持至少5种按摩模式
    """
    GENTLE = "gentle"      # 轻柔模式
    SOOTHING = "soothing"  # 舒缓模式
    DEEP = "deep"          # 深度模式
    WAVE = "wave"          # 波浪模式
    PULSE = "pulse"        # 脉冲模式
    OFF = "off"            # 关闭


@dataclass
class MassageModeConfig:
    """按摩模式配置"""
    pattern: List[int]  # 按摩模式序列 (0-3 强度)
    default_intensity: int  # 默认强度 (1-10)
    description: str  # 模式描述


# 预定义的按摩模式配置
MASSAGE_MODE_CONFIGS: Dict[MassageMode, MassageModeConfig] = {
    MassageMode.GENTLE: MassageModeConfig(
        pattern=[1, 0, 1, 0],
        default_intensity=3,
        description="轻柔按摩，适合放松"
    ),
    MassageMode.SOOTHING: MassageModeConfig(
        pattern=[1, 1, 2, 1],
        default_intensity=4,
        description="舒缓按摩，缓解疲劳"
    ),
    MassageMode.DEEP: MassageModeConfig(
        pattern=[3, 3, 3, 3],
        default_intensity=7,
        description="深度按摩，释放肌肉紧张"
    ),
    MassageMode.WAVE: MassageModeConfig(
        pattern=[1, 2, 3, 2, 1],
        default_intensity=5,
        description="波浪式按摩，循环放松"
    ),
    MassageMode.PULSE: MassageModeConfig(
        pattern=[3, 0, 3, 0],
        default_intensity=6,
        description="脉冲按摩，刺激穴位"
    ),
    MassageMode.OFF: MassageModeConfig(
        pattern=[0, 0, 0, 0],
        default_intensity=0,
        description="关闭按摩"
    )
}


@dataclass
class ChairState:
    """座椅状态"""
    mode: MassageMode = MassageMode.OFF
    intensity: int = 0  # 0-10
    is_running: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """验证强度范围"""
        if not 0 <= self.intensity <= 10:
            raise ValueError(f"intensity must be between 0 and 10, got {self.intensity}")


@dataclass
class ChairConfig:
    """座椅配置"""
    mode: str  # 按摩模式名称
    intensity: int  # 强度 1-10
    duration: Optional[int] = None  # 持续时间（秒），None表示持续运行


class BaseChairController(ABC):
    """座椅控制器基类
    
    定义座椅控制的抽象接口，所有具体的座椅适配器都需要继承此类。
    Requirements: 9.1
    """
    
    def __init__(self, name: str = "chair"):
        self.name = name
        self._current_state: ChairState = ChairState()
        self._is_connected: bool = False
        self._user_preferences: Dict[str, Any] = {}
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected
    
    @property
    def current_state(self) -> ChairState:
        """当前座椅状态"""
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
    async def set_mode(self, mode: MassageMode, intensity: int = None) -> bool:
        """设置按摩模式
        
        Args:
            mode: 按摩模式
            intensity: 强度 1-10，None则使用模式默认强度
            
        Returns:
            是否设置成功
            
        Requirements: 9.2
        """
        pass
    
    @abstractmethod
    async def set_intensity(self, intensity: int) -> bool:
        """设置按摩强度
        
        Args:
            intensity: 强度 1-10
            
        Returns:
            是否设置成功
            
        Requirements: 9.3
        """
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """开始按摩"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止按摩"""
        pass
    
    def record_user_preference(self, mode: MassageMode, intensity: int) -> None:
        """记录用户偏好
        
        Requirements: 9.4 - 记录用户偏好
        
        Args:
            mode: 用户选择的模式
            intensity: 用户选择的强度
        """
        self._user_preferences[mode.value] = {
            "intensity": intensity,
            "timestamp": datetime.now().isoformat()
        }
        logger.debug(f"Recorded user preference: mode={mode.value}, intensity={intensity}")
    
    def get_user_preference(self, mode: MassageMode) -> Optional[int]:
        """获取用户偏好的强度
        
        Args:
            mode: 按摩模式
            
        Returns:
            用户偏好的强度，如果没有记录则返回None
        """
        pref = self._user_preferences.get(mode.value)
        return pref["intensity"] if pref else None
    
    def _update_state(
        self,
        mode: MassageMode,
        intensity: int,
        is_running: bool
    ) -> None:
        """更新内部状态"""
        self._current_state = ChairState(
            mode=mode,
            intensity=intensity,
            is_running=is_running
        )



class MockChairController(BaseChairController):
    """模拟座椅控制器（用于测试和开发）"""
    
    def __init__(self, name: str = "mock_chair"):
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
        logger.info(f"Mock chair controller '{self.name}' connected")
        return True
    
    async def disconnect(self) -> None:
        """模拟断开连接"""
        await self.stop()
        self._is_connected = False
        self._command_history.append({
            "action": "disconnect",
            "timestamp": datetime.now()
        })
        logger.info(f"Mock chair controller '{self.name}' disconnected")
    
    async def set_mode(self, mode: MassageMode, intensity: int = None) -> bool:
        """设置按摩模式"""
        if not self._is_connected:
            return False
        
        # 获取模式配置
        mode_config = MASSAGE_MODE_CONFIGS.get(mode, MASSAGE_MODE_CONFIGS[MassageMode.GENTLE])
        
        # 确定强度
        if intensity is None:
            # 优先使用用户偏好，否则使用默认强度
            intensity = self.get_user_preference(mode) or mode_config.default_intensity
        
        # 验证强度范围
        intensity = max(1, min(10, intensity))
        
        self._update_state(mode, intensity, mode != MassageMode.OFF)
        self._command_history.append({
            "action": "set_mode",
            "mode": mode.value,
            "intensity": intensity,
            "pattern": mode_config.pattern,
            "timestamp": datetime.now()
        })
        
        logger.debug(f"Chair mode set to {mode.value} with intensity {intensity}")
        return True
    
    async def set_intensity(self, intensity: int) -> bool:
        """设置按摩强度"""
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
        
        # 记录用户偏好
        if self._current_state.mode != MassageMode.OFF:
            self.record_user_preference(self._current_state.mode, intensity)
        
        logger.debug(f"Chair intensity set to {intensity}")
        return True
    
    async def start(self) -> bool:
        """开始按摩"""
        if not self._is_connected:
            return False
        
        if self._current_state.mode == MassageMode.OFF:
            # 如果没有设置模式，使用默认的轻柔模式
            await self.set_mode(MassageMode.GENTLE)
        
        self._current_state.is_running = True
        self._current_state.timestamp = datetime.now()
        
        self._command_history.append({
            "action": "start",
            "mode": self._current_state.mode.value,
            "intensity": self._current_state.intensity,
            "timestamp": datetime.now()
        })
        
        logger.info(f"Chair massage started: mode={self._current_state.mode.value}")
        return True
    
    async def stop(self) -> bool:
        """停止按摩"""
        if not self._is_connected:
            return False
        
        self._update_state(MassageMode.OFF, 0, False)
        
        self._command_history.append({
            "action": "stop",
            "timestamp": datetime.now()
        })
        
        logger.info("Chair massage stopped")
        return True


class BLEChairController(BaseChairController):
    """BLE 蓝牙座椅控制器
    
    通过蓝牙 BLE 协议控制智能按摩座椅。
    Requirements: 9.5
    """
    
    # 通用 BLE 服务和特征 UUID（实际使用时需要根据具体设备调整）
    CHAIR_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
    CHAIR_CONTROL_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
    CHAIR_STATUS_CHAR_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"
    
    def __init__(
        self,
        device_address: Optional[str] = None,
        name: str = "ble_chair",
        service_uuid: Optional[str] = None,
        control_char_uuid: Optional[str] = None
    ):
        """初始化 BLE 座椅控制器
        
        Args:
            device_address: BLE 设备地址，None 则自动扫描
            name: 设备名称
            service_uuid: 自定义服务 UUID
            control_char_uuid: 自定义控制特征 UUID
        """
        if not BLEAK_AVAILABLE:
            raise RuntimeError("bleak library is required for BLE functionality")
        
        super().__init__(name)
        self.device_address = device_address
        self._client: Optional[BleakClient] = None
        self._device: Optional[BLEDevice] = None
        
        # 允许自定义 UUID
        self._service_uuid = service_uuid or self.CHAIR_SERVICE_UUID
        self._control_char_uuid = control_char_uuid or self.CHAIR_CONTROL_CHAR_UUID
    
    async def scan_devices(self, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """扫描附近的座椅设备
        
        Args:
            timeout: 扫描超时时间（秒）
            
        Returns:
            发现的座椅设备列表
        """
        logger.info(f"Scanning for chair devices (timeout: {timeout}s)...")
        devices = []
        
        try:
            discovered = await BleakScanner.discover(timeout=timeout)
            
            for device in discovered:
                # 检查是否是座椅设备（通过名称关键词）
                if device.name and any(
                    keyword in device.name.lower()
                    for keyword in ["chair", "massage", "seat", "sofa", "按摩", "座椅"]
                ):
                    devices.append({
                        "address": device.address,
                        "name": device.name,
                        "rssi": device.rssi if hasattr(device, 'rssi') else None
                    })
                    logger.debug(f"Found chair device: {device.name} ({device.address})")
            
            logger.info(f"Found {len(devices)} chair device(s)")
            
        except Exception as e:
            logger.error(f"Error scanning for devices: {e}")
        
        return devices
    
    async def connect(self, address: Optional[str] = None) -> bool:
        """连接到座椅设备
        
        Args:
            address: 设备地址，None 则使用初始化时的地址或自动扫描
            
        Returns:
            是否连接成功
        """
        target_address = address or self.device_address
        
        # 如果没有指定地址，尝试自动扫描
        if not target_address:
            devices = await self.scan_devices(timeout=5.0)
            if devices:
                target_address = devices[0]["address"]
                logger.info(f"Auto-selected device: {devices[0]['name']} ({target_address})")
            else:
                logger.error("No chair devices found")
                return False
        
        try:
            logger.info(f"Connecting to chair device: {target_address}")
            self._client = BleakClient(target_address)
            await self._client.connect()
            
            if self._client.is_connected:
                self._is_connected = True
                self.device_address = target_address
                logger.info(f"Connected to chair device: {target_address}")
                return True
            else:
                logger.error("Failed to connect to device")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        await self.stop()
        
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
                logger.info("Disconnected from chair device")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
        
        self._is_connected = False
        self._client = None
    
    def _build_command(self, mode: MassageMode, intensity: int) -> bytes:
        """构建 BLE 控制命令
        
        命令格式（示例，实际格式需根据具体设备调整）：
        - Byte 0: 命令类型 (0x01 = 设置模式)
        - Byte 1: 模式代码
        - Byte 2: 强度 (1-10)
        - Byte 3: 校验和
        
        Args:
            mode: 按摩模式
            intensity: 强度
            
        Returns:
            命令字节数据
        """
        mode_codes = {
            MassageMode.OFF: 0x00,
            MassageMode.GENTLE: 0x01,
            MassageMode.SOOTHING: 0x02,
            MassageMode.DEEP: 0x03,
            MassageMode.WAVE: 0x04,
            MassageMode.PULSE: 0x05
        }
        
        cmd_type = 0x01  # 设置模式命令
        mode_code = mode_codes.get(mode, 0x00)
        checksum = (cmd_type + mode_code + intensity) & 0xFF
        
        return bytes([cmd_type, mode_code, intensity, checksum])
    
    async def set_mode(self, mode: MassageMode, intensity: int = None) -> bool:
        """设置按摩模式"""
        if not self._is_connected or not self._client:
            logger.error("Not connected to device")
            return False
        
        # 获取模式配置
        mode_config = MASSAGE_MODE_CONFIGS.get(mode, MASSAGE_MODE_CONFIGS[MassageMode.GENTLE])
        
        # 确定强度
        if intensity is None:
            intensity = self.get_user_preference(mode) or mode_config.default_intensity
        
        # 验证强度范围
        intensity = max(1, min(10, intensity))
        
        try:
            # 构建并发送命令
            command = self._build_command(mode, intensity)
            await self._client.write_gatt_char(
                self._control_char_uuid,
                command
            )
            
            self._update_state(mode, intensity, mode != MassageMode.OFF)
            logger.info(f"Chair mode set to {mode.value} with intensity {intensity}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting mode: {e}")
            return False
    
    async def set_intensity(self, intensity: int) -> bool:
        """设置按摩强度"""
        if not self._is_connected or not self._client:
            logger.error("Not connected to device")
            return False
        
        # 验证强度范围
        intensity = max(1, min(10, intensity))
        
        try:
            # 使用当前模式重新设置
            current_mode = self._current_state.mode
            if current_mode == MassageMode.OFF:
                current_mode = MassageMode.GENTLE
            
            command = self._build_command(current_mode, intensity)
            await self._client.write_gatt_char(
                self._control_char_uuid,
                command
            )
            
            self._current_state.intensity = intensity
            self._current_state.timestamp = datetime.now()
            
            # 记录用户偏好
            self.record_user_preference(current_mode, intensity)
            
            logger.info(f"Chair intensity set to {intensity}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting intensity: {e}")
            return False
    
    async def start(self) -> bool:
        """开始按摩"""
        if not self._is_connected:
            return False
        
        if self._current_state.mode == MassageMode.OFF:
            await self.set_mode(MassageMode.GENTLE)
        else:
            # 重新发送当前模式命令以启动
            await self.set_mode(
                self._current_state.mode,
                self._current_state.intensity
            )
        
        self._current_state.is_running = True
        logger.info("Chair massage started")
        return True
    
    async def stop(self) -> bool:
        """停止按摩"""
        if not self._is_connected or not self._client:
            return False
        
        try:
            command = self._build_command(MassageMode.OFF, 0)
            await self._client.write_gatt_char(
                self._control_char_uuid,
                command
            )
            
            self._update_state(MassageMode.OFF, 0, False)
            logger.info("Chair massage stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping massage: {e}")
            return False


class ChairControllerManager:
    """座椅控制器管理器
    
    管理座椅设备，提供统一的控制接口。
    """
    
    def __init__(self):
        self.controller: Optional[BaseChairController] = None
        self._timed_task: Optional[asyncio.Task] = None
    
    def set_controller(self, controller: BaseChairController) -> None:
        """设置座椅控制器"""
        self.controller = controller
    
    async def connect(self) -> bool:
        """连接设备"""
        if self.controller:
            return await self.controller.connect()
        return False
    
    async def disconnect(self) -> None:
        """断开设备"""
        await self.stop_timed_massage()
        if self.controller:
            await self.controller.disconnect()
    
    async def apply_therapy_config(self, config: ChairConfig) -> bool:
        """应用疗愈配置
        
        Args:
            config: 座椅配置
            
        Returns:
            是否应用成功
        """
        if not self.controller or not self.controller.is_connected:
            return False
        
        # 解析模式
        try:
            mode = MassageMode(config.mode.lower())
        except ValueError:
            mode = MassageMode.GENTLE
        
        # 设置模式和强度
        success = await self.controller.set_mode(mode, config.intensity)
        
        # 如果指定了持续时间，启动定时任务
        if success and config.duration:
            await self.start_timed_massage(config.duration)
        
        return success
    
    async def start_timed_massage(self, duration_seconds: int) -> None:
        """启动定时按摩
        
        Args:
            duration_seconds: 持续时间（秒）
        """
        # 取消现有的定时任务
        await self.stop_timed_massage()
        
        async def timed_stop():
            await asyncio.sleep(duration_seconds)
            if self.controller:
                await self.controller.stop()
                logger.info(f"Timed massage completed after {duration_seconds} seconds")
        
        self._timed_task = asyncio.create_task(timed_stop())
    
    async def stop_timed_massage(self) -> None:
        """停止定时按摩任务"""
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
                "mode": state.mode.value,
                "intensity": state.intensity,
                "is_running": state.is_running
            }
        }
    
    def get_available_modes(self) -> List[Dict[str, Any]]:
        """获取可用的按摩模式列表"""
        modes = []
        for mode, config in MASSAGE_MODE_CONFIGS.items():
            if mode != MassageMode.OFF:
                modes.append({
                    "mode": mode.value,
                    "description": config.description,
                    "default_intensity": config.default_intensity
                })
        return modes


def create_chair_controller(
    controller_type: str = "mock",
    **kwargs
) -> BaseChairController:
    """创建座椅控制器实例
    
    Args:
        controller_type: 控制器类型 ("mock", "ble")
        **kwargs: 控制器特定参数
        
    Returns:
        座椅控制器实例
    """
    if controller_type == "mock":
        return MockChairController(kwargs.get("name", "mock_chair"))
    elif controller_type == "ble":
        return BLEChairController(
            device_address=kwargs.get("device_address"),
            name=kwargs.get("name", "ble_chair"),
            service_uuid=kwargs.get("service_uuid"),
            control_char_uuid=kwargs.get("control_char_uuid")
        )
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")
