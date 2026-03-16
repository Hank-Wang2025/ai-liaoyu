"""
灯光控制器模块测试
Light Controller Module Tests
"""
import pytest
import asyncio
import sys
import os

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.light_controller import (
    RGBColor,
    LightState,
    LightConfig,
    LightPattern,
    BaseLightController,
    MockLightController,
    LightTransitionController,
    EmotionLightMapper,
    LightControllerManager,
    create_light_controller
)


class TestRGBColor:
    """RGB颜色测试"""
    
    def test_rgb_creation(self):
        """测试RGB颜色创建"""
        color = RGBColor(r=255, g=128, b=64)
        assert color.r == 255
        assert color.g == 128
        assert color.b == 64
    
    def test_rgb_validation(self):
        """测试RGB值范围验证"""
        with pytest.raises(ValueError):
            RGBColor(r=256, g=0, b=0)
        with pytest.raises(ValueError):
            RGBColor(r=0, g=-1, b=0)
    
    def test_hex_to_rgb(self):
        """测试HEX到RGB转换"""
        # 带#前缀
        color = RGBColor.from_hex("#FF8040")
        assert color.r == 255
        assert color.g == 128
        assert color.b == 64
        
        # 不带#前缀
        color = RGBColor.from_hex("00FF00")
        assert color.r == 0
        assert color.g == 255
        assert color.b == 0
    
    def test_rgb_to_hex(self):
        """测试RGB到HEX转换"""
        color = RGBColor(r=255, g=128, b=64)
        assert color.to_hex() == "#ff8040"
    
    def test_hex_roundtrip(self):
        """测试HEX转换往返"""
        original = "#4ecdc4"
        color = RGBColor.from_hex(original)
        result = color.to_hex()
        assert result == original
    
    def test_invalid_hex(self):
        """测试无效HEX格式"""
        with pytest.raises(ValueError):
            RGBColor.from_hex("invalid")
        with pytest.raises(ValueError):
            RGBColor.from_hex("#GGG")
    
    def test_get_hue(self):
        """测试色相计算"""
        # 红色 - 0度
        red = RGBColor(r=255, g=0, b=0)
        assert 0 <= red.get_hue() <= 10 or 350 <= red.get_hue() <= 360
        
        # 绿色 - 120度
        green = RGBColor(r=0, g=255, b=0)
        assert 110 <= green.get_hue() <= 130
        
        # 蓝色 - 240度
        blue = RGBColor(r=0, g=0, b=255)
        assert 230 <= blue.get_hue() <= 250
        
        # 青色 - 180度
        cyan = RGBColor(r=0, g=255, b=255)
        assert 170 <= cyan.get_hue() <= 190


class TestLightState:
    """灯光状态测试"""
    
    def test_light_state_creation(self):
        """测试灯光状态创建"""
        color = RGBColor(r=255, g=255, b=255)
        state = LightState(color=color, brightness=80)
        assert state.brightness == 80
        assert state.is_on is True
        assert state.pattern == LightPattern.STATIC
    
    def test_brightness_validation(self):
        """测试亮度范围验证"""
        color = RGBColor(r=255, g=255, b=255)
        with pytest.raises(ValueError):
            LightState(color=color, brightness=101)
        with pytest.raises(ValueError):
            LightState(color=color, brightness=-1)


class TestMockLightController:
    """模拟灯光控制器测试"""
    
    @pytest.fixture
    def controller(self):
        return MockLightController("test_light")
    
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
    async def test_set_rgb(self, controller):
        """测试设置RGB颜色"""
        await controller.connect()
        color = RGBColor(r=255, g=128, b=64)
        result = await controller.set_rgb(color, 80, 3000)
        
        assert result is True
        assert controller.current_state is not None
        assert controller.current_state.color.r == 255
        assert controller.current_state.brightness == 80
    
    @pytest.mark.asyncio
    async def test_set_color_hex(self, controller):
        """测试设置HEX颜色"""
        await controller.connect()
        result = await controller.set_color("#4ECDC4", 60, 2000)
        
        assert result is True
        assert controller.current_state.color.r == 78
        assert controller.current_state.color.g == 205
        assert controller.current_state.color.b == 196
    
    @pytest.mark.asyncio
    async def test_turn_on_off(self, controller):
        """测试开关灯"""
        await controller.connect()
        await controller.set_color("#FFFFFF", 100)
        
        await controller.turn_off()
        assert controller.current_state.is_on is False
        
        await controller.turn_on()
        assert controller.current_state.is_on is True
    
    @pytest.mark.asyncio
    async def test_command_history(self, controller):
        """测试命令历史记录"""
        await controller.connect()
        await controller.set_color("#FF0000", 50)
        await controller.turn_off()
        
        history = controller.command_history
        assert len(history) == 3
        assert history[0]["action"] == "connect"
        assert history[1]["action"] == "set_rgb"
        assert history[2]["action"] == "turn_off"


class TestEmotionLightMapper:
    """情绪-灯光映射测试"""
    
    @pytest.fixture
    def mapper(self):
        return EmotionLightMapper()
    
    def test_get_anxious_config(self, mapper):
        """测试获取焦虑情绪配置"""
        config = mapper.get_light_config("anxious")
        assert config.color == "#4ECDC4"
        assert config.brightness == 60
    
    def test_get_happy_config(self, mapper):
        """测试获取开心情绪配置"""
        config = mapper.get_light_config("happy")
        assert config.color == "#FFD93D"
        assert config.brightness == 75
    
    def test_get_neutral_config(self, mapper):
        """测试获取中性情绪配置"""
        config = mapper.get_light_config("neutral")
        assert config.brightness == 65
    
    def test_unknown_emotion_fallback(self, mapper):
        """测试未知情绪回退到中性"""
        config = mapper.get_light_config("unknown_emotion")
        neutral_config = mapper.get_light_config("neutral")
        assert config.color == neutral_config.color
    
    def test_anxious_color_validation(self, mapper):
        """测试焦虑情绪颜色验证"""
        # 蓝绿色系应该有效
        cyan = RGBColor.from_hex("#4ECDC4")
        assert mapper.is_anxious_color_valid(cyan) is True
        
        # 红色不应该有效
        red = RGBColor(r=255, g=0, b=0)
        assert mapper.is_anxious_color_valid(red) is False
    
    def test_get_anxious_colors(self, mapper):
        """测试获取焦虑情绪颜色变体"""
        for i in range(5):
            color = mapper.get_anxious_color(i)
            assert mapper.is_anxious_color_valid(color) is True
    
    def test_custom_mapping(self, mapper):
        """测试自定义映射"""
        mapper.set_custom_mapping("custom", "#123456", 50, "Custom color")
        config = mapper.get_light_config("custom")
        assert config.color == "#123456"
        assert config.brightness == 50


class TestLightTransitionController:
    """灯光过渡控制器测试"""
    
    @pytest.fixture
    def transition_controller(self):
        light = MockLightController("test")
        # Use synchronous setup
        return light, LightTransitionController(light)
    
    @pytest.mark.asyncio
    async def test_smooth_transition(self, transition_controller):
        """测试平滑过渡"""
        light, tc = transition_controller
        await light.connect()
        
        # 设置初始状态
        await tc.controller.set_rgb(
            RGBColor(r=0, g=0, b=0), 0
        )
        
        # 执行过渡
        target = RGBColor(r=255, g=255, b=255)
        result = await tc.smooth_transition(
            target, 100, duration_ms=100, steps=5
        )
        
        assert result is True
        assert tc.controller.current_state.brightness == 100
    
    @pytest.mark.asyncio
    async def test_breath_mode_start_stop(self, transition_controller):
        """测试呼吸灯模式启停"""
        light, tc = transition_controller
        await light.connect()
        
        color = RGBColor(r=78, g=205, b=196)
        
        # 启动呼吸灯
        await tc.start_breath_mode(
            color, min_brightness=30, max_brightness=80, period_ms=200
        )
        assert tc.is_breathing is True
        
        # 等待一小段时间
        await asyncio.sleep(0.1)
        
        # 停止呼吸灯
        await tc.stop_breath_mode()
        assert tc.is_breathing is False
    
    @pytest.mark.asyncio
    async def test_pulse_effect(self, transition_controller):
        """测试脉冲效果"""
        light, tc = transition_controller
        await light.connect()
        
        color = RGBColor(r=255, g=0, b=0)
        result = await tc.pulse_effect(
            color, brightness=80, pulse_count=2, pulse_duration_ms=100
        )
        assert result is True


class TestLightControllerManager:
    """灯光控制器管理器测试"""
    
    @pytest.fixture
    def manager(self):
        return LightControllerManager()
    
    @pytest.mark.asyncio
    async def test_add_and_connect(self, manager):
        """测试添加和连接控制器"""
        light1 = MockLightController("light1")
        light2 = MockLightController("light2")
        
        manager.add_controller("light1", light1)
        manager.add_controller("light2", light2)
        
        results = await manager.connect_all()
        assert results["light1"] is True
        assert results["light2"] is True
    
    @pytest.mark.asyncio
    async def test_set_all_lights(self, manager):
        """测试设置所有灯光"""
        light1 = MockLightController("light1")
        light2 = MockLightController("light2")
        
        manager.add_controller("light1", light1)
        manager.add_controller("light2", light2)
        await manager.connect_all()
        
        results = await manager.set_all_lights("#FF0000", 80)
        assert all(results.values())
    
    @pytest.mark.asyncio
    async def test_apply_emotion_lighting(self, manager):
        """测试应用情绪灯光"""
        light = MockLightController("light")
        manager.add_controller("light", light)
        await manager.connect_all()
        
        results = await manager.apply_emotion_lighting("anxious")
        assert results["light"] is True
        
        # 验证颜色是否正确
        state = light.current_state
        assert state is not None
        assert manager.emotion_mapper.is_anxious_color_valid(state.color)
    
    @pytest.mark.asyncio
    async def test_get_status(self, manager):
        """测试获取状态"""
        light = MockLightController("light")
        manager.add_controller("light", light)
        await manager.connect_all()
        await manager.set_all_lights("#FFFFFF", 100)
        
        status = manager.get_status()
        assert "light" in status
        assert status["light"]["connected"] is True
        assert status["light"]["state"]["brightness"] == 100


class TestCreateLightController:
    """创建灯光控制器工厂测试"""
    
    def test_create_mock(self):
        """测试创建模拟控制器"""
        controller = create_light_controller("mock", name="test")
        assert isinstance(controller, MockLightController)
        assert controller.name == "test"
    
    def test_create_unknown_type(self):
        """测试创建未知类型"""
        with pytest.raises(ValueError):
            create_light_controller("unknown")
    
    def test_create_yeelight_without_ip(self):
        """测试创建Yeelight但未提供IP"""
        with pytest.raises(ValueError):
            create_light_controller("yeelight")
