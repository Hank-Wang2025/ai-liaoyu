# Therapy Fast Stop Design

## Goal

Make the stop interaction behave more like a commercial massage chair:

- no confirmation dialog
- immediate stop request
- stop scope covers chair, audio, and lights
- automatic navigation to the report page
- local summary first, finalized report later

## Product Decisions

- Trigger: single tap, no secondary confirmation
- Post-stop navigation: go directly to the report page
- Stop scope: massage chair, background music, and lighting
- Report behavior: render local summary immediately, then refresh with finalized backend data when available

## Current Problem

The current stop flow mixes two responsibilities into one synchronous request:

1. stop physical outputs
2. finalize session state and generate report data

That coupling makes user feedback feel slow. It also does not match commercial products, which prioritize immediate stop behavior over report completion.

## Chosen Architecture

Split the flow into two chains.

### Fast Stop Chain

Add a dedicated backend endpoint:

- `POST /api/therapy/stop-now/{session_id}`

This endpoint is responsible only for immediate device stop:

- stop chair motion
- stop music playback
- stop lighting effects

It should return quickly and be safe to call more than once.

### Finalization Chain

After fast stop succeeds, the backend continues finalization asynchronously:

- stop executor state cleanly
- end the active session
- generate finalized report data
- clear active executor references

The frontend does not wait for this chain before navigating.

## Frontend Design

### Therapy Page

- Remove the confirmation modal from the stop interaction
- Replace it with single-tap stop behavior
- On tap:
  - enter `stopping` UI state immediately
  - disable pause, next-track, skip, and stop controls
  - call `stop-now`
  - locally mark the session as ended
  - navigate directly to the report page

### Session Store

Keep local UI state and backend finalization separate.

- local state update should happen immediately
- backend finalization should continue in the background
- backend session id must remain available while the report page polls for finalized data

### Report Page

- do not block on finalized backend data
- render the local summary immediately
- poll a short number of times for the finalized backend report
- replace local data with backend data as soon as it is available

## Backend Design

### New API

Add a dedicated stop endpoint in `backend/api/therapy.py`:

- validate active session and session id
- stop device outputs immediately
- mark the session as `stopping`
- schedule asynchronous finalization work
- return success without waiting for report generation

### Executor / Device Behavior

The fast stop path must be able to stop outputs independently of full session finalization.

Needed behavior:

- chair stop
- audio stop
- light stop / revert to neutral state if available

If one device is unavailable, the endpoint should still return a success payload describing degraded stop behavior instead of failing the whole interaction.

### Session State

Introduce an explicit intermediate state:

- `running`
- `stopping`
- `ended`

`stopping` means the physical outputs should already be stopped while report finalization may still be running.

## Error Handling

- `stop-now` must be idempotent
- repeated taps must not produce duplicate teardown errors
- device-specific failures should be logged and surfaced as warnings, not crash the stop flow
- report finalization failure must not affect the already-completed fast stop interaction
- report page polling should fall back to local summary if backend data is delayed or unavailable

## Non-Goals

- no websocket push update in this pass
- no full embedded local chair controller refactor in this pass
- no redesign of therapy recommendation or plan selection flows in this pass

## Files Expected To Change

- `backend/api/therapy.py`
- `backend/services/therapy_executor.py`
- `backend/tests/test_therapy_api_executor_lifecycle.py`
- `app/src/api/index.ts`
- `app/src/stores/session.ts`
- `app/src/views/TherapyPage.vue`
- `app/src/views/ReportPage.vue`
- `app/tests/...` regression tests for stop flow and report refresh

## Verification

- backend regression test for `stop-now` stopping executor/device outputs
- backend regression test for idempotent repeated stop calls
- frontend regression test for single-tap stop without confirmation
- frontend regression test for local report render + backend refresh polling
- `npx vue-tsc --noEmit`

