# Microphone Failure Manual Fallback Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** When microphone-related capture or speech-detection fails, jump to the manual emotion selection view and show the message `很抱歉没有听到你的声音，请选择`.

**Architecture:** Keep the existing assessment entry flow and manual fallback UI, but centralize microphone-related failures behind one fallback message path. Treat missing media APIs, denied microphone access, empty/blank audio capture, and recognized no-voice analysis failures as the same user-facing branch.

**Tech Stack:** Vue 3, TypeScript, vue-i18n, node:test

---

## Chunk 1: Lock Behavior With Tests

### Task 1: Assessment fallback tests

**Files:**
- Modify: `app/tests/assessmentPageManualFlow.test.cjs`
- Modify: `app/tests/assessmentManualLocale.test.cjs`

- [x] **Step 1: Add failing test for unified no-voice fallback copy**
- [x] **Step 2: Add failing test for empty audio / microphone failure path markers**
- [x] **Step 3: Run node tests and confirm red**

## Chunk 2: Implement Unified Microphone Failure Fallback

### Task 2: Update assessment entry flow

**Files:**
- Modify: `app/src/components/entry/AssessmentEntryPanel.vue`
- Modify: `app/src/i18n/locales/zh.ts`
- Modify: `app/src/i18n/locales/en.ts`

- [x] **Step 1: Add single localized no-voice fallback message key**
- [x] **Step 2: Route getUserMedia unsupported / denied cases to the same message**
- [x] **Step 3: Treat empty audio capture as the same manual fallback case**
- [x] **Step 4: Preserve non-microphone generic backend fallback behavior**
- [x] **Step 5: Run node tests and confirm green**

## Chunk 3: Verify Frontend Flow

### Task 3: Regression verification

**Files:**
- Modify as needed based on failures

- [x] **Step 1: Run assessment-related node tests**
- [x] **Step 2: Restart frontend and verify the entry flow manually**
