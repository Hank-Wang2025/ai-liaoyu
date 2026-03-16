"""
SenseVoice 语音分析模块
SenseVoice Speech Analysis Module

使用阿里达摩院 SenseVoice 模型进行语音识别和情感分析
支持中文、英文、粤语、日语、韩语的语音识别
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger

from models.emotion import AudioAnalysisResult, SupportedLanguage, AudioEvent
from services.audio_preprocessor import AudioPreprocessor


class SenseVoiceAnalyzer:
    """
    SenseVoice 语音分析器
    
    功能:
    - 语音识别 (ASR)
    - 情感标签识别
    - 音频事件检测
    - 多语言支持
    """
    
    # 默认模型路径
    DEFAULT_MODEL = "iic/SenseVoiceSmall"
    
    # SenseVoice 支持的情感标签
    EMOTION_TAGS = {
        "HAPPY": "happy",
        "SAD": "sad", 
        "ANGRY": "angry",
        "NEUTRAL": "neutral",
        "FEARFUL": "fearful",
        "DISGUSTED": "disgusted",
        "SURPRISED": "surprised"
    }
    
    # SenseVoice 支持的音频事件
    AUDIO_EVENTS = {
        "Laughter": AudioEvent.LAUGHTER.value,
        "Crying": AudioEvent.CRYING.value,
        "Cough": AudioEvent.COUGH.value,
        "Sigh": AudioEvent.SIGH.value,
        "Applause": "applause",
        "BGM": "bgm",
        "Speech": "speech"
    }
    
    # 语言代码映射
    LANGUAGE_MAP = {
        "zh": SupportedLanguage.CHINESE.value,
        "en": SupportedLanguage.ENGLISH.value,
        "yue": SupportedLanguage.CANTONESE.value,
        "ja": SupportedLanguage.JAPANESE.value,
        "ko": SupportedLanguage.KOREAN.value,
        "auto": SupportedLanguage.AUTO.value
    }
    
    def __init__(
        self, 
        model_dir: str = None,
        device: str = "cpu",
        use_vad: bool = True,
        max_segment_time: int = 30000
    ):
        """
        初始化 SenseVoice 分析器
        
        Args:
            model_dir: 模型目录路径，默认使用 ModelScope 模型
            device: 运行设备 ("cpu", "cuda", "mps")
            use_vad: 是否使用 VAD (语音活动检测)
            max_segment_time: VAD 最大分段时间（毫秒）
        """
        self.model_dir = model_dir or self.DEFAULT_MODEL
        self.device = device
        self.use_vad = use_vad
        self.max_segment_time = max_segment_time
        
        self.model = None
        self.preprocessor = AudioPreprocessor()
        self._initialized = False
        
        logger.info(f"SenseVoice analyzer created with model: {self.model_dir}")
    
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
            
            vad_kwargs = {"max_single_segment_time": self.max_segment_time} if self.use_vad else {}
            vad_model = "fsmn-vad" if self.use_vad else None
            
            self.model = AutoModel(
                model=self.model_dir,
                vad_model=vad_model,
                vad_kwargs=vad_kwargs,
                device=self.device,
                trust_remote_code=True
            )
            
            self._initialized = True
            logger.info(f"SenseVoice model initialized successfully on {self.device}")
            return True
            
        except ImportError as e:
            logger.error(f"FunASR not installed: {e}")
            logger.info("Please install: pip install funasr modelscope")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize SenseVoice model: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查模型是否已初始化"""
        return self._initialized
    
    async def analyze(
        self, 
        audio_path: str,
        language: str = "auto",
        use_itn: bool = True
    ) -> AudioAnalysisResult:
        """
        分析音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码 ("auto", "zh", "en", "yue", "ja", "ko")
            use_itn: 是否使用逆文本正则化
            
        Returns:
            AudioAnalysisResult 分析结果
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("SenseVoice model not initialized")
        
        # 验证文件存在
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        # 获取音频信息
        try:
            audio_info = self.preprocessor.get_audio_info(audio_path)
            duration_ms = audio_info.get("duration_ms", 0)
        except Exception as e:
            logger.warning(f"Could not get audio info: {e}")
            duration_ms = 0
        
        try:
            # 调用模型进行识别
            result = self.model.generate(
                input=audio_path,
                language=language,
                use_itn=use_itn,
                batch_size_s=60
            )
            
            # 解析结果
            return self._parse_result(result, duration_ms)
            
        except Exception as e:
            logger.error(f"SenseVoice analysis failed: {e}")
            raise
    
    def analyze_sync(
        self, 
        audio_path: str,
        language: str = "auto",
        use_itn: bool = True
    ) -> AudioAnalysisResult:
        """
        同步分析音频文件（用于非异步环境）
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            use_itn: 是否使用逆文本正则化
            
        Returns:
            AudioAnalysisResult 分析结果
        """
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.analyze(audio_path, language, use_itn))
        finally:
            loop.close()
    
    def _parse_result(self, result: Any, duration_ms: int = 0) -> AudioAnalysisResult:
        """
        解析 SenseVoice 模型输出
        
        SenseVoice 输出格式示例:
        [{'key': 'audio_path', 'text': '<|zh|><|NEUTRAL|><|Speech|>识别的文本内容'}]
        
        Args:
            result: 模型原始输出
            duration_ms: 音频时长（毫秒）
            
        Returns:
            AudioAnalysisResult 解析后的结果
        """
        if not result or len(result) == 0:
            return AudioAnalysisResult(
                text="",
                language="unknown",
                emotion="neutral",
                event=AudioEvent.NONE.value,
                confidence=0.0,
                duration_ms=duration_ms,
                raw_output=result
            )
        
        # 获取第一个结果
        first_result = result[0] if isinstance(result, list) else result
        raw_text = first_result.get('text', '') if isinstance(first_result, dict) else str(first_result)
        
        # 解析标签和文本
        language, emotion, event, clean_text = self._parse_tags(raw_text)
        
        # 计算置信度（基于文本长度和标签完整性）
        confidence = self._calculate_confidence(language, emotion, event, clean_text)
        
        return AudioAnalysisResult(
            text=clean_text,
            language=language,
            emotion=emotion,
            event=event,
            confidence=confidence,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            raw_output={"result": result, "raw_text": raw_text}
        )
    
    def _parse_tags(self, text: str) -> tuple:
        """
        解析 SenseVoice 输出中的标签
        
        格式: <|language|><|EMOTION|><|Event|>实际文本
        
        Args:
            text: 原始输出文本
            
        Returns:
            (language, emotion, event, clean_text) 元组
        """
        # 默认值
        language = "unknown"
        emotion = "neutral"
        event = AudioEvent.NONE.value
        clean_text = text
        
        # 匹配标签模式 <|xxx|>
        tag_pattern = r'<\|([^|]+)\|>'
        tags = re.findall(tag_pattern, text)
        
        for tag in tags:
            tag_upper = tag.upper()
            tag_lower = tag.lower()
            
            # 检查是否是语言标签
            if tag_lower in self.LANGUAGE_MAP:
                language = self.LANGUAGE_MAP[tag_lower]
            # 检查是否是情感标签
            elif tag_upper in self.EMOTION_TAGS:
                emotion = self.EMOTION_TAGS[tag_upper]
            # 检查是否是音频事件
            elif tag in self.AUDIO_EVENTS:
                event = self.AUDIO_EVENTS[tag]
        
        # 移除所有标签，获取纯文本
        clean_text = re.sub(tag_pattern, '', text).strip()
        
        return language, emotion, event, clean_text
    
    def _calculate_confidence(
        self, 
        language: str, 
        emotion: str, 
        event: str, 
        text: str
    ) -> float:
        """
        计算识别结果的置信度
        
        Args:
            language: 识别的语言
            emotion: 识别的情感
            event: 识别的事件
            text: 识别的文本
            
        Returns:
            置信度 (0-1)
        """
        confidence = 0.0
        
        # 有文本内容 +0.4
        if text and len(text) > 0:
            confidence += 0.4
            
        # 识别到语言 +0.2
        if language != "unknown":
            confidence += 0.2
            
        # 识别到情感 +0.2
        if emotion != "neutral":
            confidence += 0.2
        else:
            confidence += 0.1  # neutral 也是有效情感
            
        # 识别到事件 +0.2
        if event != AudioEvent.NONE.value:
            confidence += 0.2
        else:
            confidence += 0.1  # 没有特殊事件也是正常的
            
        return min(confidence, 1.0)
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return list(self.LANGUAGE_MAP.keys())
    
    def get_emotion_labels(self) -> List[str]:
        """获取支持的情感标签列表"""
        return list(self.EMOTION_TAGS.values())
    
    def get_audio_events(self) -> List[str]:
        """获取支持的音频事件列表"""
        return list(self.AUDIO_EVENTS.values())
    
    def cleanup(self):
        """清理资源"""
        if self.model is not None:
            del self.model
            self.model = None
            self._initialized = False
            logger.info("SenseVoice model cleaned up")
