import type { EmotionCategory, EmotionState } from '../types/index.ts'

export type ManualFallbackEmotion = Extract<
  EmotionCategory,
  'happy' | 'neutral' | 'anxious' | 'angry' | 'sad' | 'tired'
>

export interface ManualFallbackOption {
  category: ManualFallbackEmotion
}

const MANUAL_PRESETS: Record<
  ManualFallbackEmotion,
  Pick<EmotionState, 'valence' | 'arousal'>
> = {
  happy: { valence: 0.7, arousal: 0.6 },
  neutral: { valence: 0.0, arousal: 0.4 },
  anxious: { valence: -0.6, arousal: 0.8 },
  angry: { valence: -0.7, arousal: 0.85 },
  sad: { valence: -0.7, arousal: 0.3 },
  tired: { valence: -0.4, arousal: 0.2 },
}

export const MANUAL_FALLBACK_OPTIONS: ManualFallbackOption[] = [
  { category: 'happy' },
  { category: 'neutral' },
  { category: 'anxious' },
  { category: 'angry' },
  { category: 'sad' },
  { category: 'tired' },
]

export function buildManualEmotionState(
  category: ManualFallbackEmotion,
  timestamp = new Date(),
): EmotionState {
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
