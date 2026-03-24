import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import therapy as therapy_api
from models.emotion import EmotionCategory, EmotionState
from models.session import Session
from models.therapy import (
    AudioConfig,
    ChairConfig,
    LightConfig,
    ScentConfig,
    TherapyIntensity,
    TherapyPhase,
    TherapyPlan,
    TherapyStyle,
    VoiceGuideConfig,
)
from services.plan_manager import PlanManager
from services.therapy_executor import ExecutorState, TherapyExecutor
import services.session_manager as session_manager_module


def make_phase(prefix: str, index: int, duration: int) -> TherapyPhase:
    token = f"{prefix}-phase-{index}"
    return TherapyPhase(
        name=token,
        duration=duration,
        light=LightConfig(color=f"{token}-light", brightness=40 + index),
        audio=AudioConfig(file=f"{token}.mp3", volume=50 + index),
        voice_guide=VoiceGuideConfig(text=f"{token} voice"),
        chair=ChairConfig(mode=f"{token}-mode", intensity=1 + index),
        scent=ScentConfig(scent_type=f"{token}-scent", intensity=1 + index),
    )


def make_plan(
    plan_id: str,
    intensity: TherapyIntensity,
    style: TherapyStyle,
    phase_durations: list[int],
    target_emotions: list[EmotionCategory],
) -> TherapyPlan:
    return TherapyPlan(
        id=plan_id,
        name=plan_id,
        description=f"{plan_id} description",
        target_emotions=target_emotions,
        intensity=intensity,
        style=style,
        duration=sum(phase_durations),
        phases=[
            make_phase(plan_id, index, duration)
            for index, duration in enumerate(phase_durations)
        ],
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def make_emotion(
    category: EmotionCategory = EmotionCategory.ANXIOUS,
    intensity: float = 0.55,
) -> EmotionState:
    return EmotionState(
        category=category,
        intensity=intensity,
        valence=-0.1,
        arousal=0.7,
        confidence=0.8,
        timestamp=datetime(2026, 1, 1),
    )


class FakePlanManager:
    def __init__(self, selected_plan: TherapyPlan | None):
        self.selected_plan = selected_plan
        self.calls: list[tuple[str, str, str | None]] = []

    def find_runtime_adjustment_plan(
        self,
        current_plan: TherapyPlan,
        target_intensity: TherapyIntensity,
        emotion: EmotionState | None = None,
    ) -> TherapyPlan | None:
        emotion_value = emotion.category.value if emotion else None
        self.calls.append((current_plan.id, target_intensity.value, emotion_value))
        return self.selected_plan


class FakeSessionManager:
    def __init__(
        self,
        session_id: str,
        current_plan: TherapyPlan,
        emotion: EmotionState | None,
    ):
        self.current_session = Session.create()
        self.current_session.id = session_id
        self.current_session.set_plan(current_plan)
        self.current_session.start_therapy()
        if emotion is not None:
            self.current_session.set_initial_emotion(emotion)

        self.has_active_session = True
        self.set_plan_calls: list[str] = []
        self.record_calls: list[dict] = []

    async def set_plan(self, plan: TherapyPlan) -> None:
        self.set_plan_calls.append(plan.id)
        self.current_session.set_plan(plan)

    async def record_adjustment(
        self,
        reason: str,
        adjustment_type: str,
        details: dict,
        previous_state: dict | None = None,
        new_state: dict | None = None,
    ) -> None:
        self.record_calls.append(
            {
                "reason": reason,
                "adjustment_type": adjustment_type,
                "details": details,
                "previous_state": previous_state,
                "new_state": new_state,
            }
        )
        self.current_session.add_adjustment(
            reason=reason,
            adjustment_type=adjustment_type,
            details=details,
            previous_state=previous_state,
            new_state=new_state,
        )


class FakeExecutor:
    def __init__(
        self,
        current_plan: TherapyPlan,
        adjust_chair_result: bool = True,
    ):
        self._current_plan = current_plan
        self._current_phase_index = 1
        self.adjust_chair_result = adjust_chair_result
        self.adjust_chair_calls: list[int] = []
        self.adjust_runtime_plan_calls: list[str] = []
        self.is_running = True
        self.is_paused = False

    async def adjust_chair_intensity(self, target_level: int) -> bool:
        self.adjust_chair_calls.append(target_level)
        if not self.adjust_chair_result:
            return False

        current_level = getattr(self._current_plan, "runtime_intensity_level", 3)
        delta = target_level - current_level

        for phase in self._current_plan.phases[self._current_phase_index :]:
            if phase.chair is not None:
                phase.chair.intensity = max(1, min(10, phase.chair.intensity + delta))

        self._current_plan.runtime_intensity_level = target_level
        if target_level <= 2:
            self._current_plan.intensity = TherapyIntensity.LOW
        elif target_level == 3:
            self._current_plan.intensity = TherapyIntensity.MEDIUM
        else:
            self._current_plan.intensity = TherapyIntensity.HIGH
        return True

    async def adjust_runtime_plan(self, new_plan: TherapyPlan) -> TherapyPlan:
        self.adjust_runtime_plan_calls.append(new_plan.id)
        return new_plan


@pytest.mark.asyncio
async def test_adjust_therapy_intensity_relax_updates_session_and_records_adjustment(
    monkeypatch,
):
    current_plan = make_plan(
        "current-medium",
        TherapyIntensity.LOW,
        TherapyStyle.CHINESE,
        [300, 300, 300],
        [EmotionCategory.ANXIOUS],
    )
    current_plan.runtime_intensity_level = 2
    emotion = make_emotion()
    manager = FakeSessionManager("session-1", current_plan, emotion)
    executor = FakeExecutor(current_plan)
    plan_manager = FakePlanManager(None)

    monkeypatch.setattr(session_manager_module, "session_manager", manager)
    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: plan_manager)
    monkeypatch.setattr(therapy_api, "_current_executor", executor)

    response = await therapy_api.adjust_therapy_intensity(
        "session-1",
        therapy_api.AdjustIntensityRequest(direction="relax"),
    )

    assert response["success"] is True
    assert response["changed"] is True
    assert response["atBoundary"] is False
    assert response["targetIntensity"] == "low"
    assert response["plan"]["id"] == "current-medium"
    assert response["plan"]["intensity"] == "low"
    assert response["plan"]["runtime_intensity_level"] == 1
    assert response["plan"]["phases"][0]["chair"]["intensity"] == 1
    assert response["plan"]["phases"][1]["chair"]["intensity"] == 1
    assert response["plan"]["phases"][2]["chair"]["intensity"] == 2
    assert plan_manager.calls == []
    assert executor.adjust_chair_calls == [1]
    assert executor.adjust_runtime_plan_calls == []
    assert manager.set_plan_calls == ["current-medium"]
    assert len(manager.record_calls) == 1
    assert manager.record_calls[0]["details"]["old_plan_id"] == "current-medium"
    assert manager.record_calls[0]["details"]["new_plan_id"] == "current-medium"
    assert manager.record_calls[0]["details"]["old_runtime_intensity_level"] == 2
    assert manager.record_calls[0]["details"]["new_runtime_intensity_level"] == 1
    assert manager.record_calls[0]["new_state"]["intensity"] == "low"
    assert manager.record_calls[0]["adjustment_type"] == "intensity_adjustment"
    assert manager.current_session.plan_id == "current-medium"


@pytest.mark.asyncio
async def test_adjust_therapy_intensity_returns_boundary_response(monkeypatch):
    current_plan = make_plan(
        "already-low",
        TherapyIntensity.LOW,
        TherapyStyle.MODERN,
        [300, 300, 300],
        [EmotionCategory.ANXIOUS],
    )
    manager = FakeSessionManager("session-2", current_plan, make_emotion())
    executor = FakeExecutor(current_plan)
    plan_manager = FakePlanManager(None)

    monkeypatch.setattr(session_manager_module, "session_manager", manager)
    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: plan_manager)
    monkeypatch.setattr(therapy_api, "_current_executor", executor)

    response = await therapy_api.adjust_therapy_intensity(
        "session-2",
        therapy_api.AdjustIntensityRequest(direction="relax"),
    )

    assert response["success"] is True
    assert response["changed"] is False
    assert response["atBoundary"] is True
    assert response["targetIntensity"] == "low"
    assert plan_manager.calls == []
    assert executor.adjust_chair_calls == []
    assert executor.adjust_runtime_plan_calls == []
    assert manager.set_plan_calls == []
    assert manager.record_calls == []


@pytest.mark.asyncio
async def test_adjust_therapy_intensity_returns_safe_failure_when_no_candidate(
    monkeypatch,
):
    current_plan = make_plan(
        "current-medium",
        TherapyIntensity.MEDIUM,
        TherapyStyle.MODERN,
        [300, 300, 300],
        [EmotionCategory.ANXIOUS],
    )
    manager = FakeSessionManager("session-3", current_plan, make_emotion())
    executor = FakeExecutor(current_plan, adjust_chair_result=False)
    plan_manager = FakePlanManager(None)

    monkeypatch.setattr(session_manager_module, "session_manager", manager)
    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: plan_manager)
    monkeypatch.setattr(therapy_api, "_current_executor", executor)

    response = await therapy_api.adjust_therapy_intensity(
        "session-3",
        therapy_api.AdjustIntensityRequest(direction="relax"),
    )

    assert response["success"] is True
    assert response["changed"] is False
    assert response["atBoundary"] is False
    assert response["targetIntensity"] == "low"
    assert response["plan"]["id"] == "current-medium"
    assert response["plan"]["intensity"] == "medium"
    assert response["plan"]["runtime_intensity_level"] == 3
    assert plan_manager.calls == []
    assert executor.adjust_chair_calls == [2]
    assert executor.adjust_runtime_plan_calls == []
    assert manager.set_plan_calls == []
    assert manager.record_calls == []


@pytest.mark.asyncio
async def test_adjust_chair_intensity_updates_current_and_future_phases_without_reloading_audio():
    current_plan = make_plan(
        "current-medium",
        TherapyIntensity.MEDIUM,
        TherapyStyle.MODERN,
        [100, 200, 300, 400],
        [EmotionCategory.ANXIOUS],
    )
    executor = TherapyExecutor()
    executor._current_plan = current_plan
    executor._current_plan.runtime_intensity_level = 3
    executor._current_phase_index = 1
    executor._state = ExecutorState.RUNNING
    executor._chair_manager = object()

    chair_calls: list[tuple[str, int]] = []
    audio_calls: list[str] = []
    phase_calls: list[str] = []
    observed_events = []

    async def fake_apply_chair_config(config: ChairConfig) -> None:
        chair_calls.append((config.mode, config.intensity))

    async def fake_apply_audio_config(config: AudioConfig) -> None:
        audio_calls.append(config.file)

    async def fake_apply_phase_config(phase: TherapyPhase) -> None:
        phase_calls.append(phase.name)

    executor._apply_chair_config = fake_apply_chair_config
    executor._apply_audio_config = fake_apply_audio_config
    executor._apply_phase_config = fake_apply_phase_config
    executor.add_event_listener(lambda event: observed_events.append(event))

    changed = await executor.adjust_chair_intensity(4)

    assert changed is True
    assert current_plan.runtime_intensity_level == 4
    assert current_plan.intensity == TherapyIntensity.HIGH
    assert current_plan.phases[0].chair.intensity == 1
    assert current_plan.phases[1].chair.intensity == 3
    assert current_plan.phases[2].chair.intensity == 4
    assert current_plan.phases[3].chair.intensity == 5
    assert current_plan.phases[1].audio.file == "current-medium-phase-1.mp3"
    assert chair_calls == [("current-medium-phase-1-mode", 3)]
    assert audio_calls == []
    assert phase_calls == []
    assert any(event.event_type == "chair_intensity_adjusted" for event in observed_events)


def test_find_runtime_adjustment_plan_prefers_same_style_emotion_and_closest_duration():
    manager = PlanManager.__new__(PlanManager)
    manager.default_plan = None

    current_plan = make_plan(
        "current-medium",
        TherapyIntensity.MEDIUM,
        TherapyStyle.CHINESE,
        [300, 300, 300],
        [EmotionCategory.ANXIOUS],
    )
    best_match = make_plan(
        "best-low",
        TherapyIntensity.LOW,
        TherapyStyle.CHINESE,
        [300, 300, 320],
        [EmotionCategory.ANXIOUS],
    )
    wrong_style = make_plan(
        "wrong-style",
        TherapyIntensity.LOW,
        TherapyStyle.MODERN,
        [300, 300, 300],
        [EmotionCategory.ANXIOUS],
    )
    wrong_emotion = make_plan(
        "wrong-emotion",
        TherapyIntensity.LOW,
        TherapyStyle.CHINESE,
        [300, 300, 300],
        [EmotionCategory.SAD],
    )
    farther_duration = make_plan(
        "farther-duration",
        TherapyIntensity.LOW,
        TherapyStyle.CHINESE,
        [200, 200, 200],
        [EmotionCategory.ANXIOUS],
    )
    manager.plans = [wrong_style, wrong_emotion, farther_duration, best_match]

    selected = manager.find_runtime_adjustment_plan(
        current_plan=current_plan,
        target_intensity=TherapyIntensity.LOW,
        emotion=make_emotion(),
    )

    assert selected is best_match


def test_find_runtime_adjustment_plan_returns_none_without_same_phase_count():
    manager = PlanManager.__new__(PlanManager)
    manager.default_plan = None

    current_plan = make_plan(
        "current-medium",
        TherapyIntensity.MEDIUM,
        TherapyStyle.MODERN,
        [300, 300, 300],
        [EmotionCategory.ANXIOUS],
    )
    different_phase_count = make_plan(
        "different-phase-count",
        TherapyIntensity.LOW,
        TherapyStyle.MODERN,
        [200, 200, 200, 200],
        [EmotionCategory.ANXIOUS],
    )
    manager.plans = [different_phase_count]

    selected = manager.find_runtime_adjustment_plan(
        current_plan=current_plan,
        target_intensity=TherapyIntensity.LOW,
        emotion=make_emotion(),
    )

    assert selected is None


@pytest.mark.asyncio
async def test_adjust_runtime_plan_updates_current_and_future_phases_without_restart():
    current_plan = make_plan(
        "current-medium",
        TherapyIntensity.MEDIUM,
        TherapyStyle.MODERN,
        [100, 200, 300, 400],
        [EmotionCategory.ANXIOUS],
    )
    target_plan = make_plan(
        "target-high",
        TherapyIntensity.HIGH,
        TherapyStyle.MODERN,
        [90, 110, 50, 50],
        [EmotionCategory.ANXIOUS],
    )
    executor = TherapyExecutor()
    executor._current_plan = current_plan
    executor._current_phase_index = 1
    executor._state = ExecutorState.RUNNING

    applied_phases: list[str] = []
    observed_events = []

    async def fake_apply_phase_config(phase: TherapyPhase) -> None:
        applied_phases.append(phase.name)

    async def should_not_restart(*args, **kwargs):
        raise AssertionError("runtime adjustment must not restart execution")

    executor._apply_phase_config = fake_apply_phase_config
    executor.stop = should_not_restart
    executor.start = should_not_restart
    executor.add_event_listener(lambda event: observed_events.append(event))

    adjusted_plan = await executor.adjust_runtime_plan(target_plan)

    assert adjusted_plan is current_plan
    assert current_plan.id == "target-high"
    assert current_plan.intensity == TherapyIntensity.HIGH
    assert current_plan.duration == 1000
    assert current_plan.phases[0].name == "current-medium-phase-0"
    assert current_plan.phases[1].name == "target-high-phase-1"
    assert current_plan.phases[1].duration == 200
    assert current_plan.phases[1].audio.file == "target-high-phase-1.mp3"
    assert current_plan.phases[2].name == "target-high-phase-2"
    assert current_plan.phases[2].duration == 350
    assert current_plan.phases[3].name == "target-high-phase-3"
    assert current_plan.phases[3].duration == 350
    assert applied_phases == ["target-high-phase-1"]
    assert any(event.event_type == "plan_adjusted" for event in observed_events)
