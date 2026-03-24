# Assessment Plan Summary Labels Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace raw therapy plan enum values on the assessment result card with readable Chinese labels and add strength/emotion/time metadata.

**Architecture:** Keep the change local to `AssessmentPage.vue`. Add one small formatter in the page script that maps plan style and intensity enums to Chinese labels and composes the existing `recommendedPlan.description` string. Lock the behavior with a source-level regression test.

**Tech Stack:** Vue 3, TypeScript, Node built-in test runner, vue-tsc

---

## File Structure

- Modify: `app/src/views/AssessmentPage.vue`
  - Add a small formatter for recommendation summary text.
  - Replace the raw string interpolation that currently exposes `best.style`.
- Modify: `app/tests/assessmentPageManualFlow.test.cjs`
  - Add a regression assertion for the formatter and the four Chinese labels.

## Chunk 1: Recommendation summary formatting

### Task 1: Add a failing regression test for the localized summary formatter

**Files:**
- Modify: `app/tests/assessmentPageManualFlow.test.cjs`

- [ ] **Step 1: Write the failing test**

```js
test('assessment page formats plan summary with localized style, intensity, emotion, and duration labels', () => {
  const file = path.join(__dirname, '..', 'src', 'views', 'AssessmentPage.vue')
  const content = fs.readFileSync(file, 'utf8')

  assert.ok(content.includes('const formatPlanSummary = ('))
  assert.ok(content.includes("styleLabels: Record<TherapyPlan['style'], string>"))
  assert.ok(content.includes("intensityLabels: Record<TherapyPlan['intensity'], string>"))
  assert.ok(content.includes('\\u98ce\\u683c'))
  assert.ok(content.includes('\\u5f3a\\u5ea6'))
  assert.ok(content.includes('\\u9002\\u7528\\u60c5\\u7eea'))
  assert.ok(content.includes('\\u65f6\\u957f'))
  assert.ok(content.includes('description: formatPlanSummary('))
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentPageManualFlow.test.cjs"`
Expected: FAIL because `AssessmentPage.vue` does not yet define `formatPlanSummary`.

- [ ] **Step 3: Write the minimal implementation**

Add a formatter inside `app/src/views/AssessmentPage.vue`:

```ts
const formatPlanSummary = (
  plan: Pick<TherapyPlan, 'style' | 'intensity' | 'duration'>,
  emotionCategory: EmotionCategory,
) => {
  const styleLabels: Record<TherapyPlan['style'], string> = {
    chinese: '\u4e2d\u5f0f\u7597\u6108',
    modern: '\u73b0\u4ee3\u7597\u6108',
  }
  const intensityLabels: Record<TherapyPlan['intensity'], string> = {
    low: '\u8f7b\u67d4',
    medium: '\u9002\u4e2d',
    high: '\u5f3a\u6548',
  }

  return `\u98ce\u683c: ${styleLabels[plan.style]} | \u5f3a\u5ea6: ${intensityLabels[plan.intensity]} | \u9002\u7528\u60c5\u7eea: ${t(\`emotions.${emotionCategory}\`)} | \u65f6\u957f: ${Math.round(plan.duration / 60)}\u5206\u949f`
}
```

Then replace the current `description` assignment in `matchPlan()` with:

```ts
description: formatPlanSummary(
  {
    style: best.style as TherapyPlan['style'],
    intensity: best.intensity as TherapyPlan['intensity'],
    duration: best.duration,
  },
  category,
),
```

- [ ] **Step 4: Run the test and type-check**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentPageManualFlow.test.cjs && node_modules\.bin\vue-tsc.cmd --noEmit"`
Expected: PASS

- [ ] **Step 5: Record a local checkpoint**

Run: `git diff -- app/src/views/AssessmentPage.vue app/tests/assessmentPageManualFlow.test.cjs`
Expected: Only the summary formatter and its regression test appear.

## Chunk 2: Focused verification

### Task 2: Re-run the focused assessment verification set

**Files:**
- Modify: none

- [ ] **Step 1: Run the assessment helper test**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node --experimental-strip-types tests\assessmentManualFallback.test.ts"`
Expected: PASS

- [ ] **Step 2: Run the assessment page regression test**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentPageManualFlow.test.cjs"`
Expected: PASS

- [ ] **Step 3: Run the locale smoke test**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node tests\assessmentManualLocale.test.cjs"`
Expected: PASS

- [ ] **Step 4: Run the frontend type-check**

Run: `cmd /c "cd /d D:\liaoyu\ai-liaoyu\app && node_modules\.bin\vue-tsc.cmd --noEmit"`
Expected: PASS

- [ ] **Step 5: Record the local status**

Run: `git status --short app/src/views/AssessmentPage.vue app/tests/assessmentPageManualFlow.test.cjs`
Expected: Only the intended local files are changed for this task.
