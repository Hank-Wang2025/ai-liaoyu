"""
音频预处理模块
Audio Preprocessing Module

负责音频格式转换、采样率转换等预处理操作
"""
import io
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Union
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
    logger.warning("soundfile not installed, audio file reading may be limited")


class AudioPreprocessor:
    """音频预处理器"""
    
    # 支持的音频格式
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a'}
    
    # 默认目标采样率 (SenseVoice 推荐 16kHz)
    DEFAULT_SAMPLE_RATE = 16000
    
    def __init__(self, target_sample_rate: int = DEFAULT_SAMPLE_RATE):
        """
        初始化音频预处理器
        
        Args:
            target_sample_rate: 目标采样率，默认16000Hz
        """
        self.target_sample_rate = target_sample_rate
        
    def is_supported_format(self, file_path: str) -> bool:
        """检查文件格式是否支持"""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_FORMATS
    
    def get_audio_info(self, file_path: str) -> dict:
        """
        获取音频文件信息
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            包含采样率、时长、通道数等信息的字典
        """
        if not HAS_SOUNDFILE:
            raise ImportError("soundfile library is required for audio processing")
            
        info = sf.info(file_path)
        return {
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "duration_seconds": info.duration,
            "duration_ms": int(info.duration * 1000),
            "frames": info.frames,
            "format": info.format,
            "subtype": info.subtype
        }
    
    def load_audio(self, file_path: str) -> Tuple[any, int]:
        """
        加载音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            (音频数据, 采样率) 元组
        """
        if not HAS_SOUNDFILE:
            raise ImportError("soundfile library is required for audio processing")
            
        data, sample_rate = sf.read(file_path)
        return data, sample_rate
    
    def resample(self, audio_data: any, original_sr: int, target_sr: int = None) -> any:
        """
        重采样音频数据
        
        Args:
            audio_data: 音频数据 (numpy array)
            original_sr: 原始采样率
            target_sr: 目标采样率，默认使用实例配置的采样率
            
        Returns:
            重采样后的音频数据
        """
        if not HAS_NUMPY:
            raise ImportError("numpy is required for audio resampling")
            
        target_sr = target_sr or self.target_sample_rate
        
        if original_sr == target_sr:
            return audio_data
            
        # 简单的线性插值重采样
        # 生产环境建议使用 librosa 或 scipy 进行高质量重采样
        duration = len(audio_data) / original_sr
        target_length = int(duration * target_sr)
        
        if len(audio_data.shape) == 1:
            # 单声道
            indices = np.linspace(0, len(audio_data) - 1, target_length)
            resampled = np.interp(indices, np.arange(len(audio_data)), audio_data)
        else:
            # 多声道
            resampled = np.zeros((target_length, audio_data.shape[1]))
            for ch in range(audio_data.shape[1]):
                indices = np.linspace(0, len(audio_data) - 1, target_length)
                resampled[:, ch] = np.interp(indices, np.arange(len(audio_data)), audio_data[:, ch])
                
        return resampled.astype(np.float32)
    
    def to_mono(self, audio_data: any) -> any:
        """
        将多声道音频转换为单声道
        
        Args:
            audio_data: 音频数据
            
        Returns:
            单声道音频数据
        """
        if not HAS_NUMPY:
            raise ImportError("numpy is required for audio processing")
            
        if len(audio_data.shape) == 1:
            return audio_data
            
        # 多声道取平均
        return np.mean(audio_data, axis=1).astype(np.float32)
    
    def normalize(self, audio_data: any) -> any:
        """
        归一化音频数据到 [-1, 1] 范围
        
        Args:
            audio_data: 音频数据
            
        Returns:
            归一化后的音频数据
        """
        if not HAS_NUMPY:
            raise ImportError("numpy is required for audio processing")
            
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return (audio_data / max_val).astype(np.float32)
        return audio_data.astype(np.float32)
    
    def preprocess(
        self, 
        file_path: str,
        target_sample_rate: int = None,
        to_mono: bool = True,
        normalize: bool = True
    ) -> Tuple[any, int]:
        """
        完整的音频预处理流程
        
        Args:
            file_path: 音频文件路径
            target_sample_rate: 目标采样率
            to_mono: 是否转换为单声道
            normalize: 是否归一化
            
        Returns:
            (预处理后的音频数据, 采样率) 元组
        """
        target_sr = target_sample_rate or self.target_sample_rate
        
        # 加载音频
        audio_data, original_sr = self.load_audio(file_path)
        
        # 转换为单声道
        if to_mono:
            audio_data = self.to_mono(audio_data)
            
        # 重采样
        if original_sr != target_sr:
            audio_data = self.resample(audio_data, original_sr, target_sr)
            
        # 归一化
        if normalize:
            audio_data = self.normalize(audio_data)
            
        return audio_data, target_sr
    
    def save_audio(
        self, 
        audio_data: any, 
        sample_rate: int, 
        output_path: str,
        format: str = 'WAV'
    ) -> str:
        """
        保存音频数据到文件
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            output_path: 输出文件路径
            format: 输出格式
            
        Returns:
            保存的文件路径
        """
        if not HAS_SOUNDFILE:
            raise ImportError("soundfile library is required for audio processing")
            
        sf.write(output_path, audio_data, sample_rate, format=format)
        return output_path
    
    def create_temp_wav(self, audio_data: any, sample_rate: int) -> str:
        """
        创建临时 WAV 文件
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            
        Returns:
            临时文件路径
        """
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        self.save_audio(audio_data, sample_rate, temp_file.name)
        return temp_file.name
