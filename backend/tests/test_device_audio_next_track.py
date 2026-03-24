import os
import sys
import importlib.util
import types
from types import SimpleNamespace

import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")

services_module = types.ModuleType("services")
device_manager_module = types.ModuleType("services.device_manager")
audio_controller_module = types.ModuleType("services.audio_controller")
device_manager_module.get_device_manager = lambda: None
async def _unused_shared_audio_player():
    raise RuntimeError("shared audio player not stubbed")

audio_controller_module.get_shared_audio_player = _unused_shared_audio_player
services_module.device_manager = device_manager_module
services_module.audio_controller = audio_controller_module
sys.modules.setdefault("services", services_module)
sys.modules["services.device_manager"] = device_manager_module
sys.modules["services.audio_controller"] = audio_controller_module

spec = importlib.util.spec_from_file_location(
    "device_module",
    os.path.join(BACKEND_DIR, "api", "device.py"),
)
device = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(device)


class StubAudioPlayer:
    def __init__(self, current_file: str, volume: float = 0.5, loop: bool = True):
        self.status = {
            "bgm": {
                "file": current_file,
                "volume": volume,
                "loop": loop,
            }
        }
        self.play_calls = []

    def get_status(self):
        return self.status

    async def play_background_music(self, file_path: str, volume: float, loop: bool, fade_in_ms: int):
        self.play_calls.append(
            {
                "file_path": file_path,
                "volume": volume,
                "loop": loop,
                "fade_in_ms": fade_in_ms,
            }
        )
        return True


@pytest.mark.asyncio
async def test_audio_next_switches_to_next_manifest_file(monkeypatch):
    audio_player = StubAudioPlayer("content/audio/ambient_calm.mp3", volume=0.42, loop=False)
    manager = SimpleNamespace(_device_controllers={"audio": audio_player})

    monkeypatch.setattr(device, "get_device_manager", lambda: manager)
    monkeypatch.setattr(
        device,
        "_load_background_music_playlist",
        lambda: [
            "content/audio/ambient_calm.mp3",
            "content/audio/soft_piano.mp3",
            "content/audio/ocean_waves.mp3",
        ],
    )

    result = await device.control_audio(device.AudioControlRequest(action="next", fade_ms=1500))

    assert result["success"] is True
    assert result["simulated"] is False
    assert result["file"] == "content/audio/soft_piano.mp3"
    assert audio_player.play_calls == [
        {
            "file_path": "content/audio/soft_piano.mp3",
            "volume": 0.42,
            "loop": False,
            "fade_in_ms": 1500,
        }
    ]


@pytest.mark.asyncio
async def test_audio_next_wraps_to_first_manifest_file(monkeypatch):
    audio_player = StubAudioPlayer("content/audio/ocean_waves.mp3", volume=0.7, loop=True)
    manager = SimpleNamespace(_device_controllers={"audio": audio_player})

    monkeypatch.setattr(device, "get_device_manager", lambda: manager)
    monkeypatch.setattr(
        device,
        "_load_background_music_playlist",
        lambda: [
            "content/audio/ambient_calm.mp3",
            "content/audio/soft_piano.mp3",
            "content/audio/ocean_waves.mp3",
        ],
    )

    result = await device.control_audio(device.AudioControlRequest(action="next", fade_ms=500))

    assert result["file"] == "content/audio/ambient_calm.mp3"
    assert audio_player.play_calls[-1]["file_path"] == "content/audio/ambient_calm.mp3"


@pytest.mark.asyncio
async def test_audio_next_uses_shared_player_when_no_registered_controller(monkeypatch):
    audio_player = StubAudioPlayer("content/audio/ambient_calm.mp3", volume=0.5, loop=True)
    manager = SimpleNamespace(_device_controllers={})

    async def fake_get_shared_audio_player():
        return audio_player

    monkeypatch.setattr(device, "get_device_manager", lambda: manager)
    monkeypatch.setattr(
        device,
        "get_shared_audio_player",
        fake_get_shared_audio_player,
        raising=False,
    )
    monkeypatch.setattr(
        device,
        "_load_background_music_playlist",
        lambda: [
            "content/audio/ambient_calm.mp3",
            "content/audio/soft_piano.mp3",
        ],
    )

    result = await device.control_audio(device.AudioControlRequest(action="next", fade_ms=800))

    assert result["success"] is True
    assert result["simulated"] is False
    assert result["file"] == "content/audio/soft_piano.mp3"
    assert audio_player.play_calls[-1]["file_path"] == "content/audio/soft_piano.mp3"


@pytest.mark.asyncio
async def test_audio_next_skips_missing_files_in_playlist(monkeypatch):
    audio_player = StubAudioPlayer("content/audio/ambient_calm.mp3", volume=0.35, loop=True)
    manager = SimpleNamespace(_device_controllers={"audio": audio_player})

    monkeypatch.setattr(device, "get_device_manager", lambda: manager)
    monkeypatch.setattr(
        device,
        "_load_background_music_playlist",
        lambda: [
            "content/audio/ambient_calm.mp3",
            "content/audio/__missing__.mp3",
            "content/audio/soft_piano.mp3",
        ],
    )

    result = await device.control_audio(device.AudioControlRequest(action="next", fade_ms=900))

    assert result["success"] is True
    assert result["simulated"] is False
    assert result["file"] == "content/audio/soft_piano.mp3"
    assert audio_player.play_calls[-1]["file_path"] == "content/audio/soft_piano.mp3"
