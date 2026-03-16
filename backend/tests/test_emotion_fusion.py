"""
多模态情绪融合模块测试
Multi-Modal Emotion Fusion Module Tests

Checkpoint 7: 验证多模态融合效果
Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""
import os
import sys
from datetime import datetime

import pytest
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import (
    EmotionCategory,
    EmotionState,
    Emotion2VecResult,
    FaceAnalysisResult,
    FacialExpression
)
from services.hrv_analyzer import BioAnalysisResult, HRVMetrics
from services.emotion_fusion import (
    EmotionFusion,
    FusionMode,
    FusionResult,
    ModalityWeights
)


class TestModalityWeights:
    """模态权重测试"""
    
    def test_default_weights(self):
        """测试默认权重"""
        weights = ModalityWeights()
        assert weights.audio == 0.35
        assert weights.face == 0.35
        assert weights.bio == 0.30
    
    def test_custom_weights(self):
        """测试自定义权重"""
        weights = ModalityWeights(audio=0.5, face=0.3, bio=0.2)
        assert weights.audio == 0.5
        assert weights.face == 0.3
        assert weights.bio == 0.2
    
    def test_weights_normalization(self):
        """测试权重自动归一化"""
        weights = ModalityWeights(audio=1.0, face=1.0, bio=1.0)
        total = weights.audio + weights.face + weights.bio
        assert abs(total - 1.0) < 0.01
    
    def test_normalize_with_available_modalities(self):
        """测试根据可用模态归一化"""
        weights = ModalityWeights(audio=0.4, face=0.4, bio=0.2)
        normalized = weights.normalize(["audio", "face"])
        
        assert normalized.bio == 0.0
        assert abs(normalized.audio + normalized.face - 1.0) < 0.01


class TestEmotionFusion:
    """情绪融合器测试"""
    
    def test_fusion_initialization(self):
        """测试融合器初始化"""
        fusion = EmotionFusion()
        assert fusion.weights is not None
        assert fusion.conflict_resolution_priority == ["bio", "face", "audio"]
    
    def test_fusion_with_custom_weights(self):
        """测试自定义权重初始化"""
        weights = ModalityWeights(audio=0.5, face=0.3, bio=0.2)
        fusion = EmotionFusion(weights=weights)
        assert fusion.weights.audio == 0.5
    
    def test_fusion_with_custom_priority(self):
        """测试自定义冲突解决优先级"""
        fusion = EmotionFusion(conflict_resolution_priority=["audio", "face", "bio"])
        assert fusion.conflict_resolution_priority == ["audio", "face", "bio"]


class TestFusionModes:
    """融合模式测试"""
    
    def test_full_mode_detection(self):
        """测试完整模式检测"""
        fusion = EmotionFusion()
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.HAPPY,
            scores={"happy": 0.8, "neutral": 0.2},
            intensity=0.8
        )
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.HAPPY,
            confidence=0.9,
            expression_scores={"happy": 0.9, "neutral": 0.1}
        )
        bio_result = BioAnalysisResult(
            stress_index=30.0,
            stress_level="low",
            hrv_metrics=None,
            heart_rate=70.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse(audio_result, face_result, bio_result)
        assert result.fusion_mode == FusionMode.FULL
    
    def test_audio_only_mode(self):
        """测试仅语音模式"""
        fusion = EmotionFusion()
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.SAD,
            scores={"sad": 0.7, "neutral": 0.3},
            intensity=0.7
        )
        
        result = fusion.fuse_audio_only(audio_result)
        assert result.fusion_mode == FusionMode.AUDIO_ONLY
    
    def test_face_only_mode(self):
        """测试仅面部模式"""
        fusion = EmotionFusion()
        
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.ANGRY,
            confidence=0.85,
            expression_scores={"angry": 0.85, "neutral": 0.15}
        )
        
        result = fusion.fuse_face_only(face_result)
        assert result.fusion_mode == FusionMode.FACE_ONLY
    
    def test_bio_only_mode(self):
        """测试仅生理模式"""
        fusion = EmotionFusion()
        
        bio_result = BioAnalysisResult(
            stress_index=75.0,
            stress_level="high",
            hrv_metrics=None,
            heart_rate=95.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse_bio_only(bio_result)
        assert result.fusion_mode == FusionMode.BIO_ONLY


class TestEmotionStateOutput:
    """情绪状态输出测试 - Property 9: 多模态融合输出完整性"""
    
    def test_emotion_state_completeness(self):
        """
        测试融合输出包含所有必需字段
        **Feature: healing-pod-system, Property 9: 多模态融合输出完整性**
        **Validates: Requirements 4.2**
        """
        fusion = EmotionFusion()
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.ANXIOUS,
            scores={"anxious": 0.6, "neutral": 0.4},
            intensity=0.6
        )
        
        result = fusion.fuse_audio_only(audio_result)
        emotion_state = result.emotion_state
        
        # 验证所有必需字段存在
        assert emotion_state.category is not None
        assert isinstance(emotion_state.category, EmotionCategory)
        
        # 验证强度范围 (0-1)
        assert 0 <= emotion_state.intensity <= 1
        
        # 验证效价范围 (-1 到 1)
        assert -1 <= emotion_state.valence <= 1
        
        # 验证唤醒度范围 (0-1)
        assert 0 <= emotion_state.arousal <= 1
        
        # 验证置信度范围 (0-1)
        assert 0 <= emotion_state.confidence <= 1
        
        # 验证时间戳存在
        assert emotion_state.timestamp is not None
    
    def test_emotion_state_with_all_modalities(self):
        """测试三模态融合输出完整性"""
        fusion = EmotionFusion()
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.HAPPY,
            scores={"happy": 0.7, "neutral": 0.3},
            intensity=0.7
        )
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.HAPPY,
            confidence=0.8,
            expression_scores={"happy": 0.8, "neutral": 0.2}
        )
        bio_result = BioAnalysisResult(
            stress_index=25.0,
            stress_level="low",
            hrv_metrics=None,
            heart_rate=68.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse(audio_result, face_result, bio_result)
        emotion_state = result.emotion_state
        
        # 验证所有字段
        assert emotion_state.category is not None
        assert 0 <= emotion_state.intensity <= 1
        assert -1 <= emotion_state.valence <= 1
        assert 0 <= emotion_state.arousal <= 1
        assert 0 <= emotion_state.confidence <= 1


class TestConflictResolution:
    """冲突解决测试 - Property 10: 模态冲突解决优先级"""
    
    def test_conflict_detection(self):
        """测试冲突检测"""
        fusion = EmotionFusion()
        
        # 创建冲突场景：语音显示开心，面部显示悲伤
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.HAPPY,
            scores={"happy": 0.9, "sad": 0.1},
            intensity=0.9
        )
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.SAD,
            confidence=0.85,
            expression_scores={"sad": 0.85, "happy": 0.15}
        )
        
        result = fusion.fuse(audio_result, face_result, None)
        
        # 应该检测到冲突
        assert result.conflict_detected is True
    
    def test_bio_priority_in_conflict(self):
        """
        测试生理信号在冲突中的优先级
        **Feature: healing-pod-system, Property 10: 模态冲突解决优先级**
        **Validates: Requirements 4.3**
        """
        fusion = EmotionFusion()
        
        # 语音显示开心
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.HAPPY,
            scores={"happy": 0.9, "anxious": 0.1},
            intensity=0.9
        )
        # 面部显示开心
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.HAPPY,
            confidence=0.85,
            expression_scores={"happy": 0.85, "neutral": 0.15}
        )
        # 生理信号显示高压力（焦虑）
        bio_result = BioAnalysisResult(
            stress_index=85.0,
            stress_level="very_high",
            hrv_metrics=None,
            heart_rate=100.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse(audio_result, face_result, bio_result)
        
        # 当存在冲突时，生理信号应该有更高优先级
        # 高压力应该影响最终结果
        if result.conflict_detected:
            assert "bio" in result.conflict_resolution or result.emotion_state.arousal > 0.5
    
    def test_face_priority_over_audio(self):
        """测试面部优先于语音"""
        fusion = EmotionFusion()
        
        # 语音显示开心
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.HAPPY,
            scores={"happy": 0.8, "sad": 0.2},
            intensity=0.8
        )
        # 面部显示悲伤
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.SAD,
            confidence=0.9,
            expression_scores={"sad": 0.9, "happy": 0.1}
        )
        
        result = fusion.fuse(audio_result, face_result, None)
        
        # 面部应该优先于语音
        if result.conflict_detected:
            assert "face" in result.conflict_resolution


class TestSingleModalityDegradation:
    """单模态降级测试 - Property 11: 单模态降级能力"""
    
    def test_audio_only_produces_valid_state(self):
        """
        测试仅语音模式产生有效状态
        **Feature: healing-pod-system, Property 11: 单模态降级能力**
        **Validates: Requirements 4.5**
        """
        fusion = EmotionFusion()
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.TIRED,
            scores={"tired": 0.7, "neutral": 0.3},
            intensity=0.7
        )
        
        result = fusion.fuse_audio_only(audio_result)
        
        # 验证产生有效的情绪状态
        assert result.emotion_state is not None
        assert result.emotion_state.category is not None
        assert 0 <= result.emotion_state.intensity <= 1
        assert result.fusion_mode == FusionMode.AUDIO_ONLY
    
    def test_face_only_produces_valid_state(self):
        """测试仅面部模式产生有效状态"""
        fusion = EmotionFusion()
        
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.SURPRISED,
            confidence=0.75,
            expression_scores={"surprised": 0.75, "neutral": 0.25}
        )
        
        result = fusion.fuse_face_only(face_result)
        
        assert result.emotion_state is not None
        assert result.emotion_state.category is not None
        assert 0 <= result.emotion_state.intensity <= 1
        assert result.fusion_mode == FusionMode.FACE_ONLY
    
    def test_bio_only_produces_valid_state(self):
        """测试仅生理模式产生有效状态"""
        fusion = EmotionFusion()
        
        bio_result = BioAnalysisResult(
            stress_index=50.0,
            stress_level="moderate",
            hrv_metrics=None,
            heart_rate=80.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse_bio_only(bio_result)
        
        assert result.emotion_state is not None
        assert result.emotion_state.category is not None
        assert 0 <= result.emotion_state.intensity <= 1
        assert result.fusion_mode == FusionMode.BIO_ONLY
    
    def test_no_modality_returns_default(self):
        """测试无模态数据返回默认状态"""
        fusion = EmotionFusion()
        
        result = fusion.fuse(None, None, None)
        
        assert result.emotion_state is not None
        assert result.emotion_state.category == EmotionCategory.NEUTRAL
        assert result.emotion_state.confidence == 0.0


class TestDynamicWeightAdjustment:
    """动态权重调整测试 - Requirements 4.4"""
    
    def test_set_weights(self):
        """测试设置权重"""
        fusion = EmotionFusion()
        
        fusion.set_weights(audio=0.6, face=0.3, bio=0.1)
        
        weights = fusion.get_weights()
        assert abs(weights.audio - 0.6) < 0.01
        assert abs(weights.face - 0.3) < 0.01
        assert abs(weights.bio - 0.1) < 0.01
    
    def test_set_conflict_priority(self):
        """测试设置冲突优先级"""
        fusion = EmotionFusion()
        
        fusion.set_conflict_priority(["audio", "bio", "face"])
        
        assert fusion.conflict_resolution_priority == ["audio", "bio", "face"]
    
    def test_invalid_priority_raises_error(self):
        """测试无效优先级抛出错误"""
        fusion = EmotionFusion()
        
        with pytest.raises(ValueError):
            fusion.set_conflict_priority(["audio", "invalid", "face"])


class TestDegradedModeInfo:
    """降级模式信息测试"""
    
    def test_get_degradation_info(self):
        """测试获取降级模式信息"""
        fusion = EmotionFusion()
        
        info = fusion.get_degradation_info(FusionMode.AUDIO_ONLY)
        
        assert "name" in info
        assert "description" in info
        assert "available_modalities" in info
        assert "reliability" in info
        assert "is_degraded" in info
        assert info["is_degraded"] is True
    
    def test_full_mode_not_degraded(self):
        """测试完整模式不是降级模式"""
        fusion = EmotionFusion()
        
        info = fusion.get_degradation_info(FusionMode.FULL)
        
        assert info["is_degraded"] is False
    
    def test_is_degraded_mode(self):
        """测试降级模式检测"""
        fusion = EmotionFusion()
        
        assert not fusion.is_degraded_mode(FusionMode.FULL)
        assert fusion.is_degraded_mode(FusionMode.AUDIO_ONLY)
        assert fusion.is_degraded_mode(FusionMode.FACE_ONLY)
        assert fusion.is_degraded_mode(FusionMode.BIO_ONLY)


class TestContributions:
    """模态贡献度测试"""
    
    def test_contributions_sum(self):
        """测试贡献度总和"""
        fusion = EmotionFusion()
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.NEUTRAL,
            scores={"neutral": 0.8, "happy": 0.2},
            intensity=0.5
        )
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.NEUTRAL,
            confidence=0.7,
            expression_scores={"neutral": 0.7, "happy": 0.3}
        )
        bio_result = BioAnalysisResult(
            stress_index=40.0,
            stress_level="moderate",
            hrv_metrics=None,
            heart_rate=72.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse(audio_result, face_result, bio_result)
        
        total_contribution = sum(result.modality_contributions.values())
        assert abs(total_contribution - 1.0) < 0.01
    
    def test_single_modality_full_contribution(self):
        """测试单模态时贡献度为1"""
        fusion = EmotionFusion()
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.HAPPY,
            scores={"happy": 0.9, "neutral": 0.1},
            intensity=0.9
        )
        
        result = fusion.fuse_audio_only(audio_result)
        
        assert result.modality_contributions["audio"] == 1.0
        assert result.modality_contributions["face"] == 0.0
        assert result.modality_contributions["bio"] == 0.0


class TestIntegration:
    """集成测试"""
    
    def test_full_fusion_workflow(self):
        """测试完整融合工作流"""
        fusion = EmotionFusion()
        
        # 模拟真实场景：用户感到焦虑
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.ANXIOUS,
            scores={
                "anxious": 0.5, "tired": 0.2, "neutral": 0.15,
                "sad": 0.1, "happy": 0.05
            },
            intensity=0.6
        )
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.FEARFUL,
            confidence=0.65,
            expression_scores={
                "fearful": 0.4, "neutral": 0.3, "sad": 0.2, "angry": 0.1
            }
        )
        bio_result = BioAnalysisResult(
            stress_index=65.0,
            stress_level="high",
            hrv_metrics=None,
            heart_rate=88.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse(audio_result, face_result, bio_result)
        
        # 验证结果
        assert result.fusion_mode == FusionMode.FULL
        assert result.emotion_state is not None
        
        # 高压力场景应该有负面效价
        assert result.emotion_state.valence < 0.3
        
        # 焦虑场景应该有较高唤醒度
        assert result.emotion_state.arousal > 0.3
    
    def test_relaxed_state_fusion(self):
        """测试放松状态融合"""
        fusion = EmotionFusion()
        
        # 模拟放松场景
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.NEUTRAL,
            scores={"neutral": 0.6, "happy": 0.3, "tired": 0.1},
            intensity=0.4
        )
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.NEUTRAL,
            confidence=0.7,
            expression_scores={"neutral": 0.7, "happy": 0.2, "sad": 0.1}
        )
        bio_result = BioAnalysisResult(
            stress_index=20.0,
            stress_level="low",
            hrv_metrics=None,
            heart_rate=62.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        result = fusion.fuse(audio_result, face_result, bio_result)
        
        # 放松状态应该有较低唤醒度
        assert result.emotion_state.arousal < 0.6
        
        # 低压力应该有中性或正面效价
        assert result.emotion_state.valence >= -0.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
