"""
BLE 心率数据接收模块
BLE Heart Rate Data Receiver

使用 bleak 库实现 BLE 连接和心率数据实时接收
Requirements: 3.1
"""
import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, List, Deque
from loguru import logger

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.device import BLEDevice
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    logger.warning("bleak library not available. BLE functionality will be disabled.")


# 标准心率服务和特征 UUID
HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"


@dataclass
class HeartRateReading:
    """心率读数"""
    bpm: int  # 心率值 (beats per minute)
    timestamp: datetime = field(default_factory=datetime.now)
    rr_intervals: List[int] = field(default_factory=list)  # RR间期 (ms)
    energy_expended: Optional[int] = None  # 能量消耗 (kJ)
    sensor_contact: bool = True  # 传感器接触状态


@dataclass
class HeartRateBuffer:
    """心率数据缓冲区"""
    readings: Deque[HeartRateReading] = field(default_factory=lambda: deque(maxlen=600))
    rr_intervals: Deque[int] = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_reading(self, reading: HeartRateReading) -> None:
        """添加心率读数"""
        self.readings.append(reading)
        for rr in reading.rr_intervals:
            self.rr_intervals.append(rr)
    
    def get_recent_bpm(self, count: int = 60) -> List[int]:
        """获取最近的心率值"""
        recent = list(self.readings)[-count:]
        return [r.bpm for r in recent]
    
    def get_rr_intervals(self, min_count: int = 0) -> List[int]:
        """获取RR间期数据"""
        intervals = list(self.rr_intervals)
        if len(intervals) < min_count:
            return []
        return intervals
    
    def get_duration_seconds(self) -> float:
        """获取缓冲区数据的时间跨度（秒）"""
        if len(self.readings) < 2:
            return 0.0
        first = self.readings[0].timestamp
        last = self.readings[-1].timestamp
        return (last - first).total_seconds()
    
    def clear(self) -> None:
        """清空缓冲区"""
        self.readings.clear()
        self.rr_intervals.clear()


class BLEHeartRateReceiver:
    """BLE 心率数据接收器"""
    
    def __init__(
        self,
        device_address: Optional[str] = None,
        buffer_size: int = 600,
        on_reading: Optional[Callable[[HeartRateReading], None]] = None
    ):
        """
        初始化心率接收器
        
        Args:
            device_address: BLE设备地址，None则自动扫描
            buffer_size: 缓冲区大小（读数数量）
            on_reading: 收到新读数时的回调函数
        """
        if not BLEAK_AVAILABLE:
            raise RuntimeError("bleak library is required for BLE functionality")
        
        self.device_address = device_address
        self.buffer = HeartRateBuffer()
        self.buffer.readings = deque(maxlen=buffer_size)
        self.on_reading = on_reading
        
        self._client: Optional[BleakClient] = None
        self._connected = False
        self._running = False
        self._device: Optional[BLEDevice] = None
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected and self._client is not None
    
    @property
    def is_running(self) -> bool:
        """是否正在接收数据"""
        return self._running
    
    async def scan_devices(self, timeout: float = 10.0) -> List[dict]:
        """
        扫描附近的心率设备
        
        Args:
            timeout: 扫描超时时间（秒）
            
        Returns:
            发现的心率设备列表
        """
        logger.info(f"Scanning for heart rate devices (timeout: {timeout}s)...")
        devices = []
        
        try:
            discovered = await BleakScanner.discover(timeout=timeout)
            
            for device in discovered:
                # 检查是否是心率设备（通过名称或服务UUID）
                if device.name and any(
                    keyword in device.name.lower() 
                    for keyword in ["heart", "hr", "pulse", "polar", "garmin", "wahoo"]
                ):
                    devices.append({
                        "address": device.address,
                        "name": device.name,
                        "rssi": device.rssi if hasattr(device, 'rssi') else None
                    })
                    logger.debug(f"Found heart rate device: {device.name} ({device.address})")
            
            logger.info(f"Found {len(devices)} heart rate device(s)")
            
        except Exception as e:
            logger.error(f"Error scanning for devices: {e}")
        
        return devices
    
    async def connect(self, address: Optional[str] = None) -> bool:
        """
        连接到心率设备
        
        Args:
            address: 设备地址，None则使用初始化时的地址或自动扫描
            
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
                logger.error("No heart rate devices found")
                return False
        
        try:
            logger.info(f"Connecting to device: {target_address}")
            self._client = BleakClient(target_address)
            await self._client.connect()
            
            if self._client.is_connected:
                self._connected = True
                self.device_address = target_address
                logger.info(f"Connected to heart rate device: {target_address}")
                return True
            else:
                logger.error("Failed to connect to device")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
                logger.info("Disconnected from heart rate device")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
        
        self._connected = False
        self._client = None
    
    def _parse_heart_rate_data(self, data: bytearray) -> HeartRateReading:
        """
        解析心率测量数据
        
        心率测量特征数据格式 (根据 Bluetooth SIG 规范):
        - Byte 0: Flags
          - Bit 0: 心率值格式 (0=UINT8, 1=UINT16)
          - Bit 1-2: 传感器接触状态
          - Bit 3: 能量消耗存在标志
          - Bit 4: RR间期存在标志
        - Byte 1(-2): 心率值
        - 后续字节: 能量消耗和/或RR间期
        """
        flags = data[0]
        hr_format_16bit = bool(flags & 0x01)
        sensor_contact_supported = bool(flags & 0x02)
        sensor_contact_detected = bool(flags & 0x04) if sensor_contact_supported else True
        energy_expended_present = bool(flags & 0x08)
        rr_interval_present = bool(flags & 0x10)
        
        offset = 1
        
        # 解析心率值
        if hr_format_16bit:
            bpm = int.from_bytes(data[offset:offset+2], byteorder='little')
            offset += 2
        else:
            bpm = data[offset]
            offset += 1
        
        # 解析能量消耗
        energy_expended = None
        if energy_expended_present:
            energy_expended = int.from_bytes(data[offset:offset+2], byteorder='little')
            offset += 2
        
        # 解析RR间期
        rr_intervals = []
        if rr_interval_present:
            while offset + 1 < len(data):
                rr = int.from_bytes(data[offset:offset+2], byteorder='little')
                # RR间期单位是 1/1024 秒，转换为毫秒
                rr_ms = int(rr * 1000 / 1024)
                rr_intervals.append(rr_ms)
                offset += 2
        
        return HeartRateReading(
            bpm=bpm,
            rr_intervals=rr_intervals,
            energy_expended=energy_expended,
            sensor_contact=sensor_contact_detected
        )
    
    def _notification_handler(self, sender, data: bytearray) -> None:
        """处理心率通知"""
        try:
            reading = self._parse_heart_rate_data(data)
            self.buffer.add_reading(reading)
            
            logger.debug(
                f"Heart rate: {reading.bpm} bpm, "
                f"RR intervals: {reading.rr_intervals}"
            )
            
            # 调用回调函数
            if self.on_reading:
                self.on_reading(reading)
                
        except Exception as e:
            logger.error(f"Error parsing heart rate data: {e}")
    
    async def start_receiving(self) -> bool:
        """
        开始接收心率数据
        
        Returns:
            是否成功开始接收
        """
        if not self.is_connected:
            logger.error("Not connected to device")
            return False
        
        try:
            # 订阅心率测量特征的通知
            await self._client.start_notify(
                HEART_RATE_MEASUREMENT_UUID,
                self._notification_handler
            )
            self._running = True
            logger.info("Started receiving heart rate data")
            return True
            
        except Exception as e:
            logger.error(f"Error starting notifications: {e}")
            return False
    
    async def stop_receiving(self) -> None:
        """停止接收心率数据"""
        if self._client and self._running:
            try:
                await self._client.stop_notify(HEART_RATE_MEASUREMENT_UUID)
                logger.info("Stopped receiving heart rate data")
            except Exception as e:
                logger.error(f"Error stopping notifications: {e}")
        
        self._running = False
    
    def get_buffer(self) -> HeartRateBuffer:
        """获取数据缓冲区"""
        return self.buffer
    
    def get_latest_reading(self) -> Optional[HeartRateReading]:
        """获取最新的心率读数"""
        if self.buffer.readings:
            return self.buffer.readings[-1]
        return None
    
    def get_average_bpm(self, seconds: int = 60) -> Optional[float]:
        """
        获取指定时间段内的平均心率
        
        Args:
            seconds: 时间段（秒）
            
        Returns:
            平均心率，数据不足时返回None
        """
        if not self.buffer.readings:
            return None
        
        now = datetime.now()
        recent_readings = [
            r for r in self.buffer.readings
            if (now - r.timestamp).total_seconds() <= seconds
        ]
        
        if not recent_readings:
            return None
        
        return sum(r.bpm for r in recent_readings) / len(recent_readings)


class MockBLEHeartRateReceiver:
    """
    模拟 BLE 心率接收器（用于测试和开发）
    """
    
    def __init__(
        self,
        base_bpm: int = 70,
        variability: int = 5,
        on_reading: Optional[Callable[[HeartRateReading], None]] = None
    ):
        """
        初始化模拟接收器
        
        Args:
            base_bpm: 基础心率
            variability: 心率变异范围
            on_reading: 收到新读数时的回调函数
        """
        self.base_bpm = base_bpm
        self.variability = variability
        self.on_reading = on_reading
        self.buffer = HeartRateBuffer()
        
        self._connected = False
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    async def connect(self, address: Optional[str] = None) -> bool:
        """模拟连接"""
        await asyncio.sleep(0.5)  # 模拟连接延迟
        self._connected = True
        logger.info("Mock heart rate device connected")
        return True
    
    async def disconnect(self) -> None:
        """模拟断开连接"""
        await self.stop_receiving()
        self._connected = False
        logger.info("Mock heart rate device disconnected")
    
    async def start_receiving(self) -> bool:
        """开始模拟接收数据"""
        if not self._connected:
            return False
        
        self._running = True
        self._task = asyncio.create_task(self._generate_data())
        logger.info("Started mock heart rate data generation")
        return True
    
    async def stop_receiving(self) -> None:
        """停止模拟接收"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    async def _generate_data(self) -> None:
        """生成模拟心率数据"""
        import random
        
        while self._running:
            # 生成模拟心率
            bpm = self.base_bpm + random.randint(-self.variability, self.variability)
            
            # 生成模拟RR间期 (基于心率计算)
            avg_rr = int(60000 / bpm)  # 平均RR间期（毫秒）
            rr_intervals = [
                avg_rr + random.randint(-50, 50)
                for _ in range(random.randint(1, 3))
            ]
            
            reading = HeartRateReading(
                bpm=bpm,
                rr_intervals=rr_intervals,
                sensor_contact=True
            )
            
            self.buffer.add_reading(reading)
            
            if self.on_reading:
                self.on_reading(reading)
            
            # 每秒生成一次数据
            await asyncio.sleep(1.0)
    
    def get_buffer(self) -> HeartRateBuffer:
        return self.buffer
    
    def get_latest_reading(self) -> Optional[HeartRateReading]:
        if self.buffer.readings:
            return self.buffer.readings[-1]
        return None
    
    def get_average_bpm(self, seconds: int = 60) -> Optional[float]:
        if not self.buffer.readings:
            return None
        
        now = datetime.now()
        recent_readings = [
            r for r in self.buffer.readings
            if (now - r.timestamp).total_seconds() <= seconds
        ]
        
        if not recent_readings:
            return None
        
        return sum(r.bpm for r in recent_readings) / len(recent_readings)
