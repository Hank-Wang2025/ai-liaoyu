# Therapy Fast Stop Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `stop-now` path that immediately stops chair, audio, and lights without blocking the UI on session finalization or report generation.

**Architecture:** Introduce a new backend `stop-now` endpoint for immediate device stop, keep session/report finalization asynchronous, and let the frontend navigate to the report page immediately while polling for finalized backend data.

**Tech Stack:** FastAPI, Python asyncio, Vue 3, Pinia, TypeScript, node:test, pytest

---

## Chunk 1: Backend Stop-Now API

### Task 1: Add failing backend coverage for the dedicated fast-stop path

**Files:**
- Modify: `backend/tests/test_therapy_api_executor_lifecycle.py`
- Modify: `backend/api/therapy.py`
- Modify: `backend/services/therapy_executor.py`

- [ ] **Step 1: Write a failing pytest covering `POST /api/therapy/stop-now/{session_id}`**
- [ ] **Step 2: Run the targeted pytest and verify it fails for missing endpoint or behavior**
- [ ] **Step 3: Add the new API route in `backend/api/therapy.py`**
- [ ] **Step 4: Add a minimal executor/device stop helper in `backend/services/therapy_executor.py` if needed**
- [ ] **Step 5: Make the new endpoint idempotent for repeated stop requests**
- [ ] **Step 6: Run the targeted pytest and verify it passes**

### Task 2: Ensure fast-stop does not block on full finalization

**Files:**
- Modify: `backend/tests/test_therapy_api_executor_lifecycle.py`
- Modify: `backend/api/therapy.py`

- [ ] **Step 1: Add a failing pytest proving `stop-now` schedules finalization instead of waiting for it**
- [ ] **Step 2: Run the targeted pytest and verify it fails**
- [ ] **Step 3: Schedule background finalization work from the stop endpoint**
- [ ] **Step 4: Keep the existing end/finalize path usable for background completion**
- [ ] **Step 5: Run the targeted pytest and verify it passes**

## Chunk 2: Frontend Stop Flow

### Task 3: Add failing frontend regression coverage for single-tap stop

**Files:**
- Create: `app/tests/therapyStopNowFlow.test.cjs`
- Modify: `app/src/api/index.ts`
- Modify: `app/src/stores/session.ts`
- Modify: `app/src/views/TherapyPage.vue`

- [ ] **Step 1: Write a failing regression test asserting TherapyPage no longer depends on a confirmation modal for stop**
- [ ] **Step 2: Run `node --test app/tests/therapyStopNowFlow.test.cjs` and verify it fails**
- [ ] **Step 3: Add a `stopNow` API client in `app/src/api/index.ts`**
- [ ] **Step 4: Add store support for local stop state plus background finalization tracking**
- [ ] **Step 5: Update `app/src/views/TherapyPage.vue` to call `stopNow`, disable controls, and route immediately**
- [ ] **Step 6: Run `node --test app/tests/therapyStopNowFlow.test.cjs` and verify it passes**

## Chunk 3: Report Refresh Behavior

### Task 4: Add failing coverage for local-first report rendering with backend refresh

**Files:**
- Create: `app/tests/reportPollingFlow.test.cjs`
- Modify: `app/src/views/ReportPage.vue`
- Modify: `app/src/stores/session.ts`

- [ ] **Step 1: Write a failing regression test for bounded report polling**
- [ ] **Step 2: Run `node --test app/tests/reportPollingFlow.test.cjs` and verify it fails**
- [ ] **Step 3: Make the report page render local summary immediately**
- [ ] **Step 4: Add bounded polling for finalized backend report data**
- [ ] **Step 5: Preserve fallback rendering if backend data never arrives**
- [ ] **Step 6: Run `node --test app/tests/reportPollingFlow.test.cjs` and verify it passes**

## Chunk 4: Final Verification

### Task 5: Verify backend and frontend paths together

**Files:**
- Modify: `backend/tests/test_therapy_api_executor_lifecycle.py`
- Modify: `app/tests/therapyStopNowFlow.test.cjs`
- Modify: `app/tests/reportPollingFlow.test.cjs`
- Modify: `app/src/api/index.ts`
- Modify: `app/src/stores/session.ts`
- Modify: `app/src/views/TherapyPage.vue`
- Modify: `app/src/views/ReportPage.vue`

- [ ] **Step 1: Run targeted backend pytest for the lifecycle tests**
- [ ] **Step 2: Run all targeted frontend node tests for stop/report behavior**
- [ ] **Step 3: Run `cmd /c npx vue-tsc --noEmit`**
- [ ] **Step 4: Review the diff to confirm stop flow is now single-tap and local-first**

