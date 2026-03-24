# Therapy Next Track Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a therapy-page `Next Track` button that switches the current background music to the next entry from the shared audio manifest.

**Architecture:** Extend the existing device audio API with a minimal `next` action that derives the next BGM file from the current player status and the shared audio manifest. Keep the frontend thin by calling the existing backend from the therapy page and reusing the current control layout.

**Tech Stack:** FastAPI, Pydantic, Vue 3, Pinia, TypeScript, pytest

---

## Chunk 1: Backend API behavior

### Task 1: Add failing API coverage for next-track selection

**Files:**
- Create: `backend/tests/test_device_audio_next_track.py`
- Modify: `backend/api/device.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_audio_next_switches_to_next_manifest_file(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_device_audio_next_track.py -q`
Expected: FAIL because the `next` action is not implemented.

- [ ] **Step 3: Write minimal implementation**

Implement manifest loading and `next` action handling in `backend/api/device.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_device_audio_next_track.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_device_audio_next_track.py backend/api/device.py
git commit -m "feat: add therapy next track audio action"
```

### Task 2: Add wraparound coverage

**Files:**
- Modify: `backend/tests/test_device_audio_next_track.py`
- Modify: `backend/api/device.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_audio_next_wraps_to_first_manifest_file(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_device_audio_next_track.py -q`
Expected: FAIL because wraparound is missing or incorrect.

- [ ] **Step 3: Write minimal implementation**

Ensure manifest traversal wraps to index `0` after the last file.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_device_audio_next_track.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_device_audio_next_track.py backend/api/device.py
git commit -m "test: cover next track wraparound"
```

## Chunk 2: Frontend control

### Task 3: Add frontend API call and button

**Files:**
- Modify: `app/src/api/index.ts`
- Modify: `app/src/views/TherapyPage.vue`
- Modify: `app/src/i18n/locales/zh.ts`
- Modify: `app/src/i18n/locales/en.ts`

- [ ] **Step 1: Write the failing type-level/use-site change**

Add the new frontend call site first so TypeScript reports the missing API shape.

- [ ] **Step 2: Run check to verify it fails**

Run: `cmd /c "cd /d D:\\liaoyu\\ai-liaoyu\\.worktrees\\therapy-next-track\\app && npx vue-tsc --noEmit"`
Expected: FAIL because the audio action helper does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add the device audio API helper and a new therapy-page button that invokes it.

- [ ] **Step 4: Run check to verify it passes**

Run: `cmd /c "cd /d D:\\liaoyu\\ai-liaoyu\\.worktrees\\therapy-next-track\\app && npx vue-tsc --noEmit"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/src/api/index.ts app/src/views/TherapyPage.vue app/src/i18n/locales/zh.ts app/src/i18n/locales/en.ts
git commit -m "feat: add therapy page next track control"
```

## Chunk 3: Verification

### Task 4: Run focused verification

**Files:**
- Modify: none

- [ ] **Step 1: Run backend tests**

Run: `backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_device_audio_next_track.py -q`
Expected: PASS

- [ ] **Step 2: Run frontend type-check**

Run: `cmd /c "cd /d D:\\liaoyu\\ai-liaoyu\\.worktrees\\therapy-next-track\\app && npx vue-tsc --noEmit"`
Expected: PASS

- [ ] **Step 3: Summarize constraints**

Note that phase transitions still override manual track selection by design.
