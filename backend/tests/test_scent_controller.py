"""
香薰控制器测试模块
Scent Controller Test Module

测试香薰设备控制功能
"""
import asyncio
import sys
import os

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from services.scent_controller import (
    ScentType,
    ScentState,
    ScentConfig,
    MockScentController,
    EmotionScentMapper,
    ScentControllerManager,
    create_scent_controller
)


class TestScentType:
    """测试香型枚举"""
    
    def test_scent_types_exist(self):
        """测试香型存在"""
        assert ScentType.LAVENDER in ScentType
        assert ScentType.EUCALYPTUS in ScentType
        assert ScentType.PEPPERMINT in ScentType
        assert ScentType.OFF in ScentType


class TestScentState:
    """测试香薰状态"""
    
    def test_scent_state_creation(self):
        """测试香薰状态创建"""
        state = ScentState(scent_type=ScentType.LAVENDER, intensity=5, is_running=True)
        assert state.scent_type == ScentType.LAVENDER
        assert state.intensity == 5
        assert state.is_running is True
    
    def test_intensity_validation(self):
        """测试强度范围验证"""
        # 有效范围 0-10
        state = ScentState(scent_type=ScentType.LAVENDER, intensity=0)
        assert state.intensity == 0
        
        state = ScentState(scent_type=ScentType.LAVENDER, intensity=10)
        assert state.intensity == 10
        
        # 无效范围
        with pytest.raises(ValueError):
            ScentState(scent_type=ScentType.LAVENDER, intensity=11)


class TestMockScentController:
    """测试模拟香薰控制器"""
    
    @pytest.fixture
    def controller(self):
        """创建控制器实例"""
        return MockScentController("test_scent")
    
    @pytest.mark.asyncio
    async def test_connect(self, controller):
        """测试连接"""
        result = await controller.connect()
        
        assert result is True
        assert controller.is_connected is True
    
    @pytest.mark.asyncio
    async def test_disconnect(self, controller):
        """测试断开连接"""
        await controller.connect()
        await controller.disconnect()
        
        assert controller.is_connected is False
    
    @pytest.mark.asyncio
    async def test_set_scent(self, controller):
        """测试设置香型"""
        await controller.connect()
        
        result = await controller.set_scent(ScentType.LAVENDER, intensity=6)
        
        assert result is True
        assert controller.current_state.scent_type == ScentType.LAVENDER
        assert controller.current_state.intensity == 6
    
    @pytest.mark.asyncio
    async def test_start_stop(self, controller):
        """测试开始和停止"""
        await controller.connect()
        
        # 开始
        result = await controller.start()
        assert result is True
        assert controller.current_state.is_running is True
        
        # 停止
        result = await controller.stop()
        assert result is True
        assert controller.current_state.is_running is False


class TestEmotionScentMapper:
    """测试情绪-香型映射"""
    
    @pytest.fixture
    def mapper(self):
        return EmotionScentMapper()
    
    def test_get_anxious_config(self, mapper):
        """测试获取焦虑情绪配置"""
        config = mapper.get_scent_config("anxious")
        assert config.scent_type == "lavender"
    
    def test_get_happy_config(self, mapper):
        """测试获取开心情绪配置"""
        config = mapper.get_scent_config("happy")
        assert config.scent_type == "bergamot"


class TestScentControllerManager:
    """测试香薰控制器管理器"""
    
    @pytest.fixture
    def manager(self):
        return ScentControllerManager()
    
    @pytest.mark.asyncio
    async def test_apply_emotion_scent(self, manager):
        """测试应用情绪香薰"""
        controller = MockScentController("test")
        manager.set_controller(controller)
        await manager.connect()
        
        result = await manager.apply_emotion_scent("anxious")
        
        assert result is True
        assert controller.current_state.scent_type == ScentType.LAVENDER
    
    def test_get_available_scents(self, manager):
        """测试获取可用香型列表"""
        scents = manager.get_available_scents()
        
        # 应该有多种香型（不包括OFF）
        assert len(scents) >= 5


class TestCreateScentController:
    """测试控制器工厂函数"""
    
    def test_create_mock_controller(self):
        """测试创建模拟控制器"""
        controller = create_scent_controller("mock", name="test")
        
        assert isinstance(controller, MockScentController)
    
    def test_create_unknown_type(self):
        """测试创建未知类型控制器"""
        with pytest.raises(ValueError):
            create_scent_controller("unknown")
