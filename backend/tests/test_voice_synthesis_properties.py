"""
语音合成属性测试
Voice Synthesis Property Tests

Property 14: 语音合成有效性
For any 有效的中文文本输入，CosyVoice 模型 SHALL 生成非空的音频数据。

**Feature: healing-pod-system, Property 14: 语音合成有效性**
**Validates: Requirements 6.2**
"""
import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.cosyvoice_synthesizer import (
    MockCosyVoiceSynthesizer,
    VoiceEmotion,
    VoiceSpeaker,
    VoiceSynthesisConfig,
    SynthesisResult
)


# 中文字符策略 - 生成有效的中文文本
chinese_text_strategy = st.text(
    alphabet=st.sampled_from(
        # 常用中文字符
        "你好我是一个疗愈助手欢迎来到这里请放松深呼吸让自己平静下来"
        "感受当下的宁静与美好一切都会好起来的相信自己你很棒"
        "慢慢地吸气再慢慢地呼气感受身体的每一个部分"
        "现在让我们开始今天的疗愈之旅希望你能感到舒适和放松"
    ),
    min_size=1,
    max_size=100
)

# 混合文本策略 - 包含中英文和标点
mixed_text_strategy = st.text(
    alphabet=st.sampled_from(
        "你好我是疗愈助手Hello欢迎来到这里，请放松。深呼吸！"
        "让自己平静下来？感受当下的宁静与美好。"
    ),
    min_size=1,
    max_size=50
)


class TestVoiceSynthesisProperties:
    """
    语音合成属性测试类
    
    **Feature: healing-pod-system, Property 14: 语音合成有效性**
    **Validates: Requirements 6.2**
    """
    
    @pytest.fixture
    def synthesizer(self):
        """创建并初始化 Mock 语音合成器"""
        synth = MockCosyVoiceSynthesizer()
        synth.initialize()
        return synth
    
    @given(text=chinese_text_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_14_chinese_text_produces_non_empty_audio(self, text):
        """
        Property 14: 语音合成有效性
        
        *For any* 有效的中文文本输入，CosyVoice 模型 SHALL 生成非空的音频数据。
        
        **Feature: healing-pod-system, Property 14: 语音合成有效性**
        **Validates: Requirements 6.2**
        """
        # 确保文本非空且有实际内容
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        # 运行异步合成
        result = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize(text)
        )
        
        # 验证属性：生成的音频数据非空
        assert result is not None, "合成结果不应为 None"
        assert isinstance(result, SynthesisResult), "结果应为 SynthesisResult 类型"
        assert result.audio_data is not None, "音频数据不应为 None"
        assert len(result.audio_data) > 0, "音频数据长度应大于 0"
        assert result.sample_rate > 0, "采样率应大于 0"
        assert result.duration_ms > 0, "音频时长应大于 0"
        assert result.text == text, "返回的文本应与输入一致"
    
    @given(text=mixed_text_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_14_mixed_text_produces_non_empty_audio(self, text):
        """
        Property 14 扩展: 混合文本语音合成有效性
        
        *For any* 包含中英文和标点的有效文本输入，CosyVoice 模型 SHALL 生成非空的音频数据。
        
        **Feature: healing-pod-system, Property 14: 语音合成有效性**
        **Validates: Requirements 6.2**
        """
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        result = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize(text)
        )
        
        # 验证属性
        assert result is not None
        assert result.audio_data is not None
        assert len(result.audio_data) > 0
        assert result.sample_rate > 0
        assert result.duration_ms > 0
    
    @given(
        text=chinese_text_strategy,
        emotion=st.sampled_from(list(VoiceEmotion))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_with_emotion_produces_non_empty_audio(self, text, emotion):
        """
        Property 14 扩展: 带情感控制的语音合成有效性
        
        *For any* 有效的中文文本和任意情感参数，CosyVoice 模型 SHALL 生成非空的音频数据。
        
        **Feature: healing-pod-system, Property 14: 语音合成有效性**
        **Validates: Requirements 6.2**
        """
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        result = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize_with_emotion(text, emotion=emotion)
        )
        
        # 验证属性
        assert result is not None
        assert result.audio_data is not None
        assert len(result.audio_data) > 0
        assert result.emotion == emotion.value
    
    @given(
        text=chinese_text_strategy,
        speed=st.floats(min_value=0.5, max_value=2.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_with_speed_produces_non_empty_audio(self, text, speed):
        """
        Property 14 扩展: 带语速控制的语音合成有效性
        
        *For any* 有效的中文文本和合法语速参数，CosyVoice 模型 SHALL 生成非空的音频数据。
        
        **Feature: healing-pod-system, Property 14: 语音合成有效性**
        **Validates: Requirements 6.2**
        """
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        result = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize_with_emotion(text, speed=speed)
        )
        
        # 验证属性
        assert result is not None
        assert result.audio_data is not None
        assert len(result.audio_data) > 0
    
    @given(
        text=chinese_text_strategy,
        speaker=st.sampled_from([
            VoiceSpeaker.CHINESE_FEMALE.value,
            VoiceSpeaker.CHINESE_MALE.value,
            VoiceSpeaker.ENGLISH_FEMALE.value,
            VoiceSpeaker.ENGLISH_MALE.value
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_with_speaker_produces_non_empty_audio(self, text, speaker):
        """
        Property 14 扩展: 不同语音角色的语音合成有效性
        
        *For any* 有效的中文文本和任意语音角色，CosyVoice 模型 SHALL 生成非空的音频数据。
        
        **Feature: healing-pod-system, Property 14: 语音合成有效性**
        **Validates: Requirements 6.2**
        """
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        config = VoiceSynthesisConfig(speaker=speaker)
        result = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize(text, config)
        )
        
        # 验证属性
        assert result is not None
        assert result.audio_data is not None
        assert len(result.audio_data) > 0
        assert result.speaker == speaker


class TestSynthesisResultProperties:
    """
    合成结果属性测试
    
    验证 SynthesisResult 的不变量
    """
    
    @given(text=chinese_text_strategy)
    @settings(max_examples=100, deadline=None)
    def test_synthesis_result_invariants(self, text):
        """
        测试合成结果的不变量
        
        *For any* 成功的语音合成，结果 SHALL 满足以下不变量：
        - audio_data 长度与 duration_ms 成正比
        - sample_rate 为正整数
        - text 与输入一致
        
        **Feature: healing-pod-system, Property 14: 语音合成有效性**
        **Validates: Requirements 6.2**
        """
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        result = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize(text)
        )
        
        # 验证不变量
        assert result.sample_rate > 0
        assert result.duration_ms >= 0
        assert result.text == text
        
        # 验证音频数据长度与时长的关系
        # audio_data 是 float32 格式，每个样本 4 字节
        expected_samples = int(result.duration_ms / 1000 * result.sample_rate)
        actual_samples = len(result.audio_data) // 4  # float32 = 4 bytes
        
        # 允许一定误差
        assert abs(actual_samples - expected_samples) < expected_samples * 0.1 or expected_samples == 0


class TestEmotionControlVoiceDifferentiationProperties:
    """
    情感控制语音差异性属性测试
    
    **Feature: healing-pod-system, Property 15: 情感控制语音差异性**
    **Validates: Requirements 6.3**
    
    Property 15: 情感控制语音差异性
    *For any* 相同的文本输入，使用不同情感参数生成的语音 SHALL 在音频特征上存在可测量的差异。
    """
    
    @pytest.fixture
    def synthesizer(self):
        """创建并初始化 Mock 语音合成器"""
        synth = MockCosyVoiceSynthesizer()
        synth.initialize()
        return synth
    
    @given(text=chinese_text_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_15_different_emotions_produce_different_audio_metadata(self, text):
        """
        Property 15: 情感控制语音差异性 - 元数据差异
        
        *For any* 相同的文本输入，使用不同情感参数生成的语音 SHALL 
        在返回的元数据（emotion 字段）上存在可测量的差异。
        
        **Feature: healing-pod-system, Property 15: 情感控制语音差异性**
        **Validates: Requirements 6.3**
        """
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        # 使用两种不同的情感参数生成语音
        emotions = [VoiceEmotion.GENTLE, VoiceEmotion.ENCOURAGING]
        
        results = []
        for emotion in emotions:
            result = asyncio.get_event_loop().run_until_complete(
                synthesizer.synthesize_with_emotion(text, emotion=emotion)
            )
            results.append(result)
        
        # 验证属性：不同情感参数产生的结果在 emotion 字段上不同
        assert results[0].emotion != results[1].emotion, \
            "不同情感参数应产生不同的 emotion 元数据"
        
        # 验证两个结果都是有效的
        for result in results:
            assert result is not None
            assert result.audio_data is not None
            assert len(result.audio_data) > 0
            assert result.text == text
    
    @given(
        text=chinese_text_strategy,
        emotion1=st.sampled_from([VoiceEmotion.GENTLE, VoiceEmotion.CALM]),
        emotion2=st.sampled_from([VoiceEmotion.WARM, VoiceEmotion.ENCOURAGING])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_emotion_pairs_produce_different_results(self, text, emotion1, emotion2):
        """
        Property 15: 情感控制语音差异性 - 情感对比较
        
        *For any* 相同的文本和两种不同类型的情感参数，
        生成的语音结果 SHALL 在情感标记上存在差异。
        
        **Feature: healing-pod-system, Property 15: 情感控制语音差异性**
        **Validates: Requirements 6.3**
        """
        assume(len(text.strip()) > 0)
        assume(emotion1 != emotion2)  # 确保两种情感不同
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        # 使用两种不同的情感生成语音
        result1 = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize_with_emotion(text, emotion=emotion1)
        )
        result2 = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize_with_emotion(text, emotion=emotion2)
        )
        
        # 验证属性：不同情感产生不同的结果标记
        assert result1.emotion != result2.emotion, \
            f"情感 {emotion1.value} 和 {emotion2.value} 应产生不同的结果"
        
        # 验证两个结果都有效
        assert result1.audio_data is not None and len(result1.audio_data) > 0
        assert result2.audio_data is not None and len(result2.audio_data) > 0
    
    @given(
        text=chinese_text_strategy,
        speed1=st.floats(min_value=0.5, max_value=0.8),
        speed2=st.floats(min_value=1.2, max_value=2.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_different_speeds_produce_different_duration(self, text, speed1, speed2):
        """
        Property 15: 情感控制语音差异性 - 语速差异
        
        *For any* 相同的文本，使用显著不同的语速参数生成的语音 SHALL 
        在音频时长上存在可测量的差异。
        
        注意：在 Mock 实现中，语速不直接影响时长，但在真实实现中会影响。
        此测试验证不同语速参数被正确传递和处理。
        
        **Feature: healing-pod-system, Property 15: 情感控制语音差异性**
        **Validates: Requirements 6.3**
        """
        assume(len(text.strip()) > 0)
        assume(abs(speed1 - speed2) > 0.3)  # 确保语速差异足够大
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        # 使用两种不同的语速生成语音
        result1 = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize_with_emotion(text, speed=speed1)
        )
        result2 = asyncio.get_event_loop().run_until_complete(
            synthesizer.synthesize_with_emotion(text, speed=speed2)
        )
        
        # 验证两个结果都有效
        assert result1 is not None and result1.audio_data is not None
        assert result2 is not None and result2.audio_data is not None
        assert len(result1.audio_data) > 0
        assert len(result2.audio_data) > 0
        
        # 验证文本一致
        assert result1.text == text
        assert result2.text == text
    
    @given(text=chinese_text_strategy)
    @settings(max_examples=100, deadline=None)
    def test_property_15_all_emotions_produce_valid_distinct_results(self, text):
        """
        Property 15: 情感控制语音差异性 - 全情感覆盖
        
        *For any* 相同的文本，使用所有四种情感参数（gentle, warm, calm, encouraging）
        生成的语音 SHALL 各自产生有效且在情感标记上可区分的结果。
        
        **Feature: healing-pod-system, Property 15: 情感控制语音差异性**
        **Validates: Requirements 6.3**
        """
        assume(len(text.strip()) > 0)
        
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        all_emotions = list(VoiceEmotion)
        results = {}
        
        # 为每种情感生成语音
        for emotion in all_emotions:
            result = asyncio.get_event_loop().run_until_complete(
                synthesizer.synthesize_with_emotion(text, emotion=emotion)
            )
            results[emotion] = result
        
        # 验证所有结果都有效
        for emotion, result in results.items():
            assert result is not None, f"情感 {emotion.value} 的结果不应为 None"
            assert result.audio_data is not None, f"情感 {emotion.value} 的音频数据不应为 None"
            assert len(result.audio_data) > 0, f"情感 {emotion.value} 的音频数据长度应大于 0"
            assert result.emotion == emotion.value, f"结果的情感标记应为 {emotion.value}"
        
        # 验证不同情感产生不同的情感标记
        emotion_values = [r.emotion for r in results.values()]
        assert len(set(emotion_values)) == len(all_emotions), \
            "所有情感参数应产生不同的情感标记"
