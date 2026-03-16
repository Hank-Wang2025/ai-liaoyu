"""
焦虑情绪灯光映射属性测试
Anxious Emotion Light Mapping Property Tests

**Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
**Validates: Requirements 7.5**

Property 18: 焦虑情绪灯光映射
*For any* 检测到焦虑情绪的情况，灯光控制器 SHALL 选择蓝绿色系（色相在 150-210 度范围内）的灯光颜色。

测试策略：
1. 验证焦虑情绪映射的颜色色相在 150-210 度范围内
2. 验证所有预设的焦虑情绪颜色变体都在有效范围内
3. 验证灯光控制器应用焦虑情绪时使用正确的颜色
4. 验证 is_anxious_color_valid 方法正确判断颜色有效性
"""
import pytest
import sys
import os
from hypothesis import given, strategies as st, settings, assume

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.light_controller import (
    RGBColor,
    MockLightController,
    EmotionLightMapper,
    LightControllerManager,
)


# Custom strategies for anxious emotion light mapping testing
@st.composite
def rgb_in_anxious_hue_range_strategy(draw):
    """生成色相在焦虑情绪范围内 (150-210度) 的 RGB 颜色
    
    使用更加收紧的范围 (155-205) 来避免 HSV<->RGB 转换的浮点精度问题
    导致边界值落在范围外。RGB 整数量化会导致色相计算有 ±3 度的误差。
    """
    # 色相范围 155-205 度（收紧边界以避免浮点精度和整数量化问题）
    hue = draw(st.floats(min_value=155.0, max_value=205.0))
    saturation = draw(st.floats(min_value=0.4, max_value=1.0))  # 提高最小饱和度
    value = draw(st.floats(min_value=0.4, max_value=1.0))  # 提高最小明度
    
    # HSV to RGB conversion
    r, g, b = hsv_to_rgb(hue, saturation, value)
    color = RGBColor(r=r, g=g, b=b)
    
    # 验证转换后的色相仍在有效范围内（处理量化误差）
    actual_hue = color.get_hue()
    assume(150 <= actual_hue <= 210)
    
    return color


@st.composite
def rgb_outside_anxious_hue_range_strategy(draw):
    """生成色相在焦虑情绪范围外的 RGB 颜色"""
    # 选择明显在范围外的色相：红色(0-30)、黄色(50-80)、紫色(270-330)
    hue_ranges = [(0, 30), (50, 80), (270, 330)]
    range_choice = draw(st.sampled_from(hue_ranges))
    hue = draw(st.floats(min_value=range_choice[0], max_value=range_choice[1]))
    saturation = draw(st.floats(min_value=0.5, max_value=1.0))  # 高饱和度确保色相明显
    value = draw(st.floats(min_value=0.5, max_value=1.0))
    
    # HSV to RGB conversion
    r, g, b = hsv_to_rgb(hue, saturation, value)
    return RGBColor(r=r, g=g, b=b)


def hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    """HSV 转 RGB
    
    Args:
        h: 色相 (0-360)
        s: 饱和度 (0-1)
        v: 明度 (0-1)
        
    Returns:
        (r, g, b) 元组，值范围 0-255
    """
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return (
        int((r + m) * 255),
        int((g + m) * 255),
        int((b + m) * 255)
    )


class TestAnxiousEmotionLightMappingProperties:
    """
    焦虑情绪灯光映射属性测试
    
    **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
    **Validates: Requirements 7.5**
    """
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=4))
    def test_anxious_color_variants_in_valid_hue_range(self, variation_index):
        """
        属性测试：焦虑情绪颜色变体在有效色相范围内
        
        *For any* 焦虑情绪颜色变体索引，获取的颜色 SHALL 在蓝绿色系
        色相范围 (150-210度) 内。
        
        **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
        **Validates: Requirements 7.5**
        """
        mapper = EmotionLightMapper()
        
        # 获取焦虑情绪颜色变体
        color = mapper.get_anxious_color(variation_index)
        
        # 计算色相
        hue = color.get_hue()
        
        # 验证色相在蓝绿色系范围内 (150-210度)
        assert 150 <= hue <= 210, \
            f"Anxious color variant {variation_index} hue {hue:.1f}° should be in range [150, 210]"
        
        # 验证 is_anxious_color_valid 方法也认为该颜色有效
        assert mapper.is_anxious_color_valid(color), \
            f"Anxious color variant {variation_index} should be validated as valid"
    
    @settings(max_examples=100)
    @given(rgb_in_anxious_hue_range_strategy())
    def test_colors_in_anxious_range_are_validated_as_valid(self, color):
        """
        属性测试：蓝绿色系颜色被正确验证为有效
        
        *For any* 色相在 150-210 度范围内的颜色，is_anxious_color_valid
        方法 SHALL 返回 True。
        
        **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
        **Validates: Requirements 7.5**
        """
        mapper = EmotionLightMapper()
        
        # 验证颜色被认为是有效的焦虑情绪颜色
        hue = color.get_hue()
        is_valid = mapper.is_anxious_color_valid(color)
        
        assert is_valid, \
            f"Color with hue {hue:.1f}° (RGB: {color.r}, {color.g}, {color.b}) " \
            f"should be valid for anxious emotion"
    
    @settings(max_examples=100)
    @given(rgb_outside_anxious_hue_range_strategy())
    def test_colors_outside_anxious_range_are_validated_as_invalid(self, color):
        """
        属性测试：非蓝绿色系颜色被正确验证为无效
        
        *For any* 色相明显在 150-210 度范围外的颜色，is_anxious_color_valid
        方法 SHALL 返回 False。
        
        **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
        **Validates: Requirements 7.5**
        """
        mapper = EmotionLightMapper()
        
        # 验证颜色被认为是无效的焦虑情绪颜色
        hue = color.get_hue()
        is_valid = mapper.is_anxious_color_valid(color)
        
        assert not is_valid, \
            f"Color with hue {hue:.1f}° (RGB: {color.r}, {color.g}, {color.b}) " \
            f"should NOT be valid for anxious emotion"
    
    @settings(max_examples=100)
    @given(st.just("anxious"))
    def test_anxious_emotion_config_uses_valid_color(self, emotion):
        """
        属性测试：焦虑情绪配置使用有效颜色
        
        *For any* 焦虑情绪请求，获取的灯光配置 SHALL 使用蓝绿色系颜色。
        
        **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
        **Validates: Requirements 7.5**
        """
        mapper = EmotionLightMapper()
        
        # 获取焦虑情绪的灯光配置
        config = mapper.get_light_config(emotion)
        
        # 将配置颜色转换为 RGB
        color = RGBColor.from_hex(config.color)
        
        # 计算色相
        hue = color.get_hue()
        
        # 验证色相在蓝绿色系范围内 (150-210度)
        assert 150 <= hue <= 210, \
            f"Anxious emotion config color hue {hue:.1f}° should be in range [150, 210]"
        
        # 验证 is_anxious_color_valid 方法也认为该颜色有效
        assert mapper.is_anxious_color_valid(color), \
            f"Anxious emotion config color should be validated as valid"
    
    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=100))
    @pytest.mark.asyncio
    async def test_light_controller_applies_valid_anxious_color(self, brightness):
        """
        属性测试：灯光控制器应用有效的焦虑情绪颜色
        
        *For any* 亮度设置，当应用焦虑情绪灯光时，灯光控制器 SHALL
        设置蓝绿色系颜色。
        
        **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
        **Validates: Requirements 7.5**
        """
        # 创建灯光控制器管理器
        manager = LightControllerManager()
        controller = MockLightController("test_light")
        manager.add_controller("test", controller)
        
        # 连接控制器
        await manager.connect_all()
        
        # 应用焦虑情绪灯光
        results = await manager.apply_emotion_lighting("anxious")
        
        # 验证设置成功
        assert results["test"] is True, "Should successfully apply anxious emotion lighting"
        
        # 获取当前状态
        state = controller.current_state
        assert state is not None, "Controller should have a state after applying emotion lighting"
        
        # 验证颜色在蓝绿色系范围内
        hue = state.color.get_hue()
        assert 150 <= hue <= 210, \
            f"Applied anxious color hue {hue:.1f}° should be in range [150, 210]"
        
        # 验证 is_anxious_color_valid 方法也认为该颜色有效
        assert manager.emotion_mapper.is_anxious_color_valid(state.color), \
            f"Applied anxious color should be validated as valid"
        
        # 清理
        await manager.disconnect_all()
    
    def test_all_predefined_anxious_colors_are_valid(self):
        """
        属性测试：所有预定义的焦虑情绪颜色都有效
        
        *For all* 预定义的焦虑情绪颜色，每个颜色 SHALL 在蓝绿色系
        色相范围 (150-210度) 内。
        
        **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
        **Validates: Requirements 7.5**
        """
        mapper = EmotionLightMapper()
        
        # 验证所有预定义的焦虑情绪颜色
        for i, hex_color in enumerate(mapper.ANXIOUS_COLORS):
            color = RGBColor.from_hex(hex_color)
            hue = color.get_hue()
            
            # 验证色相在蓝绿色系范围内
            assert 150 <= hue <= 210, \
                f"Predefined anxious color {i} ({hex_color}) hue {hue:.1f}° " \
                f"should be in range [150, 210]"
            
            # 验证 is_anxious_color_valid 方法也认为该颜色有效
            assert mapper.is_anxious_color_valid(color), \
                f"Predefined anxious color {i} ({hex_color}) should be validated as valid"
    
    def test_anxious_emotion_map_entry_has_correct_hue_range(self):
        """
        属性测试：焦虑情绪映射条目有正确的色相范围配置
        
        焦虑情绪在 EMOTION_COLOR_MAP 中的 hue_range 配置 SHALL 为 (150, 210)。
        
        **Feature: healing-pod-system, Property 18: 焦虑情绪灯光映射**
        **Validates: Requirements 7.5**
        """
        mapper = EmotionLightMapper()
        
        # 获取焦虑情绪的映射配置
        anxious_config = mapper.EMOTION_COLOR_MAP.get("anxious")
        assert anxious_config is not None, "Anxious emotion should be in EMOTION_COLOR_MAP"
        
        # 验证 hue_range 配置
        hue_range = anxious_config.get("hue_range")
        assert hue_range is not None, "Anxious emotion should have hue_range configured"
        assert hue_range == (150, 210), \
            f"Anxious emotion hue_range should be (150, 210), got {hue_range}"
        
        # 验证配置的颜色也在该范围内
        color = RGBColor.from_hex(anxious_config["color"])
        hue = color.get_hue()
        assert hue_range[0] <= hue <= hue_range[1], \
            f"Anxious emotion color hue {hue:.1f}° should be within configured range {hue_range}"
