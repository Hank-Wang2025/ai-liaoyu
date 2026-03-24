<template>
  <div class="assessment-page">
    <div class="assessment-page__content">
      <div v-if="step === 'voice' || step === 'manual'" class="assessment-page__voice">
        <template v-if="step === 'voice'">
          <p class="assessment-page__prompt">{{ $t('assessment.voicePrompt') }}</p>
          <p v-if="analysisError" class="assessment-page__error">{{ analysisError }}</p>

          <div
            class="assessment-page__mic-shell"
            :class="{ 'assessment-page__mic-shell--recording': isRecording }"
          >
            <div class="assessment-page__mic-halo assessment-page__mic-halo--outer" aria-hidden="true"></div>
            <div class="assessment-page__mic-halo assessment-page__mic-halo--inner" aria-hidden="true"></div>

            <button
              class="assessment-page__mic-btn"
              :class="{ recording: isRecording }"
              :aria-label="isRecording ? 'Stop recording' : 'Start recording'"
              @click="toggleRecording"
            >
              <svg v-if="!isRecording" width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
                <path
                  d="M24 4C20.6863 4 18 6.68629 18 10V24C18 27.3137 20.6863 30 24 30C27.3137 30 30 27.3137 30 24V10C30 6.68629 27.3137 4 24 4Z"
                  stroke="currentColor"
                  stroke-width="3"
                />
                <path
                  d="M12 22V24C12 30.6274 17.3726 36 24 36C30.6274 36 36 30.6274 36 24V22"
                  stroke="currentColor"
                  stroke-width="3"
                  stroke-linecap="round"
                />
                <path
                  d="M24 36V44M18 44H30"
                  stroke="currentColor"
                  stroke-width="3"
                  stroke-linecap="round"
                />
              </svg>
              <svg v-else width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
                <rect x="14" y="14" width="20" height="20" rx="4" fill="currentColor" />
              </svg>
            </button>
          </div>

          <p v-if="isRecording" class="assessment-page__status animate-pulse">
            {{ $t('assessment.recording') }}
          </p>

          <div v-if="isRecording" class="assessment-page__waveform">
            <div v-for="i in 5" :key="i" class="assessment-page__wave-bar"></div>
          </div>
        </template>

        <div v-else class="assessment-page__manual card">
          <h2 class="assessment-page__manual-title">{{ $t('assessment.manualFallbackTitle') }}</h2>
          <p class="assessment-page__manual-prompt">{{ $t('assessment.manualFallbackPrompt') }}</p>

          <div class="assessment-page__manual-actions">
            <button class="btn btn--secondary" @click="retryMicrophone">
              {{ $t('assessment.retryMicrophone') }}
            </button>
          </div>

          <div class="assessment-page__manual-options">
            <button
              v-for="option in MANUAL_FALLBACK_OPTIONS"
              :key="option.category"
              class="btn btn--secondary assessment-page__manual-option"
              :class="{
                'assessment-page__manual-option--selected': selectedManualEmotion === option.category,
              }"
              :aria-pressed="selectedManualEmotion === option.category"
              @click="selectedManualEmotion = option.category"
            >
              {{ $t(`emotions.${option.category}`) }}
            </button>
          </div>

          <button
            class="btn btn--primary assessment-page__manual-continue"
            :disabled="selectedManualEmotion === null"
            @click="continueWithManualEmotion"
          >
            {{ $t('assessment.manualContinue') }}
          </button>
        </div>
      </div>

      <div v-else-if="step === 'analyzing'" class="assessment-page__analyzing">
        <div class="assessment-page__spinner"></div>
        <p>{{ $t('assessment.analyzing') }}</p>
        <p v-if="analysisError" class="assessment-page__error">{{ analysisError }}</p>
      </div>

      <div v-else-if="step === 'result'" class="assessment-page__result">
        <h2>{{ $t('assessment.result') }}</h2>

        <div class="assessment-page__emotion-card card">
          <div class="assessment-page__emotion-icon">
            {{ getEmotionEmoji(emotionResult?.category) }}
          </div>
          <div class="assessment-page__emotion-info">
            <p class="assessment-page__emotion-label">{{ $t('assessment.emotion') }}</p>
            <p class="assessment-page__emotion-value">
              {{ $t(`emotions.${emotionResult?.category || 'neutral'}`) }}
            </p>
          </div>
          <div class="assessment-page__intensity">
            <p class="assessment-page__intensity-label">{{ $t('assessment.intensity') }}</p>
            <div class="assessment-page__intensity-bar">
              <div
                class="assessment-page__intensity-fill"
                :style="{ width: `${(emotionResult?.intensity || 0) * 100}%` }"
              ></div>
            </div>
          </div>
        </div>

        <div v-if="recommendedPlan" class="assessment-page__plan card">
          <p class="assessment-page__plan-label">{{ $t('assessment.suggestion') }}</p>
          <p class="assessment-page__plan-name">{{ recommendedPlan.name }}</p>
          <p class="assessment-page__plan-desc">{{ recommendedPlan.description }}</p>
        </div>

        <button
          class="btn btn--primary btn--large"
          :disabled="isStartingTherapy"
          @click="startTherapy"
        >
          {{ $t('common.start') }}
        </button>
      </div>

      <button v-if="props.showBackButton" class="btn btn--ghost assessment-page__back" @click="goBack">
        {{ $t('common.back') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, withDefaults } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { emotionApi, therapyApi } from '@/api'
import { useSessionStore } from '@/stores/session'
import type { EmotionCategory, EmotionState, TherapyPlan } from '@/types'
import {
  MANUAL_FALLBACK_OPTIONS,
  buildManualEmotionState,
} from '@/utils/assessmentManualFallback'
import type { ManualFallbackEmotion } from '@/utils/assessmentManualFallback'

const props = withDefaults(
  defineProps<{
    showBackButton?: boolean
  }>(),
  {
    showBackButton: true,
  },
)

type AssessmentSubtitleKey =
  | 'assessment.subtitle'
  | 'assessment.microphoneNoVoice'

const emit = defineEmits<{
  (e: 'subtitle-change', subtitleKey: AssessmentSubtitleKey): void
}>()

const router = useRouter()
const sessionStore = useSessionStore()
const { t } = useI18n()

const step = ref<'voice' | 'manual' | 'analyzing' | 'result'>('voice')
const isRecording = ref(false)
const emotionResult = ref<EmotionState | null>(null)
const recommendedPlan = ref<TherapyPlan | null>(null)
const analysisError = ref<string | null>(null)
const selectedManualEmotion = ref<EmotionCategory | null>(null)
const isStartingTherapy = ref(false)

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

const MANUAL_FALLBACK_CATEGORIES = new Set<ManualFallbackEmotion>(
  MANUAL_FALLBACK_OPTIONS.map((option) => option.category),
)
const DEFAULT_ASSESSMENT_SUBTITLE: AssessmentSubtitleKey = 'assessment.subtitle'
const MICROPHONE_NO_VOICE_SUBTITLE: AssessmentSubtitleKey =
  'assessment.microphoneNoVoice'

const getEmotionEmoji = (category?: EmotionCategory) => {
  const emojis: Record<EmotionCategory, string> = {
    happy: '\u{1F60A}',
    sad: '\u{1F622}',
    angry: '\u{1F620}',
    anxious: '\u{1F628}',
    tired: '\u{1F62A}',
    fearful: '\u{1F631}',
    surprised: '\u{1F62E}',
    disgusted: '\u{1F922}',
    neutral: '\u{1F610}',
  }

  return emojis[category || 'neutral']
}

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

  return `\u98ce\u683c: ${styleLabels[plan.style]} | \u5f3a\u5ea6: ${intensityLabels[plan.intensity]} | \u9002\u7528\u60c5\u7eea: ${t(`emotions.${emotionCategory}`)} | \u65f6\u957f: ${Math.round(plan.duration / 60)}\u5206\u949f`
}

const mapEmotion2vecCategory = (emotion: string): EmotionCategory => {
  const mapping: Record<string, EmotionCategory> = {
    happy: 'happy',
    angry: 'angry',
    sad: 'sad',
    surprised: 'surprised',
    disgusted: 'disgusted',
    fearful: 'fearful',
    neutral: 'neutral',
    anxious: 'anxious',
    tired: 'tired',
    excited: 'happy',
    contempt: 'disgusted',
    other: 'neutral',
  }

  return mapping[emotion] || 'neutral'
}

const isManualFallbackEmotion = (
  category: EmotionCategory | null,
): category is ManualFallbackEmotion => {
  return category !== null && MANUAL_FALLBACK_CATEGORIES.has(category as ManualFallbackEmotion)
}

const setAssessmentSubtitle = (
  subtitleKey: AssessmentSubtitleKey = DEFAULT_ASSESSMENT_SUBTITLE,
) => {
  emit('subtitle-change', subtitleKey)
}

const showManualFallback = (
  subtitleKey: AssessmentSubtitleKey = DEFAULT_ASSESSMENT_SUBTITLE,
) => {
  isRecording.value = false
  analysisError.value = null
  selectedManualEmotion.value = null
  step.value = 'manual'
  setAssessmentSubtitle(subtitleKey)
}

const showNoVoiceManualFallback = () => {
  showManualFallback(MICROPHONE_NO_VOICE_SUBTITLE)
}

const isNoVoiceAnalysisResult = (result: any) => {
  const event = typeof result?.event === 'string' ? result.event.toLowerCase() : ''
  const text = typeof result?.text === 'string' ? result.text.trim() : ''

  if (!text) {
    return true
  }

  if (event && event !== 'speech') {
    return true
  }

  return false
}

const toggleRecording = async () => {
  analysisError.value = null

  if (isRecording.value) {
    isRecording.value = false
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    return
  }

  try {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      showNoVoiceManualFallback()
      return
    }

    step.value = 'voice'
    setAssessmentSubtitle()
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop())
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
      if (audioBlob.size === 0) {
        showNoVoiceManualFallback()
        return
      }
      await analyzeAudio(audioBlob)
    }

    mediaRecorder.start()
    isRecording.value = true
  } catch (err) {
    console.error('microphone access failed:', err)
    showNoVoiceManualFallback()
  }
}

const retryMicrophone = async () => {
  selectedManualEmotion.value = null
  step.value = 'voice'
  setAssessmentSubtitle()
  await toggleRecording()
}

const analyzeAudio = async (audioBlob: Blob) => {
  step.value = 'analyzing'
  analysisError.value = null
  setAssessmentSubtitle()

  try {
    const result = await emotionApi.analyzeCombined(audioBlob)
    if (isNoVoiceAnalysisResult(result)) {
      showNoVoiceManualFallback()
      return
    }

    const category = mapEmotion2vecCategory(result.emotion2vec_emotion)

    emotionResult.value = {
      category,
      intensity: result.intensity,
      valence: result.valence,
      arousal: result.arousal,
      confidence: result.confidence,
      timestamp: new Date(),
    }

    await matchPlan(category, result.intensity, result.valence, result.arousal)
    step.value = 'result'
  } catch (err: any) {
    console.error('audio analysis failed:', err)
    await fallbackAnalysis()
  }
}

const continueWithManualEmotion = async () => {
  if (!isManualFallbackEmotion(selectedManualEmotion.value)) {
    return
  }

  step.value = 'analyzing'
  analysisError.value = null
  setAssessmentSubtitle()
  emotionResult.value = buildManualEmotionState(selectedManualEmotion.value)

  await matchPlan(
    emotionResult.value.category,
    emotionResult.value.intensity,
    emotionResult.value.valence,
    emotionResult.value.arousal,
  )

  step.value = 'result'
}

const matchPlan = async (
  category: EmotionCategory,
  intensity: number,
  valence: number,
  arousal: number,
) => {
  try {
    const matchResult = await therapyApi.getRecommendedPlan({
      category,
      intensity,
      valence,
      arousal,
      confidence: 0.8,
    })

    if (matchResult.best_match && matchResult.matched_plans?.length > 0) {
      const best = matchResult.matched_plans[0]
      recommendedPlan.value = {
        id: best.id,
        name: best.name,
        description: formatPlanSummary(
          {
            style: best.style as TherapyPlan['style'],
            intensity: best.intensity as TherapyPlan['intensity'],
            duration: best.duration,
          },
          category,
        ),
        targetEmotions: [],
        intensity: best.intensity as TherapyPlan['intensity'],
        style: best.style as TherapyPlan['style'],
        duration: best.duration,
        phases: [],
      }
    }
  } catch (err) {
    console.error('plan matching failed, using default plan:', err)
    recommendedPlan.value = {
      id: 'quick_calm',
      name: '\u5feb\u901f\u5e73\u9759\u65b9\u6848',
      description: '\u901a\u8fc7\u6df1\u547c\u5438\u5f15\u5bfc\u548c\u8212\u7f13\u97f3\u4e50\uff0c\u5e2e\u52a9\u60a8\u653e\u677e\u8eab\u5fc3',
      targetEmotions: [category as EmotionCategory],
      intensity: 'medium',
      style: 'modern',
      duration: 900,
      phases: [],
    }
  }
}

const fallbackAnalysis = async (
  message = '\u540e\u7aef\u670d\u52a1\u6682\u4e0d\u53ef\u7528\uff0c\u4f7f\u7528\u672c\u5730\u8bc4\u4f30',
) => {
  step.value = 'analyzing'
  analysisError.value = message
  setAssessmentSubtitle()
  await new Promise((resolve) => setTimeout(resolve, 1500))

  emotionResult.value = {
    category: 'neutral',
    intensity: 0.5,
    valence: 0.0,
    arousal: 0.5,
    confidence: 0.5,
    timestamp: new Date(),
  }

  recommendedPlan.value = {
    id: 'quick_calm',
    name: '\u5feb\u901f\u5e73\u9759\u65b9\u6848',
    description: '\u901a\u8fc7\u6df1\u547c\u5438\u5f15\u5bfc\u548c\u8212\u7f13\u97f3\u4e50\uff0c\u5e2e\u52a9\u60a8\u653e\u677e\u8eab\u5fc3',
    targetEmotions: ['neutral'],
    intensity: 'medium',
    style: 'modern',
    duration: 900,
    phases: [],
  }

  step.value = 'result'
}

const isHydratedPlanDetail = (plan: any): plan is TherapyPlan => {
  return (
    typeof plan?.id === 'string' &&
    typeof plan?.style === 'string' &&
    typeof plan?.intensity === 'string' &&
    Number.isFinite(Number(plan?.duration)) &&
    Array.isArray(plan?.phases)
  )
}

const hydrateRecommendedPlan = async (summaryPlan: TherapyPlan) => {
  if (!summaryPlan.id) {
    return summaryPlan
  }

  try {
    const hydratedPlan = await therapyApi.getPlanDetail(summaryPlan.id)
    return isHydratedPlanDetail(hydratedPlan)
      ? (hydratedPlan as TherapyPlan)
      : summaryPlan
  } catch (err) {
    console.error('plan detail hydration failed, using summary plan:', err)
    return summaryPlan
  }
}

const startTherapy = async () => {
  if (isStartingTherapy.value) {
    return
  }

  if (emotionResult.value && recommendedPlan.value) {
    isStartingTherapy.value = true

    try {
      const planForSession = await hydrateRecommendedPlan(recommendedPlan.value)
      const startSessionPromise = sessionStore.startSession(
        emotionResult.value,
        planForSession,
      )
      await router.push('/therapy')
      await startSessionPromise
    } finally {
      isStartingTherapy.value = false
    }
  }
}

const goBack = () => {
  if (step.value === 'voice') {
    if (props.showBackButton) {
      router.push('/')
    }
    return
  }

  if (step.value === 'manual') {
    selectedManualEmotion.value = null
  }

  step.value = 'voice'
  setAssessmentSubtitle()
}
</script>

<style lang="scss" scoped>
.assessment-page {
  &__content {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    width: 100%;
  }

  &__prompt {
    font-size: 1.125rem;
    color: var(--text-secondary);
    margin-bottom: 32px;
  }

  &__voice {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
  }

  &__mic-shell {
    position: relative;
    width: 220px;
    height: 220px;
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover .assessment-page__mic-btn:not(.recording) {
      border-color: var(--accent-primary);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.14),
        0 20px 52px rgba(5, 10, 24, 0.46);
    }

    &--recording {
      .assessment-page__mic-halo {
        opacity: 0;
        animation: none;
      }
    }
  }

  &__mic-halo {
    position: absolute;
    border-radius: var(--radius-full);
    pointer-events: none;
    transition: opacity var(--transition-normal);

    &--outer {
      width: 208px;
      height: 208px;
      background: radial-gradient(
        circle,
        rgba(78, 205, 196, 0.16) 0%,
        rgba(78, 205, 196, 0.06) 48%,
        rgba(78, 205, 196, 0) 72%
      );
      animation: micHaloOuterBreathe 2.8s ease-in-out infinite;
    }

    &--inner {
      width: 184px;
      height: 184px;
      border: 3px solid rgba(78, 205, 196, 0.56);
      box-shadow: 0 0 30px rgba(78, 205, 196, 0.18);
      animation: micHaloInnerBreathe 2.8s ease-in-out infinite;
    }
  }

  &__mic-btn {
    position: relative;
    z-index: 1;
    width: 128px;
    height: 128px;
    border-radius: 50%;
    background: linear-gradient(180deg, rgba(28, 73, 122, 0.96), rgba(21, 56, 100, 0.96));
    border: 2px solid rgba(120, 226, 220, 0.24);
    color: var(--text-primary);
    cursor: pointer;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.1),
      0 14px 38px rgba(5, 10, 24, 0.36);
    transition:
      border-color var(--transition-normal),
      box-shadow var(--transition-normal),
      background var(--transition-normal);
    animation: micButtonBreathe 2.8s ease-in-out infinite;

    svg {
      position: relative;
      z-index: 1;
    }

    &.recording {
      background: var(--error);
      border-color: var(--error);
      box-shadow: 0 10px 26px rgba(240, 113, 103, 0.28);
      animation: pulse 1s ease-in-out infinite;
    }
  }

  &__status {
    margin-top: 24px;
    color: var(--error);
    font-weight: 500;
  }

  &__error {
    margin-top: 12px;
    color: var(--warning, #f0ad4e);
    font-size: 0.875rem;
  }

  &__waveform {
    display: flex;
    gap: 8px;
    margin-top: 24px;
    height: 60px;
    align-items: center;
  }

  &__wave-bar {
    width: 8px;
    background: var(--accent-primary);
    border-radius: var(--radius-full);
    animation: wave 0.5s ease-in-out infinite;

    @for $i from 1 through 5 {
      &:nth-child(#{$i}) {
        animation-delay: #{$i * 0.1}s;
        height: #{20 + random(40)}px;
      }
    }
  }

  &__manual {
    display: flex;
    flex-direction: column;
    gap: 16px;
    width: 100%;
    text-align: left;
  }

  &__manual-title {
    font-size: 1.25rem;
    font-weight: 600;
  }

  &__manual-prompt {
    color: var(--text-secondary);
  }

  &__manual-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  &__manual-options {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  &__manual-option {
    width: 100%;

    &.assessment-page__manual-option--selected {
      background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
      border-color: transparent;
      color: var(--bg-primary);
    }
  }

  &__manual-continue {
    align-self: flex-end;
    min-width: 160px;
  }

  &__analyzing {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
  }

  &__spinner {
    width: 60px;
    height: 60px;
    border: 4px solid var(--bg-tertiary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  &__result {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    width: 100%;
  }

  &__emotion-card {
    display: flex;
    align-items: center;
    gap: 24px;
    width: 100%;
  }

  &__emotion-icon {
    font-size: 48px;
  }

  &__emotion-info {
    flex: 1;
    text-align: left;
  }

  &__emotion-label {
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  &__emotion-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--accent-primary);
  }

  &__intensity {
    width: 120px;
  }

  &__intensity-label {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: 8px;
  }

  &__intensity-bar {
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  &__intensity-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    border-radius: var(--radius-full);
    transition: width var(--transition-normal);
  }

  &__plan {
    width: 100%;
    text-align: left;
  }

  &__plan-label {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: 8px;
  }

  &__plan-name {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 8px;
  }

  &__plan-desc {
    color: var(--text-secondary);
  }

  &__back {
    margin-top: 32px;
  }
}

@keyframes wave {
  0%,
  100% {
    transform: scaleY(0.5);
  }

  50% {
    transform: scaleY(1);
  }
}

@keyframes micButtonBreathe {
  0%,
  100% {
    transform: scale(0.98);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.1),
      0 14px 38px rgba(5, 10, 24, 0.36);
  }

  50% {
    transform: scale(1.06);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.14),
      0 22px 52px rgba(5, 10, 24, 0.44);
  }
}

@keyframes micHaloOuterBreathe {
  0%,
  100% {
    transform: scale(0.98);
    opacity: 0.7;
  }

  50% {
    transform: scale(1.16);
    opacity: 1;
  }
}

@keyframes micHaloInnerBreathe {
  0%,
  100% {
    transform: scale(0.98);
    opacity: 0.64;
  }

  50% {
    transform: scale(1.12);
    opacity: 1;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
