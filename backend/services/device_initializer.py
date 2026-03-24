"""
设备初始化器模块
Device Initializer Module

根据配置文件自动创建和初始化硬件设备
"""
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from loguru import logger

from .device_config import (
    DeviceConfiguration,
    get_device_config,
    LightDeviceConfig,
)
from .device_manager import (
    HardwareDeviceManager,
    DeviceType,
    ConnectionStatus,
    DeviceInfo,
    ConnectionProtocol,
    get_device_manager,
)


class DeviceInitializer:
    """设备初始化器
    
    根据配置文件自动创建和初始化所有硬件设备
    """
    
    def __init__(self, config: Optional[DeviceConfiguration] = None):
        """初始化设备初始化器
        
        Args:
            config: 设备配置，None 则自动加载
        """
        self._config = config or get_device_config()
        self._device_manager = get_device_manager()
        
        # 设备控制器实例
        self._heart_rate_controller = None
        self._light_controllers: Dict[str, Any] = {}
        self._chair_controller = None
        self._scent_controller = None
        self._audio_controller = None
        
        # 初始化结果
        self._init_results: Dict[str, bool] = {}
    
    async def initialize_all(self) -> Dict[str, bool]:
        """初始化所有配置的设备
        
        Returns:
            各设备的初始化结果
        """
        logger.info("开始初始化硬件设备...")
        
        results = {}
        
        # 并行初始化各类设备
        tasks = []
        
        if self._config.heart_rate.enabled:
            tasks.append(("heart_rate", self._init_heart_rate()))
        
        if self._config.lights.enabled:
            tasks.append(("lights", self._init_lights()))
        
        if self._config.chair.enabled:
            tasks.append(("chair", self._init_chair()))
        
        if self._config.scent.enabled:
            tasks.append(("scent", self._init_scent()))
        
        if self._config.audio.enabled:
            tasks.append(("audio", self._init_audio()))
        
        # 执行所有初始化任务
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
                self._init_results[name] = result
            except Exception as e:
                logger.error(f"初始化 {name} 失败: {e}")
                results[name] = False
                self._init_results[name] = False
        
        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        logger.info(f"设备初始化完成: {success_count}/{total_count} 成功")
        
        return results

    async def ensure_chair_controller(self) -> Optional[Any]:
        """Ensure the chair controller is initialized."""
        if self._chair_controller is not None:
            self._init_results["chair"] = True
            return self._chair_controller

        try:
            initialized = await self._init_chair()
        except Exception as e:
            logger.error(f"Chair-only initialization failed: {e}")
            initialized = False

        self._init_results["chair"] = initialized
        return self._chair_controller if initialized else None
    
    async def _init_heart_rate(self) -> bool:
        """初始化心率设备"""
        hr_config = self._config.heart_rate
        
        try:
            if hr_config.type == "ble":
                from .ble_heart_rate import BLEHeartRateReceiver
                
                self._heart_rate_controller = BLEHeartRateReceiver(
                    device_address=hr_config.device_address or None,
                    device_name_keywords=hr_config.device_name_keywords,
                    scan_timeout=hr_config.scan_timeout,
                )
                
                # 尝试连接
                connected = await self._heart_rate_controller.connect()
                
                if connected:
                    logger.info("心率设备 (BLE) 连接成功")
                    return True
                elif self._config.global_config.enable_mock_fallback:
                    logger.warning("心率设备连接失败，使用模拟模式")
                    return await self._init_mock_heart_rate()
                else:
                    return False
            else:
                # 使用模拟模式
                return await self._init_mock_heart_rate()
                
        except ImportError as e:
            logger.warning(f"心率模块导入失败: {e}")
            if self._config.global_config.enable_mock_fallback:
                return await self._init_mock_heart_rate()
            return False
        except Exception as e:
            logger.error(f"心率设备初始化错误: {e}")
            if self._config.global_config.enable_mock_fallback:
                return await self._init_mock_heart_rate()
            return False
    
    async def _init_mock_heart_rate(self) -> bool:
        """初始化模拟心率设备"""
        try:
            from .ble_heart_rate import MockBLEHeartRateReceiver
            
            hr_config = self._config.heart_rate
            self._heart_rate_controller = MockBLEHeartRateReceiver(
                base_bpm=hr_config.mock_base_bpm,
                variability=hr_config.mock_variability,
            )
            await self._heart_rate_controller.connect()
            logger.info("心率设备 (模拟) 初始化成功")
            return True
        except Exception as e:
            logger.error(f"模拟心率设备初始化失败: {e}")
            return False
    
    async def _init_lights(self) -> bool:
        """初始化灯光设备"""
        lights_config = self._config.lights
        
        if not lights_config.devices:
            logger.info("未配置灯光设备，使用模拟模式")
            return await self._init_mock_light()
        
        success_count = 0
        
        for device_config in lights_config.devices:
            if not device_config.enabled:
                continue
            
            try:
                controller = await self._create_light_controller(device_config)
                if controller:
                    connected = await controller.connect()
                    if connected:
                        self._light_controllers[device_config.name] = controller
                        success_count += 1
                        logger.info(f"灯光设备 '{device_config.name}' ({device_config.type}) 连接成功")
                    else:
                        logger.warning(f"灯光设备 '{device_config.name}' 连接失败")
            except Exception as e:
                logger.error(f"灯光设备 '{device_config.name}' 初始化错误: {e}")
        
        # 如果没有成功连接任何灯光，使用模拟模式
        if success_count == 0 and self._config.global_config.enable_mock_fallback:
            logger.warning("所有灯光设备连接失败，使用模拟模式")
            return await self._init_mock_light()
        
        return success_count > 0
    
    async def _create_light_controller(self, config: LightDeviceConfig) -> Optional[Any]:
        """根据配置创建灯光控制器"""
        try:
            from .light_adapters import create_light_adapter
            
            # 构建适配器参数
            kwargs = {"name": config.name, **config.config}
            
            return create_light_adapter(config.type, **kwargs)
        except Exception as e:
            logger.error(f"创建灯光控制器失败 ({config.type}): {e}")
            return None
    
    async def _init_mock_light(self) -> bool:
        """初始化模拟灯光设备"""
        try:
            from .light_controller import MockLightController
            
            mock_light = MockLightController("mock_light")
            await mock_light.connect()
            self._light_controllers["mock_light"] = mock_light
            logger.info("灯光设备 (模拟) 初始化成功")
            return True
        except Exception as e:
            logger.error(f"模拟灯光设备初始化失败: {e}")
            return False
    
    async def _init_chair(self) -> bool:
        """初始化座椅设备"""
        chair_config = self._config.chair
        
        try:
            if chair_config.type == "ble":
                from .chair_controller import BLEChairController
                
                self._chair_controller = BLEChairController(
                    device_address=chair_config.device_address or None,
                    service_uuid=chair_config.service_uuid,
                    control_char_uuid=chair_config.control_char_uuid,
                )
                
                connected = await self._chair_controller.connect()
                
                if connected:
                    logger.info("座椅设备 (BLE) 连接成功")
                    return True
                elif self._config.global_config.enable_mock_fallback:
                    logger.warning("座椅设备连接失败，使用模拟模式")
                    return await self._init_mock_chair()
                else:
                    return False
            else:
                return await self._init_mock_chair()
                
        except ImportError as e:
            logger.warning(f"座椅模块导入失败: {e}")
            if self._config.global_config.enable_mock_fallback:
                return await self._init_mock_chair()
            return False
        except Exception as e:
            logger.error(f"座椅设备初始化错误: {e}")
            if self._config.global_config.enable_mock_fallback:
                return await self._init_mock_chair()
            return False
    
    async def _init_mock_chair(self) -> bool:
        """初始化模拟座椅设备"""
        try:
            from .chair_controller import MockChairController
            
            self._chair_controller = MockChairController()
            await self._chair_controller.connect()
            logger.info("座椅设备 (模拟) 初始化成功")
            return True
        except Exception as e:
            logger.error(f"模拟座椅设备初始化失败: {e}")
            return False
    
    async def _init_scent(self) -> bool:
        """初始化香薰设备"""
        scent_config = self._config.scent
        
        try:
            if scent_config.type == "wifi":
                from .scent_controller import WiFiScentController
                
                self._scent_controller = WiFiScentController(
                    ip=scent_config.wifi_ip,
                    port=scent_config.wifi_port,
                    api_path=scent_config.wifi_api_path,
                )
                
                connected = await self._scent_controller.connect()
                
                if connected:
                    logger.info("香薰设备 (WiFi) 连接成功")
                    return True
                elif self._config.global_config.enable_mock_fallback:
                    logger.warning("香薰设备连接失败，使用模拟模式")
                    return await self._init_mock_scent()
                else:
                    return False
            else:
                return await self._init_mock_scent()
                
        except ImportError as e:
            logger.warning(f"香薰模块导入失败: {e}")
            if self._config.global_config.enable_mock_fallback:
                return await self._init_mock_scent()
            return False
        except Exception as e:
            logger.error(f"香薰设备初始化错误: {e}")
            if self._config.global_config.enable_mock_fallback:
                return await self._init_mock_scent()
            return False
    
    async def _init_mock_scent(self) -> bool:
        """初始化模拟香薰设备"""
        try:
            from .scent_controller import MockScentController
            
            self._scent_controller = MockScentController()
            await self._scent_controller.connect()
            logger.info("香薰设备 (模拟) 初始化成功")
            return True
        except Exception as e:
            logger.error(f"模拟香薰设备初始化失败: {e}")
            return False
    
    async def _init_audio(self) -> bool:
        """初始化音频设备"""
        # 音频通常使用系统默认设备，这里只做配置验证
        logger.info("音频设备初始化成功 (使用系统默认)")
        return True
    
    # 获取控制器实例的方法
    def get_heart_rate_controller(self) -> Optional[Any]:
        """获取心率控制器"""
        return self._heart_rate_controller
    
    def get_light_controller(self, name: str = None) -> Optional[Any]:
        """获取灯光控制器
        
        Args:
            name: 设备名称，None 返回第一个可用的
        """
        if name:
            return self._light_controllers.get(name)
        # 返回第一个可用的
        if self._light_controllers:
            return next(iter(self._light_controllers.values()))
        return None
    
    def get_all_light_controllers(self) -> Dict[str, Any]:
        """获取所有灯光控制器"""
        return self._light_controllers.copy()
    
    def get_chair_controller(self) -> Optional[Any]:
        """获取座椅控制器"""
        return self._chair_controller
    
    def get_scent_controller(self) -> Optional[Any]:
        """获取香薰控制器"""
        return self._scent_controller
    
    def get_init_results(self) -> Dict[str, bool]:
        """获取初始化结果"""
        return self._init_results.copy()
    
    async def disconnect_all(self) -> None:
        """断开所有设备连接"""
        logger.info("断开所有设备连接...")
        
        if self._heart_rate_controller:
            try:
                await self._heart_rate_controller.disconnect()
            except Exception as e:
                logger.warning(f"断开心率设备失败: {e}")
        
        for name, controller in self._light_controllers.items():
            try:
                await controller.disconnect()
            except Exception as e:
                logger.warning(f"断开灯光设备 '{name}' 失败: {e}")
        
        if self._chair_controller:
            try:
                await self._chair_controller.disconnect()
            except Exception as e:
                logger.warning(f"断开座椅设备失败: {e}")
        
        if self._scent_controller:
            try:
                await self._scent_controller.disconnect()
            except Exception as e:
                logger.warning(f"断开香薰设备失败: {e}")
        
        logger.info("所有设备已断开")


# 全局设备初始化器实例
_device_initializer: Optional[DeviceInitializer] = None


def get_device_initializer() -> DeviceInitializer:
    """获取全局设备初始化器实例"""
    global _device_initializer
    if _device_initializer is None:
        _device_initializer = DeviceInitializer()
    return _device_initializer


async def init_devices_from_config() -> Dict[str, bool]:
    """根据配置初始化所有设备
    
    Returns:
        各设备的初始化结果
    """
    initializer = get_device_initializer()
    return await initializer.initialize_all()


async def cleanup_devices() -> None:
    """清理所有设备"""
    global _device_initializer
    if _device_initializer:
        await _device_initializer.disconnect_all()
    _device_initializer = None
