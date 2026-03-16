"""
音频控制器模块
Audio Controller Module

实现多声道音频播放、音量控制和淡入淡出效果
Requirements: 6.4, 6.5
"""
import asyncio
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable

import numpy as np
from loguru import logger

# 尝试导入音频库
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    logger.warning("sounddevice not installed. Install with: pip install sounddevice")

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False
    logger.warning("soundfile not installed. Install with: pip install soundfile")


class PlaybackState(str, Enum):
    """播放状态"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 44100
    channels: int = 2  # 默认立体声
    dtype: str = "float32"
    blocksize: int = 2048
    device: Optional[int] = None  # None 表示使用默认设备


@dataclass
class AudioState:
    """音频播放状态"""
    file_path: Optional[str] = None
    state: PlaybackState = PlaybackState.STOPPED
    volume: float = 1.0  # 0.0 - 1.0
    position: int = 0  # 当前播放位置（采样点）
    duration: int = 0  # 总时长（采样点）
    loop: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def progress(self) -> float:
        """播放进度 0.0 - 1.0"""
        if self.duration == 0:
            return 0.0
        return min(1.0, self.position / self.duration)
    
    @property
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self.state in (PlaybackState.PLAYING, PlaybackState.FADING_IN, PlaybackState.FADING_OUT)


class BaseAudioController(ABC):
    """音频控制器基类
    
    定义音频控制的抽象接口，所有具体的音频控制器都需要继承此类。
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._state = AudioState()
        self._is_initialized: bool = False
    
    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._is_initialized
    
    @property
    def current_state(self) -> AudioState:
        """当前播放状态"""
        return self._state
    
    @property
    def volume(self) -> float:
        """当前音量"""
        return self._state.volume
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化音频设备
        
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    @abstractmethod
    async def play(
        self,
        file_path: str,
        volume: float = 1.0,
        loop: bool = False,
        fade_in_ms: int = 0
    ) -> bool:
        """播放音频文件
        
        Args:
            file_path: 音频文件路径
            volume: 音量 0.0-1.0
            loop: 是否循环播放
            fade_in_ms: 淡入时间（毫秒）
            
        Returns:
            是否播放成功
        """
        pass
    
    @abstractmethod
    async def stop(self, fade_out_ms: int = 0) -> bool:
        """停止播放
        
        Args:
            fade_out_ms: 淡出时间（毫秒）
            
        Returns:
            是否停止成功
        """
        pass
    
    @abstractmethod
    async def pause(self) -> bool:
        """暂停播放"""
        pass
    
    @abstractmethod
    async def resume(self) -> bool:
        """恢复播放"""
        pass
    
    @abstractmethod
    async def set_volume(self, volume: float, transition_ms: int = 0) -> bool:
        """设置音量
        
        Args:
            volume: 目标音量 0.0-1.0
            transition_ms: 过渡时间（毫秒）
            
        Returns:
            是否设置成功
        """
        pass



class AudioFader:
    """音频淡入淡出处理器
    
    实现平滑的音量过渡效果。
    Requirements: 6.5
    """
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
    
    def create_fade_curve(
        self,
        duration_ms: int,
        fade_type: str = "linear",
        fade_direction: str = "in"
    ) -> np.ndarray:
        """创建淡入淡出曲线
        
        Args:
            duration_ms: 淡入淡出时长（毫秒）
            fade_type: 曲线类型 ("linear", "exponential", "logarithmic", "sine")
            fade_direction: 方向 ("in" 或 "out")
            
        Returns:
            淡入淡出曲线数组
        """
        num_samples = int(self.sample_rate * duration_ms / 1000)
        if num_samples <= 0:
            return np.array([1.0])
        
        t = np.linspace(0, 1, num_samples)
        
        if fade_type == "linear":
            curve = t
        elif fade_type == "exponential":
            # 指数曲线，更自然的淡入效果
            curve = t ** 2
        elif fade_type == "logarithmic":
            # 对数曲线，更自然的淡出效果
            curve = np.sqrt(t)
        elif fade_type == "sine":
            # 正弦曲线，最平滑的过渡
            curve = np.sin(t * np.pi / 2)
        else:
            curve = t
        
        if fade_direction == "out":
            curve = 1 - curve
        
        return curve.astype(np.float32)
    
    def apply_fade_in(
        self,
        audio_data: np.ndarray,
        duration_ms: int,
        fade_type: str = "sine"
    ) -> np.ndarray:
        """应用淡入效果
        
        Args:
            audio_data: 音频数据
            duration_ms: 淡入时长（毫秒）
            fade_type: 曲线类型
            
        Returns:
            应用淡入后的音频数据
        """
        if duration_ms <= 0:
            return audio_data
        
        curve = self.create_fade_curve(duration_ms, fade_type, "in")
        fade_samples = len(curve)
        
        # 确保不超过音频长度
        fade_samples = min(fade_samples, len(audio_data))
        curve = curve[:fade_samples]
        
        # 复制数据以避免修改原始数据
        result = audio_data.copy()
        
        # 应用淡入曲线
        if len(result.shape) == 1:
            # 单声道
            result[:fade_samples] *= curve
        else:
            # 多声道
            for ch in range(result.shape[1]):
                result[:fade_samples, ch] *= curve
        
        return result
    
    def apply_fade_out(
        self,
        audio_data: np.ndarray,
        duration_ms: int,
        fade_type: str = "sine"
    ) -> np.ndarray:
        """应用淡出效果
        
        Args:
            audio_data: 音频数据
            duration_ms: 淡出时长（毫秒）
            fade_type: 曲线类型
            
        Returns:
            应用淡出后的音频数据
        """
        if duration_ms <= 0:
            return audio_data
        
        curve = self.create_fade_curve(duration_ms, fade_type, "out")
        fade_samples = len(curve)
        
        # 确保不超过音频长度
        fade_samples = min(fade_samples, len(audio_data))
        curve = curve[-fade_samples:]
        
        # 复制数据以避免修改原始数据
        result = audio_data.copy()
        
        # 应用淡出曲线
        if len(result.shape) == 1:
            # 单声道
            result[-fade_samples:] *= curve
        else:
            # 多声道
            for ch in range(result.shape[1]):
                result[-fade_samples:, ch] *= curve
        
        return result
    
    def create_volume_transition(
        self,
        start_volume: float,
        end_volume: float,
        duration_ms: int,
        fade_type: str = "sine"
    ) -> np.ndarray:
        """创建音量过渡曲线
        
        Args:
            start_volume: 起始音量 0.0-1.0
            end_volume: 目标音量 0.0-1.0
            duration_ms: 过渡时长（毫秒）
            fade_type: 曲线类型
            
        Returns:
            音量过渡曲线
        """
        num_samples = int(self.sample_rate * duration_ms / 1000)
        if num_samples <= 0:
            return np.array([end_volume])
        
        t = np.linspace(0, 1, num_samples)
        
        if fade_type == "linear":
            curve = t
        elif fade_type == "sine":
            curve = np.sin(t * np.pi / 2)
        else:
            curve = t
        
        # 从起始音量过渡到目标音量
        volume_curve = start_volume + (end_volume - start_volume) * curve
        return volume_curve.astype(np.float32)



class MockAudioController(BaseAudioController):
    """模拟音频控制器（用于测试）"""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        super().__init__(config)
        self._command_history: List[Dict[str, Any]] = []
        self._fader = AudioFader(self.config.sample_rate)
        self._volume_transition_task: Optional[asyncio.Task] = None
    
    @property
    def command_history(self) -> List[Dict[str, Any]]:
        """获取命令历史"""
        return self._command_history
    
    def _log_command(self, action: str, **kwargs) -> None:
        """记录命令"""
        self._command_history.append({
            "action": action,
            "timestamp": datetime.now(),
            **kwargs
        })
    
    async def initialize(self) -> bool:
        self._is_initialized = True
        self._log_command("initialize")
        return True
    
    async def cleanup(self) -> None:
        if self._volume_transition_task and not self._volume_transition_task.done():
            self._volume_transition_task.cancel()
        self._is_initialized = False
        self._log_command("cleanup")
    
    async def play(
        self,
        file_path: str,
        volume: float = 1.0,
        loop: bool = False,
        fade_in_ms: int = 0
    ) -> bool:
        if not self._is_initialized:
            return False
        
        # 验证音量范围
        volume = max(0.0, min(1.0, volume))
        
        self._state = AudioState(
            file_path=file_path,
            state=PlaybackState.FADING_IN if fade_in_ms > 0 else PlaybackState.PLAYING,
            volume=volume,
            position=0,
            duration=44100 * 60,  # 模拟1分钟音频
            loop=loop
        )
        
        self._log_command(
            "play",
            file_path=file_path,
            volume=volume,
            loop=loop,
            fade_in_ms=fade_in_ms
        )
        
        # 模拟淡入完成
        if fade_in_ms > 0:
            await asyncio.sleep(fade_in_ms / 1000)
            self._state.state = PlaybackState.PLAYING
        
        return True
    
    async def stop(self, fade_out_ms: int = 0) -> bool:
        if not self._is_initialized:
            return False
        
        if fade_out_ms > 0:
            self._state.state = PlaybackState.FADING_OUT
            self._log_command("stop", fade_out_ms=fade_out_ms, fading=True)
            await asyncio.sleep(fade_out_ms / 1000)
        else:
            self._log_command("stop", fade_out_ms=fade_out_ms, fading=False)
        
        self._state = AudioState(state=PlaybackState.STOPPED)
        return True
    
    async def pause(self) -> bool:
        if not self._is_initialized or not self._state.is_playing:
            return False
        
        self._state.state = PlaybackState.PAUSED
        self._log_command("pause")
        return True
    
    async def resume(self) -> bool:
        if not self._is_initialized or self._state.state != PlaybackState.PAUSED:
            return False
        
        self._state.state = PlaybackState.PLAYING
        self._log_command("resume")
        return True
    
    async def set_volume(self, volume: float, transition_ms: int = 0) -> bool:
        if not self._is_initialized:
            return False
        
        # 验证音量范围
        volume = max(0.0, min(1.0, volume))
        
        if transition_ms > 0:
            # 平滑过渡
            start_volume = self._state.volume
            steps = max(1, transition_ms // 50)  # 每50ms一步
            step_delay = transition_ms / steps / 1000
            
            for i in range(1, steps + 1):
                progress = i / steps
                current_volume = start_volume + (volume - start_volume) * progress
                self._state.volume = current_volume
                await asyncio.sleep(step_delay)
        
        self._state.volume = volume
        self._log_command("set_volume", volume=volume, transition_ms=transition_ms)
        return True



class SoundDeviceAudioController(BaseAudioController):
    """基于 sounddevice 的音频控制器
    
    实现多声道音频播放和音量控制。
    Requirements: 6.4, 6.5
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        super().__init__(config)
        self._fader = AudioFader(self.config.sample_rate)
        self._audio_data: Optional[np.ndarray] = None
        self._stream: Optional[Any] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._volume_lock = threading.Lock()
        self._target_volume: float = 1.0
        self._current_volume: float = 1.0
        self._volume_transition_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> bool:
        """初始化音频设备"""
        if not HAS_SOUNDDEVICE:
            logger.error("sounddevice library not available")
            return False
        
        if not HAS_SOUNDFILE:
            logger.error("soundfile library not available")
            return False
        
        try:
            # 检查音频设备
            devices = sd.query_devices()
            logger.info(f"Found {len(devices)} audio devices")
            
            # 获取默认输出设备
            default_output = sd.query_devices(kind='output')
            logger.info(f"Default output device: {default_output['name']}")
            
            self._is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio device: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        await self.stop()
        
        if self._volume_transition_task and not self._volume_transition_task.done():
            self._volume_transition_task.cancel()
            try:
                await self._volume_transition_task
            except asyncio.CancelledError:
                pass
        
        self._is_initialized = False
        logger.info("Audio controller cleaned up")
    
    def _load_audio_file(self, file_path: str) -> tuple:
        """加载音频文件
        
        Returns:
            (音频数据, 采样率)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        data, sample_rate = sf.read(file_path, dtype='float32')
        
        # 确保是2D数组 (samples, channels)
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        return data, sample_rate
    
    def _playback_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: Any,
        status: Any
    ) -> None:
        """音频播放回调函数"""
        if status:
            logger.warning(f"Audio playback status: {status}")
        
        if self._pause_event.is_set():
            outdata.fill(0)
            return
        
        if self._audio_data is None:
            outdata.fill(0)
            return
        
        position = self._state.position
        remaining = len(self._audio_data) - position
        
        if remaining <= 0:
            if self._state.loop:
                # 循环播放
                self._state.position = 0
                position = 0
                remaining = len(self._audio_data)
            else:
                outdata.fill(0)
                self._stop_event.set()
                return
        
        # 获取要播放的数据
        chunk_size = min(frames, remaining)
        chunk = self._audio_data[position:position + chunk_size]
        
        # 应用音量
        with self._volume_lock:
            volume = self._current_volume
        
        chunk = chunk * volume
        
        # 填充输出缓冲区
        if chunk_size < frames:
            outdata[:chunk_size] = chunk
            outdata[chunk_size:] = 0
        else:
            outdata[:] = chunk[:frames]
        
        self._state.position = position + chunk_size
    
    async def play(
        self,
        file_path: str,
        volume: float = 1.0,
        loop: bool = False,
        fade_in_ms: int = 0
    ) -> bool:
        """播放音频文件"""
        if not self._is_initialized:
            logger.error("Audio controller not initialized")
            return False
        
        # 停止当前播放
        await self.stop()
        
        try:
            # 加载音频文件
            self._audio_data, sample_rate = self._load_audio_file(file_path)
            
            # 应用淡入效果
            if fade_in_ms > 0:
                self._audio_data = self._fader.apply_fade_in(
                    self._audio_data, fade_in_ms
                )
            
            # 验证音量范围
            volume = max(0.0, min(1.0, volume))
            
            # 更新状态
            self._state = AudioState(
                file_path=file_path,
                state=PlaybackState.PLAYING,
                volume=volume,
                position=0,
                duration=len(self._audio_data),
                loop=loop
            )
            
            with self._volume_lock:
                self._current_volume = volume
                self._target_volume = volume
            
            # 重置事件
            self._stop_event.clear()
            self._pause_event.clear()
            
            # 确定声道数
            channels = self._audio_data.shape[1] if len(self._audio_data.shape) > 1 else 1
            
            # 创建输出流
            self._stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype='float32',
                blocksize=self.config.blocksize,
                callback=self._playback_callback,
                device=self.config.device
            )
            
            self._stream.start()
            logger.info(f"Started playing: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            self._state.state = PlaybackState.STOPPED
            return False
    
    async def stop(self, fade_out_ms: int = 0) -> bool:
        """停止播放"""
        if not self._is_initialized:
            return False
        
        if self._state.state == PlaybackState.STOPPED:
            return True
        
        try:
            if fade_out_ms > 0 and self._audio_data is not None:
                # 应用淡出效果
                self._state.state = PlaybackState.FADING_OUT
                await self.set_volume(0.0, fade_out_ms)
            
            # 停止流
            self._stop_event.set()
            
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            self._audio_data = None
            self._state = AudioState(state=PlaybackState.STOPPED)
            
            logger.info("Audio playback stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop audio: {e}")
            return False
    
    async def pause(self) -> bool:
        """暂停播放"""
        if not self._is_initialized or not self._state.is_playing:
            return False
        
        self._pause_event.set()
        self._state.state = PlaybackState.PAUSED
        logger.info("Audio playback paused")
        return True
    
    async def resume(self) -> bool:
        """恢复播放"""
        if not self._is_initialized or self._state.state != PlaybackState.PAUSED:
            return False
        
        self._pause_event.clear()
        self._state.state = PlaybackState.PLAYING
        logger.info("Audio playback resumed")
        return True
    
    async def set_volume(self, volume: float, transition_ms: int = 0) -> bool:
        """设置音量
        
        实现平滑的音量过渡，避免突兀变化。
        Requirements: 6.5
        """
        if not self._is_initialized:
            return False
        
        # 验证音量范围
        volume = max(0.0, min(1.0, volume))
        
        with self._volume_lock:
            start_volume = self._current_volume
            self._target_volume = volume
        
        if transition_ms <= 0:
            # 立即设置
            with self._volume_lock:
                self._current_volume = volume
            self._state.volume = volume
            return True
        
        # 平滑过渡
        steps = max(1, transition_ms // 20)  # 每20ms一步，确保平滑
        step_delay = transition_ms / steps / 1000
        
        for i in range(1, steps + 1):
            progress = i / steps
            # 使用正弦曲线实现更自然的过渡
            smooth_progress = np.sin(progress * np.pi / 2)
            current = start_volume + (volume - start_volume) * smooth_progress
            
            with self._volume_lock:
                self._current_volume = current
            
            await asyncio.sleep(step_delay)
        
        # 确保最终值准确
        with self._volume_lock:
            self._current_volume = volume
        self._state.volume = volume
        
        logger.debug(f"Volume set to {volume} with {transition_ms}ms transition")
        return True
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """获取可用的音频设备列表"""
        if not HAS_SOUNDDEVICE:
            return []
        
        devices = sd.query_devices()
        result = []
        
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                result.append({
                    "index": i,
                    "name": device['name'],
                    "channels": device['max_output_channels'],
                    "sample_rate": device['default_samplerate'],
                    "is_default": i == sd.default.device[1]
                })
        
        return result



class AudioControllerManager:
    """音频控制器管理器
    
    管理多个音频通道，支持同时播放背景音乐和语音引导。
    """
    
    def __init__(self):
        self.controllers: Dict[str, BaseAudioController] = {}
        self._master_volume: float = 1.0
    
    @property
    def master_volume(self) -> float:
        """主音量"""
        return self._master_volume
    
    def add_controller(self, name: str, controller: BaseAudioController) -> None:
        """添加音频控制器"""
        self.controllers[name] = controller
    
    def remove_controller(self, name: str) -> None:
        """移除音频控制器"""
        if name in self.controllers:
            del self.controllers[name]
    
    def get_controller(self, name: str) -> Optional[BaseAudioController]:
        """获取指定的音频控制器"""
        return self.controllers.get(name)
    
    async def initialize_all(self) -> Dict[str, bool]:
        """初始化所有控制器"""
        results = {}
        for name, controller in self.controllers.items():
            results[name] = await controller.initialize()
        return results
    
    async def cleanup_all(self) -> None:
        """清理所有控制器"""
        for controller in self.controllers.values():
            await controller.cleanup()
    
    async def stop_all(self, fade_out_ms: int = 0) -> Dict[str, bool]:
        """停止所有播放"""
        results = {}
        for name, controller in self.controllers.items():
            results[name] = await controller.stop(fade_out_ms)
        return results
    
    async def set_master_volume(self, volume: float, transition_ms: int = 0) -> None:
        """设置主音量（影响所有控制器）"""
        self._master_volume = max(0.0, min(1.0, volume))
        
        for controller in self.controllers.values():
            current_volume = controller.current_state.volume
            adjusted_volume = current_volume * self._master_volume
            await controller.set_volume(adjusted_volume, transition_ms)
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有控制器状态"""
        status = {}
        for name, controller in self.controllers.items():
            state = controller.current_state
            status[name] = {
                "initialized": controller.is_initialized,
                "state": state.state.value,
                "file": state.file_path,
                "volume": state.volume,
                "progress": state.progress,
                "loop": state.loop
            }
        return status


class TherapyAudioPlayer:
    """疗愈音频播放器
    
    专门用于疗愈场景的音频播放，支持背景音乐和语音引导的协调播放。
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._bgm_controller: Optional[BaseAudioController] = None
        self._voice_controller: Optional[BaseAudioController] = None
        self._is_initialized: bool = False
    
    async def initialize(self, use_mock: bool = False) -> bool:
        """初始化播放器"""
        if use_mock:
            self._bgm_controller = MockAudioController(self.config)
            self._voice_controller = MockAudioController(self.config)
        else:
            self._bgm_controller = SoundDeviceAudioController(self.config)
            self._voice_controller = SoundDeviceAudioController(self.config)
        
        bgm_ok = await self._bgm_controller.initialize()
        voice_ok = await self._voice_controller.initialize()
        
        self._is_initialized = bgm_ok and voice_ok
        return self._is_initialized
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._bgm_controller:
            await self._bgm_controller.cleanup()
        if self._voice_controller:
            await self._voice_controller.cleanup()
        self._is_initialized = False
    
    async def play_background_music(
        self,
        file_path: str,
        volume: float = 0.5,
        loop: bool = True,
        fade_in_ms: int = 2000
    ) -> bool:
        """播放背景音乐"""
        if not self._is_initialized or not self._bgm_controller:
            return False
        
        return await self._bgm_controller.play(
            file_path, volume, loop, fade_in_ms
        )
    
    async def play_voice_guide(
        self,
        file_path: str,
        volume: float = 0.8,
        duck_bgm: bool = True,
        duck_volume: float = 0.3,
        fade_in_ms: int = 500
    ) -> bool:
        """播放语音引导
        
        Args:
            file_path: 语音文件路径
            volume: 语音音量
            duck_bgm: 是否降低背景音乐音量
            duck_volume: 降低后的背景音乐音量
            fade_in_ms: 淡入时间
        """
        if not self._is_initialized or not self._voice_controller:
            return False
        
        # 降低背景音乐音量
        if duck_bgm and self._bgm_controller:
            await self._bgm_controller.set_volume(duck_volume, 500)
        
        # 播放语音
        result = await self._voice_controller.play(
            file_path, volume, False, fade_in_ms
        )
        
        return result
    
    async def stop_voice_guide(
        self,
        restore_bgm: bool = True,
        bgm_volume: float = 0.5,
        fade_out_ms: int = 500
    ) -> bool:
        """停止语音引导"""
        if not self._is_initialized or not self._voice_controller:
            return False
        
        result = await self._voice_controller.stop(fade_out_ms)
        
        # 恢复背景音乐音量
        if restore_bgm and self._bgm_controller:
            await self._bgm_controller.set_volume(bgm_volume, 500)
        
        return result
    
    async def stop_all(self, fade_out_ms: int = 2000) -> bool:
        """停止所有音频"""
        results = []
        
        if self._bgm_controller:
            results.append(await self._bgm_controller.stop(fade_out_ms))
        if self._voice_controller:
            results.append(await self._voice_controller.stop(fade_out_ms))
        
        return all(results)
    
    def get_status(self) -> Dict[str, Any]:
        """获取播放状态"""
        return {
            "initialized": self._is_initialized,
            "bgm": {
                "state": self._bgm_controller.current_state.state.value if self._bgm_controller else None,
                "file": self._bgm_controller.current_state.file_path if self._bgm_controller else None,
                "volume": self._bgm_controller.current_state.volume if self._bgm_controller else None
            },
            "voice": {
                "state": self._voice_controller.current_state.state.value if self._voice_controller else None,
                "file": self._voice_controller.current_state.file_path if self._voice_controller else None,
                "volume": self._voice_controller.current_state.volume if self._voice_controller else None
            }
        }


def create_audio_controller(
    controller_type: str = "mock",
    config: Optional[AudioConfig] = None
) -> BaseAudioController:
    """创建音频控制器实例
    
    Args:
        controller_type: 控制器类型 ("mock", "sounddevice")
        config: 音频配置
        
    Returns:
        音频控制器实例
    """
    if controller_type == "mock":
        return MockAudioController(config)
    elif controller_type == "sounddevice":
        if not HAS_SOUNDDEVICE:
            raise ImportError(
                "sounddevice library not installed. "
                "Install with: pip install sounddevice"
            )
        return SoundDeviceAudioController(config)
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")
