"""
灯光适配器扩展模块
Light Adapters Extension Module

支持更多主流智能灯品牌
"""
import asyncio
from abc import ABC
from typing import Optional, List, Dict, Any
from loguru import logger

from .light_controller import (
    BaseLightController, 
    RGBColor, 
    LightState, 
    LightPattern
)


class PhilipsHueAdapter(BaseLightController):
    """飞利浦 Hue 智能灯适配器
    
    通过 Hue Bridge API 控制飞利浦 Hue 灯具。
    需要先在 Hue Bridge 上注册应用获取 API key。
    """
    
    def __init__(
        self, 
        bridge_ip: str, 
        api_key: str,
        light_id: str = "1",
        name: str = "hue"
    ):
        """初始化 Hue 适配器
        
        Args:
            bridge_ip: Hue Bridge IP 地址
            api_key: Hue API 密钥（通过 Bridge 注册获取）
            light_id: 灯具 ID
            name: 设备名称
        """
        super().__init__(name)
        self.bridge_ip = bridge_ip
        self.api_key = api_key
        self.light_id = light_id
        self._base_url = f"http://{bridge_ip}/api/{api_key}"
        self._session = None
    
    async def connect(self) -> bool:
        """连接到 Hue Bridge"""
        try:
            import aiohttp
            self._session = aiohttp.ClientSession()
            
            # 验证连接
            async with self._session.get(
                f"{self._base_url}/lights/{self.light_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self._is_connected = True
                    logger.info(f"Connected to Hue light {self.light_id}")
                    return True
                else:
                    logger.error(f"Hue API returned status {response.status}")
                    return False
        except ImportError:
            raise ImportError("aiohttp library required: pip install aiohttp")
        except Exception as e:
            logger.error(f"Hue connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._session:
            await self._session.close()
            self._session = None
        self._is_connected = False
    
    def _rgb_to_xy(self, color: RGBColor) -> tuple:
        """RGB 转换为 Hue 的 xy 色彩空间"""
        # 归一化 RGB
        r = color.r / 255.0
        g = color.g / 255.0
        b = color.b / 255.0
        
        # Gamma 校正
        r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
        g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
        b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
        
        # RGB 转 XYZ
        X = r * 0.4124 + g * 0.3576 + b * 0.1805
        Y = r * 0.2126 + g * 0.7152 + b * 0.0722
        Z = r * 0.0193 + g * 0.1192 + b * 0.9505
        
        # XYZ 转 xy
        total = X + Y + Z
        if total == 0:
            return (0.3127, 0.3290)  # 白点
        
        x = X / total
        y = Y / total
        
        return (round(x, 4), round(y, 4))
    
    async def set_rgb(
        self,
        color: RGBColor,
        brightness: int,
        transition_ms: int = 3000
    ) -> bool:
        """设置 RGB 颜色和亮度"""
        if not self._is_connected or not self._session:
            return False
        
        try:
            xy = self._rgb_to_xy(color)
            # Hue 亮度范围 1-254
            bri = max(1, min(254, int(brightness * 2.54)))
            # Hue 过渡时间单位是 100ms
            transition = transition_ms // 100
            
            payload = {
                "on": True,
                "xy": list(xy),
                "bri": bri,
                "transitiontime": transition
            }
            
            async with self._session.put(
                f"{self._base_url}/lights/{self.light_id}/state",
                json=payload
            ) as response:
                if response.status == 200:
                    self._update_state(color, brightness, True, LightPattern.STATIC, transition_ms)
                    return True
                return False
        except Exception as e:
            logger.error(f"Hue set_rgb error: {e}")
            return False
    
    async def turn_on(self) -> bool:
        """开灯"""
        if not self._is_connected or not self._session:
            return False
        try:
            async with self._session.put(
                f"{self._base_url}/lights/{self.light_id}/state",
                json={"on": True}
            ) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def turn_off(self) -> bool:
        """关灯"""
        if not self._is_connected or not self._session:
            return False
        try:
            async with self._session.put(
                f"{self._base_url}/lights/{self.light_id}/state",
                json={"on": False}
            ) as response:
                return response.status == 200
        except Exception:
            return False


class MiHomeAdapter(BaseLightController):
    """小米米家智能灯适配器
    
    通过 miio 协议控制小米智能灯具。
    需要获取设备的 token。
    """
    
    def __init__(
        self,
        ip: str,
        token: str,
        name: str = "mihome"
    ):
        """初始化米家适配器
        
        Args:
            ip: 设备 IP 地址
            token: 设备 token（32位十六进制）
            name: 设备名称
        """
        super().__init__(name)
        self.ip = ip
        self.token = token
        self._device = None
    
    async def connect(self) -> bool:
        """连接设备"""
        try:
            from miio import Yeelight as MiioYeelight
            self._device = MiioYeelight(self.ip, self.token)
            # 测试连接
            info = self._device.info()
            if info:
                self._is_connected = True
                logger.info(f"Connected to Mi Home device: {info.model}")
                return True
            return False
        except ImportError:
            raise ImportError("python-miio library required: pip install python-miio")
        except Exception as e:
            logger.error(f"Mi Home connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        self._device = None
        self._is_connected = False
    
    async def set_rgb(
        self,
        color: RGBColor,
        brightness: int,
        transition_ms: int = 3000
    ) -> bool:
        """设置 RGB 颜色和亮度"""
        if not self._is_connected or not self._device:
            return False
        
        try:
            # 转换为 RGB 整数值
            rgb_int = (color.r << 16) + (color.g << 8) + color.b
            
            # 设置颜色和亮度
            self._device.set_rgb(rgb_int)
            self._device.set_brightness(brightness)
            
            self._update_state(color, brightness, True, LightPattern.STATIC, transition_ms)
            return True
        except Exception as e:
            logger.error(f"Mi Home set_rgb error: {e}")
            return False
    
    async def turn_on(self) -> bool:
        """开灯"""
        if not self._is_connected or not self._device:
            return False
        try:
            self._device.on()
            return True
        except Exception:
            return False
    
    async def turn_off(self) -> bool:
        """关灯"""
        if not self._is_connected or not self._device:
            return False
        try:
            self._device.off()
            return True
        except Exception:
            return False


class TuyaAdapter(BaseLightController):
    """涂鸦智能灯适配器
    
    支持大量使用涂鸦方案的智能灯品牌。
    需要获取设备的 device_id 和 local_key。
    """
    
    def __init__(
        self,
        device_id: str,
        ip: str,
        local_key: str,
        version: str = "3.3",
        name: str = "tuya"
    ):
        """初始化涂鸦适配器
        
        Args:
            device_id: 设备 ID
            ip: 设备 IP 地址
            local_key: 本地密钥
            version: 协议版本 (3.1/3.3/3.4)
            name: 设备名称
        """
        super().__init__(name)
        self.device_id = device_id
        self.ip = ip
        self.local_key = local_key
        self.version = version
        self._device = None
    
    async def connect(self) -> bool:
        """连接设备"""
        try:
            import tinytuya
            self._device = tinytuya.BulbDevice(
                self.device_id,
                self.ip,
                self.local_key
            )
            self._device.set_version(float(self.version))
            
            # 测试连接
            status = self._device.status()
            if status and 'dps' in status:
                self._is_connected = True
                logger.info(f"Connected to Tuya device: {self.device_id}")
                return True
            return False
        except ImportError:
            raise ImportError("tinytuya library required: pip install tinytuya")
        except Exception as e:
            logger.error(f"Tuya connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        self._device = None
        self._is_connected = False
    
    async def set_rgb(
        self,
        color: RGBColor,
        brightness: int,
        transition_ms: int = 3000
    ) -> bool:
        """设置 RGB 颜色和亮度"""
        if not self._is_connected or not self._device:
            return False
        
        try:
            # 涂鸦使用 HSV 格式
            import colorsys
            r, g, b = color.r / 255.0, color.g / 255.0, color.b / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            
            # 涂鸦 HSV 范围: H(0-360), S(0-1000), V(0-1000)
            self._device.set_hsv(
                h * 360,
                s * 1000,
                brightness * 10  # 0-100 -> 0-1000
            )
            
            self._update_state(color, brightness, True, LightPattern.STATIC, transition_ms)
            return True
        except Exception as e:
            logger.error(f"Tuya set_rgb error: {e}")
            return False
    
    async def turn_on(self) -> bool:
        """开灯"""
        if not self._is_connected or not self._device:
            return False
        try:
            self._device.turn_on()
            return True
        except Exception:
            return False
    
    async def turn_off(self) -> bool:
        """关灯"""
        if not self._is_connected or not self._device:
            return False
        try:
            self._device.turn_off()
            return True
        except Exception:
            return False


class DMXAdapter(BaseLightController):
    """DMX512 专业灯光适配器
    
    通过 USB-DMX 接口控制专业舞台灯光。
    适用于疗愈仓的专业灯光系统。
    """
    
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        start_channel: int = 1,
        name: str = "dmx"
    ):
        """初始化 DMX 适配器
        
        Args:
            port: 串口设备路径
            start_channel: 起始 DMX 通道
            name: 设备名称
        """
        super().__init__(name)
        self.port = port
        self.start_channel = start_channel
        self._dmx = None
    
    async def connect(self) -> bool:
        """连接 DMX 接口"""
        try:
            from dmx import DMXInterface
            self._dmx = DMXInterface(self.port)
            self._is_connected = True
            logger.info(f"Connected to DMX interface on {self.port}")
            return True
        except ImportError:
            raise ImportError("PyDMX library required: pip install PyDMX")
        except Exception as e:
            logger.error(f"DMX connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._dmx:
            self._dmx.close()
        self._dmx = None
        self._is_connected = False
    
    async def set_rgb(
        self,
        color: RGBColor,
        brightness: int,
        transition_ms: int = 3000
    ) -> bool:
        """设置 RGB 颜色和亮度"""
        if not self._is_connected or not self._dmx:
            return False
        
        try:
            # 应用亮度
            factor = brightness / 100.0
            r = int(color.r * factor)
            g = int(color.g * factor)
            b = int(color.b * factor)
            
            # 设置 DMX 通道 (假设 RGB 三通道)
            self._dmx.set_channel(self.start_channel, r)
            self._dmx.set_channel(self.start_channel + 1, g)
            self._dmx.set_channel(self.start_channel + 2, b)
            self._dmx.send()
            
            self._update_state(color, brightness, True, LightPattern.STATIC, transition_ms)
            return True
        except Exception as e:
            logger.error(f"DMX set_rgb error: {e}")
            return False
    
    async def turn_on(self) -> bool:
        """开灯（恢复上次颜色）"""
        if self._current_state:
            return await self.set_rgb(
                self._current_state.color,
                self._current_state.brightness
            )
        return await self.set_rgb(RGBColor(255, 255, 255), 100)
    
    async def turn_off(self) -> bool:
        """关灯"""
        return await self.set_rgb(RGBColor(0, 0, 0), 0)


# 适配器工厂函数扩展
def create_light_adapter(
    adapter_type: str,
    **kwargs
) -> BaseLightController:
    """创建灯光适配器实例
    
    Args:
        adapter_type: 适配器类型
            - "yeelight": Yeelight 智能灯
            - "hue": 飞利浦 Hue
            - "mihome": 小米米家
            - "tuya": 涂鸦智能
            - "dmx": DMX512 专业灯光
            - "mock": 模拟适配器（测试用）
        **kwargs: 适配器特定参数
        
    Returns:
        灯光适配器实例
    """
    from .light_controller import MockLightController, YeelightAdapter
    
    adapters = {
        "mock": lambda: MockLightController(kwargs.get("name", "mock")),
        "yeelight": lambda: YeelightAdapter(
            ip=kwargs["ip"],
            name=kwargs.get("name", "yeelight")
        ),
        "hue": lambda: PhilipsHueAdapter(
            bridge_ip=kwargs["bridge_ip"],
            api_key=kwargs["api_key"],
            light_id=kwargs.get("light_id", "1"),
            name=kwargs.get("name", "hue")
        ),
        "mihome": lambda: MiHomeAdapter(
            ip=kwargs["ip"],
            token=kwargs["token"],
            name=kwargs.get("name", "mihome")
        ),
        "tuya": lambda: TuyaAdapter(
            device_id=kwargs["device_id"],
            ip=kwargs["ip"],
            local_key=kwargs["local_key"],
            version=kwargs.get("version", "3.3"),
            name=kwargs.get("name", "tuya")
        ),
        "dmx": lambda: DMXAdapter(
            port=kwargs.get("port", "/dev/ttyUSB0"),
            start_channel=kwargs.get("start_channel", 1),
            name=kwargs.get("name", "dmx")
        )
    }
    
    if adapter_type not in adapters:
        raise ValueError(f"Unknown adapter type: {adapter_type}. "
                        f"Available: {list(adapters.keys())}")
    
    return adapters[adapter_type]()
