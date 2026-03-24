import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.therapy_executor import ExecutorState, TherapyExecutor


class FakeAudioPlayer:
    def __init__(self):
        self.pause_calls = 0
        self.resume_calls = 0

    async def pause(self):
        self.pause_calls += 1
        return True

    async def resume(self):
        self.resume_calls += 1
        return True


@pytest.mark.asyncio
async def test_pause_pauses_audio_player():
    audio_player = FakeAudioPlayer()
    executor = TherapyExecutor(audio_player=audio_player)
    executor._state = ExecutorState.RUNNING

    await executor.pause()

    assert executor.state == ExecutorState.PAUSED
    assert not executor._pause_event.is_set()
    assert audio_player.pause_calls == 1


@pytest.mark.asyncio
async def test_resume_resumes_audio_player():
    audio_player = FakeAudioPlayer()
    executor = TherapyExecutor(audio_player=audio_player)
    executor._state = ExecutorState.PAUSED
    executor._pause_event.clear()

    await executor.resume()

    assert executor.state == ExecutorState.RUNNING
    assert executor._pause_event.is_set()
    assert audio_player.resume_calls == 1
