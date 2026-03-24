# Unified Entry Start/Continue Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the split welcome/assessment entry with one unified landing page that supports both starting a new assessment and continuing an unfinished therapy session from a client-side resume snapshot.

**Architecture:** Extract the assessment UI into a reusable entry component, add a focused local resume-snapshot utility plus Pinia store orchestration, and let `WelcomePage.vue` become the unified entry shell. Resume stays client-snapshot-first and uses the existing backend session endpoint only to validate that the saved session still exists before routing back into `TherapyPage`.

**Tech Stack:** Vue 3, Pinia, TypeScript, Vue Router, Vue I18n, Axios, node:test

---

## File Structure

- Create: `app/src/components/entry/AssessmentEntryPanel.vue` - reusable assessment/manual-fallback/recommendation/start panel extracted from `AssessmentPage.vue`
- Create: `app/src/components/entry/ResumeSessionCard.vue` - focused continue-session card with disabled/active/error states
- Create: `app/src/utils/sessionResume.ts` - local resume snapshot persistence, validation, load, and clear helpers
- Modify: `app/src/stores/session.ts` - own resume snapshot lifecycle, expose resume helpers, hydrate local session state for continue flow
- Modify: `app/src/api/index.ts` - add a small session validation client using `GET /session/{session_id}`
- Modify: `app/src/types/index.ts` - add resume snapshot/client resume types if needed
- Modify: `app/src/views/WelcomePage.vue` - turn into the unified entry container
- Modify: `app/src/views/AssessmentPage.vue` - keep as a thin compatibility wrapper around the extracted assessment panel or redirect-safe shell
- Modify: `app/src/router/index.ts` - keep `/` as the main entry, preserve `/assessment` compatibility intentionally
- Modify: `app/src/i18n/locales/zh.ts`
- Modify: `app/src/i18n/locales/en.ts`
- Create: `app/tests/sessionResume.test.ts`
- Create: `app/tests/sessionResumeStoreFlow.test.cjs`
- Create: `app/tests/unifiedEntryPageFlow.test.cjs`
- Create: `app/tests/resumeSessionEntryFlow.test.cjs`
- Modify: `app/tests/assessmentPageManualFlow.test.cjs`
- Modify: `app/tests/assessmentManualLocale.test.cjs`

Note: do not add commit steps while executing this plan; the user explicitly asked for local-only changes with no git commit.

## Chunk 1: Resume Snapshot Infrastructure

### Task 1: Add real helper coverage for local resume snapshot persistence

**Files:**
- Create: `app/tests/sessionResume.test.ts`
- Create: `app/src/utils/sessionResume.ts`

- [ ] **Step 1: Write the failing utility test for save/load/clear behavior**

```ts
import assert from 'node:assert/strict'
import test from 'node:test'

import {
  clearResumeSnapshot,
  loadResumeSnapshot,
  saveResumeSnapshot,
} from '../src/utils/sessionResume.ts'

function createStorage() {
  const map = new Map<string, string>()
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => map.set(key, value),
    removeItem: (key: string) => map.delete(key),
  }
}

test('resume snapshot round-trips through storage', () => {
  const storage = createStorage()
  saveResumeSnapshot(
    {
      sessionId: 'session-1',
      planId: 'plan-1',
      planName: 'Plan 1',
      phaseIndex: 1,
      elapsedSeconds: 90,
      isPaused: false,
    },
    storage,
  )

  assert.deepEqual(loadResumeSnapshot(storage), {
    sessionId: 'session-1',
    planId: 'plan-1',
    planName: 'Plan 1',
    phaseIndex: 1,
    elapsedSeconds: 90,
    isPaused: false,
  })
})

test('invalid stored snapshot returns null and clear removes data', () => {
  const storage = createStorage()
  storage.setItem('therapy_resume_snapshot', '{"broken":true}')
  assert.equal(loadResumeSnapshot(storage), null)

  saveResumeSnapshot(
    {
      sessionId: 'session-2',
      planId: 'plan-2',
      planName: 'Plan 2',
      phaseIndex: 0,
      elapsedSeconds: 15,
      isPaused: true,
    },
    storage,
  )
  clearResumeSnapshot(storage)
  assert.equal(loadResumeSnapshot(storage), null)
})
```

- [ ] **Step 2: Run the utility test and verify it fails**

Run: `node --test app/tests/sessionResume.test.ts`

Expected: FAIL because `app/src/utils/sessionResume.ts` or exported functions do not exist yet.

- [ ] **Step 3: Implement the minimal snapshot helper**

Implementation notes:
- keep the storage key in one constant
- accept an optional storage argument for testability
- validate required fields before returning a snapshot
- swallow malformed JSON by returning `null`

- [ ] **Step 4: Re-run the utility test and verify it passes**

Run: `node --test app/tests/sessionResume.test.ts`

Expected: PASS

### Task 2: Wire the session store to persist and clear resume snapshots

**Files:**
- Create: `app/tests/sessionResumeStoreFlow.test.cjs`
- Modify: `app/src/stores/session.ts`
- Modify: `app/src/types/index.ts`
- Modify: `app/tests/sessionFastEndFlow.test.cjs`

- [ ] **Step 1: Write the failing store regression test**

```js
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')

test('session store persists and clears resume snapshot around therapy lifecycle', () => {
  const file = path.join(__dirname, '..', 'src', 'stores', 'session.ts')
  const content = fs.readFileSync(file, 'utf8')

  assert.ok(content.includes('saveResumeSnapshot('))
  assert.ok(content.includes('loadResumeSnapshot('))
  assert.ok(content.includes('clearResumeSnapshot('))
  assert.ok(content.includes('async function resumeSavedSession()'))
  assert.ok(content.includes('clearResumeSnapshot()'))
})
```

- [ ] **Step 2: Run the store regression test and verify it fails**

Run: `node --test app/tests/sessionResumeStoreFlow.test.cjs app/tests/sessionFastEndFlow.test.cjs`

Expected: FAIL because the store does not yet import or call the resume helpers.

- [ ] **Step 3: Add minimal resume snapshot state to the store**

Implementation notes:
- add a store-facing snapshot type if `app/src/types/index.ts` needs one
- save snapshot when a session starts successfully (or falls back locally)
- expose `resumeSnapshot` or `hasResumableSession` computed state
- add `resumeSavedSession()` to hydrate `currentSession`, `currentPlan`, `backendSessionId`, `isPaused`, and `isTherapyActive`
- clear snapshot on `endSession()`, `resetSession()`, and any invalid-resume path

- [ ] **Step 4: Update the existing fast-end regression to reflect snapshot clearing**

Expected change:
- extend `app/tests/sessionFastEndFlow.test.cjs` so it also asserts `clearResumeSnapshot(` appears in the store end path

- [ ] **Step 5: Re-run the store regression tests and verify they pass**

Run: `node --test app/tests/sessionResumeStoreFlow.test.cjs app/tests/sessionFastEndFlow.test.cjs`

Expected: PASS

## Chunk 2: Unified Entry UI

### Task 3: Add failing coverage for the unified entry page structure

**Files:**
- Create: `app/tests/unifiedEntryPageFlow.test.cjs`
- Modify: `app/tests/assessmentPageManualFlow.test.cjs`
- Modify: `app/tests/assessmentManualLocale.test.cjs`

- [ ] **Step 1: Write the failing unified-entry regression test**

```js
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')

test('welcome page becomes the unified entry shell with start and continue cards', () => {
  const file = path.join(__dirname, '..', 'src', 'views', 'WelcomePage.vue')
  const content = fs.readFileSync(file, 'utf8')

  assert.ok(content.includes('AssessmentEntryPanel'))
  assert.ok(content.includes('ResumeSessionCard'))
  assert.ok(content.includes("entry.startNewAssessment"))
  assert.ok(content.includes("entry.continuePreviousSession"))
})
```

- [ ] **Step 2: Update the assessment regression to target the extracted component**

Expected test change:
- point `app/tests/assessmentPageManualFlow.test.cjs` at `app/src/components/entry/AssessmentEntryPanel.vue`
- keep the same assertions about the assessment/manual-fallback state machine

- [ ] **Step 3: Update locale regression expectations**

Expected test change:
- extend `app/tests/assessmentManualLocale.test.cjs` to also check:
  - `entry.startNewAssessment`
  - `entry.continuePreviousSession`
  - `entry.noResumableSession`
  - `entry.resumeFailed`

- [ ] **Step 4: Run the UI regression tests and verify they fail**

Run: `node --test app/tests/unifiedEntryPageFlow.test.cjs app/tests/assessmentPageManualFlow.test.cjs app/tests/assessmentManualLocale.test.cjs`

Expected: FAIL because the unified entry component structure and locale keys do not exist yet.

### Task 4: Refactor the entry UI without creating one oversized file

**Files:**
- Create: `app/src/components/entry/AssessmentEntryPanel.vue`
- Modify: `app/src/views/AssessmentPage.vue`
- Modify: `app/src/views/WelcomePage.vue`
- Modify: `app/src/i18n/locales/zh.ts`
- Modify: `app/src/i18n/locales/en.ts`
- Modify: `app/src/router/index.ts`

- [ ] **Step 1: Extract the current assessment flow into `AssessmentEntryPanel.vue`**

Implementation notes:
- move the voice/manual/analyzing/result state machine out of `AssessmentPage.vue`
- preserve the current manual fallback behavior and start-therapy action
- keep props/events minimal; prefer the component owning its own flow state

- [ ] **Step 2: Turn `AssessmentPage.vue` into a thin wrapper**

Implementation notes:
- render `AssessmentEntryPanel.vue` inside the existing page shell
- keep the file small so old route compatibility survives without duplicating logic

- [ ] **Step 3: Convert `WelcomePage.vue` into the unified entry container**

Implementation notes:
- keep the existing branding/header/background/language switch
- add two equal-level cards below the header
- mount `AssessmentEntryPanel.vue` in the new-assessment card area
- reserve a sibling area for `ResumeSessionCard.vue`
- ensure only one expandable section is open at a time

- [ ] **Step 4: Add the new locale keys**

Add keys in both locale files for:
- start new assessment
- continue previous session
- no resumable session
- resume failed / session invalid

- [ ] **Step 5: Keep router behavior intentional**

Implementation notes:
- leave `/` pointing to `WelcomePage.vue`
- keep `/assessment` as a compatibility route that renders the thin wrapper rather than silently breaking older navigation

- [ ] **Step 6: Re-run the unified-entry tests and verify they pass**

Run: `node --test app/tests/unifiedEntryPageFlow.test.cjs app/tests/assessmentPageManualFlow.test.cjs app/tests/assessmentManualLocale.test.cjs`

Expected: PASS

## Chunk 3: Continue Previous Session Flow

### Task 5: Add failing coverage for resume validation and direct continue routing

**Files:**
- Create: `app/tests/resumeSessionEntryFlow.test.cjs`
- Modify: `app/src/api/index.ts`
- Modify: `app/src/stores/session.ts`
- Create: `app/src/components/entry/ResumeSessionCard.vue`
- Modify: `app/src/views/WelcomePage.vue`

- [ ] **Step 1: Write the failing resume-entry regression test**

```js
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')

test('resume entry validates backend session before routing to therapy', () => {
  const api = fs.readFileSync(path.join(__dirname, '..', 'src', 'api', 'index.ts'), 'utf8')
  const store = fs.readFileSync(path.join(__dirname, '..', 'src', 'stores', 'session.ts'), 'utf8')
  const welcome = fs.readFileSync(path.join(__dirname, '..', 'src', 'views', 'WelcomePage.vue'), 'utf8')

  assert.ok(api.includes('getSession: async (sessionId: string)'))
  assert.ok(store.includes('async function validateResumeSession('))
  assert.ok(store.includes('async function resumeSavedSession()'))
  assert.ok(welcome.includes('await sessionStore.resumeSavedSession()'))
  assert.ok(welcome.includes("router.push('/therapy')"))
})
```

- [ ] **Step 2: Run the resume regression test and verify it fails**

Run: `node --test app/tests/resumeSessionEntryFlow.test.cjs`

Expected: FAIL because the validation API/store/welcome-page wiring does not exist yet.

### Task 6: Implement the continue-session card and backend validation path

**Files:**
- Modify: `app/src/api/index.ts`
- Modify: `app/src/stores/session.ts`
- Create: `app/src/components/entry/ResumeSessionCard.vue`
- Modify: `app/src/views/WelcomePage.vue`

- [ ] **Step 1: Add a small session validation API client**

Implementation notes:
- add `sessionApi.getSession(sessionId)` using `GET /session/{session_id}`
- keep it focused; do not add unrelated API wrappers

- [ ] **Step 2: Add store-level validation and hydration helpers**

Implementation notes:
- `validateResumeSession()` should:
  - load current snapshot
  - return false if snapshot is missing or malformed
  - call `sessionApi.getSession(sessionId)`
  - clear the local snapshot if backend validation fails
- `resumeSavedSession()` should:
  - validate first
  - hydrate `currentSession`, `currentPlan`, `backendSessionId`, `isPaused`, `isTherapyActive`
  - return a success/failure result that the entry page can react to

- [ ] **Step 3: Implement `ResumeSessionCard.vue`**

Implementation notes:
- show active/disabled states from the store
- render a short summary when snapshot exists
- expose a single click action that does not require a confirmation modal

- [ ] **Step 4: Wire the continue card into `WelcomePage.vue`**

Implementation notes:
- keep start and continue as equal-level cards
- on continue click, call `await sessionStore.resumeSavedSession()`
- on success, route directly to `/therapy`
- on failure, stay on the page and show the localized resume-failed message

- [ ] **Step 5: Re-run the resume regression test and verify it passes**

Run: `node --test app/tests/resumeSessionEntryFlow.test.cjs`

Expected: PASS

## Chunk 4: Final Verification

### Task 7: Verify the full unified-entry slice

**Files:**
- Modify as needed based on verification failures:
  - `app/src/components/entry/AssessmentEntryPanel.vue`
  - `app/src/components/entry/ResumeSessionCard.vue`
  - `app/src/views/WelcomePage.vue`
  - `app/src/views/AssessmentPage.vue`
  - `app/src/stores/session.ts`
  - `app/src/utils/sessionResume.ts`
  - `app/src/api/index.ts`
  - `app/src/i18n/locales/zh.ts`
  - `app/src/i18n/locales/en.ts`

- [ ] **Step 1: Run all unified-entry related node tests**

Run:

```bash
node --test \
  app/tests/sessionResume.test.ts \
  app/tests/sessionResumeStoreFlow.test.cjs \
  app/tests/unifiedEntryPageFlow.test.cjs \
  app/tests/resumeSessionEntryFlow.test.cjs \
  app/tests/assessmentPageManualFlow.test.cjs \
  app/tests/assessmentManualLocale.test.cjs
```

Expected: all PASS

- [ ] **Step 2: Run the type check**

Run: `cmd /c npx vue-tsc --noEmit`

Expected: exit code `0`

- [ ] **Step 3: Manually verify the unified entry in Electron dev mode**

Run: `npm run electron:dev`

Manual checks:
- `/` shows both start and continue cards
- no resumable session -> continue card is disabled with hint text
- start assessment still supports microphone fallback to manual emotion buttons
- resumable snapshot + valid backend session -> continue goes straight to `TherapyPage`
- invalid backend session -> continue stays on entry page and clears snapshot

- [ ] **Step 4: Review the diff against the approved spec**

Checklist:
- unified `/` entry page exists
- start and continue are equal priority
- client restart resume is local-snapshot-based
- backend restart is not required
- invalid resume degrades safely to starting again

