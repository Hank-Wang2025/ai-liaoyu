import asyncio
import os
import sys
import textwrap
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import therapy as therapy_api
from models.therapy import TherapyPlanParser
import services.session_manager as session_manager_module
import services.therapy_executor as therapy_executor_module


class FakePlanManager:
    def __init__(self, plan):
        self.plan = plan

    def get_plan_by_id(self, plan_id: str):
        if plan_id == self.plan.id:
            return self.plan
        return None


def _write_screen_prompt_plan(tmp_path, screen_prompts_block: str = ""):
    path = tmp_path / "executor_screen_prompt_plan.yaml"
    content = textwrap.dedent(
        """
        id: executor-screen-prompt-plan
        name: Executor Screen Prompt Plan
        description: Plan used by executor screen prompt tests
        target_emotions:
          - anxious
        intensity: medium
        style: modern
        duration: 120
        phases:
          - name: phase-one
            duration: 120
            light:
              color: "#FFFFFF"
              brightness: 50
            audio:
              file: content/audio/test.mp3
              volume: 40
        """
    ).strip()
    if screen_prompts_block:
        content += "\n" + textwrap.dedent(screen_prompts_block).strip()
    path.write_text(content + "\n", encoding="utf-8")
    return path


class FakeSession:
    def __init__(self, session_id: str = "session-1"):
        self.id = session_id
        self.duration_seconds = 42


class FakeSessionManager:
    def __init__(self):
        self.current_session = None
        self.has_active_session = False
        self.pause_calls = 0
        self.resume_calls = 0
        self.end_calls = 0
        self.mark_stopping_calls = 0
        self.completed_sessions = {}

    async def create_session(self):
        self.current_session = FakeSession()
        self.has_active_session = True
        return self.current_session

    async def set_initial_emotion(self, emotion):
        self.initial_emotion = emotion

    async def set_plan(self, plan):
        self.plan = plan

    async def start_therapy(self):
        self.started = True

    async def pause_session(self):
        self.pause_calls += 1

    async def resume_session(self):
        self.resume_calls += 1

    async def mark_stopping(self):
        self.mark_stopping_calls += 1

    async def end_session(self):
        self.end_calls += 1
        self.has_active_session = False
        if self.current_session is not None:
            self.completed_sessions[self.current_session.id] = self.current_session
        return self.current_session

    async def get_session_by_id(self, session_id: str):
        if self.current_session and self.current_session.id == session_id:
            return self.current_session
        return self.completed_sessions.get(session_id)


class FakeExecutor:
    instances = []
    block_start = False

    def __init__(self, audio_player=None, chair_manager=None):
        self.audio_player = audio_player
        self.chair_manager = chair_manager
        self.start_calls = 0
        self.pause_calls = 0
        self.resume_calls = 0
        self.skip_calls = 0
        self.stop_output_calls = 0
        self.stop_calls = 0
        self.started_plan = None
        self.start_entered = asyncio.Event()
        self.start_release = asyncio.Event()
        if not self.block_start:
            self.start_release.set()
        self.stop_entered = asyncio.Event()
        self.stop_release = asyncio.Event()
        self.stop_release.set()
        FakeExecutor.instances.append(self)

    async def start(self, plan):
        self.start_calls += 1
        self.started_plan = plan
        self.start_entered.set()
        await self.start_release.wait()

    async def pause(self):
        self.pause_calls += 1

    async def resume(self):
        self.resume_calls += 1

    async def skip_phase(self):
        self.skip_calls += 1

    async def stop_outputs_now(self):
        self.stop_output_calls += 1

    async def stop(self):
        self.stop_calls += 1
        self.stop_entered.set()
        await self.stop_release.wait()


class FakeDeviceInitializer:
    def __init__(self, chair_controller=None):
        self._chair_controller = chair_controller
        self.initialize_calls = 0
        self.ensure_chair_calls = 0
        self.controller_after_init = chair_controller

    async def initialize_all(self):
        self.initialize_calls += 1
        self._chair_controller = self.controller_after_init
        return {"chair": self._chair_controller is not None}

    async def ensure_chair_controller(self):
        self.ensure_chair_calls += 1
        self._chair_controller = self.controller_after_init
        return self._chair_controller

    def get_chair_controller(self):
        return self._chair_controller


@pytest.fixture
def fake_runtime(monkeypatch):
    plan = SimpleNamespace(
        id="plan-1",
        name="Plan 1",
        duration=300,
        phases=[SimpleNamespace(name="phase-1"), SimpleNamespace(name="phase-2")],
    )
    manager = FakeSessionManager()
    initializer = FakeDeviceInitializer()

    FakeExecutor.instances = []
    FakeExecutor.block_start = False
    monkeypatch.setattr(session_manager_module, "session_manager", manager)
    monkeypatch.setattr(therapy_executor_module, "TherapyExecutor", FakeExecutor)
    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: FakePlanManager(plan))
    monkeypatch.setattr(
        therapy_api,
        "get_device_initializer",
        lambda: initializer,
        raising=False,
    )

    if hasattr(therapy_api, "_current_executor"):
        monkeypatch.setattr(therapy_api, "_current_executor", None)
    if hasattr(therapy_api, "_stop_finalize_tasks"):
        monkeypatch.setattr(therapy_api, "_stop_finalize_tasks", {})
    if hasattr(therapy_api, "_stopping_session_ids"):
        monkeypatch.setattr(therapy_api, "_stopping_session_ids", set())

    return manager, plan


@pytest.mark.asyncio
async def test_execute_plan_returns_before_executor_start_finishes(fake_runtime, monkeypatch):
    manager, plan = fake_runtime
    FakeExecutor.block_start = True

    background_tasks = []
    create_task = asyncio.create_task

    def capture_task(coro):
        task = create_task(coro)
        background_tasks.append(task)
        return task

    monkeypatch.setattr(therapy_api, "create_background_task", capture_task, raising=False)

    response = await asyncio.wait_for(
        therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id)),
        timeout=0.2,
    )

    assert response["success"] is True
    assert manager.plan.id == plan.id
    assert len(FakeExecutor.instances) == 1
    assert background_tasks

    executor = FakeExecutor.instances[0]
    assert executor.start_calls == 1
    assert executor.start_entered.is_set() is True

    executor.start_release.set()
    await asyncio.gather(*background_tasks)
    FakeExecutor.block_start = False


@pytest.mark.asyncio
async def test_execute_plan_screen_prompt_missing_still_starts(fake_runtime, monkeypatch, tmp_path):
    manager, _ = fake_runtime
    plan = TherapyPlanParser.load_from_file(_write_screen_prompt_plan(tmp_path))
    background_tasks = []
    create_task = asyncio.create_task

    def capture_task(coro):
        task = create_task(coro)
        background_tasks.append(task)
        return task

    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: FakePlanManager(plan))
    monkeypatch.setattr(therapy_api, "create_background_task", capture_task, raising=False)

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    await asyncio.gather(*background_tasks)

    assert response["success"] is True
    assert response["phases"] == 1
    assert manager.plan.phases[0].name == "phase-one"
    assert manager.plan.screen_prompts is None
    assert FakeExecutor.instances[0].started_plan.screen_prompts is None


@pytest.mark.asyncio
async def test_execute_plan_screen_prompt_invalid_group_dropped_still_starts(
    fake_runtime,
    monkeypatch,
    tmp_path,
):
    manager, _ = fake_runtime
    plan = TherapyPlanParser.load_from_file(
        _write_screen_prompt_plan(
            tmp_path,
            """
screen_prompts:
  - start_second: 0
    end_second: 80
    title: First
    lines:
      - First segment.
  - start_second: 60
    end_second: 120
    title: Overlap
    lines:
      - Overlapping segment.
""",
        )
    )
    background_tasks = []
    create_task = asyncio.create_task

    def capture_task(coro):
        task = create_task(coro)
        background_tasks.append(task)
        return task

    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: FakePlanManager(plan))
    monkeypatch.setattr(therapy_api, "create_background_task", capture_task, raising=False)

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    await asyncio.gather(*background_tasks)

    assert response["success"] is True
    assert response["duration"] == 120
    assert manager.plan.phases[0].name == "phase-one"
    assert manager.plan.screen_prompts is None
    assert FakeExecutor.instances[0].started_plan.screen_prompts is None


@pytest.mark.asyncio
async def test_pause_therapy_pauses_running_executor(fake_runtime):
    manager, plan = fake_runtime

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    await therapy_api.pause_therapy(response["session_id"])

    assert manager.pause_calls == 1
    assert len(FakeExecutor.instances) == 1
    assert FakeExecutor.instances[0].pause_calls == 1


@pytest.mark.asyncio
async def test_resume_therapy_resumes_running_executor(fake_runtime):
    manager, plan = fake_runtime

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    await therapy_api.resume_therapy(response["session_id"])

    assert manager.resume_calls == 1
    assert len(FakeExecutor.instances) == 1
    assert FakeExecutor.instances[0].resume_calls == 1


@pytest.mark.asyncio
async def test_end_therapy_stops_running_executor(fake_runtime):
    manager, plan = fake_runtime

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    await therapy_api.end_therapy(response["session_id"])

    assert manager.end_calls == 1
    assert len(FakeExecutor.instances) == 1
    assert FakeExecutor.instances[0].stop_calls == 1


@pytest.mark.asyncio
async def test_stop_now_therapy_stops_outputs_and_finalizes_in_background(
    fake_runtime,
    monkeypatch,
):
    manager, plan = fake_runtime

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    executor = FakeExecutor.instances[0]
    executor.stop_release.clear()

    background_tasks = []
    create_task = asyncio.create_task

    def capture_task(coro):
        task = create_task(coro)
        background_tasks.append(task)
        return task

    monkeypatch.setattr(therapy_api, "create_background_task", capture_task, raising=False)

    stop_response = await therapy_api.stop_now_therapy(response["session_id"])

    assert stop_response["success"] is True
    assert stop_response["session_id"] == response["session_id"]
    assert executor.stop_output_calls == 1
    assert manager.mark_stopping_calls == 1
    assert manager.end_calls == 0
    assert len(background_tasks) == 1

    executor.stop_release.set()
    await asyncio.gather(*background_tasks)

    assert executor.stop_calls == 1
    assert manager.end_calls == 1


@pytest.mark.asyncio
async def test_stop_now_therapy_is_idempotent_while_finalization_is_pending(
    fake_runtime,
    monkeypatch,
):
    manager, plan = fake_runtime

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    executor = FakeExecutor.instances[0]
    executor.stop_release.clear()

    background_tasks = []
    create_task = asyncio.create_task

    def capture_task(coro):
        task = create_task(coro)
        background_tasks.append(task)
        return task

    monkeypatch.setattr(therapy_api, "create_background_task", capture_task, raising=False)

    first_response = await therapy_api.stop_now_therapy(response["session_id"])
    second_response = await therapy_api.stop_now_therapy(response["session_id"])

    assert first_response["success"] is True
    assert second_response["success"] is True
    assert second_response["already_stopping"] is True
    assert executor.stop_output_calls == 1
    assert manager.mark_stopping_calls == 1
    assert len(background_tasks) == 1

    executor.stop_release.set()
    await asyncio.gather(*background_tasks)

    assert executor.stop_calls == 1
    assert manager.end_calls == 1


@pytest.mark.asyncio
async def test_execute_plan_passes_shared_audio_player_to_executor(fake_runtime, monkeypatch):
    _, plan = fake_runtime
    audio_player = object()

    async def fake_get_shared_audio_player():
        return audio_player

    monkeypatch.setattr(
        therapy_api,
        "get_shared_audio_player",
        fake_get_shared_audio_player,
        raising=False,
    )

    await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))

    assert len(FakeExecutor.instances) == 1
    assert FakeExecutor.instances[0].audio_player is audio_player


@pytest.mark.asyncio
async def test_execute_plan_passes_chair_manager_to_executor_after_chair_initialization(
    fake_runtime,
    monkeypatch,
):
    _, plan = fake_runtime
    chair_controller = object()
    initializer = FakeDeviceInitializer()
    initializer.controller_after_init = chair_controller

    monkeypatch.setattr(
        therapy_api,
        "get_device_initializer",
        lambda: initializer,
        raising=False,
    )

    await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))

    assert len(FakeExecutor.instances) == 1
    assert FakeExecutor.instances[0].chair_manager is not None
    assert FakeExecutor.instances[0].chair_manager.controller is chair_controller
    assert initializer.ensure_chair_calls == 1
    assert initializer.initialize_calls == 0


@pytest.mark.asyncio
async def test_execute_plan_initializes_only_chair_controller_for_executor(
    fake_runtime,
    monkeypatch,
):
    _, plan = fake_runtime
    chair_controller = object()
    initializer = FakeDeviceInitializer()
    initializer.controller_after_init = chair_controller
    background_tasks = []
    create_task = asyncio.create_task

    def capture_task(coro):
        task = create_task(coro)
        background_tasks.append(task)
        return task

    monkeypatch.setattr(
        therapy_api,
        "get_device_initializer",
        lambda: initializer,
        raising=False,
    )
    monkeypatch.setattr(therapy_api, "create_background_task", capture_task, raising=False)

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    await asyncio.gather(*background_tasks)

    assert response["success"] is True
    assert len(FakeExecutor.instances) == 1
    assert FakeExecutor.instances[0].chair_manager is not None
    assert FakeExecutor.instances[0].chair_manager.controller is chair_controller
    assert initializer.ensure_chair_calls == 1
    assert initializer.initialize_calls == 0


@pytest.mark.asyncio
async def test_skip_therapy_phase_skips_running_executor_phase(fake_runtime):
    _, plan = fake_runtime

    response = await therapy_api.execute_plan(therapy_api.ExecutePlanRequest(plan_id=plan.id))
    await therapy_api.skip_therapy_phase(response["session_id"])

    assert len(FakeExecutor.instances) == 1
    assert FakeExecutor.instances[0].skip_calls == 1
