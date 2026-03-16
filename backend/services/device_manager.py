"""
设备管理器模块
Device Manager Module

实现硬件设备扫描、自动连接和连接状态监控
Requirements: 16.2
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Coroutine
from loguru import logger


class DeviceType(str, Enum):
    """设备类型"""
    LIGHT = "light"
    AUDIO = "audio"
    CHAIR = "chair"
    SCENT = "scent"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    HEART_RATE = "heart_rate"
    DISPLAY = "display"


class ConnectionStatus(str, Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class ConnectionProtocol(str, Enum):
    """连接协议"""
    USB = "usb"
    BLE = "ble"
    WIFI = "wifi"
    AUDIO_JACK = "audio_jack"
    HDMI = "hdmi"


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    device_type: DeviceType
    name: str
    protocol: ConnectionProtocol
    address: Optional[str] = None  # IP地址、MAC地址或设备路径
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "name": self.name,
            "protocol": self.protocol.value,
            "address": self.address,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata,
            "error_message": self.error_message
        }


class DeviceScanner(ABC):
    """设备扫描器基类"""
    
    def __init__(self, device_type: DeviceType, protocol: ConnectionProtocol):
        self.device_type = device_type
        self.protocol = protocol
    
    @abstractmethod
    async def scan(self, timeout: float = 5.0) -> List[DeviceInfo]:
        """扫描设备
        
        Args:
            timeout: 扫描超时时间（秒）
            
        Returns:
            发现的设备列表
        """
        pass


class BLEDeviceScanner(DeviceScanner):
    """BLE 蓝牙设备扫描器
    
    扫描心率手环、按摩座椅等 BLE 设备
    """
    
    # 设备名称关键词映射
    DEVICE_KEYWORDS = {
        DeviceType.HEART_RATE: ["heart", "hr", "pulse", "心率", "手环"],
        DeviceType.CHAIR: ["chair", "massage", "seat", "按摩", "座椅"]
    }
    
    def __init__(self, device_type: DeviceType):
        super().__init__(device_type, ConnectionProtocol.BLE)
        self._bleak_available = False
        
        try:
            from bleak import BleakScanner
            self._bleak_available = True
        except ImportError:
            logger.warning("bleak library not available for BLE scanning")
    
    async def scan(self, timeout: float = 5.0) -> List[DeviceInfo]:
        """扫描 BLE 设备"""
        if not self._bleak_available:
            logger.warning("BLE scanning not available")
            return []
        
        from bleak import BleakScanner
        
        devices = []
        keywords = self.DEVICE_KEYWORDS.get(self.device_type, [])
        
        try:
            logger.info(f"Scanning for BLE {self.device_type.value} devices...")
            discovered = await BleakScanner.discover(timeout=timeout)
            
            for device in discovered:
                if device.name:
                    name_lower = device.name.lower()
                    if any(kw in name_lower for kw in keywords):
                        devices.append(DeviceInfo(
                            device_id=device.address,
                            device_type=self.device_type,
                            name=device.name,
                            protocol=ConnectionProtocol.BLE,
                            address=device.address,
                            status=ConnectionStatus.DISCONNECTED,
                            last_seen=datetime.now(),
                            metadata={
                                "rssi": getattr(device, 'rssi', None)
                            }
                        ))
            
            logger.info(f"Found {len(devices)} BLE {self.device_type.value} device(s)")
            
        except Exception as e:
            logger.error(f"BLE scan error: {e}")
        
        return devices


class WiFiDeviceScanner(DeviceScanner):
    """WiFi 设备扫描器
    
    扫描智能灯光、香薰机等 WiFi 设备
    """
    
    def __init__(self, device_type: DeviceType):
        super().__init__(device_type, ConnectionProtocol.WIFI)
    
    async def scan(self, timeout: float = 5.0) -> List[DeviceInfo]:
        """扫描 WiFi 设备
        
        注意：实际的 WiFi 设备发现通常需要特定的协议支持
        这里提供一个基础实现框架
        """
        devices = []
        
        # 对于 Yeelight 灯光设备
        if self.device_type == DeviceType.LIGHT:
            devices.extend(await self._scan_yeelight(timeout))
        
        return devices
    
    async def _scan_yeelight(self, timeout: float) -> List[DeviceInfo]:
        """扫描 Yeelight 设备"""
        devices = []
        
        try:
            from yeelight import discover_bulbs
            
            logger.info("Scanning for Yeelight devices...")
            bulbs = discover_bulbs(timeout=timeout)
            
            for bulb in bulbs:
                devices.append(DeviceInfo(
                    device_id=bulb.get("ip", "unknown"),
                    device_type=DeviceType.LIGHT,
                    name=f"Yeelight ({bulb.get('ip', 'unknown')})",
                    protocol=ConnectionProtocol.WIFI,
                    address=bulb.get("ip"),
                    status=ConnectionStatus.DISCONNECTED,
                    last_seen=datetime.now(),
                    metadata={
                        "port": bulb.get("port", 55443),
                        "capabilities": bulb.get("capabilities", {})
                    }
                ))
            
            logger.info(f"Found {len(devices)} Yeelight device(s)")
            
        except ImportError:
            logger.warning("yeelight library not available")
        except Exception as e:
            logger.error(f"Yeelight scan error: {e}")
        
        return devices


class USBDeviceScanner(DeviceScanner):
    """USB 设备扫描器
    
    扫描摄像头、麦克风等 USB 设备
    """
    
    def __init__(self, device_type: DeviceType):
        super().__init__(device_type, ConnectionProtocol.USB)
    
    async def scan(self, timeout: float = 5.0) -> List[DeviceInfo]:
        """扫描 USB 设备"""
        devices = []
        
        if self.device_type == DeviceType.CAMERA:
            devices.extend(await self._scan_cameras())
        elif self.device_type == DeviceType.MICROPHONE:
            devices.extend(await self._scan_microphones())
        elif self.device_type == DeviceType.AUDIO:
            devices.extend(await self._scan_audio_outputs())
        
        return devices
    
    async def _scan_cameras(self) -> List[DeviceInfo]:
        """扫描摄像头设备"""
        devices = []
        
        try:
            import cv2
            
            # 尝试打开前几个摄像头索引
            for i in range(3):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    devices.append(DeviceInfo(
                        device_id=f"camera_{i}",
                        device_type=DeviceType.CAMERA,
                        name=f"Camera {i}",
                        protocol=ConnectionProtocol.USB,
                        address=str(i),
                        status=ConnectionStatus.DISCONNECTED,
                        last_seen=datetime.now(),
                        metadata={
                            "index": i,
                            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        }
                    ))
                    cap.release()
            
            logger.info(f"Found {len(devices)} camera(s)")
            
        except ImportError:
            logger.warning("OpenCV not available for camera scanning")
        except Exception as e:
            logger.error(f"Camera scan error: {e}")
        
        return devices
    
    async def _scan_microphones(self) -> List[DeviceInfo]:
        """扫描麦克风设备"""
        devices = []
        
        try:
            import sounddevice as sd
            
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device['max_input_channels'] > 0:
                    devices.append(DeviceInfo(
                        device_id=f"mic_{i}",
                        device_type=DeviceType.MICROPHONE,
                        name=device['name'],
                        protocol=ConnectionProtocol.USB,
                        address=str(i),
                        status=ConnectionStatus.DISCONNECTED,
                        last_seen=datetime.now(),
                        metadata={
                            "index": i,
                            "channels": device['max_input_channels'],
                            "sample_rate": device['default_samplerate']
                        }
                    ))
            
            logger.info(f"Found {len(devices)} microphone(s)")
            
        except ImportError:
            logger.warning("sounddevice not available for microphone scanning")
        except Exception as e:
            logger.error(f"Microphone scan error: {e}")
        
        return devices
    
    async def _scan_audio_outputs(self) -> List[DeviceInfo]:
        """扫描音频输出设备"""
        devices = []
        
        try:
            import sounddevice as sd
            
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device['max_output_channels'] > 0:
                    devices.append(DeviceInfo(
                        device_id=f"audio_{i}",
                        device_type=DeviceType.AUDIO,
                        name=device['name'],
                        protocol=ConnectionProtocol.USB,
                        address=str(i),
                        status=ConnectionStatus.DISCONNECTED,
                        last_seen=datetime.now(),
                        metadata={
                            "index": i,
                            "channels": device['max_output_channels'],
                            "sample_rate": device['default_samplerate'],
                            "is_default": i == sd.default.device[1]
                        }
                    ))
            
            logger.info(f"Found {len(devices)} audio output(s)")
            
        except ImportError:
            logger.warning("sounddevice not available for audio scanning")
        except Exception as e:
            logger.error(f"Audio output scan error: {e}")
        
        return devices




class ConnectionMonitor:
    """连接状态监控器
    
    监控设备连接状态，支持自动重连
    """
    
    def __init__(
        self,
        check_interval: float = 30.0,
        max_reconnect_attempts: int = 3
    ):
        """初始化连接监控器
        
        Args:
            check_interval: 状态检查间隔（秒）
            max_reconnect_attempts: 最大重连尝试次数
        """
        self.check_interval = check_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        
        self._devices: Dict[str, DeviceInfo] = {}
        self._connect_funcs: Dict[str, Callable[[], Coroutine[Any, Any, bool]]] = {}
        self._disconnect_funcs: Dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}
        self._reconnect_attempts: Dict[str, int] = {}
        
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._callbacks: List[Callable[[str, ConnectionStatus], None]] = []
    
    def register_device(
        self,
        device_info: DeviceInfo,
        connect_func: Callable[[], Coroutine[Any, Any, bool]],
        disconnect_func: Optional[Callable[[], Coroutine[Any, Any, None]]] = None
    ) -> None:
        """注册设备
        
        Args:
            device_info: 设备信息
            connect_func: 连接函数
            disconnect_func: 断开连接函数
        """
        self._devices[device_info.device_id] = device_info
        self._connect_funcs[device_info.device_id] = connect_func
        if disconnect_func:
            self._disconnect_funcs[device_info.device_id] = disconnect_func
        self._reconnect_attempts[device_info.device_id] = 0
    
    def register_status_callback(
        self,
        callback: Callable[[str, ConnectionStatus], None]
    ) -> None:
        """注册状态变化回调"""
        self._callbacks.append(callback)
    
    def _notify_status_change(self, device_id: str, status: ConnectionStatus) -> None:
        """通知状态变化"""
        for callback in self._callbacks:
            try:
                callback(device_id, status)
            except Exception as e:
                logger.warning(f"Status callback error: {e}")
    
    async def connect_device(self, device_id: str) -> bool:
        """连接设备
        
        Args:
            device_id: 设备 ID
            
        Returns:
            是否连接成功
        """
        if device_id not in self._devices:
            logger.error(f"Device not registered: {device_id}")
            return False
        
        device = self._devices[device_id]
        connect_func = self._connect_funcs.get(device_id)
        
        if not connect_func:
            logger.error(f"No connect function for device: {device_id}")
            return False
        
        device.status = ConnectionStatus.CONNECTING
        self._notify_status_change(device_id, ConnectionStatus.CONNECTING)
        
        try:
            result = await connect_func()
            
            if result:
                device.status = ConnectionStatus.CONNECTED
                device.last_seen = datetime.now()
                device.error_message = None
                self._reconnect_attempts[device_id] = 0
                logger.info(f"Device connected: {device.name}")
            else:
                device.status = ConnectionStatus.ERROR
                device.error_message = "Connection failed"
                logger.warning(f"Device connection failed: {device.name}")
            
            self._notify_status_change(device_id, device.status)
            return result
            
        except Exception as e:
            device.status = ConnectionStatus.ERROR
            device.error_message = str(e)
            self._notify_status_change(device_id, ConnectionStatus.ERROR)
            logger.error(f"Device connection error: {device.name} - {e}")
            return False
    
    async def disconnect_device(self, device_id: str) -> None:
        """断开设备连接"""
        if device_id not in self._devices:
            return
        
        device = self._devices[device_id]
        disconnect_func = self._disconnect_funcs.get(device_id)
        
        if disconnect_func:
            try:
                await disconnect_func()
            except Exception as e:
                logger.warning(f"Disconnect error: {e}")
        
        device.status = ConnectionStatus.DISCONNECTED
        self._notify_status_change(device_id, ConnectionStatus.DISCONNECTED)
        logger.info(f"Device disconnected: {device.name}")
    
    async def connect_all(self) -> Dict[str, bool]:
        """连接所有设备
        
        Returns:
            各设备的连接结果
        """
        results = {}
        
        # 并行连接所有设备
        tasks = [
            (device_id, self.connect_device(device_id))
            for device_id in self._devices.keys()
        ]
        
        for device_id, task in tasks:
            results[device_id] = await task
        
        return results
    
    async def disconnect_all(self) -> None:
        """断开所有设备"""
        for device_id in self._devices.keys():
            await self.disconnect_device(device_id)
    
    async def _reconnect_device(self, device_id: str) -> bool:
        """尝试重连设备"""
        if device_id not in self._devices:
            return False
        
        device = self._devices[device_id]
        attempts = self._reconnect_attempts.get(device_id, 0)
        
        if attempts >= self.max_reconnect_attempts:
            logger.warning(
                f"Max reconnect attempts reached for {device.name}"
            )
            return False
        
        self._reconnect_attempts[device_id] = attempts + 1
        device.status = ConnectionStatus.RECONNECTING
        self._notify_status_change(device_id, ConnectionStatus.RECONNECTING)
        
        logger.info(
            f"Reconnecting {device.name} (attempt {attempts + 1}/{self.max_reconnect_attempts})"
        )
        
        return await self.connect_device(device_id)
    
    async def start_monitoring(self) -> None:
        """启动连接监控"""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Connection monitoring started")
    
    async def stop_monitoring(self) -> None:
        """停止连接监控"""
        self._is_running = False
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self._monitor_task = None
        logger.info("Connection monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """监控循环"""
        while self._is_running:
            try:
                await asyncio.sleep(self.check_interval)
                
                for device_id, device in self._devices.items():
                    # 检查已连接设备的状态
                    if device.status == ConnectionStatus.CONNECTED:
                        # 这里可以添加心跳检测逻辑
                        device.last_seen = datetime.now()
                    
                    # 尝试重连断开的设备
                    elif device.status in (ConnectionStatus.ERROR, ConnectionStatus.DISCONNECTED):
                        await self._reconnect_device(device_id)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    def get_device_status(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备状态"""
        return self._devices.get(device_id)
    
    def get_all_status(self) -> Dict[str, DeviceInfo]:
        """获取所有设备状态"""
        return self._devices.copy()
    
    def get_connected_devices(self) -> List[DeviceInfo]:
        """获取已连接的设备列表"""
        return [
            device for device in self._devices.values()
            if device.status == ConnectionStatus.CONNECTED
        ]
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        total = len(self._devices)
        connected = sum(
            1 for d in self._devices.values()
            if d.status == ConnectionStatus.CONNECTED
        )
        error = sum(
            1 for d in self._devices.values()
            if d.status == ConnectionStatus.ERROR
        )
        
        return {
            "total": total,
            "connected": connected,
            "disconnected": total - connected - error,
            "error": error,
            "devices": {
                device_id: device.to_dict()
                for device_id, device in self._devices.items()
            }
        }


class HardwareDeviceManager:
    """硬件设备管理器
    
    统一管理所有硬件设备的扫描、连接和监控
    Requirements: 16.2
    """
    
    def __init__(self):
        self._scanners: Dict[DeviceType, List[DeviceScanner]] = {}
        self._discovered_devices: Dict[str, DeviceInfo] = {}
        self._connection_monitor = ConnectionMonitor()
        self._device_controllers: Dict[str, Any] = {}
    
    def register_scanner(self, scanner: DeviceScanner) -> None:
        """注册设备扫描器"""
        if scanner.device_type not in self._scanners:
            self._scanners[scanner.device_type] = []
        self._scanners[scanner.device_type].append(scanner)
    
    def register_device_controller(
        self,
        device_id: str,
        controller: Any,
        connect_func: Callable[[], Coroutine[Any, Any, bool]],
        disconnect_func: Optional[Callable[[], Coroutine[Any, Any, None]]] = None
    ) -> None:
        """注册设备控制器
        
        Args:
            device_id: 设备 ID
            controller: 控制器实例
            connect_func: 连接函数
            disconnect_func: 断开连接函数
        """
        self._device_controllers[device_id] = controller
        
        # 如果设备已发现，注册到连接监控器
        if device_id in self._discovered_devices:
            self._connection_monitor.register_device(
                self._discovered_devices[device_id],
                connect_func,
                disconnect_func
            )
    
    async def scan_all_devices(self, timeout: float = 5.0) -> Dict[str, List[DeviceInfo]]:
        """扫描所有类型的设备
        
        Args:
            timeout: 扫描超时时间
            
        Returns:
            按设备类型分组的设备列表
        """
        results: Dict[str, List[DeviceInfo]] = {}
        
        logger.info("Starting hardware device scan...")
        
        for device_type, scanners in self._scanners.items():
            results[device_type.value] = []
            
            for scanner in scanners:
                try:
                    devices = await scanner.scan(timeout)
                    results[device_type.value].extend(devices)
                    
                    # 保存发现的设备
                    for device in devices:
                        self._discovered_devices[device.device_id] = device
                        
                except Exception as e:
                    logger.error(f"Scan error for {device_type.value}: {e}")
        
        total_devices = sum(len(devices) for devices in results.values())
        logger.info(f"Device scan complete. Found {total_devices} device(s)")
        
        return results
    
    async def auto_connect_devices(
        self,
        device_configs: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """自动连接设备
        
        Args:
            device_configs: 设备配置（可选）
            
        Returns:
            各设备的连接结果
        """
        return await self._connection_monitor.connect_all()
    
    async def start_monitoring(self) -> None:
        """启动设备监控"""
        await self._connection_monitor.start_monitoring()
    
    async def stop_monitoring(self) -> None:
        """停止设备监控"""
        await self._connection_monitor.stop_monitoring()
    
    async def disconnect_all(self) -> None:
        """断开所有设备"""
        await self._connection_monitor.disconnect_all()
    
    def get_device_controller(self, device_id: str) -> Optional[Any]:
        """获取设备控制器"""
        return self._device_controllers.get(device_id)
    
    def get_discovered_devices(self) -> Dict[str, DeviceInfo]:
        """获取发现的设备"""
        return self._discovered_devices.copy()
    
    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return self._connection_monitor.get_status_summary()
    
    def register_status_callback(
        self,
        callback: Callable[[str, ConnectionStatus], None]
    ) -> None:
        """注册状态变化回调"""
        self._connection_monitor.register_status_callback(callback)


# 全局设备管理器实例
_device_manager: Optional[HardwareDeviceManager] = None


def get_device_manager() -> HardwareDeviceManager:
    """获取全局设备管理器实例"""
    global _device_manager
    if _device_manager is None:
        _device_manager = HardwareDeviceManager()
    return _device_manager


def init_device_manager() -> HardwareDeviceManager:
    """初始化全局设备管理器"""
    global _device_manager
    _device_manager = HardwareDeviceManager()
    
    # 注册默认扫描器
    _device_manager.register_scanner(BLEDeviceScanner(DeviceType.HEART_RATE))
    _device_manager.register_scanner(BLEDeviceScanner(DeviceType.CHAIR))
    _device_manager.register_scanner(WiFiDeviceScanner(DeviceType.LIGHT))
    _device_manager.register_scanner(USBDeviceScanner(DeviceType.CAMERA))
    _device_manager.register_scanner(USBDeviceScanner(DeviceType.MICROPHONE))
    _device_manager.register_scanner(USBDeviceScanner(DeviceType.AUDIO))
    
    return _device_manager


async def cleanup_device_manager() -> None:
    """清理设备管理器"""
    global _device_manager
    if _device_manager:
        await _device_manager.stop_monitoring()
        await _device_manager.disconnect_all()
    _device_manager = None
