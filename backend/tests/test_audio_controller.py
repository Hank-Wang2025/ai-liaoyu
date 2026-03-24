"""
音频控制器测试模块
Audio Controller Test Module

测试音频播放、音量控制和淡入淡出功能
"""
import asyncio
import sys
import os

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pytest
from datetime import datetime

from services.audio_controller import (
    AudioFader,
    MockAudioController,
    AudioConfig,
    AudioState,
    PlaybackState,
    SoundDeviceAudioController,
    TherapyAudioPlayer,
    create_audio_controller
)
import services.audio_controller as audio_controller_module


class TestAudioFader:
    """测试音频淡入淡出处理器"""

    def test_create_fade_curve_linear_in(self):
        """测试线性淡入曲线"""
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_fade_curve(1000, "linear", "in")

        # 曲线应该从0开始，到1结束
        assert curve[0] == pytest.approx(0.0, abs=0.01)
        assert curve[-1] == pytest.approx(1.0, abs=0.01)

        # 曲线应该单调递增
        assert all(curve[i] <= curve[i+1] for i in range(len(curve)-1))

    def test_create_fade_curve_linear_out(self):
        """测试线性淡出曲线"""
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_fade_curve(1000, "linear", "out")

        # 曲线应该从1开始，到0结束
        assert curve[0] == pytest.approx(1.0, abs=0.01)
        assert curve[-1] == pytest.approx(0.0, abs=0.01)

        # 曲线应该单调递减
        assert all(curve[i] >= curve[i+1] for i in range(len(curve)-1))

    def test_create_fade_curve_sine(self):
        """测试正弦淡入曲线"""
        fader = AudioFader(sample_rate=44100)
        curve = fader.create_fade_curve(1000, "sine", "in")

        # 曲线应该从0开始，到1结束
        assert curve[0] == pytest.approx(0.0, abs=0.01)
        assert curve[-1] == pytest.approx(1.0, abs=0.01)

    def test_apply_fade_in_mono(self):
        """测试单声道淡入效果"""
        fader = AudioFader(sample_rate=44100)

        # 创建测试音频数据（1秒，全1）
        audio_data = np.ones(44100, dtype=np.float32)

        # 应用500ms淡入
        result = fader.apply_fade_in(audio_data, 500)

        # 开始应该接近0
        assert result[0] == pytest.approx(0.0, abs=0.01)

        # 淡入结束后应该接近1
        fade_samples = int(44100 * 0.5)
        assert result[fade_samples] == pytest.approx(1.0, abs=0.01)

        # 淡入后的部分应该保持不变
        assert result[-1] == pytest.approx(1.0, abs=0.01)

    def test_apply_fade_in_stereo(self):
        """测试立体声淡入效果"""
        fader = AudioFader(sample_rate=44100)

        # 创建测试音频数据（1秒，2声道，全1）
        audio_data = np.ones((44100, 2), dtype=np.float32)

        # 应用500ms淡入
        result = fader.apply_fade_in(audio_data, 500)

        # 两个声道都应该应用淡入
        assert result[0, 0] == pytest.approx(0.0, abs=0.01)
        assert result[0, 1] == pytest.approx(0.0, abs=0.01)

    def test_apply_fade_out_mono(self):
        """测试单声道淡出效果"""
        fader = AudioFader(sample_rate=44100)

        # 创建测试音频数据（1秒，全1）
        audio_data = np.ones(44100, dtype=np.float32)

        # 应用500ms淡出
        result = fader.apply_fade_out(audio_data, 500)

        # 开始应该保持不变
        assert result[0] == pytest.approx(1.0, abs=0.01)

        # 结束应该接近0
        assert result[-1] == pytest.approx(0.0, abs=0.01)

    def test_apply_fade_out_stereo(self):
        """测试立体声淡出效果"""
        fader = AudioFader(sample_rate=44100)

        # 创建测试音频数据（1秒，2声道，全1）
        audio_data = np.ones((44100, 2), dtype=np.float32)

        # 应用500ms淡出
        result = fader.apply_fade_out(audio_data, 500)

        # 两个声道结束都应该接近0
        assert result[-1, 0] == pytest.approx(0.0, abs=0.01)
        assert result[-1, 1] == pytest.approx(0.0, abs=0.01)

    def test_create_volume_transition(self):
        """测试音量过渡曲线"""
        fader = AudioFader(sample_rate=44100)

        # 从0.3过渡到0.8
        curve = fader.create_volume_transition(0.3, 0.8, 1000)

        # 开始应该是0.3
        assert curve[0] == pytest.approx(0.3, abs=0.01)

        # 结束应该是0.8
        assert curve[-1] == pytest.approx(0.8, abs=0.01)

    def test_fade_zero_duration(self):
        """测试零时长淡入淡出"""
        fader = AudioFader(sample_rate=44100)

        audio_data = np.ones(44100, dtype=np.float32)

        # 零时长淡入应该返回原数据
        result_in = fader.apply_fade_in(audio_data, 0)
        np.testing.assert_array_equal(result_in, audio_data)

        # 零时长淡出应该返回原数据
        result_out = fader.apply_fade_out(audio_data, 0)
        np.testing.assert_array_equal(result_out, audio_data)



class TestMockAudioController:
    """测试模拟音频控制器"""

    @pytest.fixture
    def controller(self):
        """创建控制器实例"""
        return MockAudioController()

    @pytest.mark.asyncio
    async def test_initialize(self, controller):
        """测试初始化"""
        result = await controller.initialize()

        assert result is True
        assert controller.is_initialized is True

    @pytest.mark.asyncio
    async def test_play_without_init(self, controller):
        """测试未初始化时播放"""
        result = await controller.play("test.wav")

        assert result is False

    @pytest.mark.asyncio
    async def test_play_basic(self, controller):
        """测试基本播放"""
        await controller.initialize()

        result = await controller.play("test.wav", volume=0.8)

        assert result is True
        assert controller.current_state.state == PlaybackState.PLAYING
        assert controller.current_state.file_path == "test.wav"
        assert controller.current_state.volume == 0.8

    @pytest.mark.asyncio
    async def test_play_with_loop(self, controller):
        """测试循环播放"""
        await controller.initialize()

        result = await controller.play("test.wav", loop=True)

        assert result is True
        assert controller.current_state.loop is True

    @pytest.mark.asyncio
    async def test_stop(self, controller):
        """测试停止播放"""
        await controller.initialize()
        await controller.play("test.wav")

        result = await controller.stop()

        assert result is True
        assert controller.current_state.state == PlaybackState.STOPPED

    @pytest.mark.asyncio
    async def test_pause_resume(self, controller):
        """测试暂停和恢复"""
        await controller.initialize()
        await controller.play("test.wav")

        # 暂停
        result = await controller.pause()
        assert result is True
        assert controller.current_state.state == PlaybackState.PAUSED

        # 恢复
        result = await controller.resume()
        assert result is True
        assert controller.current_state.state == PlaybackState.PLAYING

    @pytest.mark.asyncio
    async def test_set_volume_immediate(self, controller):
        """测试立即设置音量"""
        await controller.initialize()
        await controller.play("test.wav", volume=0.5)

        result = await controller.set_volume(0.8)

        assert result is True
        assert controller.current_state.volume == 0.8

    @pytest.mark.asyncio
    async def test_set_volume_with_transition(self, controller):
        """测试带过渡的音量设置"""
        await controller.initialize()
        await controller.play("test.wav", volume=0.3)

        # 使用100ms过渡
        result = await controller.set_volume(0.9, transition_ms=100)

        assert result is True
        assert controller.current_state.volume == pytest.approx(0.9, abs=0.01)

    @pytest.mark.asyncio
    async def test_volume_clamping(self, controller):
        """测试音量范围限制"""
        await controller.initialize()
        await controller.play("test.wav")

        # 超出范围的音量应该被限制
        await controller.set_volume(1.5)
        assert controller.current_state.volume == 1.0

        await controller.set_volume(-0.5)
        assert controller.current_state.volume == 0.0

    @pytest.mark.asyncio
    async def test_command_history(self, controller):
        """测试命令历史记录"""
        await controller.initialize()
        await controller.play("test.wav")
        await controller.set_volume(0.5)
        await controller.stop()

        history = controller.command_history

        assert len(history) >= 4
        assert history[0]["action"] == "initialize"
        assert history[1]["action"] == "play"
        assert history[2]["action"] == "set_volume"
        assert history[3]["action"] == "stop"

    @pytest.mark.asyncio
    async def test_cleanup(self, controller):
        """测试清理"""
        await controller.initialize()
        await controller.play("test.wav")

        await controller.cleanup()

        assert controller.is_initialized is False


class TestAudioState:
    """测试音频状态"""

    def test_progress_calculation(self):
        """测试进度计算"""
        state = AudioState(
            position=22050,
            duration=44100
        )

        assert state.progress == pytest.approx(0.5, abs=0.01)

    def test_progress_zero_duration(self):
        """测试零时长进度"""
        state = AudioState(
            position=100,
            duration=0
        )

        assert state.progress == 0.0

    def test_is_playing(self):
        """测试播放状态判断"""
        state_playing = AudioState(state=PlaybackState.PLAYING)
        state_stopped = AudioState(state=PlaybackState.STOPPED)
        state_paused = AudioState(state=PlaybackState.PAUSED)
        state_fading_in = AudioState(state=PlaybackState.FADING_IN)
        state_fading_out = AudioState(state=PlaybackState.FADING_OUT)

        assert state_playing.is_playing is True
        assert state_stopped.is_playing is False
        assert state_paused.is_playing is False
        assert state_fading_in.is_playing is True
        assert state_fading_out.is_playing is True


class TestCreateAudioController:
    """测试控制器工厂函数"""

    def test_create_mock_controller(self):
        """测试创建模拟控制器"""
        controller = create_audio_controller("mock")

        assert isinstance(controller, MockAudioController)

    def test_create_with_config(self):
        """测试使用配置创建控制器"""
        config = AudioConfig(sample_rate=48000, channels=4)
        controller = create_audio_controller("mock", config)

        assert controller.config.sample_rate == 48000
        assert controller.config.channels == 4

    def test_create_unknown_type(self):
        """测试创建未知类型控制器"""
        with pytest.raises(ValueError):
            create_audio_controller("unknown")

    def test_sounddevice_load_audio_file_resolves_repo_relative_path(self, monkeypatch):
        """Repo-root relative audio paths should work even when cwd is backend."""
        controller = SoundDeviceAudioController()
        captured = {}

        def fake_read(path, dtype="float32"):
            captured["path"] = path
            return np.zeros((8, 1), dtype=np.float32), 44100

        monkeypatch.chdir(os.path.join(os.path.dirname(__file__), ".."))
        monkeypatch.setattr(audio_controller_module.sf, "read", fake_read)

        data, sample_rate = controller._load_audio_file("content/audio/chinese_guqin_calm.mp3")

        assert sample_rate == 44100
        assert data.shape == (8, 1)
        assert os.path.isabs(captured["path"])
        assert captured["path"].endswith(
            os.path.join("content", "audio", "chinese_guqin_calm.mp3")
        )


class FakeTherapyChannelController:
    def __init__(self, state=PlaybackState.PLAYING):
        self.current_state = AudioState(state=state)
        self.pause_calls = 0
        self.resume_calls = 0

    async def pause(self):
        self.pause_calls += 1
        self.current_state.state = PlaybackState.PAUSED
        return True

    async def resume(self):
        self.resume_calls += 1
        self.current_state.state = PlaybackState.PLAYING
        return True


class TestTherapyAudioPlayer:
    @pytest.mark.asyncio
    async def test_pause_pauses_bgm_and_voice_channels(self):
        player = TherapyAudioPlayer()
        bgm = FakeTherapyChannelController()
        voice = FakeTherapyChannelController()
        player._is_initialized = True
        player._bgm_controller = bgm
        player._voice_controller = voice

        result = await player.pause()

        assert result is True
        assert bgm.pause_calls == 1
        assert voice.pause_calls == 1
        assert bgm.current_state.state == PlaybackState.PAUSED
        assert voice.current_state.state == PlaybackState.PAUSED

    @pytest.mark.asyncio
    async def test_resume_resumes_bgm_and_voice_channels(self):
        player = TherapyAudioPlayer()
        bgm = FakeTherapyChannelController(state=PlaybackState.PAUSED)
        voice = FakeTherapyChannelController(state=PlaybackState.PAUSED)
        player._is_initialized = True
        player._bgm_controller = bgm
        player._voice_controller = voice

        result = await player.resume()

        assert result is True
        assert bgm.resume_calls == 1
        assert voice.resume_calls == 1
        assert bgm.current_state.state == PlaybackState.PLAYING
        assert voice.current_state.state == PlaybackState.PLAYING


class TestVolumeTransitionSmooth:
    """测试音量过渡平滑性 - Requirements 6.5"""

    @pytest.mark.asyncio
    async def test_volume_transition_is_smooth(self):
        """测试音量过渡是平滑的，没有突兀变化"""
        controller = MockAudioController()
        await controller.initialize()
        await controller.play("test.wav", volume=0.2)

        # 记录音量变化
        volume_history = [controller.current_state.volume]

        # 启动音量过渡任务
        transition_task = asyncio.create_task(
            controller.set_volume(0.8, transition_ms=200)
        )

        # 在过渡期间采样音量
        for _ in range(10):
            await asyncio.sleep(0.02)
            volume_history.append(controller.current_state.volume)

        await transition_task
        volume_history.append(controller.current_state.volume)

        # 验证音量变化是单调的（从低到高）
        for i in range(len(volume_history) - 1):
            assert volume_history[i] <= volume_history[i + 1] + 0.01, \
                f"Volume should increase smoothly: {volume_history}"

        # 验证最终音量
        assert controller.current_state.volume == pytest.approx(0.8, abs=0.01)

    @pytest.mark.asyncio
    async def test_volume_decrease_is_smooth(self):
        """测试音量降低也是平滑的"""
        controller = MockAudioController()
        await controller.initialize()
        await controller.play("test.wav", volume=0.9)

        # 记录音量变化
        volume_history = [controller.current_state.volume]

        # 启动音量过渡任务
        transition_task = asyncio.create_task(
            controller.set_volume(0.2, transition_ms=200)
        )

        # 在过渡期间采样音量
        for _ in range(10):
            await asyncio.sleep(0.02)
            volume_history.append(controller.current_state.volume)

        await transition_task
        volume_history.append(controller.current_state.volume)

        # 验证音量变化是单调的（从高到低）
        for i in range(len(volume_history) - 1):
            assert volume_history[i] >= volume_history[i + 1] - 0.01, \
                f"Volume should decrease smoothly: {volume_history}"

        # 验证最终音量
        assert controller.current_state.volume == pytest.approx(0.2, abs=0.01)
