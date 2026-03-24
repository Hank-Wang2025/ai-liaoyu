# Unified Entry Start/Continue Design

## Goal

Replace the current split welcome + assessment entry with one unified entry page that supports both:

- starting a new assessment flow
- continuing an unfinished therapy session

The page should feel simpler for operators, keep both actions at equal priority, and resume directly into therapy when a valid recoverable session exists.

## Product Decisions

- Use a single unified entry page at `/`
- Show `Start New Assessment` and `Continue Previous Session` as equal-level entry cards
- Keep welcome branding, subtitle, background, and language switch on the same page
- Continue action should jump directly to `TherapyPage`
- Client restart may still continue from local snapshot
- Backend restart is not required to support resume
- If backend resume validation fails, clear the local snapshot and guide the operator back to starting a new assessment

## Current Problem

The current experience splits the pre-therapy journey into separate pages:

1. `WelcomePage.vue` only provides a branding-first start button
2. `AssessmentPage.vue` holds the actual assessment and manual fallback flow
3. There is no clear unified resume entry on the first screen

That structure adds unnecessary navigation and does not match the operator workflow the user wants: one page for both starting and continuing.

## Chosen Architecture

Keep the therapy flow and report flow unchanged, but replace the entry experience with a unified entry shell.

### Unified Entry Page

The root route remains the operator landing page, but now combines:

- welcome/branding content
- new assessment entry
- unfinished session resume entry

This page becomes the only pre-therapy entry surface.

### Resume Model

Resume is client-led and snapshot-based.

The client stores a local resumable session snapshot containing enough information to rebuild entry and therapy context after a client restart:

- backend session id
- selected plan
- current phase index
- elapsed time / progress baseline
- paused/running state
- optional emotion/recommendation context needed by the entry page

Resume remains valid only if the backend session still exists and is still resumable.

## Frontend Design

### Entry Page Structure

Refactor the current landing flow so the root page contains two equal cards below the welcome header:

- `Start New Assessment`
- `Continue Previous Session`

Both cards remain visible at the same time. Neither becomes the primary CTA when resumable data exists.

#### New Assessment Card

Expanding or activating this card reveals the current early assessment flow:

- voice collection
- fallback to manual emotion buttons when microphone is unavailable or analysis fails
- emotion result display
- recommended plan display
- start therapy action

Only one entry section should be expanded at a time to avoid visual clutter.

#### Continue Session Card

This card always exists.

- If no resumable snapshot exists: show disabled state plus a `No resumable session` hint
- If snapshot exists: show active state and minimal progress/session summary if available

Click behavior:

1. validate local snapshot
2. validate backend session
3. if valid, navigate directly to `TherapyPage`
4. restore playback/session state automatically
5. if invalid, clear snapshot and show a failure notice on the entry page

### Therapy Page Resume Behavior

`TherapyPage` must support entering from two sources:

- new assessment start
- resumed session restore

When entering from resume:

- hydrate phase index and elapsed timing from local snapshot
- restore paused/running UI state
- if backend validation indicated active playback should continue, auto-resume

### Session Store Responsibilities

Extend the session store to manage resumable state explicitly.

Needed responsibilities:

- persist resumable snapshot locally
- update snapshot during therapy progress changes
- restore snapshot on app startup / entry page mount
- clear snapshot on:
  - completed report flow
  - manual stop/end
  - invalid resume detection

### Router / Navigation

Keep `/` as the unified entry route.

Likely route changes:

- `WelcomePage.vue` becomes the unified entry container, or is replaced by a new entry page component
- `AssessmentPage.vue` no longer acts as a standalone first destination in the normal flow

## Error Handling

- Resume card should never crash the entry page if local snapshot data is malformed
- Invalid snapshot should be cleared immediately
- Backend validation failure should degrade to `start new assessment`, not trap the operator
- Resume should not require a second confirmation step
- If resume fails after click, keep the operator on the entry page and show a clear message

## Non-Goals

- no backend cross-restart session recovery in this pass
- no redesign of therapy playback/report architecture in this pass
- no attempt to merge the entire pre-therapy flow into one long single-file page

## Files Expected To Change

- `app/src/views/WelcomePage.vue`
- `app/src/views/AssessmentPage.vue`
- `app/src/router/index.ts`
- `app/src/stores/session.ts`
- `app/src/utils/...` for local resume snapshot helpers
- `app/tests/...` entry/resume regression tests

## Verification

- frontend regression test for unified entry showing both start and continue actions
- frontend regression test for disabled continue state when no resumable session exists
- frontend regression test for valid local snapshot + valid backend session resuming directly into therapy
- frontend regression test for invalid backend resume clearing local snapshot and falling back safely
- `cmd /c npx vue-tsc --noEmit`

