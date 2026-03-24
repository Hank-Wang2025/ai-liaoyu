# Five-Level Hidden Intensity Model Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Keep the current `更放松 / 更有力` UI unchanged while upgrading the runtime chair intensity model from a visible 3-state model to an internal 5-level hidden model.

**Architecture:** The backend remains the source of truth for runtime chair intensity and stores a hidden `runtime_intensity_level` on the active plan/session flow. The frontend continues to render only implicit controls, but uses the hidden level to decide boundary states without exposing numeric levels to users. Existing `low / medium / high` values stay as compatibility metadata and initial mapping only.

**Tech Stack:** FastAPI, Python, pytest, Vue 3, Pinia, TypeScript, node:test

---

## Chunk 1: Lock The New 5-Level Behavior With Tests

### Task 1: Backend runtime intensity tests

**Files:**
- Modify: `backend/tests/test_therapy_runtime_intensity_adjustment.py`
- Modify: `backend/tests/test_therapy_api_executor_lifecycle.py`

- [x] **Step 1: Write failing backend tests for hidden 5-level runtime intensity**
- [x] **Step 2: Assert one click changes exactly one internal level**
- [x] **Step 3: Assert plan response keeps UI-compatible fields but includes hidden runtime level**
- [x] **Step 4: Run targeted pytest and confirm red**

## Chunk 2: Implement Backend 5-Level Runtime Model

### Task 2: Add hidden runtime level to plan adjustment flow

**Files:**
- Modify: `backend/api/therapy.py`
- Modify: `backend/services/therapy_executor.py`
- Modify: `backend/models/therapy.py` (only if response serialization needs a field)

- [x] **Step 1: Introduce runtime level mapping helpers (`low->1`, `medium->3`, `high->5`)**
- [x] **Step 2: Store and update active runtime level independently from compatibility intensity label**
- [x] **Step 3: Make `relax/intensify` move exactly one hidden level per click**
- [x] **Step 4: Keep chair hardware application based on hidden 5-level model**
- [x] **Step 5: Serialize hidden runtime level for frontend boundary logic without displaying it**
- [x] **Step 6: Run backend tests and confirm green**

## Chunk 3: Update Frontend Boundary Logic Without Changing UI

### Task 3: Frontend hidden-level compatibility

**Files:**
- Modify: `app/src/types/index.ts`
- Modify: `app/src/stores/session.ts`
- Modify: `app/src/views/TherapyPage.vue`
- Modify: `app/tests/therapyIntensityControlsFlow.test.cjs`

- [x] **Step 1: Write failing frontend test for hidden runtime level support**
- [x] **Step 2: Extend frontend plan typing/normalization to carry hidden runtime level**
- [x] **Step 3: Switch button boundary logic from 3 labels to 5-level hidden state**
- [x] **Step 4: Keep UI copy and layout unchanged**
- [x] **Step 5: Run node tests and confirm green**

## Chunk 4: Regression Verification

### Task 4: Verify therapy controls and stop flow still work

**Files:**
- Modify as needed based on failures

- [x] **Step 1: Run backend regression suite for runtime intensity and executor lifecycle**
- [x] **Step 2: Run frontend control-flow tests**
- [x] **Step 3: Restart frontend/backend for manual verification**
