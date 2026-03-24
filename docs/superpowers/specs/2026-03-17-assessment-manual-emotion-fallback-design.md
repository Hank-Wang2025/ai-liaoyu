# Assessment Manual Emotion Fallback Design

## Goal

Add a manual emotion-selection fallback to the assessment screen for cases where microphone capture is unavailable or microphone permission is denied.

This fallback is for the healing-chair workflow, where the user may still need to start a therapy session even when voice capture cannot be used.

## Scope

In scope:
- Detect microphone-unavailable and microphone-denied cases on the assessment page
- Replace the voice-capture area inline on the same page with a manual emotion picker
- Offer six common emotions for manual selection
- Keep intensity fixed at `0.5` for manual selection
- Provide a `Retry Microphone` action
- Reuse the existing plan-matching flow after a manual choice is made

Out of scope:
- Removing voice capture as the default assessment path
- Adding free-text emotion input
- Adding slider-based or custom intensity input
- Changing backend APIs for plan matching
- Adding new emotion categories beyond the existing frontend types

## Current Context

`app/src/views/AssessmentPage.vue` currently uses a three-step flow:
- `voice`
- `analyzing`
- `result`

When microphone access fails, the page currently falls back to a simulated neutral emotion via `fallbackAnalysis()` instead of asking the user for explicit input.

This creates a behavior problem: the system may continue with a therapy recommendation based on a default neutral state that the user did not choose.

## User Experience

### Default path

- The page still opens in the existing voice-first state.
- The microphone button remains the primary input path.

### Fallback trigger

The page enters manual-selection mode only when one of these conditions happens:
- The runtime does not support microphone capture
- The browser/device denies microphone permission

### Inline fallback layout

The user selected the inline replacement layout instead of a separate step.

When fallback mode is active, the existing voice-capture area is replaced in-place with:
- A clear message that microphone capture is unavailable and manual selection is available
- A `Retry Microphone` action
- A six-option manual emotion picker
- A continue action that stays disabled until an emotion is selected

### Manual emotion options

The page shows these six emotions:
- `happy`
- `neutral`
- `anxious`
- `angry`
- `sad`
- `tired`

User-facing labels should be localized Chinese/English strings, while the stored values continue to use the existing `EmotionCategory` union.

### Selection behavior

- Manual selection is single-select only
- The selected option must have a clear active visual state
- The continue action is disabled until a selection exists
- Selecting an emotion does not immediately start analysis; the user must explicitly continue

### Retry behavior

- Clicking `Retry Microphone` attempts microphone access again
- On success, the page returns to the normal voice mode and clears fallback UI state
- On failure, the page stays in fallback mode and updates the error/help message

## Data Model

No backend schema change is required.

The manual path creates a normal frontend `EmotionState` object using existing types.

### Manual emotion defaults

Each manual emotion maps to a fixed intensity and default valence/arousal pair so the existing recommendation logic can still run.

Fixed intensity for all manual selections:
- `intensity = 0.5`

Default valence/arousal presets:
- `happy`: `valence = 0.7`, `arousal = 0.6`
- `neutral`: `valence = 0.0`, `arousal = 0.4`
- `anxious`: `valence = -0.6`, `arousal = 0.8`
- `angry`: `valence = -0.7`, `arousal = 0.85`
- `sad`: `valence = -0.7`, `arousal = 0.3`
- `tired`: `valence = -0.4`, `arousal = 0.2`

Confidence should be set to a stable frontend-owned manual value, such as `0.8`, to distinguish it from backend voice analysis while still satisfying current type expectations.

## Page State Design

## Step/state model

The page should expand its step model from:
- `voice | analyzing | result`

to:
- `voice | manual | analyzing | result`

Even though the selected layout is inline, keeping `manual` as an explicit state is recommended because it makes the UI behavior easier to reason about and test.

This is an internal state distinction, not a separate routed page.

## State transitions

- Initial page load -> `voice`
- Microphone unsupported -> `manual`
- Microphone denied -> `manual`
- `Retry Microphone` success -> `voice`
- Manual emotion selected + continue -> `analyzing`
- Voice analysis success -> `result`
- Manual plan matching success -> `result`
- Plan matching fallback path -> `result`

## Logic Changes

### Voice path

Keep the existing voice-first behavior as the default path.

### Manual fallback path

Replace the current direct neutral fallback behavior.

Instead of calling `fallbackAnalysis()` to synthesize a neutral result immediately after microphone failure:
- store a user-facing fallback reason
- enter `manual` state
- wait for explicit user selection

### Recommendation path reuse

After a manual choice is confirmed:
- build a standard `EmotionState`
- call the existing plan matching logic
- reuse the current result and start-therapy path without branching into a separate backend flow

This keeps the change UI-focused and minimizes risk.

## Error Handling

- Unsupported microphone environment: enter manual mode with a clear explanation
- Permission denied: enter manual mode with a message that the user can retry or select manually
- Retry failure: stay in manual mode and refresh the error/help text
- Plan matching failure after manual choice: use the existing default-plan fallback already used by the assessment page
- Back navigation from manual mode: behave like returning from the assessment page, not like preserving a hidden partial recording state

## Localization

Add assessment-page localization keys for:
- manual fallback title/message
- retry microphone action
- manual selection prompt
- continue action label
- microphone unavailable/permission denied help text

The existing emotion translation keys should be reused for button labels where possible.

## Implementation Units

### 1. Assessment page state and UI

File: `app/src/views/AssessmentPage.vue`

Responsibilities:
- manage `voice/manual/analyzing/result` states
- show the inline manual picker when needed
- handle retry flow
- build the manual `EmotionState`
- route the result into existing plan matching and therapy start behavior

### 2. Manual emotion preset mapping

Preferred location: a small local constant in `AssessmentPage.vue`, unless it becomes large enough to extract.

Responsibilities:
- map each allowed manual emotion to valence/arousal defaults
- keep fixed intensity behavior explicit and testable

### 3. Localization updates

Files:
- `app/src/i18n/locales/zh.ts`
- `app/src/i18n/locales/en.ts`

Responsibilities:
- add strings required for manual fallback mode
- keep labels consistent with the rest of the assessment flow

## Testing and Verification

Manual verification should cover:
- microphone unsupported environment enters manual mode
- microphone denial enters manual mode
- retry succeeds and returns to voice mode
- retry failure stays in manual mode
- six manual emotions render correctly
- selection is single-select
- continue is disabled until selection exists
- manual choice produces a plan recommendation
- user can start therapy from the result state
- the old direct-neutral fallback path is no longer used for microphone failures

Recommended automated coverage for implementation:
- state transition tests for microphone failure -> manual mode
- UI logic test for continue-button disabled/enabled behavior
- manual preset mapping test to ensure each emotion produces the intended `EmotionState`
- regression test that microphone failure no longer auto-generates a neutral result

## Risks

- The inline layout increases state density inside `AssessmentPage.vue`
- If retry logic and manual logic are not clearly separated, future changes may create contradictory UI states
- If localization is incomplete, the fallback path may expose raw keys or mixed language content

## Risk Controls

- Keep `manual` as an explicit internal state even with inline rendering
- Keep manual preset mapping centralized in one constant
- Reuse existing result and therapy-start logic rather than duplicating it
- Add targeted tests around state transitions and disabled-button behavior

## Success Criteria

The feature is successful when:
- users without microphone access can still provide an emotion intentionally
- the system no longer silently substitutes a neutral emotion in those cases
- the user can retry microphone capture without leaving the page
- the existing recommendation and therapy-start flow continues to work after manual selection
