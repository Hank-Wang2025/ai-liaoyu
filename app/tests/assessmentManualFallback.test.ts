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
