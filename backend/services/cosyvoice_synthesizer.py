"""
CosyVoice 语音合成模块
CosyVoice Voice Synthesis Module

使用阿里达摩院 CosyVoice 3.0 模型进行语音合成
支持情感控制、语速调节和流式生成
"""
import os
import io
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

# 尝试导入音频处理库
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy not installed, some audio features may be limited")

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False
    logger.warning("soundfile not installed, audio file saving may be limited")


class VoiceEmotion(str, Enum):
    """语音情感类型"""
    GENTLE = "gentle"       # 温柔
    WARM = "warm"           # 温暖
    CALM = "calm"           # 平静
    ENCOURAGING = "encouraging"  # 鼓励


class VoiceSpeaker(str, Enum):
    """预设语音角色"""
    CHINESE_FEMALE = "中文女"
    CHINESE_MALE = "中文男"
    ENGLISH_FEMALE = "英文女"
    ENGLISH_MALE = "英文男"


@dataclass
class VoiceSynthesisConfig:
    """语音合成配置"""
    speaker: str = VoiceSpeaker.CHINESE_FEMALE.value
    emotion: VoiceEmotion = VoiceEmotion.GENTLE
    speed: float = 1.0  # 语速 0.8-1.2
    stream: bool = False  # 是否流式生成
    
    def __post_init__(self):
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError(f"speed must be between 0.5 and 2.0, got {self.speed}")


@dataclass
class SynthesisResult:
    """语音合成结果"""
    audio_data: bytes  # 音频数据
    sample_rate: int  # 采样率
    duration_ms: int  # 时长（毫秒）
    text: str  # 原始文本
    emotion: str  # 使用的情感
    speaker: str  # 使用的语音角色
    timestamp: datetime = field(default_factory=datetime.now)
    
    def save_to_file(self, file_path: str) -> str:
        """保存音频到文件"""
        if not HAS_SOUNDFILE:
            raise ImportError("soundfile library is required for saving audio")
        
        # 将 bytes 转换为 numpy array
        audio_array = np.frombuffer(self.audio_data, dtype=np.float32)
        sf.write(file_path, audio_array, self.sample_rate)
        return file_path


class CosyVoiceSynthesizer:
    """
    CosyVoice 语音合成器
    
    功能:
    - 文本转语音 (TTS)
    - 情感控制语音生成
    - 语速控制
    - 流式语音生成
    - 零样本语音克隆
    """
    
    # 默认模型路径
    DEFAULT_MODEL = "pretrained_models/CosyVoice-300M-SFT"
    DEFAULT_MODEL_V2 = "pretrained_models/CosyVoice2-0.5B"
    DEFAULT_MODEL_V3 = "pretrained_models/Fun-CosyVoice3-0.5B"
    
    # 情感到指令的映射
    EMOTION_PROMPTS = {
        VoiceEmotion.GENTLE: "请用温柔、轻柔的语气说这句话",
        VoiceEmotion.WARM: "请用温暖、亲切的语气说这句话",
        VoiceEmotion.CALM: "请用平静、舒缓的语气说这句话",
        VoiceEmotion.ENCOURAGING: "请用鼓励、积极的语气说这句话",
    }
    
    # 语速到指令的映射
    SPEED_PROMPTS = {
        "slow": "请用较慢的语速说这句话",
        "normal": "",
        "fast": "请用较快的语速说这句话",
    }
    
    def __init__(
        self,
        model_dir: str = None,
        device: str = "cpu",
        model_version: str = "v1"
    ):
        """
        初始化 CosyVoice 合成器
        
        Args:
            model_dir: 模型目录路径
            device: 运行设备 ("cpu", "cuda", "mps")
            model_version: 模型版本 ("v1", "v2", "v3")
        """
        self.model_version = model_version
        
        # 根据版本选择默认模型
        if model_dir is None:
            if model_version == "v3":
                self.model_dir = self.DEFAULT_MODEL_V3
            elif model_version == "v2":
                self.model_dir = self.DEFAULT_MODEL_V2
            else:
                self.model_dir = self.DEFAULT_MODEL
        else:
            self.model_dir = model_dir
            
        self.device = device
        self.model = None
        self.sample_rate = 22050  # CosyVoice 默认采样率
        self._initialized = False
        self._available_speakers: List[str] = []
        
        logger.info(f"CosyVoice synthesizer created with model: {self.model_dir}")
    
    def initialize(self) -> bool:
        """
        初始化模型
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        try:
            # 尝试导入 CosyVoice
            from cosyvoice.cli.cosyvoice import AutoModel
            
            self.model = AutoModel(model_dir=self.model_dir)
            self.sample_rate = self.model.sample_rate
            
            # 获取可用的语音角色
            try:
                self._available_speakers = self.model.list_available_spks()
            except Exception:
                self._available_speakers = [
                    VoiceSpeaker.CHINESE_FEMALE.value,
                    VoiceSpeaker.CHINESE_MALE.value
                ]
            
            self._initialized = True
            logger.info(f"CosyVoice model initialized successfully on {self.device}")
            logger.info(f"Available speakers: {self._available_speakers}")
            return True
            
        except ImportError as e:
            logger.error(f"CosyVoice not installed: {e}")
            logger.info("Please install CosyVoice: git clone https://github.com/FunAudioLLM/CosyVoice.git")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize CosyVoice model: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查模型是否已初始化"""
        return self._initialized
    
    def get_available_speakers(self) -> List[str]:
        """获取可用的语音角色列表"""
        return self._available_speakers.copy()
    
    def _build_instruct_prompt(
        self,
        emotion: VoiceEmotion,
        speed: float
    ) -> str:
        """
        构建指令提示词
        
        Args:
            emotion: 情感类型
            speed: 语速
            
        Returns:
            指令提示词
        """
        prompts = []
        
        # 添加情感指令
        if emotion in self.EMOTION_PROMPTS:
            prompts.append(self.EMOTION_PROMPTS[emotion])
        
        # 添加语速指令
        if speed < 0.9:
            prompts.append(self.SPEED_PROMPTS["slow"])
        elif speed > 1.1:
            prompts.append(self.SPEED_PROMPTS["fast"])
        
        if prompts:
            return "。".join(prompts) + "<|endofprompt|>"
        return ""
    
    def _add_emotion_markers(self, text: str, emotion: VoiceEmotion) -> str:
        """
        为文本添加情感标记
        
        CosyVoice 支持的标记:
        - [laughter] 笑声
        - [breath] 呼吸声
        - <strong></strong> 强调
        
        Args:
            text: 原始文本
            emotion: 情感类型
            
        Returns:
            添加标记后的文本
        """
        # 根据情感类型添加适当的标记
        if emotion == VoiceEmotion.ENCOURAGING:
            # 鼓励语气可以在关键词前后添加强调
            # 这里简单处理，实际可以更智能
            pass
        
        return text
    
    async def synthesize(
        self,
        text: str,
        config: VoiceSynthesisConfig = None
    ) -> SynthesisResult:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            config: 合成配置
            
        Returns:
            SynthesisResult 合成结果
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("CosyVoice model not initialized")
        
        if config is None:
            config = VoiceSynthesisConfig()
        
        # 验证语音角色
        speaker = config.speaker
        if speaker not in self._available_speakers and self._available_speakers:
            logger.warning(f"Speaker '{speaker}' not available, using default")
            speaker = self._available_speakers[0]
        
        try:
            # 收集所有音频块
            audio_chunks = []
            
            # 使用 SFT 模式进行合成
            for chunk in self.model.inference_sft(
                text,
                speaker,
                stream=config.stream
            ):
                if 'tts_speech' in chunk:
                    audio_chunks.append(chunk['tts_speech'])
            
            # 合并音频块
            if audio_chunks:
                import torch
                combined_audio = torch.cat(audio_chunks, dim=1)
                audio_numpy = combined_audio.squeeze().cpu().numpy()
                audio_bytes = audio_numpy.astype(np.float32).tobytes()
                duration_ms = int(len(audio_numpy) / self.sample_rate * 1000)
            else:
                audio_bytes = b''
                duration_ms = 0
            
            return SynthesisResult(
                audio_data=audio_bytes,
                sample_rate=self.sample_rate,
                duration_ms=duration_ms,
                text=text,
                emotion=config.emotion.value,
                speaker=speaker
            )
            
        except Exception as e:
            logger.error(f"CosyVoice synthesis failed: {e}")
            raise
    
    async def synthesize_with_emotion(
        self,
        text: str,
        emotion: VoiceEmotion = VoiceEmotion.GENTLE,
        speed: float = 1.0,
        speaker: str = None
    ) -> SynthesisResult:
        """
        使用情感控制合成语音
        
        Args:
            text: 要合成的文本
            emotion: 情感类型
            speed: 语速 (0.8-1.2)
            speaker: 语音角色
            
        Returns:
            SynthesisResult 合成结果
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("CosyVoice model not initialized")
        
        # 验证语速范围
        speed = max(0.5, min(2.0, speed))
        
        # 验证语音角色
        if speaker is None:
            speaker = VoiceSpeaker.CHINESE_FEMALE.value
        if speaker not in self._available_speakers and self._available_speakers:
            speaker = self._available_speakers[0]
        
        try:
            audio_chunks = []
            
            # 根据模型版本选择不同的合成方式
            if self.model_version in ["v2", "v3"] and hasattr(self.model, 'inference_instruct2'):
                # 使用 instruct 模式进行情感控制
                instruct_prompt = self._build_instruct_prompt(emotion, speed)
                
                # 需要参考音频，这里使用默认的
                # 实际使用时可以提供参考音频
                for chunk in self.model.inference_sft(
                    text,
                    speaker,
                    stream=False
                ):
                    if 'tts_speech' in chunk:
                        audio_chunks.append(chunk['tts_speech'])
            else:
                # 使用 SFT 模式
                for chunk in self.model.inference_sft(
                    text,
                    speaker,
                    stream=False
                ):
                    if 'tts_speech' in chunk:
                        audio_chunks.append(chunk['tts_speech'])
            
            # 合并音频块
            if audio_chunks:
                import torch
                combined_audio = torch.cat(audio_chunks, dim=1)
                audio_numpy = combined_audio.squeeze().cpu().numpy()
                
                # 应用语速调整（通过重采样实现）
                if speed != 1.0:
                    audio_numpy = self._adjust_speed(audio_numpy, speed)
                
                audio_bytes = audio_numpy.astype(np.float32).tobytes()
                duration_ms = int(len(audio_numpy) / self.sample_rate * 1000)
            else:
                audio_bytes = b''
                duration_ms = 0
            
            return SynthesisResult(
                audio_data=audio_bytes,
                sample_rate=self.sample_rate,
                duration_ms=duration_ms,
                text=text,
                emotion=emotion.value,
                speaker=speaker
            )
            
        except Exception as e:
            logger.error(f"CosyVoice emotion synthesis failed: {e}")
            raise
    
    def _adjust_speed(self, audio: np.ndarray, speed: float) -> np.ndarray:
        """
        调整音频语速
        
        通过重采样实现语速调整
        speed > 1.0 加快语速
        speed < 1.0 减慢语速
        
        Args:
            audio: 音频数据
            speed: 语速倍率
            
        Returns:
            调整后的音频数据
        """
        if not HAS_NUMPY:
            return audio
        
        if speed == 1.0:
            return audio
        
        # 计算新的长度
        original_length = len(audio)
        new_length = int(original_length / speed)
        
        # 使用线性插值进行重采样
        indices = np.linspace(0, original_length - 1, new_length)
        adjusted_audio = np.interp(indices, np.arange(original_length), audio)
        
        return adjusted_audio.astype(np.float32)
    
    async def synthesize_stream(
        self,
        text: str,
        config: VoiceSynthesisConfig = None
    ) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音
        
        Args:
            text: 要合成的文本
            config: 合成配置
            
        Yields:
            音频数据块
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("CosyVoice model not initialized")
        
        if config is None:
            config = VoiceSynthesisConfig(stream=True)
        
        speaker = config.speaker
        if speaker not in self._available_speakers and self._available_speakers:
            speaker = self._available_speakers[0]
        
        try:
            for chunk in self.model.inference_sft(
                text,
                speaker,
                stream=True
            ):
                if 'tts_speech' in chunk:
                    audio_tensor = chunk['tts_speech']
                    audio_numpy = audio_tensor.squeeze().cpu().numpy()
                    yield audio_numpy.astype(np.float32).tobytes()
                    
        except Exception as e:
            logger.error(f"CosyVoice stream synthesis failed: {e}")
            raise
    
    async def clone_voice(
        self,
        text: str,
        reference_audio: str,
        reference_text: str = ""
    ) -> SynthesisResult:
        """
        零样本语音克隆
        
        Args:
            text: 要合成的文本
            reference_audio: 参考音频文件路径
            reference_text: 参考音频的文本内容
            
        Returns:
            SynthesisResult 合成结果
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("CosyVoice model not initialized")
        
        if not os.path.exists(reference_audio):
            raise FileNotFoundError(f"Reference audio not found: {reference_audio}")
        
        try:
            audio_chunks = []
            
            for chunk in self.model.inference_zero_shot(
                text,
                reference_text,
                reference_audio,
                stream=False
            ):
                if 'tts_speech' in chunk:
                    audio_chunks.append(chunk['tts_speech'])
            
            if audio_chunks:
                import torch
                combined_audio = torch.cat(audio_chunks, dim=1)
                audio_numpy = combined_audio.squeeze().cpu().numpy()
                audio_bytes = audio_numpy.astype(np.float32).tobytes()
                duration_ms = int(len(audio_numpy) / self.sample_rate * 1000)
            else:
                audio_bytes = b''
                duration_ms = 0
            
            return SynthesisResult(
                audio_data=audio_bytes,
                sample_rate=self.sample_rate,
                duration_ms=duration_ms,
                text=text,
                emotion="cloned",
                speaker="cloned_voice"
            )
            
        except Exception as e:
            logger.error(f"CosyVoice voice cloning failed: {e}")
            raise
    
    def cleanup(self):
        """清理资源"""
        if self.model is not None:
            del self.model
            self.model = None
            self._initialized = False
            logger.info("CosyVoice model cleaned up")



class MockCosyVoiceSynthesizer:
    """
    Mock CosyVoice 合成器
    
    用于测试和开发环境，当 CosyVoice 模型未安装时使用
    生成静音或简单的测试音频
    """
    
    def __init__(
        self,
        model_dir: str = None,
        device: str = "cpu",
        model_version: str = "v1"
    ):
        self.model_dir = model_dir or "mock_model"
        self.device = device
        self.model_version = model_version
        self.sample_rate = 22050
        self._initialized = False
        self._available_speakers = [
            VoiceSpeaker.CHINESE_FEMALE.value,
            VoiceSpeaker.CHINESE_MALE.value,
            VoiceSpeaker.ENGLISH_FEMALE.value,
            VoiceSpeaker.ENGLISH_MALE.value
        ]
        
        logger.info("MockCosyVoice synthesizer created (for testing)")
    
    def initialize(self) -> bool:
        """初始化 Mock 模型"""
        self._initialized = True
        logger.info("MockCosyVoice initialized")
        return True
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def get_available_speakers(self) -> List[str]:
        """获取可用的语音角色列表"""
        return self._available_speakers.copy()
    
    async def synthesize(
        self,
        text: str,
        config: VoiceSynthesisConfig = None
    ) -> SynthesisResult:
        """
        Mock 合成语音
        
        生成与文本长度成比例的静音音频
        """
        if not self._initialized:
            self.initialize()
        
        if config is None:
            config = VoiceSynthesisConfig()
        
        # 根据文本长度估算音频时长（假设每个字符约 0.2 秒）
        estimated_duration_sec = len(text) * 0.2
        num_samples = int(estimated_duration_sec * self.sample_rate)
        
        # 生成静音音频（或简单的正弦波用于测试）
        if HAS_NUMPY:
            # 生成低音量的正弦波作为测试音频
            t = np.linspace(0, estimated_duration_sec, num_samples)
            frequency = 440  # A4 音符
            audio_data = 0.1 * np.sin(2 * np.pi * frequency * t)
            audio_bytes = audio_data.astype(np.float32).tobytes()
        else:
            # 没有 numpy 时生成空字节
            audio_bytes = b'\x00' * (num_samples * 4)  # float32 = 4 bytes
        
        duration_ms = int(estimated_duration_sec * 1000)
        
        return SynthesisResult(
            audio_data=audio_bytes,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
            text=text,
            emotion=config.emotion.value,
            speaker=config.speaker
        )
    
    async def synthesize_with_emotion(
        self,
        text: str,
        emotion: VoiceEmotion = VoiceEmotion.GENTLE,
        speed: float = 1.0,
        speaker: str = None
    ) -> SynthesisResult:
        """Mock 情感控制合成"""
        config = VoiceSynthesisConfig(
            speaker=speaker or VoiceSpeaker.CHINESE_FEMALE.value,
            emotion=emotion,
            speed=speed
        )
        return await self.synthesize(text, config)
    
    async def synthesize_stream(
        self,
        text: str,
        config: VoiceSynthesisConfig = None
    ) -> AsyncGenerator[bytes, None]:
        """Mock 流式合成"""
        if not self._initialized:
            self.initialize()
        
        if config is None:
            config = VoiceSynthesisConfig(stream=True)
        
        # 将文本分成多个块
        chunk_size = 10  # 每 10 个字符一个块
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        for chunk_text in chunks:
            estimated_duration_sec = len(chunk_text) * 0.2
            num_samples = int(estimated_duration_sec * self.sample_rate)
            
            if HAS_NUMPY:
                t = np.linspace(0, estimated_duration_sec, num_samples)
                audio_data = 0.1 * np.sin(2 * np.pi * 440 * t)
                yield audio_data.astype(np.float32).tobytes()
            else:
                yield b'\x00' * (num_samples * 4)
    
    async def clone_voice(
        self,
        text: str,
        reference_audio: str,
        reference_text: str = ""
    ) -> SynthesisResult:
        """Mock 语音克隆"""
        config = VoiceSynthesisConfig(
            speaker="cloned_voice",
            emotion=VoiceEmotion.GENTLE
        )
        result = await self.synthesize(text, config)
        result.speaker = "cloned_voice"
        result.emotion = "cloned"
        return result
    
    def cleanup(self):
        """清理资源"""
        self._initialized = False
        logger.info("MockCosyVoice cleaned up")


def create_voice_synthesizer(
    model_dir: str = None,
    device: str = "cpu",
    model_version: str = "v1",
    use_mock: bool = False
) -> Union[CosyVoiceSynthesizer, MockCosyVoiceSynthesizer]:
    """
    创建语音合成器实例
    
    Args:
        model_dir: 模型目录路径
        device: 运行设备
        model_version: 模型版本
        use_mock: 是否使用 Mock 实现
        
    Returns:
        语音合成器实例
    """
    if use_mock:
        return MockCosyVoiceSynthesizer(model_dir, device, model_version)
    
    # 尝试创建真实的合成器
    try:
        synthesizer = CosyVoiceSynthesizer(model_dir, device, model_version)
        # 尝试初始化，如果失败则使用 Mock
        if synthesizer.initialize():
            return synthesizer
        else:
            logger.warning("CosyVoice initialization failed, using mock synthesizer")
            return MockCosyVoiceSynthesizer(model_dir, device, model_version)
    except Exception as e:
        logger.warning(f"Failed to create CosyVoice synthesizer: {e}, using mock")
        return MockCosyVoiceSynthesizer(model_dir, device, model_version)



class EmotionVoiceMapper:
    """
    情绪到语音参数映射器
    
    根据用户的情绪状态动态调整语音合成参数
    """
    
    # 情绪类别到语音情感的映射
    EMOTION_TO_VOICE = {
        "happy": VoiceEmotion.WARM,
        "sad": VoiceEmotion.GENTLE,
        "angry": VoiceEmotion.CALM,
        "anxious": VoiceEmotion.CALM,
        "tired": VoiceEmotion.GENTLE,
        "fearful": VoiceEmotion.WARM,
        "surprised": VoiceEmotion.WARM,
        "disgusted": VoiceEmotion.CALM,
        "neutral": VoiceEmotion.GENTLE,
    }
    
    # 情绪强度到语速的映射
    # 高强度负面情绪 -> 较慢语速（更舒缓）
    # 低强度情绪 -> 正常语速
    @staticmethod
    def get_speed_for_emotion(
        emotion_category: str,
        intensity: float,
        arousal: float
    ) -> float:
        """
        根据情绪状态计算合适的语速
        
        Args:
            emotion_category: 情绪类别
            intensity: 情绪强度 (0-1)
            arousal: 唤醒度 (0-1)
            
        Returns:
            语速 (0.8-1.2)
        """
        # 负面情绪列表
        negative_emotions = {"sad", "angry", "anxious", "tired", "fearful", "disgusted"}
        
        # 基础语速
        base_speed = 1.0
        
        if emotion_category in negative_emotions:
            # 负面情绪时，强度越高，语速越慢（更舒缓）
            speed_adjustment = -0.15 * intensity
        else:
            # 正面或中性情绪时，保持正常或稍快
            speed_adjustment = 0.05 * intensity
        
        # 唤醒度高时，稍微加快语速
        arousal_adjustment = 0.1 * (arousal - 0.5)
        
        final_speed = base_speed + speed_adjustment + arousal_adjustment
        
        # 限制在合理范围内
        return max(0.8, min(1.2, final_speed))
    
    @classmethod
    def get_voice_params_for_emotion(
        cls,
        emotion_category: str,
        intensity: float = 0.5,
        valence: float = 0.0,
        arousal: float = 0.5
    ) -> Dict[str, Any]:
        """
        根据情绪状态获取语音合成参数
        
        Args:
            emotion_category: 情绪类别
            intensity: 情绪强度 (0-1)
            valence: 效价 (-1 到 1)
            arousal: 唤醒度 (0-1)
            
        Returns:
            语音合成参数字典
        """
        # 获取语音情感
        voice_emotion = cls.EMOTION_TO_VOICE.get(
            emotion_category.lower(),
            VoiceEmotion.GENTLE
        )
        
        # 根据效价调整情感
        if valence > 0.3:
            # 正面情绪倾向
            voice_emotion = VoiceEmotion.WARM
        elif valence < -0.3 and intensity > 0.6:
            # 强烈负面情绪
            voice_emotion = VoiceEmotion.CALM
        
        # 计算语速
        speed = cls.get_speed_for_emotion(emotion_category, intensity, arousal)
        
        return {
            "emotion": voice_emotion,
            "speed": speed,
            "speaker": VoiceSpeaker.CHINESE_FEMALE.value
        }


class TherapyVoiceSynthesizer:
    """
    疗愈语音合成器
    
    专门用于疗愈场景的语音合成，根据用户情绪状态动态调整语音参数
    """
    
    def __init__(
        self,
        synthesizer: Union[CosyVoiceSynthesizer, MockCosyVoiceSynthesizer] = None,
        use_mock: bool = False
    ):
        """
        初始化疗愈语音合成器
        
        Args:
            synthesizer: 底层语音合成器实例
            use_mock: 是否使用 Mock 实现
        """
        if synthesizer is None:
            self.synthesizer = create_voice_synthesizer(use_mock=use_mock)
        else:
            self.synthesizer = synthesizer
        
        self.emotion_mapper = EmotionVoiceMapper()
        logger.info("TherapyVoiceSynthesizer initialized")
    
    async def synthesize_for_emotion_state(
        self,
        text: str,
        emotion_category: str,
        intensity: float = 0.5,
        valence: float = 0.0,
        arousal: float = 0.5
    ) -> SynthesisResult:
        """
        根据用户情绪状态合成语音
        
        Args:
            text: 要合成的文本
            emotion_category: 用户当前情绪类别
            intensity: 情绪强度 (0-1)
            valence: 效价 (-1 到 1)
            arousal: 唤醒度 (0-1)
            
        Returns:
            SynthesisResult 合成结果
        """
        # 获取适合当前情绪的语音参数
        params = self.emotion_mapper.get_voice_params_for_emotion(
            emotion_category, intensity, valence, arousal
        )
        
        logger.info(
            f"Synthesizing voice for emotion: {emotion_category}, "
            f"using params: emotion={params['emotion'].value}, speed={params['speed']:.2f}"
        )
        
        return await self.synthesizer.synthesize_with_emotion(
            text=text,
            emotion=params["emotion"],
            speed=params["speed"],
            speaker=params["speaker"]
        )
    
    async def synthesize_guide_text(
        self,
        guide_text: str,
        emotion: VoiceEmotion = VoiceEmotion.GENTLE,
        speed: float = 0.95
    ) -> SynthesisResult:
        """
        合成引导语
        
        引导语通常使用较慢、温柔的语速
        
        Args:
            guide_text: 引导语文本
            emotion: 情感类型
            speed: 语速（默认稍慢）
            
        Returns:
            SynthesisResult 合成结果
        """
        return await self.synthesizer.synthesize_with_emotion(
            text=guide_text,
            emotion=emotion,
            speed=speed,
            speaker=VoiceSpeaker.CHINESE_FEMALE.value
        )
    
    async def synthesize_encouragement(
        self,
        text: str
    ) -> SynthesisResult:
        """
        合成鼓励性语音
        
        使用温暖、鼓励的语气
        
        Args:
            text: 鼓励文本
            
        Returns:
            SynthesisResult 合成结果
        """
        return await self.synthesizer.synthesize_with_emotion(
            text=text,
            emotion=VoiceEmotion.ENCOURAGING,
            speed=1.0,
            speaker=VoiceSpeaker.CHINESE_FEMALE.value
        )
    
    async def synthesize_calming(
        self,
        text: str
    ) -> SynthesisResult:
        """
        合成舒缓性语音
        
        使用平静、舒缓的语气，适用于焦虑或紧张的用户
        
        Args:
            text: 舒缓文本
            
        Returns:
            SynthesisResult 合成结果
        """
        return await self.synthesizer.synthesize_with_emotion(
            text=text,
            emotion=VoiceEmotion.CALM,
            speed=0.9,
            speaker=VoiceSpeaker.CHINESE_FEMALE.value
        )
    
    def cleanup(self):
        """清理资源"""
        if self.synthesizer:
            self.synthesizer.cleanup()
