from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ELECTRON_MAIN = REPO_ROOT / "app" / "electron" / "main.ts"
ASSESSMENT_PAGE = REPO_ROOT / "app" / "src" / "views" / "AssessmentPage.vue"


def test_electron_main_configures_media_permissions():
    content = ELECTRON_MAIN.read_text(encoding="utf-8")

    assert "setPermissionCheckHandler" in content
    assert "setPermissionRequestHandler" in content
    assert "audioCapture" in content or "media" in content


def test_assessment_page_shows_microphone_errors_on_voice_step():
    content = ASSESSMENT_PAGE.read_text(encoding="utf-8")

    analyzing_index = content.index("v-else-if=\"step === 'analyzing'\"")
    error_index = content.index(
        "<p v-if=\"analysisError\" class=\"assessment-page__error\">{{ analysisError }}</p>"
    )

    assert error_index < analyzing_index


def test_assessment_page_falls_back_when_microphone_access_fails():
    content = ASSESSMENT_PAGE.read_text(encoding="utf-8")

    assert "await fallbackAnalysis(" in content
