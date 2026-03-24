import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.therapy import AudioConfig
import services.therapy_executor as therapy_executor_module
from services.therapy_executor import TherapyExecutor


class FakeAudioPlayer:
    def __init__(self):
        self.play_calls = []

    async def play_background_music(self, file_path, volume=0.8, loop=True, fade_in_ms=2000):
        self.play_calls.append(
            {
                "file": file_path,
                "volume": volume,
                "loop": loop,
                "fade_in_ms": fade_in_ms,
            }
        )
        return True


@pytest.mark.asyncio
async def test_apply_audio_config_falls_back_to_existing_track_when_configured_file_missing(
    monkeypatch,
):
    audio_player = FakeAudioPlayer()
    executor = TherapyExecutor(audio_player=audio_player)
    config = AudioConfig(
        file="content/audio/deep_bass_calm.mp3",
        volume=80,
        loop=True,
        fade_in=1500,
        fade_out=0,
    )

    monkeypatch.setattr(
        therapy_executor_module,
        "_track_exists",
        lambda path: path == "content/audio/chinese_guqin_calm.mp3",
        raising=False,
    )
    monkeypatch.setattr(
        therapy_executor_module,
        "_load_playable_background_music_playlist",
        lambda: ["content/audio/chinese_guqin_calm.mp3"],
        raising=False,
    )

    await executor._apply_audio_config(config)

    assert audio_player.play_calls == [
        {
            "file": "content/audio/chinese_guqin_calm.mp3",
            "volume": 0.8,
            "loop": True,
            "fade_in_ms": 1500,
        }
    ]
