"""
设备配置加载器
Device Configuration Loader

加载和管理硬件设备配置
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from loguru import logger

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed. Install with: pip install pyyaml")


@dataclass
class HeartRateConfig:
    """心率设备配置"""
    enabled: bool = True
    type: str = "mock"
    device_address: str = ""
    device_name_keywords: List[str] = field(default_factory=lambda: ["Polar", "HRM", "Heart"])
    scan_timeout: int = 10
    buffer_size: int = 600
    mock_base_bpm: int = 72
    mock_variability: int = 8


@dataclass
class LightDeviceConfig:
    """单个灯光设备配置"""
    name: str
    type: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LightsConfig:
    """灯光系统配置"""
    enabled: bool = True
    devices: List[LightDeviceConfig] = field(default_factory=list)
    default_brightness: int = 60
    default_transition_ms: int = 3000
    breath_min_brightness: int = 30
    breath_max_brightness: int = 80
    breath_period_ms: int = 4000


@dataclass
class ChairConfig:
    """座椅配置"""
    enabled: bool = True
    type: str = "mock"
    device_address: str = ""
    device_name_keywords: List[str] = field(default_factory=lambda: ["Chair", "Massage"])
    service_uuid: str = "0000fff0-0000-1000-8000-00805f9b34fb"
    control_char_uuid: str = "0000fff1-0000-1000-8000-00805f9b34fb"
    scan_timeout: int = 10
    default_mode: str = "gentle"
    default_intensity: int = 5


@dataclass
class ScentConfig:
    """香薰配置"""
    enabled: bool = True
    type: str = "mock"
    wifi_ip: str = ""
    wifi_port: int = 80
    wifi_api_path: str = "/api"
    tuya_device_id: str = ""
    tuya_ip: str = ""
    tuya_local_key: str = ""
    default_scent_type: str = "lavender"
    default_intensity: int = 5


@dataclass
class AudioConfig:
    """音频配置"""
    enabled: bool = True
    output_device: str = ""
    default_volume: int = 50
    fade_duration_ms: int = 2000
    surround_sound: bool = False


@dataclass
class GlobalConfig:
    """全局配置"""
    connection_timeout: int = 10
    reconnect_interval: int = 30
    enable_mock_fallback: bool = True
    log_level: str = "INFO"


@dataclass
class DiscoveryConfig:
    """设备发现配置"""
    auto_discover: bool = True
    timeout: int = 15
    ble_enabled: bool = True
    ble_scan_duration: int = 10
    wifi_enabled: bool = True
    yeelight_discovery: bool = True
    mdns_discovery: bool = True


@dataclass
class DeviceConfiguration:
    """完整设备配置"""
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    heart_rate: HeartRateConfig = field(default_factory=HeartRateConfig)
    lights: LightsConfig = field(default_factory=LightsConfig)
    chair: ChairConfig = field(default_factory=ChairConfig)
    scent: ScentConfig = field(default_factory=ScentConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)


class DeviceConfigLoader:
    """设备配置加载器"""
    
    DEFAULT_CONFIG_PATHS = [
        "config/devices.yaml",
        "config/devices.yml",
        "../config/devices.yaml",
        "devices.yaml",
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置加载器
        
        Args:
            config_path: 配置文件路径，None 则自动查找
        """
        self.config_path = config_path
        self._config: Optional[DeviceConfiguration] = None
        self._raw_config: Dict[str, Any] = {}
    
    def find_config_file(self) -> Optional[str]:
        """查找配置文件
        
        Returns:
            配置文件路径，未找到返回 None
        """
        if self.config_path and os.path.exists(self.config_path):
            return self.config_path
        
        # 从环境变量获取
        env_path = os.environ.get("HEALING_POD_DEVICE_CONFIG")
        if env_path and os.path.exists(env_path):
            return env_path
        
        # 搜索默认路径
        for path in self.DEFAULT_CONFIG_PATHS:
            if os.path.exists(path):
                return path
        
        return None
    
    def load(self) -> DeviceConfiguration:
        """加载配置
        
        Returns:
            设备配置对象
        """
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not available, using default configuration")
            self._config = DeviceConfiguration()
            return self._config
        
        config_file = self.find_config_file()
        
        if not config_file:
            logger.info("No device configuration file found, using defaults")
            self._config = DeviceConfiguration()
            return self._config
        
        try:
            logger.info(f"Loading device configuration from: {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f) or {}
            
            self._config = self._parse_config(self._raw_config)
            logger.info("Device configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration")
            self._config = DeviceConfiguration()
        
        return self._config
    
    def _parse_config(self, raw: Dict[str, Any]) -> DeviceConfiguration:
        """解析配置字典
        
        Args:
            raw: 原始配置字典
            
        Returns:
            设备配置对象
        """
        config = DeviceConfiguration()
        
        # 解析全局配置
        if "global" in raw:
            g = raw["global"]
            config.global_config = GlobalConfig(
                connection_timeout=g.get("connection_timeout", 10),
                reconnect_interval=g.get("reconnect_interval", 30),
                enable_mock_fallback=g.get("enable_mock_fallback", True),
                log_level=g.get("log_level", "INFO"),
            )
        
        # 解析心率配置
        if "heart_rate" in raw:
            hr = raw["heart_rate"]
            ble = hr.get("ble", {})
            mock = hr.get("mock", {})
            config.heart_rate = HeartRateConfig(
                enabled=hr.get("enabled", True),
                type=hr.get("type", "mock"),
                device_address=ble.get("device_address", ""),
                device_name_keywords=ble.get("device_name_keywords", ["Polar", "HRM"]),
                scan_timeout=ble.get("scan_timeout", 10),
                buffer_size=ble.get("buffer_size", 600),
                mock_base_bpm=mock.get("base_bpm", 72),
                mock_variability=mock.get("variability", 8),
            )
        
        # 解析灯光配置
        if "lights" in raw:
            lights = raw["lights"]
            defaults = lights.get("defaults", {})
            breath = defaults.get("breath", {})
            
            devices = []
            for dev in lights.get("devices", []):
                if dev.get("enabled", True):
                    devices.append(LightDeviceConfig(
                        name=dev.get("name", "light"),
                        type=dev.get("type", "mock"),
                        enabled=dev.get("enabled", True),
                        config=dev.get("config", {}),
                    ))
            
            config.lights = LightsConfig(
                enabled=lights.get("enabled", True),
                devices=devices,
                default_brightness=defaults.get("brightness", 60),
                default_transition_ms=defaults.get("transition_ms", 3000),
                breath_min_brightness=breath.get("min_brightness", 30),
                breath_max_brightness=breath.get("max_brightness", 80),
                breath_period_ms=breath.get("period_ms", 4000),
            )
        
        # 解析座椅配置
        if "chair" in raw:
            chair = raw["chair"]
            ble = chair.get("ble", {})
            defaults = chair.get("defaults", {})
            config.chair = ChairConfig(
                enabled=chair.get("enabled", True),
                type=chair.get("type", "mock"),
                device_address=ble.get("device_address", ""),
                device_name_keywords=ble.get("device_name_keywords", ["Chair", "Massage"]),
                service_uuid=ble.get("service_uuid", "0000fff0-0000-1000-8000-00805f9b34fb"),
                control_char_uuid=ble.get("control_char_uuid", "0000fff1-0000-1000-8000-00805f9b34fb"),
                scan_timeout=ble.get("scan_timeout", 10),
                default_mode=defaults.get("mode", "gentle"),
                default_intensity=defaults.get("intensity", 5),
            )
        
        # 解析香薰配置
        if "scent" in raw:
            scent = raw["scent"]
            wifi = scent.get("wifi", {})
            tuya = scent.get("tuya", {})
            defaults = scent.get("defaults", {})
            config.scent = ScentConfig(
                enabled=scent.get("enabled", True),
                type=scent.get("type", "mock"),
                wifi_ip=wifi.get("ip", ""),
                wifi_port=wifi.get("port", 80),
                wifi_api_path=wifi.get("api_path", "/api"),
                tuya_device_id=tuya.get("device_id", ""),
                tuya_ip=tuya.get("ip", ""),
                tuya_local_key=tuya.get("local_key", ""),
                default_scent_type=defaults.get("scent_type", "lavender"),
                default_intensity=defaults.get("intensity", 5),
            )
        
        # 解析音频配置
        if "audio" in raw:
            audio = raw["audio"]
            config.audio = AudioConfig(
                enabled=audio.get("enabled", True),
                output_device=audio.get("output_device", ""),
                default_volume=audio.get("default_volume", 50),
                fade_duration_ms=audio.get("fade_duration_ms", 2000),
                surround_sound=audio.get("surround_sound", False),
            )
        
        # 解析设备发现配置
        if "discovery" in raw:
            disc = raw["discovery"]
            ble = disc.get("ble", {})
            wifi = disc.get("wifi", {})
            config.discovery = DiscoveryConfig(
                auto_discover=disc.get("auto_discover", True),
                timeout=disc.get("timeout", 15),
                ble_enabled=ble.get("enabled", True) if isinstance(ble, dict) else True,
                ble_scan_duration=ble.get("scan_duration", 10) if isinstance(ble, dict) else 10,
                wifi_enabled=wifi.get("enabled", True) if isinstance(wifi, dict) else True,
                yeelight_discovery=wifi.get("yeelight_discovery", True) if isinstance(wifi, dict) else True,
                mdns_discovery=wifi.get("mdns_discovery", True) if isinstance(wifi, dict) else True,
            )
        
        return config
    
    @property
    def config(self) -> DeviceConfiguration:
        """获取配置（自动加载）"""
        if self._config is None:
            self.load()
        return self._config
    
    def get_raw_config(self) -> Dict[str, Any]:
        """获取原始配置字典"""
        return self._raw_config
    
    def reload(self) -> DeviceConfiguration:
        """重新加载配置"""
        self._config = None
        self._raw_config = {}
        return self.load()


# 全局配置实例
_config_loader: Optional[DeviceConfigLoader] = None


def get_device_config() -> DeviceConfiguration:
    """获取设备配置（单例）
    
    Returns:
        设备配置对象
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = DeviceConfigLoader()
    return _config_loader.config


def reload_device_config() -> DeviceConfiguration:
    """重新加载设备配置
    
    Returns:
        设备配置对象
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = DeviceConfigLoader()
    return _config_loader.reload()


def set_config_path(path: str) -> None:
    """设置配置文件路径
    
    Args:
        path: 配置文件路径
    """
    global _config_loader
    _config_loader = DeviceConfigLoader(path)
