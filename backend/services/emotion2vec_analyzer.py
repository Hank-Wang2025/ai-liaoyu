"""
emotion2vec+ 情绪识别模块
emotion2vec+ Emotion Recognition Module

使用阿里达摩院 emotion2vec+ 模型进行细粒度情绪识别
支持 9 类情绪识别：angry, happy, neutral, sad, surprised, fearful, disgusted, anxious, tired
"""
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from loguru import logger

from models.emotion import EmotionCategory, Emotion2VecResult
from services.audio_preprocessor import AudioPreprocessor


class Emotion2VecAnalyzer:
    """
    emotion2vec+ 情绪分析器
    
    功能:
    - 9 类细粒度情绪识别
    - 情绪强度计算
    - 跨语言情绪识别
    """
    
    # 默认模型路径
    DEFAULT_MODEL = "iic/emotion2vec_plus_large"
    
    # emotion2vec+ 支持的 9 类情绪标签
    EMOTION_LABELS = [
        "angry",      # 生气
        "happy",      # 开心
        "neutral",    # 中立
        "sad",        # 难过
        "surprised",  # 惊讶
        "fearful",    # 恐惧
        "disgusted",  # 厌恶
        "anxious",    # 焦虑 (emotion2vec+ 扩展)
        "tired"       # 疲惫 (emotion2vec+ 扩展)
    ]
    
    # 情绪到 EmotionCategory 的映射
    EMOTION_CATEGORY_MAP = {
        "angry": EmotionCategory.ANGRY,
        "happy": EmotionCategory.HAPPY,
        "neutral": EmotionCategory.NEUTRAL,
        "sad": EmotionCategory.SAD,
        "surprised": EmotionCategory.SURPRISED,
        "fearful": EmotionCategory.FEARFUL,
        "disgusted": EmotionCategory.DISGUSTED,
        "anxious": EmotionCategory.ANXIOUS,
        "tired": EmotionCategory.TIRED
    }
    
    # 情绪效价映射 (valence: -1 负面 到 1 正面)
    EMOTION_VALENCE = {
        "angry": -0.8,
        "happy": 0.9,
        "neutral": 0.0,
        "sad": -0.7,
        "surprised": 0.2,
        "fearful": -0.6,
        "disgusted": -0.7,
        "anxious": -0.5,
        "tired": -0.3
    }
    
    # 情绪唤醒度映射 (arousal: 0 平静 到 1 激动)
    EMOTION_AROUSAL = {
        "angry": 0.9,
        "happy": 0.7,
        "neutral": 0.3,
        "sad": 0.2,
        "surprised": 0.8,
        "fearful": 0.8,
        "disgusted": 0.5,
        "anxious": 0.7,
        "tired": 0.1
    }
    
    def __init__(
        self, 
        model_dir: str = None,
        device: str = "cpu",
        granularity: str = "utterance"
    ):
        """
        初始化 emotion2vec+ 分析器
        
        Args:
            model_dir: 模型目录路径，默认使用 ModelScope 模型
            device: 运行设备 ("cpu", "cuda", "mps")
            granularity: 分析粒度 ("utterance" 整句, "frame" 帧级)
        """
        self.model_dir = model_dir or self.DEFAULT_MODEL
        self.device = device
        self.granularity = granularity
        
        self.model = None
        self.preprocessor = AudioPreprocessor()
        self._initialized = False
        
        logger.info(f"emotion2vec+ analyzer created with model: {self.model_dir}")
    
    def initialize(self) -> bool:
        """
        初始化模型
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
            
        try:
            # 尝试导入 FunASR
            from funasr import AutoModel
            
            self.model = AutoModel(
                model=self.model_dir,
                device=self.device,
                trust_remote_code=True
            )
            
            self._initialized = True
            logger.info(f"emotion2vec+ model initialized successfully on {self.device}")
            return True
            
        except ImportError as e:
            logger.error(f"FunASR not installed: {e}")
            logger.info("Please install: pip install funasr modelscope")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize emotion2vec+ model: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查模型是否已初始化"""
        return self._initialized
    
    async def analyze(self, audio_path: str) -> Emotion2VecResult:
        """
        分析音频情绪
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            Emotion2VecResult 分析结果
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("emotion2vec+ model not initialized")
        
        # 验证文件存在
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # 调用模型进行识别
            result = self.model.generate(
                input=audio_path,
                granularity=self.granularity,
                extract_embedding=False
            )
            
            # 解析结果
            return self._parse_result(result)
            
        except Exception as e:
            logger.error(f"emotion2vec+ analysis failed: {e}")
            raise
    
    def analyze_sync(self, audio_path: str) -> Emotion2VecResult:
        """
        同步分析音频情绪（用于非异步环境）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            Emotion2VecResult 分析结果
        """
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.analyze(audio_path))
        finally:
            loop.close()
    
    def _parse_result(self, result: Any) -> Emotion2VecResult:
        """
        解析 emotion2vec+ 模型输出
        
        emotion2vec+ 输出格式示例:
        [{'key': 'audio_path', 'scores': [0.1, 0.2, ...], 'labels': ['angry', 'happy', ...]}]
        
        Args:
            result: 模型原始输出
            
        Returns:
            Emotion2VecResult 解析后的结果
        """
        if not result or len(result) == 0:
            return Emotion2VecResult(
                emotion=EmotionCategory.NEUTRAL,
                scores={label: 0.0 for label in self.EMOTION_LABELS},
                intensity=0.0
            )
        
        # 获取第一个结果
        first_result = result[0] if isinstance(result, list) else result
        
        # 解析分数
        scores_dict = self._extract_scores(first_result)
        
        # 获取主要情绪
        primary_emotion = self._get_primary_emotion(scores_dict)
        
        # 计算情绪强度
        intensity = self._calculate_intensity(scores_dict, primary_emotion)
        
        return Emotion2VecResult(
            emotion=self.EMOTION_CATEGORY_MAP.get(primary_emotion, EmotionCategory.NEUTRAL),
            scores=scores_dict,
            intensity=intensity,
            timestamp=datetime.now()
        )
    
    def _extract_scores(self, result: Dict) -> Dict[str, float]:
        """
        从模型输出中提取情绪分数
        
        Args:
            result: 单个结果字典
            
        Returns:
            情绪标签到分数的映射
        """
        scores_dict = {label: 0.0 for label in self.EMOTION_LABELS}
        
        if isinstance(result, dict):
            # 尝试获取 scores 和 labels
            scores = result.get('scores', [])
            labels = result.get('labels', self.EMOTION_LABELS)
            
            if isinstance(scores, list) and len(scores) > 0:
                # 如果 scores 是嵌套列表，取第一个
                if isinstance(scores[0], list):
                    scores = scores[0]
                
                # 映射分数到标签
                for i, score in enumerate(scores):
                    if i < len(labels):
                        label = labels[i].lower() if isinstance(labels[i], str) else str(labels[i])
                        if label in scores_dict:
                            scores_dict[label] = float(score)
        
        # 归一化分数（确保总和为 1）
        total = sum(scores_dict.values())
        if total > 0:
            scores_dict = {k: v / total for k, v in scores_dict.items()}
        
        return scores_dict
    
    def _get_primary_emotion(self, scores: Dict[str, float]) -> str:
        """
        获取主要情绪（分数最高的情绪）
        
        Args:
            scores: 情绪分数字典
            
        Returns:
            主要情绪标签
        """
        if not scores:
            return "neutral"
        
        return max(scores, key=scores.get)
    
    def _calculate_intensity(self, scores: Dict[str, float], primary_emotion: str) -> float:
        """
        计算情绪强度
        
        强度计算方法:
        1. 主要情绪的分数作为基础
        2. 考虑与其他情绪的差距（差距越大，强度越高）
        
        Args:
            scores: 情绪分数字典
            primary_emotion: 主要情绪
            
        Returns:
            情绪强度 (0-1)
        """
        if not scores or primary_emotion not in scores:
            return 0.0
        
        primary_score = scores[primary_emotion]
        
        # 计算与第二高分数的差距
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) > 1:
            second_score = sorted_scores[1]
            gap = primary_score - second_score
        else:
            gap = primary_score
        
        # 强度 = 主要分数 * (1 + 差距权重)
        # 差距越大，强度越高
        intensity = primary_score * (1 + gap * 0.5)
        
        return min(intensity, 1.0)
    
    def get_valence(self, emotion: str) -> float:
        """
        获取情绪的效价值
        
        Args:
            emotion: 情绪标签
            
        Returns:
            效价值 (-1 到 1)
        """
        return self.EMOTION_VALENCE.get(emotion.lower(), 0.0)
    
    def get_arousal(self, emotion: str) -> float:
        """
        获取情绪的唤醒度
        
        Args:
            emotion: 情绪标签
            
        Returns:
            唤醒度 (0 到 1)
        """
        return self.EMOTION_AROUSAL.get(emotion.lower(), 0.3)
    
    def get_emotion_labels(self) -> List[str]:
        """获取支持的情绪标签列表"""
        return self.EMOTION_LABELS.copy()
    
    def cleanup(self):
        """清理资源"""
        if self.model is not None:
            del self.model
            self.model = None
            self._initialized = False
            logger.info("emotion2vec+ model cleaned up")
