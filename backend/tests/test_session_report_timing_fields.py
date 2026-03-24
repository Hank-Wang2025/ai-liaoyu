import os
import sys
from types import SimpleNamespace
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import session as session_api
from models.emotion import EmotionCategory


class FakeSessionManager:
    def __init__(self, session):
        self._session = session

    async def get_session_by_id(self, session_id: str):
        return self._session


class FakeReportGenerator:
    def __init__(self, report):
        self._report = report

    async def generate_report(self, session):
        return self._report


class FakePlanManager:
    def __init__(self, plan):
        self._plan = plan

    def get_plan_by_id(self, plan_id: str):
        if self._plan and self._plan.id == plan_id:
            return self._plan
        return None


@pytest.mark.asyncio
async def test_session_report_exposes_planned_and_actual_duration(monkeypatch):
    session = SimpleNamespace(id="session-1", plan_id="plan-1")
    report = SimpleNamespace(
        id="report-1",
        status=SimpleNamespace(value="completed"),
        therapy_start_time=datetime(2026, 3, 17, 10, 0, 0),
        therapy_end_time=datetime(2026, 3, 17, 10, 3, 0),
        duration_seconds=180,
        duration_minutes=3.0,
        plan_name="Quick Calm",
        initial_emotion_category=EmotionCategory.NEUTRAL,
        initial_emotion_intensity=0.3,
        initial_emotion_valence=0.0,
        final_emotion_category=EmotionCategory.HAPPY,
        final_emotion_intensity=0.6,
        final_emotion_valence=0.5,
        effectiveness_metrics=SimpleNamespace(
            effectiveness_rating="good",
            emotion_improvement=0.5,
            valence_change=0.5,
            stability_index=0.9,
        ),
        summary_text="ok",
        recommendations=["rest"],
        emotion_curve=[],
        adjustment_count=0,
    )
    plan = SimpleNamespace(id="plan-1", duration=300)

    monkeypatch.setattr(session_api, "session_manager", FakeSessionManager(session))
    monkeypatch.setattr(session_api, "report_generator", FakeReportGenerator(report))
    monkeypatch.setattr(session_api, "get_plan_manager", lambda: FakePlanManager(plan), raising=False)

    response = await session_api.get_session_report("session-1")

    assert response["duration_seconds"] == 180
    assert response["planned_duration_seconds"] == 300
