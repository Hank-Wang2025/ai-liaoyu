"""
座椅控制器测试模块
Chair Controller Test Module

测试按摩座椅控制功能
Requirements: 9.1, 9.2, 9.3
"""
import asyncio
import sys
import os

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime

from services.chair_controller import (
    MassageMode,
    MassageModeConfig,
    MASSAGE_MODE_CONFIGS,
    ChairState,
    ChairConfig,
    MockChairController,
    ChairControllerManager,
    create_chair_controller
)


class TestMassageMode:
    """测试按摩模式枚举"""
    
    def test_massage_modes_exist(self):
        """测试所有按摩模式存在 - Requirements 9.2"""
        # 验证至少5种按摩模式
        modes = [m for m in MassageMode if m != MassageMode.OFF]
        assert len(modes) >= 5
        
        # 验证必需的模式
        assert MassageMode.GENTLE in MassageMode
        assert MassageMode.SOOTHING in MassageMode
        assert MassageMode.DEEP in MassageMode
        assert MassageMode.WAVE in MassageMode
        assert MassageMode.PULSE in MassageMode
    
    def test_mode_configs_exist(self):
        """测试所有模式都有配置"""
        for mode in MassageMode:
            assert mode in MASSAGE_MODE_CONFIGS


class TestChairState:
    """测试座椅状态"""
    
    def test_chair_state_creation(self):
        """测试座椅状态创建"""
        state = ChairState(mode=MassageMode.GENTLE, intensity=5, is_running=True)
        assert state.mode == MassageMode.GENTLE
        assert state.intensity == 5
        assert state.is_running is True
    
    def test_intensity_validation(self):
        """测试强度范围验证 - Requirements 9.3"""
        # 有效范围 0-10
        state = ChairState(mode=MassageMode.GENTLE, intensity=0)
        assert state.intensity == 0
        
        state = ChairState(mode=MassageMode.GENTLE, intensity=10)
        assert state.intensity == 10
        
        # 无效范围
        with pytest.raises(ValueError):
            ChairState(mode=MassageMode.GENTLE, intensity=11)
        
        with pytest.raises(ValueError):
            ChairState(mode=MassageMode.GENTLE, intensity=-1)


class TestMockChairController:
    """测试模拟座椅控制器"""
    
    @pytest.fixture
    def controller(self):
        """创建控制器实例"""
        return MockChairController("test_chair")
    
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
    async def test_set_mode_gentle(self, controller):
        """测试设置轻柔模式"""
        await controller.connect()
        
        result = await controller.set_mode(MassageMode.GENTLE)
        
        assert result is True
        assert controller.current_state.mode == MassageMode.GENTLE
        assert controller.current_state.is_running is True
    
    @pytest.mark.asyncio
    async def test_set_mode_with_intensity(self, controller):
        """测试设置模式和强度 - Requirements 9.2, 9.3"""
        await controller.connect()
        
        result = await controller.set_mode(MassageMode.DEEP, intensity=8)
        
        assert result is True
        assert controller.current_state.mode == MassageMode.DEEP
        assert controller.current_state.intensity == 8
    
    @pytest.mark.asyncio
    async def test_set_intensity(self, controller):
        """测试设置强度 - Requirements 9.3"""
        await controller.connect()
        await controller.set_mode(MassageMode.WAVE)
        
        result = await controller.set_intensity(7)
        
        assert result is True
        assert controller.current_state.intensity == 7
    
    @pytest.mark.asyncio
    async def test_intensity_clamping(self, controller):
        """测试强度范围限制"""
        await controller.connect()
        await controller.set_mode(MassageMode.GENTLE)
        
        # 超出范围应该被限制
        await controller.set_intensity(15)
        assert controller.current_state.intensity == 10
        
        await controller.set_intensity(0)
        assert controller.current_state.intensity == 1  # 最小为1
    
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
        assert controller.current_state.mode == MassageMode.OFF
    
    @pytest.mark.asyncio
    async def test_user_preference_recording(self, controller):
        """测试用户偏好记录 - Requirements 9.4"""
        await controller.connect()
        await controller.set_mode(MassageMode.WAVE, intensity=6)
        
        # 手动调节强度
        await controller.set_intensity(8)
        
        # 验证偏好被记录
        pref = controller.get_user_preference(MassageMode.WAVE)
        assert pref == 8
    
    @pytest.mark.asyncio
    async def test_user_preference_applied(self, controller):
        """测试用户偏好被应用"""
        await controller.connect()
        
        # 记录偏好
        controller.record_user_preference(MassageMode.DEEP, 9)
        
        # 设置模式时不指定强度，应该使用偏好
        await controller.set_mode(MassageMode.DEEP)
        
        assert controller.current_state.intensity == 9
    
    @pytest.mark.asyncio
    async def test_command_history(self, controller):
        """测试命令历史记录"""
        await controller.connect()
        await controller.set_mode(MassageMode.GENTLE, intensity=5)
        await controller.stop()
        
        history = controller.command_history
        
        assert len(history) >= 3
        assert history[0]["action"] == "connect"
        assert history[1]["action"] == "set_mode"
        assert history[2]["action"] == "stop"
    
    @pytest.mark.asyncio
    async def test_operations_without_connection(self, controller):
        """测试未连接时的操作"""
        # 未连接时操作应该失败
        result = await controller.set_mode(MassageMode.GENTLE)
        assert result is False
        
        result = await controller.set_intensity(5)
        assert result is False
        
        result = await controller.start()
        assert result is False


class TestChairControllerManager:
    """测试座椅控制器管理器"""
    
    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return ChairControllerManager()
    
    @pytest.mark.asyncio
    async def test_set_and_connect_controller(self, manager):
        """测试设置和连接控制器"""
        controller = MockChairController("test")
        manager.set_controller(controller)
        
        result = await manager.connect()
        
        assert result is True
        assert manager.controller.is_connected is True
    
    @pytest.mark.asyncio
    async def test_apply_therapy_config(self, manager):
        """测试应用疗愈配置"""
        controller = MockChairController("test")
        manager.set_controller(controller)
        await manager.connect()
        
        config = ChairConfig(mode="wave", intensity=6)
        result = await manager.apply_therapy_config(config)
        
        assert result is True
        assert controller.current_state.mode == MassageMode.WAVE
        assert controller.current_state.intensity == 6
    
    @pytest.mark.asyncio
    async def test_apply_therapy_config_with_duration(self, manager):
        """测试应用带持续时间的疗愈配置"""
        controller = MockChairController("test")
        manager.set_controller(controller)
        await manager.connect()
        
        config = ChairConfig(mode="gentle", intensity=4, duration=1)
        result = await manager.apply_therapy_config(config)
        
        assert result is True
        
        # 等待定时任务完成
        await asyncio.sleep(1.2)
        
        # 应该已经停止
        assert controller.current_state.is_running is False
    
    @pytest.mark.asyncio
    async def test_get_status(self, manager):
        """测试获取状态"""
        controller = MockChairController("test")
        manager.set_controller(controller)
        await manager.connect()
        await controller.set_mode(MassageMode.PULSE, intensity=7)
        
        status = manager.get_status()
        
        assert status["connected"] is True
        assert status["state"]["mode"] == "pulse"
        assert status["state"]["intensity"] == 7
        assert status["state"]["is_running"] is True
    
    def test_get_available_modes(self, manager):
        """测试获取可用模式列表"""
        modes = manager.get_available_modes()
        
        # 应该有至少5种模式（不包括OFF）
        assert len(modes) >= 5
        
        # 验证模式信息完整
        for mode in modes:
            assert "mode" in mode
            assert "description" in mode
            assert "default_intensity" in mode


class TestCreateChairController:
    """测试控制器工厂函数"""
    
    def test_create_mock_controller(self):
        """测试创建模拟控制器"""
        controller = create_chair_controller("mock", name="test")
        
        assert isinstance(controller, MockChairController)
        assert controller.name == "test"
    
    def test_create_unknown_type(self):
        """测试创建未知类型控制器"""
        with pytest.raises(ValueError):
            create_chair_controller("unknown")
