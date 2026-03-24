from datetime import datetime, timedelta

from models.emotion import EmotionCategory, EmotionState
from models.session import Session
from services.report_generator import ReportDataCollector


def test_report_curve_includes_terminal_point_for_single_sample_session():
    session = Session.create()
    initial = EmotionState(
        category=EmotionCategory.NEUTRAL,
        intensity=0.4,
        valence=0.0,
        arousal=0.5,
        confidence=0.8,
        timestamp=datetime.now(),
    )

    session.set_initial_emotion(initial)
    session.complete()
    session.end_time = initial.timestamp + timedelta(minutes=5)

    report = ReportDataCollector().collect_from_session(session)

    assert len(report.emotion_curve) == 2
    assert report.emotion_curve[0].timestamp == initial.timestamp
    assert report.emotion_curve[-1].timestamp == session.end_time
    assert report.emotion_curve[-1].category == EmotionCategory.NEUTRAL
