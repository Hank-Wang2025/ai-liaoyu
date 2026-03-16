"""
多模态情绪融合模块
Multi-Modal Emotion Fusion Module

实现多模态情绪数据的加权融合、冲突解决和降级模式
Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple
from loguru import logger

from models.emotion import (
    EmotionCategory,
    EmotionState,
    AudioAnalysisResult,
    Emotion2VecResult,
    FaceAnalysisResult,
    FacialExpression
)
from services.hrv_analyzer import BioAnalysisResult


class FusionMode(str, Enum):
    """融合模式"""
    FULL = "full"           # 完整模式（三模态）
    AUDIO_FACE = "audio_face"  # 语音+面部
    AUDIO_BIO = "audio_bio"    # 语音+生理
    FACE_BIO = "face_bio"      # 面部+生理
    AUDIO_ONLY = "audio_only"  # 仅语音
    FACE_ONLY = "face_only"    # 仅面部
    BIO_ONLY = "bio_only"      # 仅生理


@dataclass
class ModalityWeights:
    """模态权重配置"""
    audio: float = 0.35      # 语音权重
    face: float = 0.35       # 面部权重
    bio: float = 0.30        # 生理信号权重
    
    def __post_init__(self):
        """验证权重总和"""
        total = self.audio + self.face + self.bio
        if abs(total - 1.0) > 0.01:
            # 自动归一化
            self.audio /= total
            self.face /= total
            self.bio /= total
    
    def normalize(self, available_modalities: List[str]) -> 'ModalityWeights':
        """
        根据可用模态重新归一化权重
        
        Args:
            available_modalities: 可用的模态列表 ["audio", "face", "bio"]
            
        Returns:
            归一化后的权重
        """
        weights = {"audio": 0.0, "face": 0.0, "bio": 0.0}
        
        if "audio" in available_modalities:
            weights["audio"] = self.audio
        if "face" in available_modalities:
            weights["face"] = self.face
        if "bio" in available_modalities:
            weights["bio"] = self.bio
        
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return ModalityWeights(
            audio=weights["audio"],
            face=weights["face"],
            bio=weights["bio"]
        )


@dataclass
class FusionResult:
    """融合结果"""
    emotion_state: EmotionState
    fusion_mode: FusionMode
    modality_contributions: Dict[str, float]  # 各模态的贡献度
    conflict_detected: bool = False
    conflict_resolution: Optional[str] = None
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)


class EmotionFusion:
    """
    多模态情绪融合器
    
    功能:
    - 加权融合多模态情绪数据
    - 冲突检测和解决（优先级：生理 > 面部 > 语音）
    - 单模态降级模式
    - 动态权重调整
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    
    # 情绪类别映射（统一不同模态的情绪标签）
    EMOTION_MAPPING = {
        # 面部表情 -> EmotionCategory
        "happy": EmotionCategory.HAPPY,
        "sad": EmotionCategory.SAD,
        "angry": EmotionCategory.ANGRY,
        "fearful": EmotionCategory.FEARFUL,
        "surprised": EmotionCategory.SURPRISED,
        "disgusted": EmotionCategory.DISGUSTED,
        "neutral": EmotionCategory.NEUTRAL,
        # emotion2vec 扩展
        "anxious": EmotionCategory.ANXIOUS,
        "tired": EmotionCategory.TIRED,
    }
    
    # 情绪效价映射 (valence: -1 负面 到 1 正面)
    EMOTION_VALENCE = {
        EmotionCategory.HAPPY: 0.9,
        EmotionCategory.SAD: -0.7,
        EmotionCategory.ANGRY: -0.8,
        EmotionCategory.FEARFUL: -0.6,
        EmotionCategory.SURPRISED: 0.2,
        EmotionCategory.DISGUSTED: -0.7,
        EmotionCategory.NEUTRAL: 0.0,
        EmotionCategory.ANXIOUS: -0.5,
        EmotionCategory.TIRED: -0.3,
    }
    
    # 情绪唤醒度映射 (arousal: 0 平静 到 1 激动)
    EMOTION_AROUSAL = {
        EmotionCategory.HAPPY: 0.7,
        EmotionCategory.SAD: 0.2,
        EmotionCategory.ANGRY: 0.9,
        EmotionCategory.FEARFUL: 0.8,
        EmotionCategory.SURPRISED: 0.8,
        EmotionCategory.DISGUSTED: 0.5,
        EmotionCategory.NEUTRAL: 0.3,
        EmotionCategory.ANXIOUS: 0.7,
        EmotionCategory.TIRED: 0.1,
    }
    
    # 冲突检测阈值
    CONFLICT_THRESHOLD = 0.4  # 情绪差异超过此阈值视为冲突
    
    def __init__(
        self,
        weights: Optional[ModalityWeights] = None,
        conflict_resolution_priority: List[str] = None
    ):
        """
        初始化多模态融合器
        
        Args:
            weights: 模态权重配置
            conflict_resolution_priority: 冲突解决优先级，默认 ["bio", "face", "audio"]
        """
        self.weights = weights or ModalityWeights()
        self.conflict_resolution_priority = conflict_resolution_priority or ["bio", "face", "audio"]
        
        logger.info(
            f"EmotionFusion initialized with weights: "
            f"audio={self.weights.audio:.2f}, face={self.weights.face:.2f}, bio={self.weights.bio:.2f}"
        )
    
    def fuse(
        self,
        audio_result: Optional[Emotion2VecResult] = None,
        face_result: Optional[FaceAnalysisResult] = None,
        bio_result: Optional[BioAnalysisResult] = None,
        sensevoice_result: Optional[AudioAnalysisResult] = None
    ) -> FusionResult:
        """
        融合多模态情绪数据
        
        Args:
            audio_result: emotion2vec+ 语音情绪分析结果
            face_result: 面部表情分析结果
            bio_result: 生理信号分析结果
            sensevoice_result: SenseVoice 语音识别结果（可选，用于补充）
            
        Returns:
            FusionResult 融合结果
        """
        # 确定可用模态
        available_modalities = self._get_available_modalities(
            audio_result, face_result, bio_result
        )
        
        if not available_modalities:
            logger.warning("No valid modality data available, returning neutral state")
            return self._create_default_result()
        
        # 确定融合模式
        fusion_mode = self._determine_fusion_mode(available_modalities)
        
        # 归一化权重
        normalized_weights = self.weights.normalize(available_modalities)
        
        # 提取各模态的情绪向量
        emotion_vectors = self._extract_emotion_vectors(
            audio_result, face_result, bio_result, sensevoice_result
        )
        
        # 检测冲突
        conflict_detected, conflict_info = self._detect_conflict(
            emotion_vectors, available_modalities
        )
        
        # 融合情绪
        if conflict_detected:
            # 使用冲突解决策略
            fused_emotion, resolution_info = self._resolve_conflict(
                emotion_vectors, available_modalities
            )
        else:
            # 使用加权融合
            fused_emotion = self._weighted_fusion(
                emotion_vectors, normalized_weights, available_modalities
            )
            resolution_info = None
        
        # 计算最终情绪状态
        emotion_state = self._create_emotion_state(
            fused_emotion,
            audio_result,
            face_result,
            bio_result
        )
        
        # 计算各模态贡献度
        contributions = self._calculate_contributions(
            emotion_vectors, normalized_weights, available_modalities
        )
        
        return FusionResult(
            emotion_state=emotion_state,
            fusion_mode=fusion_mode,
            modality_contributions=contributions,
            conflict_detected=conflict_detected,
            conflict_resolution=resolution_info,
            confidence_breakdown={
                "audio": audio_result.intensity if audio_result else 0.0,
                "face": face_result.confidence if face_result and face_result.detected else 0.0,
                "bio": 1.0 - (bio_result.stress_index / 100.0) if bio_result and bio_result.is_valid else 0.0
            }
        )
    
    def _get_available_modalities(
        self,
        audio_result: Optional[Emotion2VecResult],
        face_result: Optional[FaceAnalysisResult],
        bio_result: Optional[BioAnalysisResult]
    ) -> List[str]:
        """
        确定可用的模态
        
        Args:
            audio_result: 语音分析结果
            face_result: 面部分析结果
            bio_result: 生理信号分析结果
            
        Returns:
            可用模态列表
        """
        available = []
        
        if audio_result is not None and audio_result.intensity > 0:
            available.append("audio")
        
        if face_result is not None and face_result.detected:
            available.append("face")
        
        if bio_result is not None and bio_result.is_valid:
            available.append("bio")
        
        return available
    
    def _determine_fusion_mode(self, available_modalities: List[str]) -> FusionMode:
        """
        确定融合模式
        
        Args:
            available_modalities: 可用模态列表
            
        Returns:
            融合模式
        """
        modality_set = set(available_modalities)
        
        if modality_set == {"audio", "face", "bio"}:
            return FusionMode.FULL
        elif modality_set == {"audio", "face"}:
            return FusionMode.AUDIO_FACE
        elif modality_set == {"audio", "bio"}:
            return FusionMode.AUDIO_BIO
        elif modality_set == {"face", "bio"}:
            return FusionMode.FACE_BIO
        elif modality_set == {"audio"}:
            return FusionMode.AUDIO_ONLY
        elif modality_set == {"face"}:
            return FusionMode.FACE_ONLY
        elif modality_set == {"bio"}:
            return FusionMode.BIO_ONLY
        else:
            return FusionMode.AUDIO_ONLY  # 默认
    
    def _extract_emotion_vectors(
        self,
        audio_result: Optional[Emotion2VecResult],
        face_result: Optional[FaceAnalysisResult],
        bio_result: Optional[BioAnalysisResult],
        sensevoice_result: Optional[AudioAnalysisResult]
    ) -> Dict[str, Dict[str, float]]:
        """
        提取各模态的情绪向量
        
        Args:
            audio_result: 语音分析结果
            face_result: 面部分析结果
            bio_result: 生理信号分析结果
            sensevoice_result: SenseVoice 结果
            
        Returns:
            各模态的情绪向量 {modality: {emotion: score}}
        """
        vectors = {}
        
        # 语音情绪向量
        if audio_result is not None:
            vectors["audio"] = {
                "category": audio_result.emotion.value,
                "scores": audio_result.scores,
                "intensity": audio_result.intensity,
                "valence": self.EMOTION_VALENCE.get(audio_result.emotion, 0.0),
                "arousal": self.EMOTION_AROUSAL.get(audio_result.emotion, 0.3)
            }
        
        # 面部情绪向量
        if face_result is not None and face_result.detected:
            face_emotion = self.EMOTION_MAPPING.get(
                face_result.expression.value, 
                EmotionCategory.NEUTRAL
            )
            vectors["face"] = {
                "category": face_result.expression.value,
                "scores": face_result.expression_scores,
                "intensity": face_result.confidence,
                "valence": self.EMOTION_VALENCE.get(face_emotion, 0.0),
                "arousal": self.EMOTION_AROUSAL.get(face_emotion, 0.3)
            }
        
        # 生理信号情绪向量（基于压力指数推断）
        if bio_result is not None and bio_result.is_valid:
            bio_emotion = self._infer_emotion_from_stress(bio_result.stress_index)
            vectors["bio"] = {
                "category": bio_emotion.value,
                "scores": self._stress_to_emotion_scores(bio_result.stress_index),
                "intensity": bio_result.stress_index / 100.0,
                "valence": self._stress_to_valence(bio_result.stress_index),
                "arousal": self._stress_to_arousal(bio_result.stress_index)
            }
        
        return vectors
    
    def _infer_emotion_from_stress(self, stress_index: float) -> EmotionCategory:
        """
        从压力指数推断情绪类别
        
        Args:
            stress_index: 压力指数 (0-100)
            
        Returns:
            推断的情绪类别
        """
        if stress_index < 25:
            return EmotionCategory.NEUTRAL
        elif stress_index < 50:
            return EmotionCategory.TIRED
        elif stress_index < 75:
            return EmotionCategory.ANXIOUS
        else:
            return EmotionCategory.FEARFUL
    
    def _stress_to_emotion_scores(self, stress_index: float) -> Dict[str, float]:
        """
        将压力指数转换为情绪分数分布
        
        Args:
            stress_index: 压力指数 (0-100)
            
        Returns:
            情绪分数字典
        """
        # 基于压力指数生成情绪分布
        normalized_stress = stress_index / 100.0
        
        scores = {
            "neutral": max(0, 1.0 - normalized_stress * 1.5),
            "tired": normalized_stress * 0.3 if normalized_stress < 0.5 else 0.3 - (normalized_stress - 0.5) * 0.3,
            "anxious": max(0, normalized_stress - 0.3) * 0.8,
            "fearful": max(0, normalized_stress - 0.6) * 0.5,
            "happy": max(0, 0.3 - normalized_stress * 0.5),
            "sad": normalized_stress * 0.2,
            "angry": max(0, normalized_stress - 0.7) * 0.3,
            "surprised": 0.05,
            "disgusted": 0.02
        }
        
        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores
    
    def _stress_to_valence(self, stress_index: float) -> float:
        """
        将压力指数转换为效价值
        
        Args:
            stress_index: 压力指数 (0-100)
            
        Returns:
            效价值 (-1 到 1)
        """
        # 压力越高，效价越负
        return 0.5 - (stress_index / 100.0)
    
    def _stress_to_arousal(self, stress_index: float) -> float:
        """
        将压力指数转换为唤醒度
        
        Args:
            stress_index: 压力指数 (0-100)
            
        Returns:
            唤醒度 (0 到 1)
        """
        # 压力与唤醒度正相关
        return 0.2 + (stress_index / 100.0) * 0.6
    
    def _detect_conflict(
        self,
        emotion_vectors: Dict[str, Dict[str, float]],
        available_modalities: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        检测模态间的情绪冲突
        
        Args:
            emotion_vectors: 各模态的情绪向量
            available_modalities: 可用模态列表
            
        Returns:
            (是否存在冲突, 冲突描述)
        """
        if len(available_modalities) < 2:
            return False, None
        
        # 比较各模态的主要情绪
        categories = []
        valences = []
        
        for modality in available_modalities:
            if modality in emotion_vectors:
                categories.append(emotion_vectors[modality]["category"])
                valences.append(emotion_vectors[modality]["valence"])
        
        # 检查情绪类别冲突
        unique_categories = set(categories)
        if len(unique_categories) > 1:
            # 检查效价方向是否一致
            positive_count = sum(1 for v in valences if v > 0.1)
            negative_count = sum(1 for v in valences if v < -0.1)
            
            if positive_count > 0 and negative_count > 0:
                # 存在正负情绪冲突
                conflict_info = f"Emotion conflict detected: {categories}, valences: {valences}"
                logger.info(conflict_info)
                return True, conflict_info
        
        # 检查效价差异
        if len(valences) >= 2:
            valence_diff = max(valences) - min(valences)
            if valence_diff > self.CONFLICT_THRESHOLD:
                conflict_info = f"Valence conflict: diff={valence_diff:.2f}"
                logger.info(conflict_info)
                return True, conflict_info
        
        return False, None
    
    def _resolve_conflict(
        self,
        emotion_vectors: Dict[str, Dict[str, float]],
        available_modalities: List[str]
    ) -> Tuple[Dict[str, float], str]:
        """
        解决模态冲突
        
        优先级：生理 > 面部 > 语音
        
        Args:
            emotion_vectors: 各模态的情绪向量
            available_modalities: 可用模态列表
            
        Returns:
            (融合后的情绪向量, 解决策略描述)
        """
        # 按优先级选择主导模态
        primary_modality = None
        for modality in self.conflict_resolution_priority:
            if modality in available_modalities and modality in emotion_vectors:
                primary_modality = modality
                break
        
        if primary_modality is None:
            primary_modality = available_modalities[0]
        
        primary_vector = emotion_vectors[primary_modality]
        
        resolution_info = f"Conflict resolved using {primary_modality} (priority: {self.conflict_resolution_priority})"
        logger.info(resolution_info)
        
        # 使用主导模态的情绪，但融合其他模态的强度信息
        fused = {
            "category": primary_vector["category"],
            "intensity": primary_vector["intensity"],
            "valence": primary_vector["valence"],
            "arousal": primary_vector["arousal"]
        }
        
        # 融合其他模态的唤醒度（取平均）
        arousal_values = [
            emotion_vectors[m]["arousal"] 
            for m in available_modalities 
            if m in emotion_vectors
        ]
        if arousal_values:
            fused["arousal"] = sum(arousal_values) / len(arousal_values)
        
        return fused, resolution_info
    
    def _weighted_fusion(
        self,
        emotion_vectors: Dict[str, Dict[str, float]],
        weights: ModalityWeights,
        available_modalities: List[str]
    ) -> Dict[str, float]:
        """
        加权融合情绪向量
        
        Args:
            emotion_vectors: 各模态的情绪向量
            weights: 归一化后的权重
            available_modalities: 可用模态列表
            
        Returns:
            融合后的情绪向量
        """
        # 融合情绪分数
        fused_scores = {}
        for emotion in EmotionCategory:
            emotion_key = emotion.value
            weighted_score = 0.0
            
            for modality in available_modalities:
                if modality in emotion_vectors:
                    modality_weight = getattr(weights, modality)
                    modality_scores = emotion_vectors[modality].get("scores", {})
                    score = modality_scores.get(emotion_key, 0.0)
                    weighted_score += score * modality_weight
            
            fused_scores[emotion_key] = weighted_score
        
        # 获取主要情绪
        primary_emotion = max(fused_scores, key=fused_scores.get)
        
        # 融合效价和唤醒度
        fused_valence = 0.0
        fused_arousal = 0.0
        fused_intensity = 0.0
        
        for modality in available_modalities:
            if modality in emotion_vectors:
                modality_weight = getattr(weights, modality)
                fused_valence += emotion_vectors[modality]["valence"] * modality_weight
                fused_arousal += emotion_vectors[modality]["arousal"] * modality_weight
                fused_intensity += emotion_vectors[modality]["intensity"] * modality_weight
        
        return {
            "category": primary_emotion,
            "scores": fused_scores,
            "intensity": fused_intensity,
            "valence": fused_valence,
            "arousal": fused_arousal
        }
    
    def _create_emotion_state(
        self,
        fused_emotion: Dict[str, float],
        audio_result: Optional[Emotion2VecResult],
        face_result: Optional[FaceAnalysisResult],
        bio_result: Optional[BioAnalysisResult]
    ) -> EmotionState:
        """
        创建最终的情绪状态
        
        Args:
            fused_emotion: 融合后的情绪向量
            audio_result: 语音分析结果
            face_result: 面部分析结果
            bio_result: 生理信号分析结果
            
        Returns:
            EmotionState 情绪状态
        """
        category = self.EMOTION_MAPPING.get(
            fused_emotion["category"],
            EmotionCategory.NEUTRAL
        )
        
        # 计算置信度（基于各模态的置信度加权）
        confidence = self._calculate_confidence(audio_result, face_result, bio_result)
        
        # 确保值在有效范围内
        intensity = max(0.0, min(1.0, fused_emotion.get("intensity", 0.5)))
        valence = max(-1.0, min(1.0, fused_emotion.get("valence", 0.0)))
        arousal = max(0.0, min(1.0, fused_emotion.get("arousal", 0.3)))
        
        return EmotionState(
            category=category,
            intensity=intensity,
            valence=valence,
            arousal=arousal,
            confidence=confidence,
            timestamp=datetime.now(),
            audio_emotion=audio_result.scores if audio_result else None,
            face_emotion=face_result.expression_scores if face_result and face_result.detected else None,
            bio_stress=bio_result.stress_index if bio_result and bio_result.is_valid else None
        )
    
    def _calculate_confidence(
        self,
        audio_result: Optional[Emotion2VecResult],
        face_result: Optional[FaceAnalysisResult],
        bio_result: Optional[BioAnalysisResult]
    ) -> float:
        """
        计算融合结果的置信度
        
        Args:
            audio_result: 语音分析结果
            face_result: 面部分析结果
            bio_result: 生理信号分析结果
            
        Returns:
            置信度 (0-1)
        """
        confidences = []
        weights = []
        
        if audio_result is not None:
            confidences.append(audio_result.intensity)
            weights.append(self.weights.audio)
        
        if face_result is not None and face_result.detected:
            confidences.append(face_result.confidence)
            weights.append(self.weights.face)
        
        if bio_result is not None and bio_result.is_valid:
            # 生理信号的置信度基于数据有效性
            confidences.append(0.8)  # 有效的生理数据给予较高置信度
            weights.append(self.weights.bio)
        
        if not confidences:
            return 0.0
        
        # 加权平均
        total_weight = sum(weights)
        if total_weight > 0:
            weighted_confidence = sum(c * w for c, w in zip(confidences, weights)) / total_weight
        else:
            weighted_confidence = sum(confidences) / len(confidences)
        
        return min(1.0, weighted_confidence)
    
    def _calculate_contributions(
        self,
        emotion_vectors: Dict[str, Dict[str, float]],
        weights: ModalityWeights,
        available_modalities: List[str]
    ) -> Dict[str, float]:
        """
        计算各模态的贡献度
        
        Args:
            emotion_vectors: 各模态的情绪向量
            weights: 权重配置
            available_modalities: 可用模态列表
            
        Returns:
            各模态的贡献度
        """
        contributions = {"audio": 0.0, "face": 0.0, "bio": 0.0}
        
        for modality in available_modalities:
            if modality in emotion_vectors:
                contributions[modality] = getattr(weights, modality)
        
        return contributions
    
    def _create_default_result(self) -> FusionResult:
        """
        创建默认的融合结果（无有效数据时）
        
        Returns:
            默认的 FusionResult
        """
        default_state = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.0,
            valence=0.0,
            arousal=0.3,
            confidence=0.0,
            timestamp=datetime.now()
        )
        
        return FusionResult(
            emotion_state=default_state,
            fusion_mode=FusionMode.AUDIO_ONLY,
            modality_contributions={"audio": 0.0, "face": 0.0, "bio": 0.0},
            conflict_detected=False,
            conflict_resolution=None
        )
    
    def set_weights(self, audio: float, face: float, bio: float) -> None:
        """
        动态设置模态权重
        
        Args:
            audio: 语音权重
            face: 面部权重
            bio: 生理信号权重
        """
        self.weights = ModalityWeights(audio=audio, face=face, bio=bio)
        logger.info(
            f"Weights updated: audio={self.weights.audio:.2f}, "
            f"face={self.weights.face:.2f}, bio={self.weights.bio:.2f}"
        )
    
    def get_weights(self) -> ModalityWeights:
        """获取当前权重配置"""
        return self.weights
    
    def set_conflict_priority(self, priority: List[str]) -> None:
        """
        设置冲突解决优先级
        
        Args:
            priority: 优先级列表，如 ["bio", "face", "audio"]
        """
        valid_modalities = {"bio", "face", "audio"}
        if not all(m in valid_modalities for m in priority):
            raise ValueError(f"Invalid modality in priority list. Valid: {valid_modalities}")
        
        self.conflict_resolution_priority = priority
        logger.info(f"Conflict resolution priority updated: {priority}")
    
    # ==================== 单模态降级模式 ====================
    
    def fuse_audio_only(
        self,
        audio_result: Emotion2VecResult,
        sensevoice_result: Optional[AudioAnalysisResult] = None
    ) -> FusionResult:
        """
        仅语音模式融合
        
        当面部和生理信号不可用时使用
        
        Args:
            audio_result: emotion2vec+ 语音情绪分析结果
            sensevoice_result: SenseVoice 语音识别结果（可选）
            
        Returns:
            FusionResult 融合结果
        """
        return self.fuse(
            audio_result=audio_result,
            face_result=None,
            bio_result=None,
            sensevoice_result=sensevoice_result
        )
    
    def fuse_face_only(
        self,
        face_result: FaceAnalysisResult
    ) -> FusionResult:
        """
        仅面部模式融合
        
        当语音和生理信号不可用时使用
        
        Args:
            face_result: 面部表情分析结果
            
        Returns:
            FusionResult 融合结果
        """
        return self.fuse(
            audio_result=None,
            face_result=face_result,
            bio_result=None
        )
    
    def fuse_bio_only(
        self,
        bio_result: BioAnalysisResult
    ) -> FusionResult:
        """
        仅生理信号模式融合
        
        当语音和面部不可用时使用
        
        Args:
            bio_result: 生理信号分析结果
            
        Returns:
            FusionResult 融合结果
        """
        return self.fuse(
            audio_result=None,
            face_result=None,
            bio_result=bio_result
        )
    
    def configure_degraded_mode(
        self,
        mode: FusionMode
    ) -> ModalityWeights:
        """
        配置降级模式的权重
        
        根据指定的融合模式返回适当的权重配置
        
        Args:
            mode: 融合模式
            
        Returns:
            适合该模式的权重配置
        """
        mode_weights = {
            FusionMode.FULL: ModalityWeights(audio=0.35, face=0.35, bio=0.30),
            FusionMode.AUDIO_FACE: ModalityWeights(audio=0.55, face=0.45, bio=0.0),
            FusionMode.AUDIO_BIO: ModalityWeights(audio=0.50, face=0.0, bio=0.50),
            FusionMode.FACE_BIO: ModalityWeights(audio=0.0, face=0.55, bio=0.45),
            FusionMode.AUDIO_ONLY: ModalityWeights(audio=1.0, face=0.0, bio=0.0),
            FusionMode.FACE_ONLY: ModalityWeights(audio=0.0, face=1.0, bio=0.0),
            FusionMode.BIO_ONLY: ModalityWeights(audio=0.0, face=0.0, bio=1.0),
        }
        
        return mode_weights.get(mode, ModalityWeights())
    
    def get_degradation_info(self, fusion_mode: FusionMode) -> Dict[str, Any]:
        """
        获取降级模式的详细信息
        
        Args:
            fusion_mode: 当前融合模式
            
        Returns:
            降级模式信息字典
        """
        mode_info = {
            FusionMode.FULL: {
                "name": "完整模式",
                "description": "使用语音、面部和生理信号三模态融合",
                "available_modalities": ["audio", "face", "bio"],
                "reliability": "high",
                "is_degraded": False
            },
            FusionMode.AUDIO_FACE: {
                "name": "语音+面部模式",
                "description": "生理信号不可用，使用语音和面部双模态融合",
                "available_modalities": ["audio", "face"],
                "reliability": "medium-high",
                "is_degraded": True
            },
            FusionMode.AUDIO_BIO: {
                "name": "语音+生理模式",
                "description": "面部不可用，使用语音和生理信号双模态融合",
                "available_modalities": ["audio", "bio"],
                "reliability": "medium-high",
                "is_degraded": True
            },
            FusionMode.FACE_BIO: {
                "name": "面部+生理模式",
                "description": "语音不可用，使用面部和生理信号双模态融合",
                "available_modalities": ["face", "bio"],
                "reliability": "medium-high",
                "is_degraded": True
            },
            FusionMode.AUDIO_ONLY: {
                "name": "仅语音模式",
                "description": "仅使用语音情绪分析",
                "available_modalities": ["audio"],
                "reliability": "medium",
                "is_degraded": True
            },
            FusionMode.FACE_ONLY: {
                "name": "仅面部模式",
                "description": "仅使用面部表情分析",
                "available_modalities": ["face"],
                "reliability": "medium",
                "is_degraded": True
            },
            FusionMode.BIO_ONLY: {
                "name": "仅生理模式",
                "description": "仅使用生理信号分析",
                "available_modalities": ["bio"],
                "reliability": "medium-low",
                "is_degraded": True
            }
        }
        
        return mode_info.get(fusion_mode, {
            "name": "未知模式",
            "description": "未知的融合模式",
            "available_modalities": [],
            "reliability": "unknown",
            "is_degraded": True
        })
    
    def is_degraded_mode(self, fusion_mode: FusionMode) -> bool:
        """
        检查是否处于降级模式
        
        Args:
            fusion_mode: 融合模式
            
        Returns:
            是否为降级模式
        """
        return fusion_mode != FusionMode.FULL
