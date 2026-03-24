from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_STORE = REPO_ROOT / "app" / "src" / "stores" / "session.ts"


def test_session_store_marks_therapy_active_before_backend_start_completes():
    content = SESSION_STORE.read_text(encoding="utf-8")

    active_idx = content.index("isTherapyActive.value = true")
    await_idx = content.index("const result = await therapyApi.startTherapy(")

    assert active_idx < await_idx
