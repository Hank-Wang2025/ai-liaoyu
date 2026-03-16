"""
AI 身份声明属性测试
AI Identity Disclosure Property Tests

Property 23: AI 身份声明
For any 对话会话的首次响应，系统 SHALL 在响应中包含 AI 助手身份声明。

**Feature: healing-pod-system, Property 23: AI 身份声明**
**Validates: Requirements 11.4**
"""
import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.qwen_dialog import (
    MockQwenDialogEngine,
    DialogResponse,
    DialogMessage,
    DialogRole
)


# AI 身份声明关键词 - 用于验证响应中包含身份声明
AI_DISCLOSURE_KEYWORDS = [
    "AI",
    "助手",
    "不能替代",
    "专业",
    "心理咨询"
]

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

# 英文对话消息策略
english_message_strategy = st.text(
    alphabet=st.sampled_from(
        "Hello I feel tired today work pressure is high"
        "I want to chat with you can you help me relax"
        "I am anxious and cannot sleep well"
    ),
    min_size=1,
    max_size=100
)

# 简短消息策略
short_message_strategy = st.text(
    alphabet=st.sampled_from("你好嗯是的好的谢谢明白了"),
    min_size=1,
    max_size=10
)


def contains_ai_disclosure(response_content: str) -> bool:
    """
    检查响应内容是否包含 AI 身份声明
    
    Args:
        response_content: 响应文本内容
        
    Returns:
        是否包含 AI 身份声明
    """
    # 检查是否包含关键词
    keyword_count = sum(1 for kw in AI_DISCLOSURE_KEYWORDS if kw in response_content)
    # 至少包含 3 个关键词才认为包含有效的 AI 身份声明
    return keyword_count >= 3


class TestAIIdentityDisclosureProperties:
    """
    AI 身份声明属性测试类
    
    **Feature: healing-pod-system, Property 23: AI 身份声明**
    **Validates: Requirements 11.4**
    """
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_first_response_contains_ai_disclosure(self, message):
        """
        Property 23: AI 身份声明 - 首次响应包含声明
        
        *For any* 对话会话的首次响应，系统 SHALL 在响应中包含 AI 助手身份声明。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        # 确保消息非空且有实际内容
        assume(len(message.strip()) > 0)
        
        # 创建新的对话引擎（新会话）
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 发送首条消息
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 验证属性：首次响应标记为 True
        assert response.is_first_response is True, \
            "首次响应的 is_first_response 标记应为 True"
        
        # 验证属性：contains_ai_disclosure 标记为 True
        assert response.contains_ai_disclosure is True, \
            "首次响应的 contains_ai_disclosure 标记应为 True"
        
        # 验证属性：响应内容包含 AI 身份声明关键词
        assert contains_ai_disclosure(response.content), \
            f"首次响应应包含 AI 身份声明，但响应内容为: {response.content[:200]}..."
    
    @given(message=english_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_first_response_english_contains_ai_disclosure(self, message):
        """
        Property 23: AI 身份声明 - 英文消息首次响应包含声明
        
        *For any* 英文对话会话的首次响应，系统 SHALL 在响应中包含 AI 助手身份声明。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 验证属性
        assert response.is_first_response is True
        assert response.contains_ai_disclosure is True
        assert contains_ai_disclosure(response.content)
    
    @given(message=short_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_first_response_short_message_contains_ai_disclosure(self, message):
        """
        Property 23: AI 身份声明 - 简短消息首次响应包含声明
        
        *For any* 简短对话消息的首次响应，系统 SHALL 在响应中包含 AI 助手身份声明。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 验证属性
        assert response.is_first_response is True
        assert response.contains_ai_disclosure is True
        assert contains_ai_disclosure(response.content)


class TestAIIdentityDisclosureOnlyOnFirstResponse:
    """
    AI 身份声明仅在首次响应测试
    
    验证 AI 身份声明仅在首次响应中出现，后续响应不重复
    """
    
    @given(
        message1=chinese_message_strategy,
        message2=chinese_message_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_23_second_response_no_disclosure_flag(self, message1, message2):
        """
        Property 23: AI 身份声明 - 第二次响应不标记为首次
        
        *For any* 对话会话的第二次及后续响应，系统 SHALL NOT 将其标记为首次响应。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        assume(len(message1.strip()) > 0)
        assume(len(message2.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 第一次对话
        response1 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message1)
        )
        
        # 第二次对话
        response2 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message2)
        )
        
        # 验证第一次响应包含声明
        assert response1.is_first_response is True
        assert response1.contains_ai_disclosure is True
        
        # 验证第二次响应不标记为首次响应
        assert response2.is_first_response is False, \
            "第二次响应的 is_first_response 标记应为 False"
        assert response2.contains_ai_disclosure is False, \
            "第二次响应的 contains_ai_disclosure 标记应为 False"
    
    @given(messages=st.lists(chinese_message_strategy, min_size=3, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_property_23_only_first_response_has_disclosure(self, messages):
        """
        Property 23: AI 身份声明 - 仅首次响应包含声明
        
        *For any* 多轮对话，仅第一次响应 SHALL 包含 AI 身份声明标记。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        valid_messages = [m for m in messages if len(m.strip()) > 0]
        assume(len(valid_messages) >= 3)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        responses = []
        for message in valid_messages:
            response = asyncio.get_event_loop().run_until_complete(
                engine.chat(message)
            )
            responses.append(response)
        
        # 验证仅第一次响应标记为首次
        assert responses[0].is_first_response is True
        assert responses[0].contains_ai_disclosure is True
        
        # 验证后续响应都不标记为首次
        for i, response in enumerate(responses[1:], start=2):
            assert response.is_first_response is False, \
                f"第 {i} 次响应的 is_first_response 应为 False"
            assert response.contains_ai_disclosure is False, \
                f"第 {i} 次响应的 contains_ai_disclosure 应为 False"


class TestAIIdentityDisclosureAfterSessionReset:
    """
    会话重置后 AI 身份声明测试
    
    验证会话重置后，首次响应重新包含 AI 身份声明
    """
    
    @given(
        message1=chinese_message_strategy,
        message2=chinese_message_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_property_23_disclosure_after_session_reset(self, message1, message2):
        """
        Property 23: AI 身份声明 - 会话重置后重新声明
        
        *For any* 会话重置后的首次响应，系统 SHALL 重新包含 AI 助手身份声明。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        assume(len(message1.strip()) > 0)
        assume(len(message2.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 第一次会话
        response1 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message1)
        )
        assert response1.is_first_response is True
        assert response1.contains_ai_disclosure is True
        
        # 重置会话
        engine.reset_session()
        
        # 重置后的首次响应
        response2 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message2)
        )
        
        # 验证重置后首次响应重新包含声明
        assert response2.is_first_response is True, \
            "会话重置后的首次响应 is_first_response 应为 True"
        assert response2.contains_ai_disclosure is True, \
            "会话重置后的首次响应 contains_ai_disclosure 应为 True"
        assert contains_ai_disclosure(response2.content), \
            "会话重置后的首次响应应包含 AI 身份声明"
    
    @given(
        message1=chinese_message_strategy,
        message2=chinese_message_strategy,
        message3=chinese_message_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_property_23_multiple_resets_disclosure(self, message1, message2, message3):
        """
        Property 23: AI 身份声明 - 多次重置后声明
        
        *For any* 多次会话重置，每次重置后的首次响应 SHALL 包含 AI 身份声明。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        assume(len(message1.strip()) > 0)
        assume(len(message2.strip()) > 0)
        assume(len(message3.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 第一次会话
        response1 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message1)
        )
        assert response1.is_first_response is True
        assert response1.contains_ai_disclosure is True
        
        # 第一次重置
        engine.reset_session()
        response2 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message2)
        )
        assert response2.is_first_response is True
        assert response2.contains_ai_disclosure is True
        
        # 第二次重置
        engine.reset_session()
        response3 = asyncio.get_event_loop().run_until_complete(
            engine.chat(message3)
        )
        assert response3.is_first_response is True
        assert response3.contains_ai_disclosure is True


class TestAIIdentityDisclosureContent:
    """
    AI 身份声明内容测试
    
    验证 AI 身份声明的具体内容要求
    """
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_disclosure_mentions_ai_identity(self, message):
        """
        Property 23: AI 身份声明 - 声明提及 AI 身份
        
        *For any* 首次响应中的 AI 身份声明，SHALL 明确提及 "AI" 身份。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 验证响应内容包含 "AI" 关键词
        assert "AI" in response.content, \
            "首次响应应明确提及 'AI' 身份"
    
    @given(message=chinese_message_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_23_disclosure_mentions_professional_help(self, message):
        """
        Property 23: AI 身份声明 - 声明提及专业帮助
        
        *For any* 首次响应中的 AI 身份声明，SHALL 提及不能替代专业心理咨询。
        
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        assume(len(message.strip()) > 0)
        
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = asyncio.get_event_loop().run_until_complete(
            engine.chat(message)
        )
        
        # 验证响应内容提及专业帮助相关内容
        professional_keywords = ["专业", "心理咨询", "不能替代"]
        has_professional_mention = any(kw in response.content for kw in professional_keywords)
        
        assert has_professional_mention, \
            "首次响应应提及不能替代专业心理咨询"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
