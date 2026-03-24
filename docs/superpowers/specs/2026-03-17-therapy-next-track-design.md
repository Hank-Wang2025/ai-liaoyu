# Therapy Next Track Design

## Goal

Add a manual `Next Track` control on the therapy page that switches the current background music to the next audio file from the shared audio manifest, without changing the current therapy phase.

## Scope

- Add a backend API action for manual next-track switching.
- Reuse the existing therapy audio player and current playback settings.
- Add a therapy-page-only UI button to trigger the action.
- Keep phase progression unchanged.

## Non-Goals

- No playlist UI.
- No previous-track control.
- No cross-page audio controller abstraction.
- No persistence of manual track choice across phase transitions.

## Current State

- Device audio API supports `play`, `stop`, `pause`, `resume`, and `volume`.
- Therapy execution applies each phase's configured audio file directly.
- Audio resources already exist in `content/audio/` and are indexed by `content/audio/audio_manifest.yaml`.
- The therapy page already has pause, skip-phase, and end controls.

## Design

### Backend

Add a `next` audio action in `backend/api/device.py`.

When called:

1. Resolve the active audio player from the device manager.
2. Read the currently playing BGM file from the player's status.
3. Load the ordered list of audio files from `content/audio/audio_manifest.yaml`.
4. Choose the next file, wrapping to the first file when needed.
5. Play the new file with the current BGM volume and loop settings.
6. Return the selected file path in the response for observability.

If no current BGM file is available, fall back to the first manifest entry.

### Frontend

Add a `Next Track` button to `app/src/views/TherapyPage.vue`.

When clicked:

1. Call the backend device audio API with action `next`.
2. Leave therapy timing and phase state untouched.
3. Surface failures through the browser console for now, matching existing page behavior.

### Phase Interaction

Manual next-track switching only affects the current phase's active BGM. When the executor advances to a new phase, that phase's configured audio still overrides the manual choice.

## Error Handling

- If the manifest is missing or contains no valid entries, return HTTP 400.
- If no audio player is available, preserve the existing simulated response pattern.
- If the audio player cannot report status or cannot play the next file, return HTTP 500.

## Testing

- Backend API test: `next` selects the next manifest file from the current BGM file.
- Backend API test: `next` wraps to the first manifest file at the end.
- Frontend type-check: ensure the new therapy-page call compiles.

## Open Constraint

Git identity is not configured in this environment, so this spec can be saved locally but not committed until identity is provided.
