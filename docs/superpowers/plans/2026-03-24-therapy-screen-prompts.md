# Therapy Screen Prompts Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add plan-driven on-screen therapy prompt timelines so the therapy page shows time-based stage titles and multi-line guidance, while falling back cleanly to the existing stage display when prompt timelines are absent or invalid.

**Architecture:** Keep device execution phases and screen prompt timelines separate. Parse and validate optional `screen_prompts` from therapy plan YAML on the backend, expose valid timelines through plan detail data, hydrate the full plan into the frontend before entering the therapy page, and let the therapy page resolve the active prompt from `elapsedTime` using `[start_second, end_second)` matching. Invalid timelines must invalidate the whole prompt group and trigger fallback to the existing stage display.

**Tech Stack:** FastAPI, Python dataclasses, pytest, Vue 3, Pinia, TypeScript, node:test, vue-tsc

**Constraints:** Follow the approved spec in `docs/superpowers/specs/2026-03-24-therapy-screen-prompts-design.md`. Keep changes local only; do not create git commits in this implementation.

---

## File Map

- `backend/models/therapy.py` - add screen prompt data structures, parser validation, and serialization support
- `backend/api/therapy.py` - expose validated `screen_prompts` in plan detail responses
- `backend/tests/test_therapy_engine.py` - parser and validation regression coverage for valid and invalid prompt timelines
- `backend/tests/test_therapy_api_executor_lifecycle.py` - startup-path regression coverage proving missing or invalid prompt groups do not block therapy execution
- `backend/tests/test_therapy_screen_prompts_api.py` - API contract coverage for valid, missing, and invalid prompt timelines
- `content/plans/anxiety_relief_chinese.yaml` - seed a 15-minute `screen_prompts` timeline for `[0, 900)`
- `content/plans/anger_release_modern.yaml` - seed a 15-minute `screen_prompts` timeline for `[0, 900)`
- `content/plans/depression_relief_chinese.yaml` - seed a 20-minute `screen_prompts` timeline for `[0, 1200)`
- `content/plans/emotional_balance_chinese.yaml` - seed a second 20-minute `screen_prompts` timeline for `[0, 1200)`
- `app/src/types/index.ts` - define canonical camelCase frontend prompt timeline types
- `app/src/stores/session.ts` - normalize backend prompt payloads into camelCase-only session plan objects
- `app/src/api/index.ts` - expose plan-detail fetch helper used before therapy start
- `app/src/components/entry/AssessmentEntryPanel.vue` - fetch full plan detail before `startSession`, with summary-plan fallback only when detail hydration cannot be used
- `app/src/views/TherapyPage.vue` - resolve and render the active prompt from `currentPlan.screenPrompts`, with fallback to the existing stage display
- `app/tests/therapyScreenPromptsFlow.test.cjs` - static regression coverage for prompt normalization, hydration ordering, rendering, boundaries, and fallback branches

## Chunk 1: Lock Backend Timeline Rules With Tests

### Task 1: Parser validation coverage

**Files:**
- Modify: `backend/tests/test_therapy_engine.py`
- Modify: `backend/tests/test_therapy_api_executor_lifecycle.py`

- [ ] **Step 1: Add failing parser tests for valid `screen_prompts` loading and for plans with no `screen_prompts` field remaining loadable with `screen_prompts` absent or `None`**
- [ ] **Step 2: Add failing parser tests for whole-group invalidation when the first segment does not start at `0`, segments overlap, segments leave a gap, a range has zero or negative length, the final segment does not end at `total_duration`, the title is missing or blank, or `lines` is empty**
- [ ] **Step 3: Add failing parser tests for `[start_second, end_second)` semantics, full `[0, total_duration)` coverage, invalid-group omission (`screen_prompts` becomes absent or `None` instead of partially preserved), and invalid-group fallback that still leaves the plan loadable with normal `id`, `duration`, and `phases` data**
- [ ] **Step 4: Add failing startup-path tests proving `execute_plan` still succeeds when the selected plan has no `screen_prompts` or when an invalid prompt group has already been dropped, and that normal phase data still drives startup**
- [ ] **Step 5: Add a failing round-trip serialization test covering `to_dict` and `from_dict` for a valid prompt timeline**
- [ ] **Step 6: Run `cd backend && pytest tests/test_therapy_engine.py -k screen_prompt -v && pytest tests/test_therapy_api_executor_lifecycle.py -k screen_prompt -v` and confirm red**

### Task 2: Backend plan model support

**Files:**
- Modify: `backend/models/therapy.py`

- [ ] **Step 1: Add a focused plan-level screen-prompt model with required `start_second`, `end_second`, `title`, and `lines` fields**
- [ ] **Step 2: Extend `TherapyPlan` to carry optional validated `screen_prompts`**
- [ ] **Step 3: Parse raw YAML timeline data and invalidate the whole prompt group when any rule fails**
- [ ] **Step 4: Keep `to_dict` and `from_dict` serialization consistent with the validated timeline field**
- [ ] **Step 5: Re-run `cd backend && pytest tests/test_therapy_engine.py -k screen_prompt -v && pytest tests/test_therapy_api_executor_lifecycle.py -k screen_prompt -v` and confirm green**

## Chunk 2: Expose Validated Timelines And Seed Plan Content

### Task 3: API payload coverage

**Files:**
- Create: `backend/tests/test_therapy_screen_prompts_api.py`
- Modify: `backend/api/therapy.py`

- [ ] **Step 1: Add a failing API contract test that monkeypatches `backend.api.therapy.get_plan_manager` to return a fake manager with a known valid plan, then asserts `get_plan(plan_id)` returns the exact ordered `screen_prompts` payload shape (`start_second`, `end_second`, `title`, `lines`) alongside the existing `id`, `duration`, and `phases` fields**
- [ ] **Step 2: Add failing API contract tests for the two fallback cases: a plan with no `screen_prompts` configured omits the `screen_prompts` field entirely, and a plan loaded from a temporary invalid YAML timeline also omits the field entirely instead of returning `[]`, `None`, or partial entries**
- [ ] **Step 3: Run `cd backend && pytest tests/test_therapy_screen_prompts_api.py -v` and confirm red**
- [ ] **Step 4: Extend the plan-detail response in `backend/api/therapy.py` to include `screen_prompts` only when the backend model exposes a valid validated group, while preserving all unrelated response fields and prompt ordering**
- [ ] **Step 5: Re-run `cd backend && pytest tests/test_therapy_screen_prompts_api.py -v` and confirm green**

### Task 4: Seed first-batch YAML timelines

**Files:**
- Modify: `content/plans/anxiety_relief_chinese.yaml`
- Modify: `content/plans/anger_release_modern.yaml`
- Modify: `content/plans/depression_relief_chinese.yaml`
- Modify: `content/plans/emotional_balance_chinese.yaml`

- [ ] **Step 1: Add plan-specific 15-minute `screen_prompts` timelines to `content/plans/anxiety_relief_chinese.yaml` and `content/plans/anger_release_modern.yaml`, each covering `[0, 900)` continuously without reusing or scaling the 20-minute timeline**
- [ ] **Step 2: Add plan-specific 20-minute `screen_prompts` timelines to `content/plans/depression_relief_chinese.yaml` and `content/plans/emotional_balance_chinese.yaml`, each covering `[0, 1200)` continuously and using the approved 20-minute stage boundaries from the spec-backed design**
- [ ] **Step 3: Keep all other plan YAML files on fallback behavior by leaving them without `screen_prompts`**
- [ ] **Step 4: Run `cd backend && pytest tests/test_therapy_engine.py -k screen_prompt -v && pytest tests/test_therapy_screen_prompts_api.py -v` and confirm the seeded YAML stays valid**

## Chunk 3: Hydrate Full Plan Data Before Therapy Starts

### Task 5: Frontend typing and normalization

**Files:**
- Modify: `app/src/types/index.ts`
- Modify: `app/src/stores/session.ts`
- Create: `app/tests/therapyScreenPromptsFlow.test.cjs`

- [ ] **Step 1: Add a failing frontend test that `normalizeTherapyPlan` accepts backend `screen_prompts` and frontend `screenPrompts` inputs, but always outputs one canonical camelCase `screenPrompts` array on the normalized `TherapyPlan` object**
- [ ] **Step 2: Add a failing frontend test that `currentPlan.value.screenPrompts` and `currentSession.value.planUsed.screenPrompts` survive `startSession` normalization without retaining a `screen_prompts` key**
- [ ] **Step 3: Run `cd app && node --test tests/therapyScreenPromptsFlow.test.cjs` and confirm red**
- [ ] **Step 4: Add `TherapyScreenPrompt` typing and normalize each prompt entry into `{ startSecond, endSecond, title, lines }`, keeping the frontend store contract camelCase-only after ingestion**
- [ ] **Step 5: Re-run `cd app && node --test tests/therapyScreenPromptsFlow.test.cjs` and confirm green**

### Task 6: Fetch detailed plan data before entering therapy

**Files:**
- Modify: `app/src/api/index.ts`
- Modify: `app/src/components/entry/AssessmentEntryPanel.vue`
- Modify: `app/src/stores/session.ts`
- Modify: `app/tests/therapyScreenPromptsFlow.test.cjs`

- [ ] **Step 1: Add a failing frontend test that `AssessmentEntryPanel.vue` awaits `therapyApi.getPlanDetail(recommendedPlan.value.id)` before `sessionStore.startSession(...)` and `router.push('/therapy')`, and passes the hydrated detail plan into `startSession` instead of the summary-only recommendation object**
- [ ] **Step 2: Add failing frontend tests that only these entry-flow fallback triggers may bypass detail hydration: `recommendedPlan.value.id` is missing, the detail fetch rejects, or the detail payload is missing any of the required hydrated-plan fields `id`, `style`, `intensity`, `duration`, or `phases`; also assert that absent or malformed `screen_prompts` do not trigger summary-plan fallback and instead continue with the hydrated plan so the therapy page can fall back later**
- [ ] **Step 3: Run `cd app && node --test tests/therapyScreenPromptsFlow.test.cjs tests/assessmentPageManualFlow.test.cjs` and confirm red**
- [ ] **Step 4: Update the plan-detail API helper and `startTherapy` flow so the page fetches detail by `planId`, starts the session with the hydrated plan when it contains the required fields from Step 2, preserves hydrated plans even when `screen_prompts` is absent or malformed, and only falls back to the existing summary plan on the explicit non-prompt triggers from Step 2**
- [ ] **Step 5: Re-run `cd app && node --test tests/therapyScreenPromptsFlow.test.cjs tests/assessmentPageManualFlow.test.cjs` and confirm green**

## Chunk 4: Render Active Prompts On The Therapy Page

### Task 7: Therapy page prompt rendering and fallback

**Files:**
- Modify: `app/src/views/TherapyPage.vue`
- Modify: `app/tests/therapyScreenPromptsFlow.test.cjs`

- [ ] **Step 1: Add a failing frontend test that an active `currentPlan.value.screenPrompts` entry takes precedence over the old phase-name display for the red-box content area**
- [ ] **Step 2: Add a failing frontend test for exact `[startSecond, endSecond)` boundary behavior at `0`, `endSecond - 1`, and `endSecond`, proving the prompt switches to the next segment exactly at the boundary with no overlap or gap**
- [ ] **Step 3: Add a failing frontend test that multi-line guidance renders one DOM node per prompt line (for example, repeated `.therapy-page__prompt-line` elements) so line breaks are preserved instead of collapsed into one sentence**
- [ ] **Step 4: Add a failing frontend test that fallback stays on the existing stage display for all three branches: `screenPrompts` absent, `screenPrompts` malformed in frontend state, and summary-only not-hydrated plan data**
- [ ] **Step 5: Add a failing frontend test that pause holds the current prompt while resume continues prompt progression from the resumed `elapsedTime`**
- [ ] **Step 6: Run `cd app && node --test tests/therapyScreenPromptsFlow.test.cjs tests/therapyResumeStateFlow.test.cjs` and confirm red**
- [ ] **Step 7: In `TherapyPage.vue`, derive prompt data from `currentPlan.value?.screenPrompts`, validate the group defensively on the frontend, and compute `activeScreenPrompt` from `elapsedTime` using `[startSecond, endSecond)` matching**
- [ ] **Step 8: Render the prompt title plus repeated prompt-line nodes when `activeScreenPrompt` exists; otherwise keep the existing phase label and `currentPhase?.name || $t('common.loading')` fallback path unchanged**
- [ ] **Step 9: Keep layout width, controls, music behavior, stop flow, and intensity controls unchanged; if prompt styling is needed, limit it to the new prompt text container and line classes**
- [ ] **Step 10: Re-run `cd app && node --test tests/therapyScreenPromptsFlow.test.cjs tests/therapyPageLayoutParity.test.cjs tests/therapyResumeStateFlow.test.cjs tests/therapyStopNowFlow.test.cjs` and confirm green**

## Chunk 5: End-To-End Verification

### Task 8: Regression and type verification

**Files:**
- Modify as needed based on failures

- [ ] **Step 1: Run backend regression commands**
  - `cd backend && pytest tests/test_therapy_engine.py -k screen_prompt -v`
  - `cd backend && pytest tests/test_therapy_screen_prompts_api.py -v`
- [ ] **Step 2: Run frontend regression commands**
  - `cd app && node --test tests/therapyScreenPromptsFlow.test.cjs tests/assessmentPageManualFlow.test.cjs tests/therapyPageLayoutParity.test.cjs tests/therapyResumeStateFlow.test.cjs tests/therapyStopNowFlow.test.cjs`
- [ ] **Step 3: Run frontend type and build verification**
  - `cd app && npx vue-tsc --noEmit`
  - `cd app && npm run build`
- [ ] **Step 4: Start the local stack for manual verification**
  - `cd backend && uvicorn main:app --reload`
  - `cd app && npm run dev`
- [ ] **Step 5: Manually verify the seeded scenarios in the web client with explicit pass criteria**
  - Scenario A: use the manual emotion fallback to reach the result page with an `anxious` recommendation, confirm the displayed plan is `anxiety_relief_chinese`, start therapy, and verify the red-box area shows prompt title plus multi-line guidance at `00:00`, then changes at a configured timeline boundary, and stays frozen while paused
  - Scenario B: repeat with a `sad` recommendation, confirm the displayed plan is `depression_relief_chinese`, start therapy, and verify the prompt timeline follows the 20-minute plan's own stages rather than the 15-minute timing
  - Scenario C: repeat with a `tired` recommendation, confirm the displayed plan is `fatigue_recovery`, start therapy, and verify the page stays on the existing stage display with no prompt-title or prompt-line block because that plan intentionally has no `screen_prompts`
  - Invalid-data release gate: before sign-off, confirm the invalid-YAML API contract case from `backend/tests/test_therapy_screen_prompts_api.py` and the malformed-frontend-state fallback case from `app/tests/therapyScreenPromptsFlow.test.cjs` both pass, since the seeded manual catalog intentionally contains only valid YAML
  - Pass only if all three scenarios render without console errors, the browser devtools console stays clean during each run, prompt transitions match the intended branch, and therapy start, pause, and stop flows still work normally
