"""
灯光控制器模块
Light Controller Module

实现灯光控制的抽象层和具体适配器
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""
import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any


class LightPattern(str, Enum):
    """灯光模式"""
    STATIC = "static"      # 静态
    BREATH = "breath"      # 呼吸灯
    PULSE = "pulse"        # 脉冲


@dataclass
class RGBColor:
    """RGB颜色值"""
    r: int  # 0-255
    g: int  # 0-255
    b: int  # 0-255
    
    def __post_init__(self):
        """验证RGB值范围"""
        for name, value in [('r', self.r), ('g', self.g), ('b', self.b)]:
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be between 0 and 255, got {value}")
    
    def to_tuple(self) -> Tuple[int, int, int]:
        """转换为元组"""
        return (self.r, self.g, self.b)
    
    def to_hex(self) -> str:
        """转换为HEX格式"""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
    
    @classmethod
    def from_hex(cls, hex_color: str) -> 'RGBColor':
        """从HEX颜色值创建RGB颜色
        
        Args:
            hex_color: HEX颜色值，支持 #RRGGBB 或 RRGGBB 格式
            
        Returns:
            RGBColor实例
            
        Raises:
            ValueError: 如果HEX格式无效
        """
        # 移除#前缀
        hex_color = hex_color.lstrip('#')
        
        # 验证格式
        if not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
            raise ValueError(f"Invalid HEX color format: {hex_color}")
        
        # 解析RGB值
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        return cls(r=r, g=g, b=b)
    
    def get_hue(self) -> float:
        """计算色相角度 (0-360)"""
        r, g, b = self.r / 255.0, self.g / 255.0, self.b / 255.0
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        diff = max_c - min_c
        
        if diff == 0:
            return 0.0
        elif max_c == r:
            hue = 60 * (((g - b) / diff) % 6)
        elif max_c == g:
            hue = 60 * (((b - r) / diff) + 2)
        else:
            hue = 60 * (((r - g) / diff) + 4)
        
        return hue if hue >= 0 else hue + 360


@dataclass
class LightState:
    """灯光状态"""
    color: RGBColor
    brightness: int  # 0-100
    is_on: bool = True
    pattern: LightPattern = LightPattern.STATIC
    transition_ms: int = 0  # 过渡时间（毫秒）
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """验证亮度范围"""
        if not 0 <= self.brightness <= 100:
            raise ValueError(f"brightness must be between 0 and 100, got {self.brightness}")


@dataclass
class LightConfig:
    """灯光配置"""
    color: str  # HEX颜色值
    brightness: int  # 0-100
    transition: int = 3000  # 过渡时间（毫秒）
    pattern: Optional[str] = None  # breath/static/pulse


class BaseLightController(ABC):
    """灯光控制器基类
    
    定义灯光控制的抽象接口，所有具体的灯光适配器都需要继承此类。
    """
    
    def __init__(self, name: str = "light"):
        self.name = name
        self._current_state: Optional[LightState] = None
        self._is_connected: bool = False
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected
    
    @property
    def current_state(self) -> Optional[LightState]:
        """当前灯光状态"""
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
    async def set_rgb(
        self, 
        color: RGBColor, 
        brightness: int, 
        transition_ms: int = 3000
    ) -> bool:
        """设置RGB颜色和亮度
        
        Args:
            color: RGB颜色值
            brightness: 亮度 0-100
            transition_ms: 过渡时间（毫秒）
            
        Returns:
            是否设置成功
        """
        pass
    
    @abstractmethod
    async def turn_on(self) -> bool:
        """开灯"""
        pass
    
    @abstractmethod
    async def turn_off(self) -> bool:
        """关灯"""
        pass
    
    async def set_color(
        self,
        color: str,
        brightness: int,
        transition_ms: int = 3000
    ) -> bool:
        """设置灯光颜色和亮度（HEX格式）
        
        Args:
            color: HEX颜色值 (#RRGGBB 或 RRGGBB)
            brightness: 亮度 0-100
            transition_ms: 过渡时间（毫秒）
            
        Returns:
            是否设置成功
        """
        rgb = RGBColor.from_hex(color)
        return await self.set_rgb(rgb, brightness, transition_ms)
    
    def _update_state(
        self,
        color: RGBColor,
        brightness: int,
        is_on: bool = True,
        pattern: LightPattern = LightPattern.STATIC,
        transition_ms: int = 0
    ) -> None:
        """更新内部状态"""
        self._current_state = LightState(
            color=color,
            brightness=brightness,
            is_on=is_on,
            pattern=pattern,
            transition_ms=transition_ms
        )


class MockLightController(BaseLightController):
    """模拟灯光控制器（用于测试）"""
    
    def __init__(self, name: str = "mock_light"):
        super().__init__(name)
        self._command_history: List[Dict[str, Any]] = []
    
    @property
    def command_history(self) -> List[Dict[str, Any]]:
        """获取命令历史"""
        return self._command_history
    
    async def connect(self) -> bool:
        self._is_connected = True
        self._command_history.append({
            "action": "connect",
            "timestamp": datetime.now()
        })
        return True
    
    async def disconnect(self) -> None:
        self._is_connected = False
        self._command_history.append({
            "action": "disconnect",
            "timestamp": datetime.now()
        })
    
    async def set_rgb(
        self,
        color: RGBColor,
        brightness: int,
        transition_ms: int = 3000
    ) -> bool:
        if not self._is_connected:
            return False
        
        self._update_state(color, brightness, True, LightPattern.STATIC, transition_ms)
        self._command_history.append({
            "action": "set_rgb",
            "color": color.to_tuple(),
            "brightness": brightness,
            "transition_ms": transition_ms,
            "timestamp": datetime.now()
        })
        return True
    
    async def turn_on(self) -> bool:
        if not self._is_connected:
            return False
        
        if self._current_state:
            self._current_state.is_on = True
        self._command_history.append({
            "action": "turn_on",
            "timestamp": datetime.now()
        })
        return True
    
    async def turn_off(self) -> bool:
        if not self._is_connected:
            return False
        
        if self._current_state:
            self._current_state.is_on = False
        self._command_history.append({
            "action": "turn_off",
            "timestamp": datetime.now()
        })
        return True



class YeelightAdapter(BaseLightController):
    """Yeelight智能灯适配器
    
    通过WiFi协议控制Yeelight智能灯。
    Requirements: 7.6
    """
    
    def __init__(self, ip: str, name: str = "yeelight"):
        """初始化Yeelight适配器
        
        Args:
            ip: Yeelight设备的IP地址
            name: 设备名称
        """
        super().__init__(name)
        self.ip = ip
        self._bulb = None
    
    async def connect(self) -> bool:
        """连接Yeelight设备"""
        try:
            from yeelight import Bulb
            self._bulb = Bulb(self.ip)
            # 尝试获取设备属性以验证连接
            self._bulb.get_properties()
            self._is_connected = True
            return True
        except ImportError:
            raise ImportError(
                "yeelight library not installed. "
                "Install with: pip install yeelight"
            )
        except Exception:
            self._is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        self._bulb = None
        self._is_connected = False
    
    async def set_rgb(
        self,
        color: RGBColor,
        brightness: int,
        transition_ms: int = 3000
    ) -> bool:
        """设置RGB颜色和亮度"""
        if not self._is_connected or not self._bulb:
            return False
        
        try:
            # Yeelight使用duration参数（毫秒）
            self._bulb.set_rgb(
                color.r, color.g, color.b,
                duration=transition_ms
            )
            self._bulb.set_brightness(brightness, duration=transition_ms)
            self._update_state(color, brightness, True, LightPattern.STATIC, transition_ms)
            return True
        except Exception:
            return False
    
    async def turn_on(self) -> bool:
        """开灯"""
        if not self._is_connected or not self._bulb:
            return False
        
        try:
            self._bulb.turn_on()
            if self._current_state:
                self._current_state.is_on = True
            return True
        except Exception:
            return False
    
    async def turn_off(self) -> bool:
        """关灯"""
        if not self._is_connected or not self._bulb:
            return False
        
        try:
            self._bulb.turn_off()
            if self._current_state:
                self._current_state.is_on = False
            return True
        except Exception:
            return False
    
    @staticmethod
    async def discover_devices(timeout: float = 5.0) -> List[Dict[str, str]]:
        """发现局域网内的Yeelight设备
        
        Args:
            timeout: 发现超时时间（秒）
            
        Returns:
            发现的设备列表，每个设备包含ip和capabilities
        """
        try:
            from yeelight import discover_bulbs
            bulbs = discover_bulbs(timeout=timeout)
            return [
                {
                    "ip": bulb.get("ip", ""),
                    "port": bulb.get("port", 55443),
                    "capabilities": bulb.get("capabilities", {})
                }
                for bulb in bulbs
            ]
        except ImportError:
            raise ImportError(
                "yeelight library not installed. "
                "Install with: pip install yeelight"
            )
        except Exception:
            return []



class LightTransitionController:
    """灯光渐变过渡控制器
    
    实现平滑的灯光过渡效果和呼吸灯模式。
    Requirements: 7.3, 7.4
    """
    
    def __init__(self, light_controller: BaseLightController):
        """初始化过渡控制器
        
        Args:
            light_controller: 灯光控制器实例
        """
        self.controller = light_controller
        self._breath_task: Optional[asyncio.Task] = None
        self._is_breathing: bool = False
    
    @property
    def is_breathing(self) -> bool:
        """是否正在执行呼吸灯模式"""
        return self._is_breathing
    
    async def smooth_transition(
        self,
        target_color: RGBColor,
        target_brightness: int,
        duration_ms: int = 3000,
        steps: int = 30
    ) -> bool:
        """平滑过渡到目标颜色和亮度
        
        Args:
            target_color: 目标颜色
            target_brightness: 目标亮度 0-100
            duration_ms: 过渡时间（毫秒）
            steps: 过渡步数
            
        Returns:
            是否过渡成功
        """
        if not self.controller.is_connected:
            return False
        
        current_state = self.controller.current_state
        if current_state is None:
            # 如果没有当前状态，直接设置目标状态
            return await self.controller.set_rgb(
                target_color, target_brightness, duration_ms
            )
        
        # 计算每步的颜色和亮度变化
        start_color = current_state.color
        start_brightness = current_state.brightness
        
        step_delay = duration_ms / steps / 1000  # 转换为秒
        
        for i in range(1, steps + 1):
            progress = i / steps
            
            # 线性插值计算中间颜色
            r = int(start_color.r + (target_color.r - start_color.r) * progress)
            g = int(start_color.g + (target_color.g - start_color.g) * progress)
            b = int(start_color.b + (target_color.b - start_color.b) * progress)
            
            # 线性插值计算中间亮度
            brightness = int(
                start_brightness + (target_brightness - start_brightness) * progress
            )
            
            intermediate_color = RGBColor(r=r, g=g, b=b)
            
            # 设置中间状态（使用较短的过渡时间）
            step_transition = int(step_delay * 1000)
            success = await self.controller.set_rgb(
                intermediate_color, brightness, step_transition
            )
            
            if not success:
                return False
            
            await asyncio.sleep(step_delay)
        
        return True
    
    async def start_breath_mode(
        self,
        color: RGBColor,
        min_brightness: int = 30,
        max_brightness: int = 80,
        period_ms: int = 4000
    ) -> None:
        """启动呼吸灯模式
        
        Args:
            color: 灯光颜色
            min_brightness: 最低亮度 0-100
            max_brightness: 最高亮度 0-100
            period_ms: 呼吸周期（毫秒）
        """
        # 停止现有的呼吸灯任务
        await self.stop_breath_mode()
        
        self._is_breathing = True
        self._breath_task = asyncio.create_task(
            self._breath_loop(color, min_brightness, max_brightness, period_ms)
        )
    
    async def stop_breath_mode(self) -> None:
        """停止呼吸灯模式"""
        self._is_breathing = False
        if self._breath_task and not self._breath_task.done():
            self._breath_task.cancel()
            try:
                await self._breath_task
            except asyncio.CancelledError:
                pass
        self._breath_task = None
    
    async def _breath_loop(
        self,
        color: RGBColor,
        min_brightness: int,
        max_brightness: int,
        period_ms: int
    ) -> None:
        """呼吸灯循环
        
        实现平滑的亮度渐变，模拟呼吸效果。
        """
        half_period = period_ms / 2 / 1000  # 半周期（秒）
        
        while self._is_breathing:
            try:
                # 渐亮（吸气）
                await self.controller.set_rgb(
                    color, max_brightness, int(half_period * 1000)
                )
                await asyncio.sleep(half_period)
                
                if not self._is_breathing:
                    break
                
                # 渐暗（呼气）
                await self.controller.set_rgb(
                    color, min_brightness, int(half_period * 1000)
                )
                await asyncio.sleep(half_period)
                
            except asyncio.CancelledError:
                break
            except Exception:
                # 发生错误时停止呼吸灯
                self._is_breathing = False
                break
    
    async def pulse_effect(
        self,
        color: RGBColor,
        brightness: int = 80,
        pulse_count: int = 3,
        pulse_duration_ms: int = 500
    ) -> bool:
        """脉冲效果
        
        Args:
            color: 灯光颜色
            brightness: 亮度 0-100
            pulse_count: 脉冲次数
            pulse_duration_ms: 每次脉冲时长（毫秒）
            
        Returns:
            是否执行成功
        """
        if not self.controller.is_connected:
            return False
        
        half_duration = pulse_duration_ms / 2 / 1000
        
        for _ in range(pulse_count):
            # 亮
            await self.controller.set_rgb(color, brightness, int(half_duration * 1000))
            await asyncio.sleep(half_duration)
            
            # 暗
            await self.controller.set_rgb(color, 10, int(half_duration * 1000))
            await asyncio.sleep(half_duration)
        
        # 恢复正常亮度
        await self.controller.set_rgb(color, brightness, 500)
        return True



class EmotionLightMapper:
    """情绪-灯光映射器
    
    根据用户情绪状态选择合适的灯光颜色。
    Requirements: 7.5
    
    色相范围说明：
    - 焦虑情绪：蓝绿色系 (150-210度)
    - 开心情绪：暖黄色系 (30-60度)
    - 难过情绪：柔和蓝色 (200-240度)
    - 愤怒情绪：冷色调 (180-220度)
    - 疲惫情绪：暖橙色系 (20-40度)
    - 恐惧情绪：柔和紫色 (260-290度)
    - 惊讶情绪：明亮白色
    - 厌恶情绪：中性灰绿 (120-150度)
    - 中性情绪：自然白光
    """
    
    # 情绪到颜色的映射表
    EMOTION_COLOR_MAP: Dict[str, Dict[str, Any]] = {
        "anxious": {
            "color": "#4ECDC4",  # 蓝绿色 (色相约175度)
            "brightness": 60,
            "description": "蓝绿色系，有助于缓解焦虑",
            "hue_range": (150, 210)  # 蓝绿色系范围
        },
        "happy": {
            "color": "#FFD93D",  # 暖黄色 (色相约50度)
            "brightness": 75,
            "description": "暖黄色，增强愉悦感",
            "hue_range": (30, 60)
        },
        "sad": {
            "color": "#6C9BCF",  # 柔和蓝色 (色相约215度)
            "brightness": 50,
            "description": "柔和蓝色，提供安慰",
            "hue_range": (200, 240)
        },
        "angry": {
            "color": "#5DADE2",  # 冷蓝色 (色相约200度)
            "brightness": 55,
            "description": "冷色调，帮助平静",
            "hue_range": (180, 220)
        },
        "tired": {
            "color": "#F5B041",  # 暖橙色 (色相约35度)
            "brightness": 45,
            "description": "暖橙色，温暖舒适",
            "hue_range": (20, 40)
        },
        "fearful": {
            "color": "#BB8FCE",  # 柔和紫色 (色相约280度)
            "brightness": 50,
            "description": "柔和紫色，提供安全感",
            "hue_range": (260, 290)
        },
        "surprised": {
            "color": "#F8F9FA",  # 明亮白色
            "brightness": 70,
            "description": "明亮白光，保持清醒",
            "hue_range": None  # 白色无特定色相
        },
        "disgusted": {
            "color": "#82E0AA",  # 中性灰绿 (色相约140度)
            "brightness": 55,
            "description": "中性灰绿，平衡情绪",
            "hue_range": (120, 150)
        },
        "neutral": {
            "color": "#FFF5E6",  # 自然暖白
            "brightness": 65,
            "description": "自然白光，舒适放松",
            "hue_range": None  # 白色无特定色相
        }
    }
    
    # 焦虑情绪的备选颜色（都在蓝绿色系范围内）
    ANXIOUS_COLORS: List[str] = [
        "#4ECDC4",  # 青绿色 (175度)
        "#48C9B0",  # 薄荷绿 (165度)
        "#5DADE2",  # 天蓝色 (200度)
        "#45B7D1",  # 蓝绿色 (190度)
        "#3498DB",  # 蓝色 (210度)
    ]
    
    def __init__(self):
        self._custom_mappings: Dict[str, Dict[str, Any]] = {}
    
    def get_light_config(self, emotion: str) -> LightConfig:
        """根据情绪获取灯光配置
        
        Args:
            emotion: 情绪类别
            
        Returns:
            灯光配置
        """
        emotion_lower = emotion.lower()
        
        # 优先使用自定义映射
        if emotion_lower in self._custom_mappings:
            mapping = self._custom_mappings[emotion_lower]
        elif emotion_lower in self.EMOTION_COLOR_MAP:
            mapping = self.EMOTION_COLOR_MAP[emotion_lower]
        else:
            # 默认使用中性配置
            mapping = self.EMOTION_COLOR_MAP["neutral"]
        
        return LightConfig(
            color=mapping["color"],
            brightness=mapping["brightness"],
            transition=3000,
            pattern="static"
        )
    
    def get_anxious_color(self, variation: int = 0) -> RGBColor:
        """获取焦虑情绪对应的蓝绿色系颜色
        
        Args:
            variation: 颜色变体索引 (0-4)
            
        Returns:
            蓝绿色系的RGB颜色
        """
        color_hex = self.ANXIOUS_COLORS[variation % len(self.ANXIOUS_COLORS)]
        return RGBColor.from_hex(color_hex)
    
    def is_anxious_color_valid(self, color: RGBColor) -> bool:
        """验证颜色是否在焦虑情绪的蓝绿色系范围内
        
        焦虑情绪应使用色相在150-210度范围内的颜色。
        
        Args:
            color: RGB颜色
            
        Returns:
            是否在有效范围内
        """
        hue = color.get_hue()
        return 150 <= hue <= 210
    
    def set_custom_mapping(
        self,
        emotion: str,
        color: str,
        brightness: int,
        description: str = ""
    ) -> None:
        """设置自定义情绪-颜色映射
        
        Args:
            emotion: 情绪类别
            color: HEX颜色值
            brightness: 亮度 0-100
            description: 描述
        """
        self._custom_mappings[emotion.lower()] = {
            "color": color,
            "brightness": brightness,
            "description": description
        }
    
    def get_all_mappings(self) -> Dict[str, Dict[str, Any]]:
        """获取所有情绪-颜色映射"""
        result = dict(self.EMOTION_COLOR_MAP)
        result.update(self._custom_mappings)
        return result


class LightControllerManager:
    """灯光控制器管理器
    
    管理多个灯光设备，提供统一的控制接口。
    """
    
    def __init__(self):
        self.controllers: Dict[str, BaseLightController] = {}
        self.emotion_mapper = EmotionLightMapper()
        self._transition_controllers: Dict[str, LightTransitionController] = {}
    
    def add_controller(self, name: str, controller: BaseLightController) -> None:
        """添加灯光控制器"""
        self.controllers[name] = controller
        self._transition_controllers[name] = LightTransitionController(controller)
    
    def remove_controller(self, name: str) -> None:
        """移除灯光控制器"""
        if name in self.controllers:
            del self.controllers[name]
        if name in self._transition_controllers:
            del self._transition_controllers[name]
    
    async def connect_all(self) -> Dict[str, bool]:
        """连接所有设备"""
        results = {}
        for name, controller in self.controllers.items():
            results[name] = await controller.connect()
        return results
    
    async def disconnect_all(self) -> None:
        """断开所有设备"""
        for controller in self.controllers.values():
            await controller.disconnect()
    
    async def set_all_lights(
        self,
        color: str,
        brightness: int,
        transition_ms: int = 3000
    ) -> Dict[str, bool]:
        """设置所有灯光
        
        Args:
            color: HEX颜色值
            brightness: 亮度 0-100
            transition_ms: 过渡时间（毫秒）
            
        Returns:
            各设备的设置结果
        """
        results = {}
        tasks = []
        
        for name, controller in self.controllers.items():
            task = controller.set_color(color, brightness, transition_ms)
            tasks.append((name, task))
        
        for name, task in tasks:
            results[name] = await task
        
        return results
    
    async def apply_emotion_lighting(
        self,
        emotion: str,
        transition_ms: int = 3000
    ) -> Dict[str, bool]:
        """根据情绪应用灯光设置
        
        Args:
            emotion: 情绪类别
            transition_ms: 过渡时间（毫秒）
            
        Returns:
            各设备的设置结果
        """
        config = self.emotion_mapper.get_light_config(emotion)
        return await self.set_all_lights(
            config.color,
            config.brightness,
            transition_ms
        )
    
    async def start_breath_mode_all(
        self,
        color: str,
        min_brightness: int = 30,
        max_brightness: int = 80,
        period_ms: int = 4000
    ) -> None:
        """所有灯光启动呼吸灯模式"""
        rgb_color = RGBColor.from_hex(color)
        for tc in self._transition_controllers.values():
            await tc.start_breath_mode(
                rgb_color, min_brightness, max_brightness, period_ms
            )
    
    async def stop_breath_mode_all(self) -> None:
        """停止所有灯光的呼吸灯模式"""
        for tc in self._transition_controllers.values():
            await tc.stop_breath_mode()
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有设备状态"""
        status = {}
        for name, controller in self.controllers.items():
            state = controller.current_state
            status[name] = {
                "connected": controller.is_connected,
                "state": {
                    "color": state.color.to_hex() if state else None,
                    "brightness": state.brightness if state else None,
                    "is_on": state.is_on if state else None,
                    "pattern": state.pattern.value if state else None
                } if state else None
            }
        return status


def create_light_controller(
    controller_type: str = "mock",
    **kwargs
) -> BaseLightController:
    """创建灯光控制器实例
    
    Args:
        controller_type: 控制器类型 ("mock", "yeelight")
        **kwargs: 控制器特定参数
        
    Returns:
        灯光控制器实例
    """
    if controller_type == "mock":
        return MockLightController(kwargs.get("name", "mock_light"))
    elif controller_type == "yeelight":
        ip = kwargs.get("ip")
        if not ip:
            raise ValueError("Yeelight controller requires 'ip' parameter")
        return YeelightAdapter(ip, kwargs.get("name", "yeelight"))
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")
