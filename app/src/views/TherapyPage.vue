<template>
  <div class="therapy-page">
    <div class="therapy-page__visual">
      <video
        ref="videoRef"
        class="therapy-page__video"
        autoplay
        loop
        muted
        playsinline
      >
        <source src="" type="video/mp4" />
      </video>
      <div class="therapy-page__overlay"></div>
    </div>

    <div class="therapy-page__panel animate-fadeIn">
      <h1 class="therapy-page__title">{{ $t('therapy.title') }}</h1>

      <div class="therapy-page__phase card card--glass">
        <template v-if="activeScreenPrompt">
          <p class="therapy-page__prompt-title">{{ activeScreenPrompt.title }}</p>
          <p
            v-for="line in activeScreenPrompt.lines"
            :key="`${activeScreenPrompt.startSecond}-${line}`"
            class="therapy-page__prompt-line"
          >
            {{ line }}
          </p>
        </template>
        <template v-else>
          <p class="therapy-page__phase-label">{{ $t('therapy.currentPhase') }}</p>
          <p class="therapy-page__phase-name">
            {{ currentPhase?.name || $t('common.loading') }}
          </p>
        </template>
      </div>

      <div class="therapy-page__progress">
        <div class="therapy-page__progress-info">
          <span>{{ $t('therapy.totalProgress') }}</span>
          <span>{{ progressPercent }}%</span>
        </div>
        <div class="therapy-page__progress-bar">
          <div
            class="therapy-page__progress-fill"
            :style="{ width: `${progressPercent}%` }"
          ></div>
        </div>
      </div>

      <div class="therapy-page__time">
        <p class="therapy-page__time-label">{{ $t('therapy.remainingTime') }}</p>
        <p class="therapy-page__time-value">{{ formatTime(remainingTime) }}</p>
      </div>

      <div class="therapy-page__time-stats">
        <div class="therapy-page__time-stat">
          <p class="therapy-page__time-stat-label">{{ $t('therapy.plannedDuration') }}</p>
          <p class="therapy-page__time-stat-value">{{ formatTime(totalDuration) }}</p>
        </div>
        <div class="therapy-page__time-stat">
          <p class="therapy-page__time-stat-label">{{ $t('therapy.totalElapsed') }}</p>
          <p class="therapy-page__time-stat-value">{{ formatTime(totalElapsedTime) }}</p>
        </div>
      </div>

      <div class="therapy-page__controls">
        <button
          class="therapy-page__control-btn"
          @click="togglePause"
          :disabled="isStopping || isAdjustingIntensity"
          :title="isPaused ? $t('common.resume') : $t('common.pause')"
          :aria-label="isPaused ? $t('common.resume') : $t('common.pause')"
        >
          {{ isPaused ? $t('common.resume') : $t('common.pause') }}
        </button>

        <button
          class="therapy-page__control-btn"
          @click="adjustIntensity('relax')"
          :disabled="isStopping || isAdjustingIntensity || !canRelaxMore"
          :title="$t('therapy.relaxMore')"
          :aria-label="$t('therapy.relaxMore')"
        >
          {{ $t('therapy.relaxMore') }}
        </button>

        <button
          class="therapy-page__control-btn"
          @click="adjustIntensity('intensify')"
          :disabled="isStopping || isAdjustingIntensity || !canIntensifyMore"
          :title="$t('therapy.intensifyMore')"
          :aria-label="$t('therapy.intensifyMore')"
        >
          {{ $t('therapy.intensifyMore') }}
        </button>

        <button
          class="therapy-page__control-btn therapy-page__control-btn--danger"
          @click="endTherapy"
          :disabled="isStopping || isAdjustingIntensity"
          :title="$t('common.end')"
          :aria-label="$t('common.end')"
        >
          {{ $t('common.end') }}
        </button>
      </div>

      <p v-if="controlFeedback" class="therapy-page__control-feedback">
        {{ controlFeedback }}
      </p>

      <p class="therapy-page__hint">{{ $t('therapy.pauseHint') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useSessionStore } from '@/stores/session'
import type {
  TherapyAdjustmentDirection,
  TherapyPhase,
  TherapyScreenPrompt,
} from '@/types'

const router = useRouter()
const sessionStore = useSessionStore()
const { t } = useI18n()

const videoRef = ref<HTMLVideoElement | null>(null)
const isStopping = ref(false)
const isAdjustingIntensity = ref(false)
const elapsedTime = ref(0)
const wallClockNow = ref(Date.now())
const controlFeedback = ref<string | null>(null)
const timer = ref<number | null>(null)
let controlFeedbackTimer: number | null = null

const isPaused = computed(() => sessionStore.isPaused)
const currentPlan = computed(() => sessionStore.currentPlan)
const currentRuntimeIntensityLevel = computed(() =>
  currentPlan.value?.runtimeIntensityLevel ?? null,
)
const canRelaxMore = computed(() =>
  currentRuntimeIntensityLevel.value !== null
    ? currentRuntimeIntensityLevel.value > 1
    : currentPlan.value?.intensity
      ? currentPlan.value.intensity !== 'low'
      : false,
)
const canIntensifyMore = computed(() =>
  currentRuntimeIntensityLevel.value !== null
    ? currentRuntimeIntensityLevel.value < 5
    : currentPlan.value?.intensity
      ? currentPlan.value.intensity !== 'high'
      : false,
)

const currentPhaseIndex = computed(() => {
  const phases = currentPlan.value?.phases
  if (!phases?.length) return 0

  let elapsed = 0
  for (let index = 0; index < phases.length; index++) {
    elapsed += phases[index].duration
    if (elapsedTime.value < elapsed || index === phases.length - 1) {
      return index
    }
  }

  return 0
})

const currentPhase = computed<TherapyPhase | null>(() => {
  if (!currentPlan.value?.phases?.length) return null
  return currentPlan.value.phases[currentPhaseIndex.value] || null
})

const totalDuration = computed(() => currentPlan.value?.duration || 900)

const isValidScreenPromptTimeline = (
  prompts: TherapyScreenPrompt[] | undefined,
  duration: number,
) => {
  if (!Array.isArray(prompts) || !prompts.length || duration <= 0) {
    return false
  }

  let expectedStart = 0
  for (const prompt of prompts) {
    if (
      typeof prompt?.startSecond !== 'number' ||
      typeof prompt?.endSecond !== 'number' ||
      typeof prompt?.title !== 'string' ||
      prompt.startSecond !== expectedStart ||
      prompt.startSecond >= prompt.endSecond ||
      prompt.endSecond > duration ||
      !prompt.title.trim() ||
      !Array.isArray(prompt.lines) ||
      !prompt.lines.length ||
      prompt.lines.some((line) => !line.trim())
    ) {
      return false
    }

    expectedStart = prompt.endSecond
  }

  return expectedStart === duration
}

const validatedScreenPrompts = computed(() => {
  const prompts = currentPlan.value?.screenPrompts
  return isValidScreenPromptTimeline(prompts, totalDuration.value) ? prompts : null
})

const activeScreenPrompt = computed<TherapyScreenPrompt | null>(() => {
  const prompts = validatedScreenPrompts.value
  if (!prompts) {
    return null
  }

  return (
    prompts.find(
      (prompt) =>
        prompt.startSecond <= elapsedTime.value &&
        elapsedTime.value < prompt.endSecond,
    ) ?? null
  )
})

const remainingTime = computed(() => {
  return Math.max(0, totalDuration.value - elapsedTime.value)
})

const totalElapsedTime = computed(() => {
  const startTime = sessionStore.currentSession?.startTime
  if (!startTime) return 0
  return Math.max(
    0,
    Math.round((wallClockNow.value - new Date(startTime).getTime()) / 1000),
  )
})

const progressPercent = computed(() => {
  return Math.round((elapsedTime.value / totalDuration.value) * 100)
})

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const startTimer = () => {
  timer.value = window.setInterval(() => {
    wallClockNow.value = Date.now()
    if (!isPaused.value) {
      elapsedTime.value++

      // End the session when the timer reaches the target duration.
      if (elapsedTime.value >= totalDuration.value) {
        void endTherapy()
      }
    }
  }, 1000)
}

const togglePause = async () => {
  if (isPaused.value) {
    await sessionStore.resumeTherapy()
  } else {
    await sessionStore.pauseTherapy()
  }
}

const setControlFeedback = (message: string | null) => {
  controlFeedback.value = message

  if (controlFeedbackTimer) {
    clearTimeout(controlFeedbackTimer)
    controlFeedbackTimer = null
  }

  if (message) {
    controlFeedbackTimer = window.setTimeout(() => {
      controlFeedback.value = null
      controlFeedbackTimer = null
    }, 2500)
  }
}

const adjustIntensity = async (direction: TherapyAdjustmentDirection) => {
  if (isStopping.value || isAdjustingIntensity.value) {
    return
  }

  if (direction === 'relax' && !canRelaxMore.value) {
    setControlFeedback(t('therapy.atMostRelaxed'))
    return
  }

  if (direction === 'intensify' && !canIntensifyMore.value) {
    setControlFeedback(t('therapy.atMostIntense'))
    return
  }

  isAdjustingIntensity.value = true

  try {
    const response = await sessionStore.adjustTherapyIntensity(direction)
    if (!response.changed) {
      setControlFeedback(
        response.atBoundary
          ? direction === 'relax'
            ? t('therapy.atMostRelaxed')
            : t('therapy.atMostIntense')
          : t('therapy.adjustmentUnavailable'),
      )
    } else {
      setControlFeedback(null)
    }
  } catch (error) {
    console.error('Failed to adjust therapy intensity:', error)
    setControlFeedback(t('therapy.adjustmentFailed'))
  } finally {
    isAdjustingIntensity.value = false
  }
}

const endTherapy = async () => {
  if (isStopping.value) {
    return
  }

  isStopping.value = true

  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }

  try {
    // Start backend stop-now teardown without blocking the report transition.
    const stopNowRequest = sessionStore.stopNowSession()
    await sessionStore.endSession()
    await router.push('/report')
    void stopNowRequest
  } finally {
    isStopping.value = false
  }
}

onMounted(() => {
  if (!sessionStore.isTherapyActive) {
    router.push('/')
    return
  }
  startTimer()
})

onUnmounted(() => {
  if (timer.value) {
    clearInterval(timer.value)
  }
  if (controlFeedbackTimer) {
    clearTimeout(controlFeedbackTimer)
  }
})
</script>

<style lang="scss" scoped>
.therapy-page {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  &__visual {
    position: absolute;
    inset: 0;
    z-index: 0;
  }

  &__video {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &__overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      135deg,
      rgba(26, 26, 46, 0.8) 0%,
      rgba(22, 33, 62, 0.6) 100%
    );
  }

  &__panel {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    width: 100%;
    padding: 48px;
    max-width: 720px;
    box-sizing: border-box;
    background: rgba(22, 33, 62, 0.9);
    backdrop-filter: blur(20px);
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-color);
  }

  &__title {
    font-size: 1.5rem;
    margin-bottom: 32px;
    color: var(--accent-primary);
  }

  &__phase {
    width: 100%;
    margin-bottom: 24px;
  }

  &__phase-label {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: 8px;
  }

  &__phase-name {
    font-size: 1.25rem;
    font-weight: 600;
  }

  &__prompt-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 8px;
  }

  &__prompt-line {
    color: var(--text-secondary);
    line-height: 1.7;

    &:not(:last-child) {
      margin-bottom: 6px;
    }
  }

  &__progress {
    width: 100%;
    margin-bottom: 24px;
  }

  &__progress-info {
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }

  &__progress-bar {
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  &__progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    border-radius: var(--radius-full);
    transition: width 1s linear;
  }

  &__time {
    margin-bottom: 20px;
  }

  &__time-label {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: 8px;
  }

  &__time-value {
    font-size: 3rem;
    font-weight: 300;
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
  }

  &__time-stats {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 32px;
  }

  &__time-stat {
    padding: 12px;
    border-radius: var(--radius-md);
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-color);
  }

  &__time-stat-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  &__time-stat-value {
    font-size: 1.125rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
  }

  &__controls {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  &__control-btn {
    min-height: 48px;
    padding: 0 18px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: var(--radius-full);
    background: rgba(34, 79, 130, 0.92);
    color: var(--text-primary);
    font-size: 0.95rem;
    font-weight: 600;
    transition:
      transform 0.2s ease,
      opacity 0.2s ease,
      background 0.2s ease,
      border-color 0.2s ease;

    &:not(:disabled):hover {
      transform: translateY(-1px);
      background: rgba(43, 96, 154, 0.98);
      border-color: rgba(78, 205, 196, 0.35);
    }

    &:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    &--danger {
      background: rgba(53, 69, 100, 0.95);
    }
  }

  &__control-feedback {
    min-height: 20px;
    margin-bottom: 8px;
    font-size: 0.875rem;
    color: var(--accent-primary);
  }

  &__hint {
    font-size: 0.875rem;
    color: var(--text-muted);
  }

  @media (max-width: 720px) {
    &__controls {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
}
</style>
