import textwrap

import pytest

from api import therapy as therapy_api
from models.therapy import TherapyPlan
from models.therapy import TherapyPlanParser


class FakePlanManager:
    def __init__(self, plan):
        self.plan = plan

    def get_plan_by_id(self, plan_id: str):
        if self.plan.id == plan_id:
            return self.plan
        return None


def _phase_dict():
    return {
        "name": "phase-one",
        "duration": 120,
        "light": {
            "color": "#FFFFFF",
            "brightness": 50,
            "transition": 0,
            "pattern": "static",
        },
        "audio": {
            "file": "content/audio/test.mp3",
            "volume": 40,
            "loop": True,
            "fade_in": 0,
            "fade_out": 0,
        },
    }


def _write_screen_prompt_plan(tmp_path, screen_prompts_block: str = ""):
    path = tmp_path / "api_screen_prompt_plan.yaml"
    content = textwrap.dedent(
        """
        id: api-screen-prompt-plan
        name: API Screen Prompt Plan
        description: Plan used by therapy API screen prompt tests
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


@pytest.mark.asyncio
async def test_get_plan_includes_valid_screen_prompts(monkeypatch):
    plan = TherapyPlan.from_dict(
        {
            "id": "api-screen-prompt-plan",
            "name": "API Screen Prompt Plan",
            "description": "Plan used by therapy API screen prompt tests",
            "target_emotions": ["anxious"],
            "intensity": "medium",
            "style": "modern",
            "duration": 120,
            "phases": [_phase_dict()],
            "screen_prompts": [
                {
                    "start_second": 0,
                    "end_second": 60,
                    "title": "Settle In",
                    "lines": ["Breathe in slowly.", "Let your shoulders drop."],
                },
                {
                    "start_second": 60,
                    "end_second": 120,
                    "title": "Stay Here",
                    "lines": ["Keep resting here.", "Let the breath stay easy."],
                },
            ],
        }
    )
    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: FakePlanManager(plan))

    response = await therapy_api.get_plan(plan.id)

    assert response["id"] == plan.id
    assert response["duration"] == 120
    assert len(response["phases"]) == 1
    assert response["screen_prompts"] == [
        {
            "start_second": 0,
            "end_second": 60,
            "title": "Settle In",
            "lines": ["Breathe in slowly.", "Let your shoulders drop."],
        },
        {
            "start_second": 60,
            "end_second": 120,
            "title": "Stay Here",
            "lines": ["Keep resting here.", "Let the breath stay easy."],
        },
    ]


@pytest.mark.asyncio
async def test_get_plan_omits_missing_screen_prompts(monkeypatch, tmp_path):
    plan = TherapyPlanParser.load_from_file(_write_screen_prompt_plan(tmp_path))
    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: FakePlanManager(plan))

    response = await therapy_api.get_plan(plan.id)

    assert response["id"] == plan.id
    assert response["duration"] == 120
    assert "screen_prompts" not in response


@pytest.mark.asyncio
async def test_get_plan_omits_invalid_screen_prompts(monkeypatch, tmp_path):
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
    monkeypatch.setattr(therapy_api, "get_plan_manager", lambda: FakePlanManager(plan))

    response = await therapy_api.get_plan(plan.id)

    assert plan.screen_prompts is None
    assert response["id"] == plan.id
    assert response["duration"] == 120
    assert "screen_prompts" not in response
