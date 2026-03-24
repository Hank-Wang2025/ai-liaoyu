# Assessment Manual Emotion Fallback Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an inline manual emotion-selection fallback to the assessment page when microphone capture is unavailable or permission is denied.

**Architecture:** Keep the existing voice-first assessment flow, but introduce an explicit `manual` state inside `AssessmentPage.vue` so microphone failures no longer auto-create a neutral emotion. Extract the manual emotion presets into a small utility module for testability, keep the UI inline on the existing page, and reuse the current plan-matching/result flow after the user confirms a manual choice.

**Tech Stack:** Vue 3, TypeScript, Pinia, vue-i18n, Node built-in test runner, vue-tsc

**Local-only note:** The user asked to keep changes local and not create Git commits. Replace commit steps with local diff/status checkpoints.

---

## File Structure

- Create: `app/src/utils/assessmentManualFallback.ts`
  - Own the six allowed manual emotions and the fixed intensity/valence/arousal presets.
  - Export a helper that builds a standard `EmotionState` from a manual selection.
- Modify: `app/src/views/AssessmentPage.vue`
  - Add the `manual` step, inline fallback UI, retry action, single-select state, and continue action.
  - Stop routing microphone failures into the old direct-neutral fallback path.
- Modify: `app/src/i18n/locales/zh.ts`
  - Add assessment fallback strings without corrupting file encoding.
- Modify: `app/src/i18n/locales/en.ts`
  - Add matching English fallback strings.
- Create: `app/tests/assessmentManualFallback.test.ts`
  - Verify the manual preset helper returns the approved six emotions and fixed intensity defaults.
- Create: `app/tests/assessmentPageManualFlow.test.cjs`
  - Source-level regression guard for the new `manual` state and inline fallback wiring in `AssessmentPage.vue`.
- Create: `app/tests/assessmentManualLocale.test.cjs`
  - Source-level smoke test for the new assessment locale keys in `zh.ts` and `en.ts`.

## Chunk 1: Manual preset foundation

### Task 1: Extract the manual emotion presets into a testable helper

**Files:**
- Create: `app/src/utils/assessmentManualFallback.ts`
- Create: `app/tests/assessmentManualFallback.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import assert from 'node:assert/strict'
import test from 'node:test'

import {
  MANUAL_FALLBACK_OPTIONS,
  buildManualEmotionState,
} from '../src/utils/assessmentManualFallback.ts'

test('manual fallback exposes the six approved emotions', () => {
  assert.deepEqual(
    MANUAL_FALLBACK_OPTIONS.map((option) => option.category),
    ['happy', 'neutral', 'anxious', 'angry', 'sad', 'tired'],
  )
})

test('buildManualEmotionState uses fixed intensity and presets', () => {
  const state = buildManualEmotionState('angry', new Date('2026-03-17T00:00:00Z'))

  assert.equal(state.intensity, 0.5)
  assert.equal(state.valence, -0.7)
  assert.equal(state.arousal, 0.85)
  assert.equal(state.confidence, 0.8)
  assert.equal(state.category, 'angry')
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node --experimental-strip-types tests\assessmentManualFallback.test.ts"`
Expected: FAIL because `assessmentManualFallback.ts` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```ts
import type { EmotionCategory, EmotionState } from '@/types'

export interface ManualFallbackOption {
  category: Extract<EmotionCategory, 'happy' | 'neutral' | 'anxious' | 'angry' | 'sad' | 'tired'>
}

const MANUAL_PRESETS = {
  happy: { valence: 0.7, arousal: 0.6 },
  neutral: { valence: 0.0, arousal: 0.4 },
  anxious: { valence: -0.6, arousal: 0.8 },
  angry: { valence: -0.7, arousal: 0.85 },
  sad: { valence: -0.7, arousal: 0.3 },
  tired: { valence: -0.4, arousal: 0.2 },
} as const

export const MANUAL_FALLBACK_OPTIONS: ManualFallbackOption[] = [
  { category: 'happy' },
  { category: 'neutral' },
  { category: 'anxious' },
  { category: 'angry' },
  { category: 'sad' },
  { category: 'tired' },
]

export function buildManualEmotionState(category: ManualFallbackOption['category'], timestamp = new Date()): EmotionState {
  const preset = MANUAL_PRESETS[category]
  return {
    category,
    intensity: 0.5,
    valence: preset.valence,
    arousal: preset.arousal,
    confidence: 0.8,
    timestamp,
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node --experimental-strip-types tests\assessmentManualFallback.test.ts"`
Expected: PASS

- [ ] **Step 5: Record a local checkpoint**

Run: `git diff -- app/src/utils/assessmentManualFallback.ts app/tests/assessmentManualFallback.test.ts`
Expected: Only the helper and its test appear in the diff.

## Chunk 2: Assessment page fallback behavior

### Task 2: Add a regression guard for the inline manual state and wire the UI

**Files:**
- Create: `app/tests/assessmentPageManualFlow.test.cjs`
- Modify: `app/src/views/AssessmentPage.vue`
- Modify: `app/src/utils/assessmentManualFallback.ts`

- [ ] **Step 1: Write the failing regression test**

```js
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')

test('assessment page wires the inline manual fallback state', () => {
  const file = path.join(__dirname, '..', 'src', 'views', 'AssessmentPage.vue')
  const content = fs.readFileSync(file, 'utf8')

  assert.ok(content.includes("ref<'voice' | 'manual' | 'analyzing' | 'result'>('voice')"))
  assert.ok(content.includes("const selectedManualEmotion = ref<EmotionCategory | null>(null)"))
  assert.ok(content.includes("const showManualFallback = ("))
  assert.ok(content.includes("const retryMicrophone = async () => {"))
  assert.ok(content.includes("const continueWithManualEmotion = async () => {"))
  assert.ok(content.includes("step === 'manual'"))
})
```

- [ ] **Step 2: Run the regression test to verify it fails**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentPageManualFlow.test.cjs"`
Expected: FAIL because `AssessmentPage.vue` does not have a `manual` state or retry/manual handlers yet.

- [ ] **Step 3: Write the minimal implementation**

Update `app/src/views/AssessmentPage.vue` to:

```ts
import { computed, ref } from 'vue'
import {
  MANUAL_FALLBACK_OPTIONS,
  buildManualEmotionState,
} from '@/utils/assessmentManualFallback'

const step = ref<'voice' | 'manual' | 'analyzing' | 'result'>('voice')
const manualFallbackReason = ref<string | null>(null)
const selectedManualEmotion = ref<EmotionCategory | null>(null)

const showManualFallback = (message: string) => {
  isRecording.value = false
  manualFallbackReason.value = message
  selectedManualEmotion.value = null
  step.value = 'manual'
}

const retryMicrophone = async () => {
  manualFallbackReason.value = null
  await toggleRecording()
}

const continueWithManualEmotion = async () => {
  if (!selectedManualEmotion.value) return
  emotionResult.value = buildManualEmotionState(selectedManualEmotion.value)
  await matchPlan(
    emotionResult.value.category,
    emotionResult.value.intensity,
    emotionResult.value.valence,
    emotionResult.value.arousal,
  )
  step.value = 'result'
}
```

Then change the template so the voice area has an inline `manual` branch that shows:
- the fallback message
- a `Retry Microphone` button
- six single-select emotion buttons sourced from `MANUAL_FALLBACK_OPTIONS`
- a continue button disabled when `selectedManualEmotion` is `null`

Finally, replace microphone unsupported/denied branches inside `toggleRecording()` so they call `showManualFallback(...)` instead of immediately calling `fallbackAnalysis(...)`.

- [ ] **Step 4: Run the regression test and type-check**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentPageManualFlow.test.cjs && node_modules\.bin\vue-tsc.cmd --noEmit"`
Expected: PASS

- [ ] **Step 5: Record a local checkpoint**

Run: `git diff -- app/src/views/AssessmentPage.vue app/tests/assessmentPageManualFlow.test.cjs app/src/utils/assessmentManualFallback.ts`
Expected: The diff shows only the manual fallback UI/state changes and related guard.

## Chunk 3: Localization and focused verification

### Task 3: Add locale smoke coverage for the new assessment fallback strings

**Files:**
- Create: `app/tests/assessmentManualLocale.test.cjs`
- Modify: `app/src/i18n/locales/zh.ts`
- Modify: `app/src/i18n/locales/en.ts`

- [ ] **Step 1: Write the failing locale smoke test**

```js
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')

function readLocale(name) {
  return fs.readFileSync(path.join(__dirname, '..', 'src', 'i18n', 'locales', name), 'utf8')
}

test('assessment manual fallback locale keys exist in zh and en', () => {
  const zh = readLocale('zh.ts')
  const en = readLocale('en.ts')

  for (const content of [zh, en]) {
    assert.ok(content.includes('manualFallbackTitle'))
    assert.ok(content.includes('manualFallbackPrompt'))
    assert.ok(content.includes('retryMicrophone'))
    assert.ok(content.includes('manualContinue'))
  }
})
```

- [ ] **Step 2: Run the locale smoke test to verify it fails**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentManualLocale.test.cjs"`
Expected: FAIL because the new assessment locale keys are missing.

- [ ] **Step 3: Write the minimal locale implementation**

Add these keys under `assessment` in both locale files:

```ts
manualFallbackTitle: '手动选择情绪'
manualFallbackPrompt: '麦克风不可用，请选择你现在最接近的感受'
retryMicrophone: '重试麦克风'
manualContinue: '继续'
microphoneUnavailable: '当前环境不支持麦克风录音，已切换为手动选择'
microphoneDenied: '无法访问麦克风，你可以重试或手动选择情绪'
```

English equivalents:

```ts
manualFallbackTitle: 'Manual Emotion Selection'
manualFallbackPrompt: 'Microphone is unavailable. Choose the emotion closest to how you feel now.'
retryMicrophone: 'Retry Microphone'
manualContinue: 'Continue'
microphoneUnavailable: 'Microphone recording is not supported in this environment. Switched to manual selection.'
microphoneDenied: 'Microphone access failed. You can retry or choose an emotion manually.'
```

When editing `zh.ts`, preserve encoding carefully so Chinese strings do not turn into `?` again.

- [ ] **Step 4: Run the locale smoke test and type-check**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentManualLocale.test.cjs && node_modules\.bin\vue-tsc.cmd --noEmit"`
Expected: PASS

- [ ] **Step 5: Record a local checkpoint**

Run: `git diff -- app/src/i18n/locales/zh.ts app/src/i18n/locales/en.ts app/tests/assessmentManualLocale.test.cjs`
Expected: Only the new assessment fallback keys and locale smoke test appear.

### Task 4: Run focused verification

**Files:**
- Modify: none

- [ ] **Step 1: Run the helper test**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node --experimental-strip-types tests\assessmentManualFallback.test.ts"`
Expected: PASS

- [ ] **Step 2: Run the source-level UI regression test**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentPageManualFlow.test.cjs"`
Expected: PASS

- [ ] **Step 3: Run the locale smoke test**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentManualLocale.test.cjs"`
Expected: PASS

- [ ] **Step 4: Run the frontend type-check**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node_modules\.bin\vue-tsc.cmd --noEmit"`
Expected: PASS

- [ ] **Step 5: Manually verify the desktop flow**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && npm run electron:dev"`
Expected manual checks:
- deny microphone permission and confirm the inline manual picker appears
- click `Retry Microphone` and confirm success returns to voice mode
- click `Retry Microphone` and deny again to confirm manual mode persists
- pick each emotion and confirm the continue button only enables after a selection
- continue into the result page and confirm therapy can still start

- [ ] **Step 6: Record the final local checkpoint**

Run: `git status --short`
Expected: Only the intended local files for this feature are modified/created.
