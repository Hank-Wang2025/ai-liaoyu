"""
灯光颜色转换正确性属性测试
Light Color Conversion Correctness Property Tests

**Feature: healing-pod-system, Property 16: 灯光颜色转换正确性**
**Validates: Requirements 7.2**

Property 16: 灯光颜色转换正确性
*For any* 有效的 HEX 颜色值，灯光控制器 SHALL 正确转换为 RGB 值并发送到设备。

测试策略：
1. 验证 HEX 到 RGB 的转换正确性（往返测试）
2. 验证 RGB 到 HEX 的转换正确性
3. 验证转换后的 RGB 值在有效范围内 (0-255)
4. 验证灯光控制器正确接收并应用转换后的颜色
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
)


# Custom strategy for valid HEX color strings
@st.composite
def hex_color_strategy(draw):
    """生成有效的 HEX 颜色值"""
    r = draw(st.integers(min_value=0, max_value=255))
    g = draw(st.integers(min_value=0, max_value=255))
    b = draw(st.integers(min_value=0, max_value=255))
    # Generate HEX string with or without # prefix
    with_prefix = draw(st.booleans())
    hex_str = f"{r:02x}{g:02x}{b:02x}"
    if with_prefix:
        hex_str = "#" + hex_str
    return hex_str, (r, g, b)


@st.composite
def rgb_values_strategy(draw):
    """生成有效的 RGB 值"""
    r = draw(st.integers(min_value=0, max_value=255))
    g = draw(st.integers(min_value=0, max_value=255))
    b = draw(st.integers(min_value=0, max_value=255))
    return (r, g, b)


class TestLightColorConversionProperties:
    """
    灯光颜色转换正确性属性测试
    
    **Feature: healing-pod-system, Property 16: 灯光颜色转换正确性**
    **Validates: Requirements 7.2**
    """
    
    @given(hex_color_strategy())
    @settings(max_examples=100)
    def test_hex_to_rgb_conversion_correctness(self, hex_data):
        """
        属性测试：HEX 到 RGB 转换正确性
        
        *For any* 有效的 HEX 颜色值，转换后的 RGB 值应与原始值匹配。
        
        **Feature: healing-pod-system, Property 16: 灯光颜色转换正确性**
        **Validates: Requirements 7.2**
        """
        hex_str, expected_rgb = hex_data
        
        # 执行转换
        rgb_color = RGBColor.from_hex(hex_str)
        
        # 验证转换结果
        assert rgb_color.r == expected_rgb[0], f"R value mismatch: expected {expected_rgb[0]}, got {rgb_color.r}"
        assert rgb_color.g == expected_rgb[1], f"G value mismatch: expected {expected_rgb[1]}, got {rgb_color.g}"
        assert rgb_color.b == expected_rgb[2], f"B value mismatch: expected {expected_rgb[2]}, got {rgb_color.b}"
    
    @given(rgb_values_strategy())
    @settings(max_examples=100)
    def test_rgb_to_hex_roundtrip(self, rgb_values):
        """
        属性测试：RGB 到 HEX 往返转换
        
        *For any* 有效的 RGB 值，转换为 HEX 后再转回 RGB 应得到相同的值。
        
        **Feature: healing-pod-system, Property 16: 灯光颜色转换正确性**
        **Validates: Requirements 7.2**
        """
        r, g, b = rgb_values
        
        # 创建 RGB 颜色
        original = RGBColor(r=r, g=g, b=b)
        
        # 转换为 HEX
        hex_str = original.to_hex()
        
        # 转回 RGB
        converted = RGBColor.from_hex(hex_str)
        
        # 验证往返转换
        assert converted.r == original.r, f"R roundtrip failed: {original.r} -> {hex_str} -> {converted.r}"
        assert converted.g == original.g, f"G roundtrip failed: {original.g} -> {hex_str} -> {converted.g}"
        assert converted.b == original.b, f"B roundtrip failed: {original.b} -> {hex_str} -> {converted.b}"
    
    @given(hex_color_strategy())
    @settings(max_examples=100)
    def test_converted_rgb_values_in_valid_range(self, hex_data):
        """
        属性测试：转换后的 RGB 值在有效范围内
        
        *For any* 有效的 HEX 颜色值，转换后的 RGB 值应在 0-255 范围内。
        
        **Feature: healing-pod-system, Property 16: 灯光颜色转换正确性**
        **Validates: Requirements 7.2**
        """
        hex_str, _ = hex_data
        
        # 执行转换
        rgb_color = RGBColor.from_hex(hex_str)
        
        # 验证范围
        assert 0 <= rgb_color.r <= 255, f"R value out of range: {rgb_color.r}"
        assert 0 <= rgb_color.g <= 255, f"G value out of range: {rgb_color.g}"
        assert 0 <= rgb_color.b <= 255, f"B value out of range: {rgb_color.b}"
    
    @given(hex_color_strategy(), st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_light_controller_receives_correct_color(self, hex_data, brightness):
        """
        属性测试：灯光控制器正确接收转换后的颜色
        
        *For any* 有效的 HEX 颜色值，灯光控制器应正确接收并应用转换后的 RGB 值。
        
        **Feature: healing-pod-system, Property 16: 灯光颜色转换正确性**
        **Validates: Requirements 7.2**
        """
        hex_str, expected_rgb = hex_data
        
        # 创建并连接控制器
        controller = MockLightController("test_light")
        await controller.connect()
        
        # 使用 HEX 颜色设置灯光
        result = await controller.set_color(hex_str, brightness)
        
        # 验证设置成功
        assert result is True, "Failed to set color"
        
        # 验证控制器状态
        state = controller.current_state
        assert state is not None, "Controller state is None"
        
        # 验证颜色转换正确
        assert state.color.r == expected_rgb[0], f"Controller R mismatch: expected {expected_rgb[0]}, got {state.color.r}"
        assert state.color.g == expected_rgb[1], f"Controller G mismatch: expected {expected_rgb[1]}, got {state.color.g}"
        assert state.color.b == expected_rgb[2], f"Controller B mismatch: expected {expected_rgb[2]}, got {state.color.b}"
        
        # 验证亮度设置正确
        assert state.brightness == brightness, f"Brightness mismatch: expected {brightness}, got {state.brightness}"
        
        # 清理
        await controller.disconnect()
    
    @given(hex_color_strategy())
    @settings(max_examples=100)
    def test_hex_format_normalization(self, hex_data):
        """
        属性测试：HEX 格式标准化
        
        *For any* 有效的 HEX 颜色值（带或不带 # 前缀），转换结果应相同。
        
        **Feature: healing-pod-system, Property 16: 灯光颜色转换正确性**
        **Validates: Requirements 7.2**
        """
        hex_str, expected_rgb = hex_data
        
        # 获取不带 # 的版本
        hex_without_prefix = hex_str.lstrip('#')
        hex_with_prefix = '#' + hex_without_prefix
        
        # 两种格式都应该转换成功
        rgb_without = RGBColor.from_hex(hex_without_prefix)
        rgb_with = RGBColor.from_hex(hex_with_prefix)
        
        # 结果应该相同
        assert rgb_without.r == rgb_with.r, "R values differ between formats"
        assert rgb_without.g == rgb_with.g, "G values differ between formats"
        assert rgb_without.b == rgb_with.b, "B values differ between formats"
        
        # 都应该匹配预期值
        assert rgb_without.r == expected_rgb[0]
        assert rgb_without.g == expected_rgb[1]
        assert rgb_without.b == expected_rgb[2]
