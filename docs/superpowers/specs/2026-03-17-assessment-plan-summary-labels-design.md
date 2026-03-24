# Assessment Plan Summary Labels Design

**Goal:** Replace the raw therapy plan enum display on the assessment result card with user-facing Chinese labels, while adding more readable metadata for the recommended plan.

**Scope:** Only the assessment result card in `app/src/views/AssessmentPage.vue`. Do not change backend response shape. Do not change admin-facing configuration screens.

**Design:**
- Keep the existing recommendation card layout and continue using `recommendedPlan.description` as the single rendered summary line.
- Stop interpolating raw backend values such as `chinese` directly into the description string.
- Format the summary with four Chinese labels: `风格`、`强度`、`适用情绪`、`时长`.
- Map `TherapyPlan.style` for this page only:
  - `chinese` -> `中式疗愈`
  - `modern` -> `现代疗愈`
- Map `TherapyPlan.intensity` for this page only:
  - `low` -> `轻柔`
  - `medium` -> `适中`
  - `high` -> `强效`
- For `适用情绪`, use the currently analyzed emotion category already available in the page flow, because the current recommendation API does not return `target_emotions` in `matched_plans`.
- Keep `时长` in minutes.

**Testing:**
- Add a source-level regression assertion in `app/tests/assessmentPageManualFlow.test.cjs` to require a dedicated formatter and the four Chinese labels.
- Re-run the focused assessment page source test and frontend type-check.
