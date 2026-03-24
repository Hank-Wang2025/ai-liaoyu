# Microphone Halo Breathe Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the idle microphone button to the approved B visual with a larger wrapped halo and breathing animation, while keeping the recording state red and behavior unchanged.

**Architecture:** Keep the change local to the assessment entry component by adding a small idle-state halo wrapper around the existing microphone button and updating scoped SCSS animations. Lock the visual contract with a minimal source-level front-end test that checks the new structure and class names.

**Tech Stack:** Vue 3 `<script setup>`, scoped SCSS, Node built-in test runner

---

## Chunk 1: Idle microphone halo visual

### Task 1: Add test coverage for the idle halo visual

**Files:**
- Modify: `app/tests/assessmentPageManualFlow.test.cjs`
- Modify: `app/src/components/entry/AssessmentEntryPanel.vue`

- [x] **Step 1: Write the failing test**

Add assertions that the assessment entry component defines:
- `assessment-page__mic-shell`
- `assessment-page__mic-halo`
- `assessment-page__mic-halo--outer`
- `assessment-page__mic-halo--inner`
- a dedicated breathe animation for the idle microphone button

- [x] **Step 2: Run test to verify it fails**

Run: `node --test app/tests/assessmentPageManualFlow.test.cjs`
Expected: FAIL because the new halo structure and animation names do not exist yet.

- [x] **Step 3: Write minimal implementation**

Update the idle microphone markup and scoped styles in `app/src/components/entry/AssessmentEntryPanel.vue` so that:
- idle state renders a larger wrapped double halo
- idle button has a breathing animation
- recording state keeps the existing red treatment

- [x] **Step 4: Run test to verify it passes**

Run: `node --test app/tests/assessmentPageManualFlow.test.cjs`
Expected: PASS

- [x] **Step 5: Run focused regression checks**

Run: `node --test app/tests/assessmentPageManualFlow.test.cjs app/tests/assessmentRouteCompatibility.test.cjs app/tests/unifiedEntryPageFlow.test.cjs`
Expected: PASS

- [x] **Step 6: Run type check**

Run: `npx vue-tsc --noEmit`
Expected: PASS
