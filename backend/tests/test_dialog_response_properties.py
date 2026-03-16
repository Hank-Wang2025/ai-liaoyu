"""
对话响应属性测试
Dialog Response Property Tests

Property 22: 对话响应有效性
For any 用户发起的对话消息，Qwen3 模型 SHALL 在 5 秒内返回非空的响应文本。

**Feature: healing-pod-system, Property 22: 对话响应有效性**
**Validates: Requirements 11.1**
"""
import pytest
import asyncio
import time
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.qwen_dialog import (
    MockQwenDialogEngine,
    DialogResponse,
    DialogMessage,
    DialogRole,
    CrisisKeywordDetector,
    create_dialog_engine
)


# 中文对话消息策略 - 生成有效的中文对话文本
chinese_message_strategy = st.text(
    alphabet=st.sampled_from(
        "你好我今天感觉有点累最近工作压力很大心情不太好"
        "想和你聊聊天能帮我放松一下吗谢谢你的陪伴"
        "我有些焦虑睡眠不好希望能得到一些建议"
        "生活中遇到了一些困难不知道该怎么办"
        "感觉很孤独需要有人倾听我的心声"
    ),
    min_size=1,
    max_size=200
)

# 混合语言消息策略 - 包含中英文
mixed_message_strategy = st.text(
    alphabet=st.sampled_from(
        "你好Hello我今天feeling有点tired最近work压力很大"
        "心情不太好想和你chat能帮我relax一下吗thanks"
    ),
    min_size=1,
    max_size=100
)

# 简短消息策略 - 模拟简短的用户输入
short_message_strategy = st.text(
    alphabet=st.sampled_from("你好嗯是的好的谢谢明白了"),
    min_size=1,
    max_size=10
)

# 长消息策略 - 模拟较长的用户倾诉
long_message_strategy = st.text(
    alphabet=st.sampled_from(
        "我今天遇到了很多事情让我感到非常疲惫和焦虑"
        "工作上的压力越来越大同事之间的关系也变得复杂"
        "回到家里也没有人可以倾诉感觉很孤独"
        "有时候真的不知道该怎么继续下去"
        "希望能有人理解我的感受给我一些支持和鼓励"
    ),
    min_size=50,
    max_size=500
)


class TestDialogResponseProperties:
    """
    对话响应属性测试类
    
    **Feature: healing-pod-system, Property 22: 对话响应有效性**
    **Validates: Requirements 11.1**
    """
    
    @pytest.fixture
    def dialog_engine(self):
        """创建并初始化 Mock 对话引擎"""
        engine = MockQwenDialogEngine()
        engine.initialize()
        return engine
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_chinese_message_returns_non_empty_response(self, message):
        """
        Property 22: 对话响应有效性 - 中文消息
        
        *For any* 用户发起的中文对话消息，Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        # 确保消息非空且有实际内容
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 记录开始时间
        start_time = time.time()
        
        # 运行异步对话
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 记录结束时间
        elapsed_time = time.time() - start_time
        
        # 验证属性：响应非空
        assert response is not None, "对话响应不应为 None"
        assert isinstance(response, DialogResponse), "响应应为 DialogResponse 类型"
        assert response.content is not None, "响应内容不应为 None"
        assert len(response.content) > 0, "响应内容长度应大于 0"
        assert len(response.content.strip()) > 0, "响应内容不应只包含空白字符"
        
        # 验证响应时间约束（5秒内）
        assert elapsed_time < 5.0, f"响应时间 {elapsed_time:.2f}s 超过 5 秒限制"
    
    @given(message=mixed_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_mixed_language_message_returns_non_empty_response(self, message):
        """
        Property 22: 对话响应有效性 - 混合语言消息
        
        *For any* 包含中英文的用户对话消息，Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        start_time = time.time()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        elapsed_time = time.time() - start_time
        
        # 验证属性
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert elapsed_time < 5.0
    
    @given(message=short_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_short_message_returns_non_empty_response(self, message):
        """
        Property 22: 对话响应有效性 - 简短消息
        
        *For any* 简短的用户对话消息，Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        start_time = time.time()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        elapsed_time = time.time() - start_time
        
        # 验证属性
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert elapsed_time < 5.0
    
    @given(message=long_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_long_message_returns_non_empty_response(self, message):
        """
        Property 22: 对话响应有效性 - 长消息
        
        *For any* 较长的用户倾诉消息，Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        start_time = time.time()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        elapsed_time = time.time() - start_time
        
        # 验证属性
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert elapsed_time < 5.0


class TestDialogResponseInvariants:
    """
    对话响应不变量测试
    
    验证 DialogResponse 的不变量
    """
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_dialog_response_invariants(self, message):
        """
        测试对话响应的不变量
        
        *For any* 成功的对话，响应 SHALL 满足以下不变量：
        - content 非空
        - generation_time_ms 为非负整数
        - timestamp 存在
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 验证不变量
        assert response.content is not None and len(response.content) > 0
        assert response.generation_time_ms >= 0
        assert response.timestamp is not None
        assert isinstance(response.is_first_response, bool)
        assert isinstance(response.contains_ai_disclosure, bool)
        assert isinstance(response.contains_crisis_warning, bool)
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_dialog_history_consistency(self, message):
        """
        测试对话历史一致性
        
        *For any* 成功的对话，对话历史 SHALL 正确记录用户消息和助手响应。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 清除历史确保干净状态
        engine.clear_history()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 验证历史记录
        history = engine.get_history()
        assert len(history) >= 2, "历史应至少包含用户消息和助手响应"
        
        # 验证最后两条记录
        user_msg = history[-2]
        assistant_msg = history[-1]
        
        assert user_msg.role == DialogRole.USER
        assert user_msg.content == message
        assert assistant_msg.role == DialogRole.ASSISTANT
        assert assistant_msg.content == response.content


class TestMultiTurnDialogProperties:
    """
    多轮对话属性测试
    
    验证多轮对话场景下的响应有效性
    """
    
    @given(
        message1=chinese_message_strategy,
        message2=chinese_message_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_22_multi_turn_dialog_returns_non_empty_responses(self, message1, message2):
        """
        Property 22: 对话响应有效性 - 多轮对话
        
        *For any* 多轮对话中的每条用户消息，Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message1.strip()) > 0)
        assume(len(message2.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 第一轮对话
        start_time1 = time.time()
        response1 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message1)
        )
        elapsed_time1 = time.time() - start_time1
        
        # 第二轮对话
        start_time2 = time.time()
        response2 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message2)
        )
        elapsed_time2 = time.time() - start_time2
        
        # 验证两轮对话的响应都有效
        assert response1 is not None and response1.content is not None
        assert len(response1.content) > 0
        assert elapsed_time1 < 5.0
        
        assert response2 is not None and response2.content is not None
        assert len(response2.content) > 0
        assert elapsed_time2 < 5.0
        
        # 验证首次响应标记
        assert response1.is_first_response is True
        assert response2.is_first_response is False
    
    @given(messages=st.lists(chinese_message_strategy, min_size=3, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_property_22_extended_dialog_returns_non_empty_responses(self, messages):
        """
        Property 22: 对话响应有效性 - 扩展多轮对话
        
        *For any* 扩展多轮对话（3-5轮）中的每条用户消息，
        Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        # 过滤空消息
        valid_messages = [m for m in messages if len(m.strip()) > 0]
        assume(len(valid_messages) >= 3)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        responses = []
        for i, message in enumerate(valid_messages):
            start_time = time.time()
            response = asyncio.get_event_loop().run_until_complete(
                engine.chat(message)
            )
            elapsed_time = time.time() - start_time
            
            # 验证每轮响应
            assert response is not None, f"第 {i+1} 轮响应不应为 None"
            assert response.content is not None, f"第 {i+1} 轮响应内容不应为 None"
            assert len(response.content) > 0, f"第 {i+1} 轮响应内容长度应大于 0"
            assert elapsed_time < 5.0, f"第 {i+1} 轮响应时间超过 5 秒"
            
            responses.append(response)
        
        # 验证首次响应标记只在第一轮为 True
        assert responses[0].is_first_response is True
        for response in responses[1:]:
            assert response.is_first_response is False


class TestDialogWithCrisisDetection:
    """
    带危机检测的对话属性测试
    
    验证危机检测场景下的响应有效性
    """
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_with_crisis_check_returns_non_empty_response(self, message):
        """
        Property 22: 对话响应有效性 - 带危机检测
        
        *For any* 用户消息（启用危机检测），Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        start_time = time.time()
        
        # 启用危机检测
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message, check_crisis=True)
        )
        
        elapsed_time = time.time() - start_time
        
        # 验证属性
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert elapsed_time < 5.0
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_22_without_crisis_check_returns_non_empty_response(self, message):
        """
        Property 22: 对话响应有效性 - 不带危机检测
        
        *For any* 用户消息（禁用危机检测），Qwen3 模型 SHALL 返回非空的响应文本。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        start_time = time.time()
        
        # 禁用危机检测
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message, check_crisis=False)
        )
        
        elapsed_time = time.time() - start_time
        
        # 验证属性
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert elapsed_time < 5.0


class TestSessionResetProperties:
    """
    会话重置属性测试
    
    验证会话重置后的响应有效性
    """
    
    @given(
        message1=chinese_message_strategy,
        message2=chinese_message_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_22_after_session_reset_returns_non_empty_response(self, message1, message2):
        """
        Property 22: 对话响应有效性 - 会话重置后
        
        *For any* 会话重置后的用户消息，Qwen3 模型 SHALL 返回非空的响应文本，
        且首次响应标记应重新为 True。
        
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        assume(len(message1.strip()) > 0)
        assume(len(message2.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 第一轮对话
        response1 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message1)
        )
        assert response1.is_first_response is True
        
        # 重置会话
        engine.reset_session()
        
        # 重置后的对话
        start_time = time.time()
        response2 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message2)
        )
        elapsed_time = time.time() - start_time
        
        # 验证属性
        assert response2 is not None
        assert response2.content is not None
        assert len(response2.content) > 0
        assert elapsed_time < 5.0
        
        # 验证重置后首次响应标记重新为 True
        assert response2.is_first_response is True
        assert response2.contains_ai_disclosure is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
