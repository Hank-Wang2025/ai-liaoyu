"""
灯光过渡平滑性属性测试
Light Transition Smoothness Property Tests

**Feature: healing-pod-system, Property 17: 灯光过渡平滑性**
**Validates: Requirements 7.3**

Property 17: 灯光过渡平滑性
*For any* 灯光状态切换，控制器 SHALL 使用配置的过渡时间进行渐变，而非瞬间切换。

测试策略：
1. 验证过渡使用配置的过渡时间
2. 验证过渡产生中间状态（渐变而非瞬间切换）
3. 验证过渡步数影响中间状态数量
4. 验证过渡后最终状态正确
"""
import pytest
import sys
import os
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.light_controller import (
    RGBColor,
    MockLightController,
    LightTransitionController,
)


# Custom strategies for light transition testing
@st.composite
def rgb_color_strategy(draw):
    """生成有效的 RGB 颜色"""
    r = draw(st.integers(min_value=0, max_value=255))
    g = draw(st.integers(min_value=0, max_value=255))
    b = draw(st.integers(min_value=0, max_value=255))
    return RGBColor(r=r, g=g, b=b)


@st.composite
def transition_params_strategy(draw):
    """生成有效的过渡参数"""
    start_color = draw(rgb_color_strategy())
    end_color = draw(rgb_color_strategy())
    start_brightness = draw(st.integers(min_value=0, max_value=100))
    end_brightness = draw(st.integers(min_value=0, max_value=100))
    # Use small duration for faster tests, but enough steps to verify gradual transition
    duration_ms = draw(st.integers(min_value=50, max_value=200))
    steps = draw(st.integers(min_value=3, max_value=10))
    return {
        'start_color': start_color,
        'end_color': end_color,
        'start_brightness': start_brightness,
        'end_brightness': end_brightness,
        'duration_ms': duration_ms,
        'steps': steps
    }


class TestLightTransitionSmoothnessProperties:
    """
    灯光过渡平滑性属性测试
    
    **Feature: healing-pod-system, Property 17: 灯光过渡平滑性**
    **Validates: Requirements 7.3**
    """
    
    @given(transition_params_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_transition_produces_intermediate_states(self, params):
        """
        属性测试：过渡产生中间状态
        
        *For any* 灯光状态切换，控制器 SHALL 产生多个中间状态，
        实现渐变过渡而非瞬间切换。
        
        **Feature: healing-pod-system, Property 17: 灯光过渡平滑性**
        **Validates: Requirements 7.3**
        """
        # 创建并连接控制器
        controller = MockLightController("test_light")
        await controller.connect()
        
        # 设置初始状态
        await controller.set_rgb(
            params['start_color'],
            params['start_brightness']
        )
        
        # 创建过渡控制器
        tc = LightTransitionController(controller)
        
        # 执行过渡
        result = await tc.smooth_transition(
            params['end_color'],
            params['end_brightness'],
            duration_ms=params['duration_ms'],
            steps=params['steps']
        )
        
        # 验证过渡成功
        assert result is True, "Transition should succeed"
        
        # 验证命令历史记录了多个 set_rgb 调用（渐变而非瞬间）
        set_rgb_commands = [
            cmd for cmd in controller.command_history
            if cmd['action'] == 'set_rgb'
        ]
        
        # 应该有初始设置 + 过渡步数的 set_rgb 调用
        # 初始设置 1 次 + 过渡 steps 次
        expected_min_commands = params['steps'] + 1
        assert len(set_rgb_commands) >= expected_min_commands, \
            f"Expected at least {expected_min_commands} set_rgb commands for gradual transition, got {len(set_rgb_commands)}"
        
        # 清理
        await controller.disconnect()
    
    @given(transition_params_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_transition_uses_configured_transition_time(self, params):
        """
        属性测试：过渡使用配置的过渡时间
        
        *For any* 灯光状态切换，每个中间步骤 SHALL 使用基于配置过渡时间
        计算的步骤过渡时间。
        
        **Feature: healing-pod-system, Property 17: 灯光过渡平滑性**
        **Validates: Requirements 7.3**
        """
        # 创建并连接控制器
        controller = MockLightController("test_light")
        await controller.connect()
        
        # 设置初始状态
        await controller.set_rgb(
            params['start_color'],
            params['start_brightness']
        )
        
        # 创建过渡控制器
        tc = LightTransitionController(controller)
        
        # 执行过渡
        await tc.smooth_transition(
            params['end_color'],
            params['end_brightness'],
            duration_ms=params['duration_ms'],
            steps=params['steps']
        )
        
        # 获取过渡期间的 set_rgb 命令（排除初始设置）
        set_rgb_commands = [
            cmd for cmd in controller.command_history
            if cmd['action'] == 'set_rgb'
        ][1:]  # 排除初始设置
        
        # 验证每个步骤都有过渡时间参数
        expected_step_transition = int(params['duration_ms'] / params['steps'])
        
        for cmd in set_rgb_commands:
            # 每个命令应该有 transition_ms 参数
            assert 'transition_ms' in cmd, "Each step should have transition_ms"
            # 过渡时间应该是基于总时间和步数计算的
            assert cmd['transition_ms'] == expected_step_transition, \
                f"Step transition time should be {expected_step_transition}ms, got {cmd['transition_ms']}ms"
        
        # 清理
        await controller.disconnect()
    
    @given(transition_params_strategy())
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_transition_final_state_matches_target(self, params):
        """
        属性测试：过渡后最终状态正确
        
        *For any* 灯光状态切换，过渡完成后的最终状态 SHALL 与目标状态匹配。
        
        **Feature: healing-pod-system, Property 17: 灯光过渡平滑性**
        **Validates: Requirements 7.3**
        """
        # 创建并连接控制器
        controller = MockLightController("test_light")
        await controller.connect()
        
        # 设置初始状态
        await controller.set_rgb(
            params['start_color'],
            params['start_brightness']
        )
        
        # 创建过渡控制器
        tc = LightTransitionController(controller)
        
        # 执行过渡
        result = await tc.smooth_transition(
            params['end_color'],
            params['end_brightness'],
            duration_ms=params['duration_ms'],
            steps=params['steps']
        )
        
        assert result is True, "Transition should succeed"
        
        # 验证最终状态
        final_state = controller.current_state
        assert final_state is not None, "Final state should not be None"
        
        # 最终颜色应该与目标颜色匹配
        assert final_state.color.r == params['end_color'].r, \
            f"Final R should be {params['end_color'].r}, got {final_state.color.r}"
        assert final_state.color.g == params['end_color'].g, \
            f"Final G should be {params['end_color'].g}, got {final_state.color.g}"
        assert final_state.color.b == params['end_color'].b, \
            f"Final B should be {params['end_color'].b}, got {final_state.color.b}"
        
        # 最终亮度应该与目标亮度匹配
        assert final_state.brightness == params['end_brightness'], \
            f"Final brightness should be {params['end_brightness']}, got {final_state.brightness}"
        
        # 清理
        await controller.disconnect()
    
    @given(
        rgb_color_strategy(),
        rgb_color_strategy(),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_transition_intermediate_values_are_interpolated(
        self, start_color, end_color, start_brightness, end_brightness, steps
    ):
        """
        属性测试：中间值是线性插值的
        
        *For any* 灯光状态切换，中间状态的颜色和亮度值 SHALL 是
        起始值和目标值之间的线性插值。
        
        **Feature: healing-pod-system, Property 17: 灯光过渡平滑性**
        **Validates: Requirements 7.3**
        """
        # 创建并连接控制器
        controller = MockLightController("test_light")
        await controller.connect()
        
        # 设置初始状态
        await controller.set_rgb(start_color, start_brightness)
        
        # 创建过渡控制器
        tc = LightTransitionController(controller)
        
        # 执行过渡
        await tc.smooth_transition(
            end_color,
            end_brightness,
            duration_ms=100,  # 快速过渡用于测试
            steps=steps
        )
        
        # 获取过渡期间的 set_rgb 命令（排除初始设置）
        set_rgb_commands = [
            cmd for cmd in controller.command_history
            if cmd['action'] == 'set_rgb'
        ][1:]  # 排除初始设置
        
        # 验证中间值是单调变化的（朝向目标值）
        # 对于每个颜色分量和亮度，值应该在起始和目标之间
        for i, cmd in enumerate(set_rgb_commands):
            progress = (i + 1) / steps
            
            # 计算预期的插值
            expected_r = int(start_color.r + (end_color.r - start_color.r) * progress)
            expected_g = int(start_color.g + (end_color.g - start_color.g) * progress)
            expected_b = int(start_color.b + (end_color.b - start_color.b) * progress)
            expected_brightness = int(start_brightness + (end_brightness - start_brightness) * progress)
            
            actual_r, actual_g, actual_b = cmd['color']
            actual_brightness = cmd['brightness']
            
            # 验证值与预期插值匹配
            assert actual_r == expected_r, \
                f"Step {i+1}: R should be {expected_r}, got {actual_r}"
            assert actual_g == expected_g, \
                f"Step {i+1}: G should be {expected_g}, got {actual_g}"
            assert actual_b == expected_b, \
                f"Step {i+1}: B should be {expected_b}, got {actual_b}"
            assert actual_brightness == expected_brightness, \
                f"Step {i+1}: Brightness should be {expected_brightness}, got {actual_brightness}"
        
        # 清理
        await controller.disconnect()
    
    @given(
        rgb_color_strategy(),
        st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_transition_without_initial_state_sets_directly(
        self, target_color, target_brightness
    ):
        """
        属性测试：无初始状态时直接设置
        
        *For any* 没有初始状态的灯光控制器，过渡 SHALL 直接设置目标状态
        并使用配置的过渡时间。
        
        **Feature: healing-pod-system, Property 17: 灯光过渡平滑性**
        **Validates: Requirements 7.3**
        """
        # 创建并连接控制器（不设置初始状态）
        controller = MockLightController("test_light")
        await controller.connect()
        
        # 创建过渡控制器
        tc = LightTransitionController(controller)
        
        duration_ms = 3000  # 默认过渡时间
        
        # 执行过渡（无初始状态）
        result = await tc.smooth_transition(
            target_color,
            target_brightness,
            duration_ms=duration_ms
        )
        
        assert result is True, "Transition should succeed"
        
        # 验证直接设置了目标状态
        final_state = controller.current_state
        assert final_state is not None, "Final state should not be None"
        assert final_state.color.r == target_color.r
        assert final_state.color.g == target_color.g
        assert final_state.color.b == target_color.b
        assert final_state.brightness == target_brightness
        
        # 验证使用了配置的过渡时间
        set_rgb_commands = [
            cmd for cmd in controller.command_history
            if cmd['action'] == 'set_rgb'
        ]
        assert len(set_rgb_commands) == 1, "Should have exactly one set_rgb command"
        assert set_rgb_commands[0]['transition_ms'] == duration_ms, \
            f"Should use configured transition time {duration_ms}ms"
        
        # 清理
        await controller.disconnect()
