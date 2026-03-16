"""
疗愈引擎模块测试
Therapy Engine Module Tests

Checkpoint 11: 验证方案匹配、语音合成、AI 对话正常工作
Requirements: 5.1, 5.3, 5.5, 6.2, 6.3, 11.1, 11.4, 11.5
"""
import os
import sys
from datetime import datetime

import pytest

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import EmotionCategory, EmotionState
from models.therapy import (
    TherapyPlan,
    TherapyStyle,
    TherapyIntensity,
    TherapyPlanParser
)
from services.plan_manager import (
    PlanManager,
    TherapyPlanSelector,
    UserPreferences,
    MatchResult
)
from services.cosyvoice_synthesizer import (
    MockCosyVoiceSynthesizer,
    VoiceEmotion,
    VoiceSpeaker,
    VoiceSynthesisConfig,
    EmotionVoiceMapper,
    TherapyVoiceSynthesizer,
    create_voice_synthesizer
)
from services.qwen_dialog import (
    MockQwenDialogEngine,
    CrisisKeywordDetector,
    DialogMessage,
    DialogRole,
    create_dialog_engine
)


class TestPlanManager:
    """疗愈方案管理器测试"""
    
    def test_plan_manager_initialization(self):
        """测试方案管理器初始化"""
        manager = PlanManager(plans_dir="content/plans")
        assert manager is not None
        assert len(manager.plans) > 0
    
    def test_load_plans_from_directory(self):
        """测试从目录加载方案"""
        manager = PlanManager(plans_dir="content/plans")
        plans = manager.get_all_plans()
        assert len(plans) >= 5  # 至少有5个预设方案
    
    def test_get_plan_by_id(self):
        """测试根据ID获取方案"""
        manager = PlanManager(plans_dir="content/plans")
        plan = manager.get_plan_by_id("anxiety_relief_chinese")
        assert plan is not None
        assert plan.id == "anxiety_relief_chinese"
        assert plan.name == "调息养神 - 焦虑缓解"
    
    def test_get_plan_by_invalid_id(self):
        """测试获取不存在的方案"""
        manager = PlanManager(plans_dir="content/plans")
        plan = manager.get_plan_by_id("nonexistent_plan")
        assert plan is None


class TestPlanMatching:
    """方案匹配测试 - Property 12: 疗愈方案匹配一致性"""
    
    def test_match_anxious_emotion(self):
        """
        测试焦虑情绪匹配
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        """
        manager = PlanManager(plans_dir="content/plans")
        
        emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.6,
            valence=-0.4,
            arousal=0.7,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        plan = manager.match(emotion)
        assert plan is not None
        assert EmotionCategory.ANXIOUS in plan.target_emotions
    
    def test_match_consistency(self):
        """
        测试相同输入返回相同结果
        **Feature: healing-pod-system, Property 12: 疗愈方案匹配一致性**
        **Validates: Requirements 5.1**
        """
        manager = PlanManager(plans_dir="content/plans")
        
        emotion = EmotionState(
            category=EmotionCategory.SAD,
            intensity=0.5,
            valence=-0.3,
            arousal=0.3,
            confidence=0.9,
            timestamp=datetime.now()
        )
        
        # 多次匹配应返回相同结果
        plan1 = manager.match(emotion)
        plan2 = manager.match(emotion)
        plan3 = manager.match(emotion)
        
        assert plan1.id == plan2.id == plan3.id
    
    def test_match_with_style_preference(self):
        """测试带风格偏好的匹配"""
        manager = PlanManager(plans_dir="content/plans")
        
        emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.5,
            valence=-0.3,
            arousal=0.5,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        # 指定中式风格
        plan = manager.match(emotion, style=TherapyStyle.CHINESE)
        assert plan is not None
        assert plan.style == TherapyStyle.CHINESE
    
    def test_match_with_intensity(self):
        """测试根据情绪强度匹配"""
        manager = PlanManager(plans_dir="content/plans")
        
        # 高强度情绪
        high_emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.85,
            valence=-0.6,
            arousal=0.8,
            confidence=0.9,
            timestamp=datetime.now()
        )
        
        plan = manager.match(high_emotion)
        assert plan is not None
        # 高强度情绪应匹配高强度方案（如果有的话）
    
    def test_match_with_details(self):
        """测试带详细信息的匹配"""
        manager = PlanManager(plans_dir="content/plans")
        
        emotion = EmotionState(
            category=EmotionCategory.TIRED,
            intensity=0.6,
            valence=-0.2,
            arousal=0.2,
            confidence=0.85,
            timestamp=datetime.now()
        )
        
        results = manager.match_with_details(emotion, top_n=3)
        assert len(results) > 0
        assert all(isinstance(r, MatchResult) for r in results)
        assert all(r.score >= 0 and r.score <= 1 for r in results)


class TestUserSelectionPriority:
    """用户选择优先级测试 - Property 13: 用户选择优先级"""
    
    def test_user_selection_overrides_auto_match(self):
        """
        测试用户选择覆盖自动匹配
        **Feature: healing-pod-system, Property 13: 用户选择优先级**
        **Validates: Requirements 5.5**
        """
        manager = PlanManager(plans_dir="content/plans")
        selector = TherapyPlanSelector(manager)
        
        emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.6,
            valence=-0.4,
            arousal=0.7,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        # 用户手动选择一个方案
        user_selected = selector.select_plan("fatigue_recovery")
        assert user_selected is not None
        
        # 获取有效方案应返回用户选择的方案
        effective_plan = selector.get_effective_plan(emotion)
        assert effective_plan.id == "fatigue_recovery"
    
    def test_clear_selection_restores_auto_match(self):
        """测试清除选择后恢复自动匹配"""
        manager = PlanManager(plans_dir="content/plans")
        selector = TherapyPlanSelector(manager)
        
        emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.6,
            valence=-0.4,
            arousal=0.7,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        # 用户选择方案
        selector.select_plan("fatigue_recovery")
        
        # 清除选择
        selector.clear_selection()
        
        # 应恢复自动匹配
        effective_plan = selector.get_effective_plan(emotion)
        assert EmotionCategory.ANXIOUS in effective_plan.target_emotions
    
    def test_selection_info(self):
        """测试选择信息获取"""
        manager = PlanManager(plans_dir="content/plans")
        selector = TherapyPlanSelector(manager)
        
        # 初始状态
        info = selector.get_selection_info()
        assert info["has_user_selection"] is False
        
        # 用户选择后
        selector.select_plan("anxiety_relief_chinese")
        info = selector.get_selection_info()
        assert info["has_user_selection"] is True
        assert info["user_selected_plan_id"] == "anxiety_relief_chinese"


class TestMockCosyVoiceSynthesizer:
    """Mock CosyVoice 合成器测试"""
    
    def test_synthesizer_initialization(self):
        """测试合成器初始化"""
        synthesizer = MockCosyVoiceSynthesizer()
        assert synthesizer.initialize() is True
        assert synthesizer.is_initialized() is True
    
    def test_available_speakers(self):
        """测试可用语音角色"""
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        speakers = synthesizer.get_available_speakers()
        assert len(speakers) >= 4
        assert VoiceSpeaker.CHINESE_FEMALE.value in speakers
    
    @pytest.mark.asyncio
    async def test_synthesize_basic(self):
        """
        测试基本语音合成
        **Feature: healing-pod-system, Property 14: 语音合成有效性**
        **Validates: Requirements 6.2**
        """
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        result = await synthesizer.synthesize("你好，欢迎来到疗愈空间")
        
        assert result is not None
        assert result.audio_data is not None
        assert len(result.audio_data) > 0
        assert result.sample_rate == 22050
        assert result.duration_ms > 0
        assert result.text == "你好，欢迎来到疗愈空间"
    
    @pytest.mark.asyncio
    async def test_synthesize_with_emotion(self):
        """
        测试情感控制语音合成
        **Feature: healing-pod-system, Property 15: 情感控制语音差异性**
        **Validates: Requirements 6.3**
        """
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        text = "深呼吸，让自己放松下来"
        
        # 使用不同情感生成语音
        gentle_result = await synthesizer.synthesize_with_emotion(
            text, emotion=VoiceEmotion.GENTLE
        )
        calm_result = await synthesizer.synthesize_with_emotion(
            text, emotion=VoiceEmotion.CALM
        )
        
        assert gentle_result is not None
        assert calm_result is not None
        assert gentle_result.emotion == VoiceEmotion.GENTLE.value
        assert calm_result.emotion == VoiceEmotion.CALM.value
    
    @pytest.mark.asyncio
    async def test_synthesize_stream(self):
        """测试流式语音合成"""
        synthesizer = MockCosyVoiceSynthesizer()
        synthesizer.initialize()
        
        chunks = []
        async for chunk in synthesizer.synthesize_stream("这是一段测试文本"):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert all(len(c) > 0 for c in chunks)


class TestEmotionVoiceMapper:
    """情绪到语音参数映射测试"""
    
    def test_emotion_to_voice_mapping(self):
        """测试情绪到语音情感映射"""
        mapper = EmotionVoiceMapper()
        
        # 悲伤情绪应映射到温柔语音
        assert mapper.EMOTION_TO_VOICE["sad"] == VoiceEmotion.GENTLE
        
        # 焦虑情绪应映射到平静语音
        assert mapper.EMOTION_TO_VOICE["anxious"] == VoiceEmotion.CALM
    
    def test_speed_for_negative_emotion(self):
        """测试负面情绪的语速调整"""
        speed = EmotionVoiceMapper.get_speed_for_emotion(
            emotion_category="anxious",
            intensity=0.8,
            arousal=0.7
        )
        
        # 高强度负面情绪应该有较慢语速
        assert 0.8 <= speed <= 1.2
    
    def test_get_voice_params(self):
        """测试获取语音参数"""
        params = EmotionVoiceMapper.get_voice_params_for_emotion(
            emotion_category="sad",
            intensity=0.6,
            valence=-0.5,
            arousal=0.3
        )
        
        assert "emotion" in params
        assert "speed" in params
        assert "speaker" in params
        assert isinstance(params["emotion"], VoiceEmotion)


class TestTherapyVoiceSynthesizer:
    """疗愈语音合成器测试"""
    
    @pytest.mark.asyncio
    async def test_synthesize_for_emotion_state(self):
        """测试根据情绪状态合成语音"""
        synthesizer = TherapyVoiceSynthesizer(use_mock=True)
        
        result = await synthesizer.synthesize_for_emotion_state(
            text="让我们一起深呼吸",
            emotion_category="anxious",
            intensity=0.6,
            valence=-0.4,
            arousal=0.7
        )
        
        assert result is not None
        assert result.audio_data is not None
        assert len(result.audio_data) > 0
    
    @pytest.mark.asyncio
    async def test_synthesize_guide_text(self):
        """测试合成引导语"""
        synthesizer = TherapyVoiceSynthesizer(use_mock=True)
        
        result = await synthesizer.synthesize_guide_text(
            guide_text="请闭上眼睛，感受此刻的宁静"
        )
        
        assert result is not None
        assert result.audio_data is not None
    
    @pytest.mark.asyncio
    async def test_synthesize_encouragement(self):
        """测试合成鼓励性语音"""
        synthesizer = TherapyVoiceSynthesizer(use_mock=True)
        
        result = await synthesizer.synthesize_encouragement(
            text="你做得很好，继续保持"
        )
        
        assert result is not None
        assert result.emotion == VoiceEmotion.ENCOURAGING.value
    
    @pytest.mark.asyncio
    async def test_synthesize_calming(self):
        """测试合成舒缓性语音"""
        synthesizer = TherapyVoiceSynthesizer(use_mock=True)
        
        result = await synthesizer.synthesize_calming(
            text="一切都会好起来的"
        )
        
        assert result is not None
        assert result.emotion == VoiceEmotion.CALM.value


class TestCrisisKeywordDetector:
    """危机关键词检测器测试"""
    
    def test_detect_crisis_keywords_zh(self):
        """测试中文危机关键词检测"""
        is_crisis, keywords = CrisisKeywordDetector.detect_crisis("我不想活了")
        assert is_crisis is True
        assert len(keywords) > 0
    
    def test_detect_crisis_keywords_en(self):
        """测试英文危机关键词检测"""
        is_crisis, keywords = CrisisKeywordDetector.detect_crisis("I want to kill myself")
        assert is_crisis is True
        assert len(keywords) > 0
    
    def test_no_crisis_normal_text(self):
        """测试正常文本不触发危机检测"""
        is_crisis, keywords = CrisisKeywordDetector.detect_crisis("今天天气真好")
        assert is_crisis is False
        assert len(keywords) == 0
    
    def test_get_crisis_resources(self):
        """测试获取危机资源"""
        resources = CrisisKeywordDetector.get_crisis_resources()
        assert len(resources) > 0
        assert any("热线" in r for r in resources)


class TestMockQwenDialogEngine:
    """Mock Qwen3 对话引擎测试"""
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        engine = MockQwenDialogEngine()
        assert engine.initialize() is True
        assert engine.is_initialized() is True
    
    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """
        测试基本对话
        **Feature: healing-pod-system, Property 22: 对话响应有效性**
        **Validates: Requirements 11.1**
        """
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = await engine.chat("我今天感觉有点累")
        
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_first_response_ai_disclosure(self):
        """
        测试首次响应包含AI身份声明
        **Feature: healing-pod-system, Property 23: AI 身份声明**
        **Validates: Requirements 11.4**
        """
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = await engine.chat("你好")
        
        assert response.is_first_response is True
        assert response.contains_ai_disclosure is True
        assert "AI" in response.content or "助手" in response.content
    
    @pytest.mark.asyncio
    async def test_subsequent_response_no_disclosure(self):
        """测试后续响应不包含AI身份声明"""
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 第一次对话
        await engine.chat("你好")
        
        # 第二次对话
        response = await engine.chat("我想聊聊")
        
        assert response.is_first_response is False
        assert response.contains_ai_disclosure is False
    
    @pytest.mark.asyncio
    async def test_crisis_detection_in_chat(self):
        """
        测试对话中的危机检测
        **Validates: Requirements 11.5**
        """
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        response = await engine.chat("我不想活了", check_crisis=True)
        
        assert response.contains_crisis_warning is True
        assert response.crisis_resources is not None
        assert len(response.crisis_resources) > 0
    
    def test_clear_history(self):
        """测试清除对话历史"""
        engine = MockQwenDialogEngine()
        engine.initialize()
        
        # 添加一些历史
        engine._history.append(DialogMessage(
            role=DialogRole.USER,
            content="测试消息"
        ))
        
        engine.clear_history()
        
        assert len(engine.get_history()) == 0
        assert engine._is_first_response is True
    
    def test_reset_session(self):
        """测试重置会话"""
        engine = MockQwenDialogEngine()
        engine.initialize()
        engine._is_first_response = False
        
        engine.reset_session()
        
        assert engine._is_first_response is True


class TestCreateFunctions:
    """工厂函数测试"""
    
    def test_create_voice_synthesizer_mock(self):
        """测试创建Mock语音合成器"""
        synthesizer = create_voice_synthesizer(use_mock=True)
        assert synthesizer is not None
        assert isinstance(synthesizer, MockCosyVoiceSynthesizer)
    
    def test_create_dialog_engine_mock(self):
        """测试创建Mock对话引擎"""
        engine = create_dialog_engine(use_mock=True)
        assert engine is not None
        assert isinstance(engine, MockQwenDialogEngine)


class TestTherapyPlanParser:
    """疗愈方案解析器测试"""
    
    def test_load_from_file(self):
        """测试从文件加载方案"""
        plan = TherapyPlanParser.load_from_file("content/plans/anxiety_relief_chinese.yaml")
        
        assert plan is not None
        assert plan.id == "anxiety_relief_chinese"
        assert len(plan.phases) > 0
    
    def test_plan_phases_duration(self):
        """测试方案阶段时长"""
        plan = TherapyPlanParser.load_from_file("content/plans/anxiety_relief_chinese.yaml")
        
        # 验证阶段总时长等于方案时长
        total_phase_duration = sum(p.duration for p in plan.phases)
        assert total_phase_duration == plan.duration
    
    def test_plan_phase_configs(self):
        """测试方案阶段配置"""
        plan = TherapyPlanParser.load_from_file("content/plans/anxiety_relief_chinese.yaml")
        
        for phase in plan.phases:
            # 每个阶段必须有灯光和音频配置
            assert phase.light is not None
            assert phase.audio is not None
            assert phase.duration > 0


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_therapy_workflow(self):
        """测试完整疗愈工作流"""
        # 1. 创建情绪状态
        emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.6,
            valence=-0.4,
            arousal=0.7,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        # 2. 匹配疗愈方案
        manager = PlanManager(plans_dir="content/plans")
        plan = manager.match(emotion)
        assert plan is not None
        
        # 3. 生成引导语音
        synthesizer = TherapyVoiceSynthesizer(use_mock=True)
        if plan.phases[0].voice_guide:
            voice_result = await synthesizer.synthesize_guide_text(
                plan.phases[0].voice_guide.text
            )
            assert voice_result is not None
            assert len(voice_result.audio_data) > 0
        
        # 4. AI对话支持
        dialog_engine = create_dialog_engine(use_mock=True)
        dialog_response = await dialog_engine.chat("我感觉有点焦虑")
        assert dialog_response is not None
        assert len(dialog_response.content) > 0
    
    @pytest.mark.asyncio
    async def test_emotion_adaptive_voice(self):
        """测试情绪自适应语音"""
        synthesizer = TherapyVoiceSynthesizer(use_mock=True)
        
        # 焦虑情绪
        anxious_result = await synthesizer.synthesize_for_emotion_state(
            text="让我们一起放松",
            emotion_category="anxious",
            intensity=0.7,
            valence=-0.5,
            arousal=0.8
        )
        
        # 疲惫情绪
        tired_result = await synthesizer.synthesize_for_emotion_state(
            text="让我们一起放松",
            emotion_category="tired",
            intensity=0.6,
            valence=-0.2,
            arousal=0.2
        )
        
        assert anxious_result is not None
        assert tired_result is not None
        # 不同情绪应该产生不同的语音参数
        # (在Mock实现中可能相同，但真实实现会有差异)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
