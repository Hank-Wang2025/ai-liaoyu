"""
设备初始化器测试
Device Initializer Tests
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.device_config import (
    DeviceConfiguration,
    HeartRateConfig,
    LightsConfig,
    LightDeviceConfig,
    ChairConfig,
    ScentConfig,
    AudioConfig,
    GlobalConfig,
)
from backend.services.device_initializer import (
    DeviceInitializer,
    get_device_initializer,
    init_devices_from_config,
    cleanup_devices,
)


@pytest.fixture
def mock_config():
    """创建模拟配置"""
    config = DeviceConfiguration()
    config.global_config = GlobalConfig(
        connection_timeout=5,
        reconnect_interval=10,
        enable_mock_fallback=True,
        log_level="DEBUG"
    )
    config.heart_rate = HeartRateConfig(
        enabled=True,
        type="mock",
        mock_base_bpm=72,
        mock_variability=8
    )
    config.lights = LightsConfig(
        enabled=True,
        devices=[],  # 空设备列表，将使用模拟
        default_brightness=60
    )
    config.chair = ChairConfig(
        enabled=True,
        type="mock"
    )
    config.scent = ScentConfig(
        enabled=True,
        type="mock"
    )
    config.audio = AudioConfig(
        enabled=True,
        default_volume=50
    )
    return config


@pytest.fixture
def disabled_config():
    """创建禁用所有设备的配置"""
    config = DeviceConfiguration()
    config.heart_rate = HeartRateConfig(enabled=False)
    config.lights = LightsConfig(enabled=False)
    config.chair = ChairConfig(enabled=False)
    config.scent = ScentConfig(enabled=False)
    config.audio = AudioConfig(enabled=False)
    return config


class TestDeviceInitializer:
    """设备初始化器测试"""
    
    @pytest.mark.asyncio
    async def test_initialize_all_with_mock_devices(self, mock_config):
        """测试使用模拟设备初始化所有设备"""
        initializer = DeviceInitializer(mock_config)
        results = await initializer.initialize_all()
        
        # 所有设备应该初始化成功（使用模拟模式）
        assert results.get("heart_rate") is True
        assert results.get("lights") is True
        assert results.get("chair") is True
        assert results.get("scent") is True
        assert results.get("audio") is True
        
        # 清理
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_initialize_with_disabled_devices(self, disabled_config):
        """测试禁用设备时不初始化"""
        initializer = DeviceInitializer(disabled_config)
        results = await initializer.initialize_all()
        
        # 禁用的设备不应该在结果中
        assert "heart_rate" not in results
        assert "lights" not in results
        assert "chair" not in results
        assert "scent" not in results
        assert "audio" not in results
    
    @pytest.mark.asyncio
    async def test_get_heart_rate_controller(self, mock_config):
        """测试获取心率控制器"""
        initializer = DeviceInitializer(mock_config)
        await initializer.initialize_all()
        
        controller = initializer.get_heart_rate_controller()
        assert controller is not None
        
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_get_light_controller(self, mock_config):
        """测试获取灯光控制器"""
        initializer = DeviceInitializer(mock_config)
        await initializer.initialize_all()
        
        # 获取默认灯光控制器
        controller = initializer.get_light_controller()
        assert controller is not None
        
        # 获取所有灯光控制器
        all_controllers = initializer.get_all_light_controllers()
        assert len(all_controllers) > 0
        
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_get_chair_controller(self, mock_config):
        """测试获取座椅控制器"""
        initializer = DeviceInitializer(mock_config)
        await initializer.initialize_all()
        
        controller = initializer.get_chair_controller()
        assert controller is not None
        
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_get_scent_controller(self, mock_config):
        """测试获取香薰控制器"""
        initializer = DeviceInitializer(mock_config)
        await initializer.initialize_all()
        
        controller = initializer.get_scent_controller()
        assert controller is not None
        
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_get_init_results(self, mock_config):
        """测试获取初始化结果"""
        initializer = DeviceInitializer(mock_config)
        await initializer.initialize_all()
        
        results = initializer.get_init_results()
        assert isinstance(results, dict)
        assert len(results) > 0
        
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_disconnect_all(self, mock_config):
        """测试断开所有设备"""
        initializer = DeviceInitializer(mock_config)
        await initializer.initialize_all()
        
        # 断开所有设备不应该抛出异常
        await initializer.disconnect_all()
        
        # 再次断开也不应该抛出异常
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_fallback_to_mock_on_connection_failure(self):
        """测试连接失败时回退到模拟模式"""
        config = DeviceConfiguration()
        config.global_config = GlobalConfig(enable_mock_fallback=True)
        config.heart_rate = HeartRateConfig(
            enabled=True,
            type="ble",  # BLE 设备，但没有实际设备
            device_address="",  # 空地址
        )
        config.lights = LightsConfig(enabled=False)
        config.chair = ChairConfig(enabled=False)
        config.scent = ScentConfig(enabled=False)
        config.audio = AudioConfig(enabled=False)
        
        initializer = DeviceInitializer(config)
        
        # 由于启用了 mock_fallback，即使 BLE 连接失败也应该成功
        results = await initializer.initialize_all()
        
        # 应该回退到模拟模式
        assert results.get("heart_rate") is True
        
        await initializer.disconnect_all()


class TestDeviceInitializerWithLightDevices:
    """带灯光设备配置的初始化器测试"""
    
    @pytest.mark.asyncio
    async def test_initialize_with_mock_light_config(self):
        """测试使用模拟灯光配置初始化"""
        config = DeviceConfiguration()
        config.global_config = GlobalConfig(enable_mock_fallback=True)
        config.heart_rate = HeartRateConfig(enabled=False)
        config.lights = LightsConfig(
            enabled=True,
            devices=[
                LightDeviceConfig(
                    name="mock_test",
                    type="mock",
                    enabled=True,
                    config={}
                )
            ]
        )
        config.chair = ChairConfig(enabled=False)
        config.scent = ScentConfig(enabled=False)
        config.audio = AudioConfig(enabled=False)
        
        initializer = DeviceInitializer(config)
        results = await initializer.initialize_all()
        
        assert results.get("lights") is True
        
        # 验证灯光控制器
        controller = initializer.get_light_controller("mock_test")
        assert controller is not None
        
        await initializer.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_initialize_with_invalid_light_type_fallback(self):
        """测试无效灯光类型回退到模拟"""
        config = DeviceConfiguration()
        config.global_config = GlobalConfig(enable_mock_fallback=True)
        config.heart_rate = HeartRateConfig(enabled=False)
        config.lights = LightsConfig(
            enabled=True,
            devices=[
                LightDeviceConfig(
                    name="invalid_light",
                    type="invalid_type",  # 无效类型
                    enabled=True,
                    config={}
                )
            ]
        )
        config.chair = ChairConfig(enabled=False)
        config.scent = ScentConfig(enabled=False)
        config.audio = AudioConfig(enabled=False)
        
        initializer = DeviceInitializer(config)
        results = await initializer.initialize_all()
        
        # 应该回退到模拟模式
        assert results.get("lights") is True
        
        await initializer.disconnect_all()


class TestGlobalFunctions:
    """全局函数测试"""
    
    @pytest.mark.asyncio
    async def test_init_devices_from_config(self):
        """测试从配置初始化设备"""
        # 使用默认配置（模拟模式）
        results = await init_devices_from_config()
        
        assert isinstance(results, dict)
        
        # 清理
        await cleanup_devices()
    
    @pytest.mark.asyncio
    async def test_cleanup_devices(self):
        """测试清理设备"""
        # 先初始化
        await init_devices_from_config()
        
        # 清理不应该抛出异常
        await cleanup_devices()
        
        # 再次清理也不应该抛出异常
        await cleanup_devices()
    
    def test_get_device_initializer_singleton(self):
        """测试获取设备初始化器单例"""
        initializer1 = get_device_initializer()
        initializer2 = get_device_initializer()
        
        assert initializer1 is initializer2
