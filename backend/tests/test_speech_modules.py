"""
语音模块验证测试
Speech Module Verification Tests

Checkpoint 3: 验证 SenseVoice 和 emotion2vec+ 模型正常工作
"""
import os
import sys
import tempfile
from datetime import datetime

import pytest
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import (
    AudioAnalysisResult, 
    Emotion2VecResult, 
    EmotionCategory, 
    AudioEvent,
    SupportedLanguage
)
from services.audio_preprocessor import AudioPreprocessor
from services.sensevoice_analyzer import SenseVoiceAnalyzer
from services.emotion2vec_analyzer import Emotion2VecAnalyzer


class TestAudioPreprocessor:
    """音频预处理器测试"""
    
    def test_preprocessor_initialization(self):
        """测试预处理器初始化"""
        preprocessor = AudioPreprocessor()
        assert preprocessor.target_sample_rate == 16000
        
    def test_supported_formats(self):
        """测试支持的音频格式"""
        preprocessor = AudioPreprocessor()
        assert preprocessor.is_supported_format("test.wav")
        assert preprocessor.is_supported_format("test.mp3")
        assert preprocessor.is_supported_format("test.flac")
        assert preprocessor.is_supported_format("test.ogg")
        assert preprocessor.is_supported_format("test.m4a")
        assert not preprocessor.is_supported_format("test.txt")
        assert not preprocessor.is_supported_format("test.pdf")
        
    def test_to_mono_single_channel(self):
        """测试单声道转换 - 已是单声道"""
        preprocessor = AudioPreprocessor()
        mono_audio = np.array([0.1, 0.2, 0.3, 0.4])
        result = preprocessor.to_mono(mono_audio)
        np.testing.assert_array_equal(result, mono_audio)
        
    def test_to_mono_stereo(self):
        """测试单声道转换 - 立体声"""
        preprocessor = AudioPreprocessor()
        stereo_audio = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        result = preprocessor.to_mono(stereo_audio)
        expected = np.array([0.15, 0.35, 0.55], dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)
        
    def test_normalize(self):
        """测试音频归一化"""
        preprocessor = AudioPreprocessor()
        audio = np.array([0.5, -1.0, 0.25, 0.75])
        result = preprocessor.normalize(audio)
        assert np.max(np.abs(result)) <= 1.0
        assert np.max(np.abs(result)) == 1.0  # 最大值应该是1
        
    def test_normalize_zero_audio(self):
        """测试零音频归一化"""
        preprocessor = AudioPreprocessor()
        audio = np.array([0.0, 0.0, 0.0])
        result = preprocessor.normalize(audio)
        np.testing.assert_array_equal(result, audio)


class TestSenseVoiceAnalyzer:
    """SenseVoice 分析器测试"""
    
    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = SenseVoiceAnalyzer()
        assert analyzer.model_dir == "iic/SenseVoiceSmall"
        assert analyzer.device == "cpu"
        assert analyzer.use_vad == True
        assert not analyzer.is_initialized()
        
    def test_supported_languages(self):
        """测试支持的语言列表"""
        analyzer = SenseVoiceAnalyzer()
        languages = analyzer.get_supported_languages()
        assert "zh" in languages
        assert "en" in languages
        assert "yue" in languages
        assert "ja" in languages
        assert "ko" in languages
        assert "auto" in languages
        
    def test_emotion_labels(self):
        """测试情感标签列表"""
        analyzer = SenseVoiceAnalyzer()
        labels = analyzer.get_emotion_labels()
        assert "happy" in labels
        assert "sad" in labels
        assert "angry" in labels
        assert "neutral" in labels
        
    def test_audio_events(self):
        """测试音频事件列表"""
        analyzer = SenseVoiceAnalyzer()
        events = analyzer.get_audio_events()
        assert "laughter" in events
        assert "crying" in events
        
    def test_parse_tags_with_all_tags(self):
        """测试标签解析 - 完整标签"""
        analyzer = SenseVoiceAnalyzer()
        text = "<|zh|><|HAPPY|><|Laughter|>这是一段测试文本"
        language, emotion, event, clean_text = analyzer._parse_tags(text)
        assert language == "zh"
        assert emotion == "happy"
        assert event == "laughter"
        assert clean_text == "这是一段测试文本"
        
    def test_parse_tags_partial(self):
        """测试标签解析 - 部分标签"""
        analyzer = SenseVoiceAnalyzer()
        text = "<|en|><|NEUTRAL|>Hello world"
        language, emotion, event, clean_text = analyzer._parse_tags(text)
        assert language == "en"
        assert emotion == "neutral"
        assert event == AudioEvent.NONE.value
        assert clean_text == "Hello world"
        
    def test_parse_tags_no_tags(self):
        """测试标签解析 - 无标签"""
        analyzer = SenseVoiceAnalyzer()
        text = "纯文本内容"
        language, emotion, event, clean_text = analyzer._parse_tags(text)
        assert language == "unknown"
        assert emotion == "neutral"
        assert event == AudioEvent.NONE.value
        assert clean_text == "纯文本内容"
        
    def test_calculate_confidence_full(self):
        """测试置信度计算 - 完整结果"""
        analyzer = SenseVoiceAnalyzer()
        confidence = analyzer._calculate_confidence("zh", "happy", "laughter", "测试文本")
        assert confidence == 1.0
        
    def test_calculate_confidence_partial(self):
        """测试置信度计算 - 部分结果"""
        analyzer = SenseVoiceAnalyzer()
        confidence = analyzer._calculate_confidence("zh", "neutral", "none", "测试文本")
        assert 0.5 < confidence < 1.0
        
    def test_calculate_confidence_empty(self):
        """测试置信度计算 - 空结果"""
        analyzer = SenseVoiceAnalyzer()
        confidence = analyzer._calculate_confidence("unknown", "neutral", "none", "")
        assert confidence < 0.5
        
    def test_parse_result_empty(self):
        """测试结果解析 - 空结果"""
        analyzer = SenseVoiceAnalyzer()
        result = analyzer._parse_result([], 1000)
        assert result.text == ""
        assert result.emotion == "neutral"
        assert result.confidence == 0.0
        assert result.duration_ms == 1000
        
    def test_parse_result_valid(self):
        """测试结果解析 - 有效结果"""
        analyzer = SenseVoiceAnalyzer()
        mock_result = [{"text": "<|zh|><|HAPPY|><|Speech|>你好世界"}]
        result = analyzer._parse_result(mock_result, 2000)
        assert result.text == "你好世界"
        assert result.language == "zh"
        assert result.emotion == "happy"
        assert result.duration_ms == 2000


class TestEmotion2VecAnalyzer:
    """emotion2vec+ 分析器测试"""
    
    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = Emotion2VecAnalyzer()
        assert analyzer.model_dir == "iic/emotion2vec_plus_large"
        assert analyzer.device == "cpu"
        assert not analyzer.is_initialized()
        
    def test_emotion_labels(self):
        """测试情绪标签列表 - 9类情绪"""
        analyzer = Emotion2VecAnalyzer()
        labels = analyzer.get_emotion_labels()
        assert len(labels) == 9
        assert "angry" in labels
        assert "happy" in labels
        assert "neutral" in labels
        assert "sad" in labels
        assert "surprised" in labels
        assert "fearful" in labels
        assert "disgusted" in labels
        assert "anxious" in labels
        assert "tired" in labels
        
    def test_emotion_category_mapping(self):
        """测试情绪类别映射"""
        analyzer = Emotion2VecAnalyzer()
        assert analyzer.EMOTION_CATEGORY_MAP["happy"] == EmotionCategory.HAPPY
        assert analyzer.EMOTION_CATEGORY_MAP["sad"] == EmotionCategory.SAD
        assert analyzer.EMOTION_CATEGORY_MAP["anxious"] == EmotionCategory.ANXIOUS
        
    def test_valence_values(self):
        """测试效价值"""
        analyzer = Emotion2VecAnalyzer()
        assert analyzer.get_valence("happy") > 0  # 正面情绪
        assert analyzer.get_valence("sad") < 0    # 负面情绪
        assert analyzer.get_valence("neutral") == 0  # 中性
        assert analyzer.get_valence("anxious") < 0  # 负面情绪
        
    def test_arousal_values(self):
        """测试唤醒度值"""
        analyzer = Emotion2VecAnalyzer()
        assert analyzer.get_arousal("angry") > 0.5   # 高唤醒
        assert analyzer.get_arousal("tired") < 0.3   # 低唤醒
        assert analyzer.get_arousal("neutral") < 0.5  # 中等唤醒
        
    def test_get_primary_emotion(self):
        """测试主要情绪获取"""
        analyzer = Emotion2VecAnalyzer()
        scores = {"happy": 0.6, "sad": 0.2, "neutral": 0.2}
        primary = analyzer._get_primary_emotion(scores)
        assert primary == "happy"
        
    def test_get_primary_emotion_empty(self):
        """测试主要情绪获取 - 空分数"""
        analyzer = Emotion2VecAnalyzer()
        primary = analyzer._get_primary_emotion({})
        assert primary == "neutral"
        
    def test_calculate_intensity(self):
        """测试情绪强度计算"""
        analyzer = Emotion2VecAnalyzer()
        scores = {"happy": 0.8, "sad": 0.1, "neutral": 0.1}
        intensity = analyzer._calculate_intensity(scores, "happy")
        assert 0 < intensity <= 1.0
        assert intensity > 0.5  # 高分数应该有高强度
        
    def test_calculate_intensity_low(self):
        """测试情绪强度计算 - 低强度"""
        analyzer = Emotion2VecAnalyzer()
        scores = {"happy": 0.35, "sad": 0.33, "neutral": 0.32}
        intensity = analyzer._calculate_intensity(scores, "happy")
        assert intensity < 0.5  # 分数接近时强度较低
        
    def test_extract_scores_normalization(self):
        """测试分数提取和归一化"""
        analyzer = Emotion2VecAnalyzer()
        mock_result = {
            "scores": [0.2, 0.3, 0.1, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05],
            "labels": analyzer.EMOTION_LABELS
        }
        scores = analyzer._extract_scores(mock_result)
        total = sum(scores.values())
        assert abs(total - 1.0) < 0.01  # 归一化后总和应为1
        
    def test_parse_result_empty(self):
        """测试结果解析 - 空结果"""
        analyzer = Emotion2VecAnalyzer()
        result = analyzer._parse_result([])
        assert result.emotion == EmotionCategory.NEUTRAL
        assert result.intensity == 0.0


class TestDataModels:
    """数据模型测试"""
    
    def test_audio_analysis_result_valid(self):
        """测试 AudioAnalysisResult 有效性检查"""
        result = AudioAnalysisResult(
            text="测试文本",
            language="zh",
            emotion="happy",
            event="laughter",
            confidence=0.9,
            duration_ms=1000
        )
        assert result.is_valid()
        
    def test_audio_analysis_result_invalid_empty_text(self):
        """测试 AudioAnalysisResult 有效性检查 - 空文本"""
        result = AudioAnalysisResult(
            text="",
            language="zh",
            emotion="happy",
            event="laughter",
            confidence=0.9,
            duration_ms=1000
        )
        assert not result.is_valid()
        
    def test_emotion2vec_result_labels(self):
        """测试 Emotion2VecResult 标签获取"""
        labels = Emotion2VecResult.get_emotion_labels()
        assert len(labels) == 9
        
    def test_emotion_category_values(self):
        """测试 EmotionCategory 枚举值"""
        assert EmotionCategory.HAPPY.value == "happy"
        assert EmotionCategory.ANXIOUS.value == "anxious"
        assert EmotionCategory.TIRED.value == "tired"
        
    def test_audio_event_values(self):
        """测试 AudioEvent 枚举值"""
        assert AudioEvent.LAUGHTER.value == "laughter"
        assert AudioEvent.CRYING.value == "crying"
        assert AudioEvent.NONE.value == "none"
        
    def test_supported_language_values(self):
        """测试 SupportedLanguage 枚举值"""
        assert SupportedLanguage.CHINESE.value == "zh"
        assert SupportedLanguage.ENGLISH.value == "en"
        assert SupportedLanguage.CANTONESE.value == "yue"


class TestIntegration:
    """集成测试 - 模块间协作"""
    
    def test_sensevoice_preprocessor_integration(self):
        """测试 SenseVoice 与预处理器集成"""
        analyzer = SenseVoiceAnalyzer()
        assert analyzer.preprocessor is not None
        assert isinstance(analyzer.preprocessor, AudioPreprocessor)
        
    def test_emotion2vec_preprocessor_integration(self):
        """测试 emotion2vec+ 与预处理器集成"""
        analyzer = Emotion2VecAnalyzer()
        assert analyzer.preprocessor is not None
        assert isinstance(analyzer.preprocessor, AudioPreprocessor)
        
    def test_emotion_category_coverage(self):
        """测试情绪类别覆盖 - emotion2vec+ 应覆盖所有 EmotionCategory"""
        analyzer = Emotion2VecAnalyzer()
        emotion_labels = set(analyzer.EMOTION_LABELS)
        category_values = set(e.value for e in EmotionCategory)
        assert emotion_labels == category_values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
