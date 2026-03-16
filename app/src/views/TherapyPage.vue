<template>
  <div class="therapy-page">
    <!-- 视觉内容背景 -->
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
    
    <!-- 控制面板 -->
    <div class="therapy-page__panel animate-fadeIn">
      <h1 class="therapy-page__title">{{ $t('therapy.title') }}</h1>
      
      <!-- 当前阶段 -->
      <div class="therapy-page__phase card card--glass">
        <p class="therapy-page__phase-label">{{ $t('therapy.currentPhase') }}</p>
        <p class="therapy-page__phase-name">{{ currentPhase?.name || '准备中' }}</p>
      </div>
      
      <!-- 进度 -->
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
      
      <!-- 剩余时间 -->
      <div class="therapy-page__time">
        <p class="therapy-page__time-label">{{ $t('therapy.remainingTime') }}</p>
        <p class="therapy-page__time-value">{{ formatTime(remainingTime) }}</p>
      </div>
      
      <!-- 控制按钮 -->
      <div class="therapy-page__controls">
        <button 
          class="btn btn--secondary btn--icon"
          @click="togglePause"
          :title="isPaused ? $t('common.resume') : $t('common.pause')"
          :aria-label="isPaused ? '恢复疗愈' : '暂停疗愈'"
        >
          <svg v-if="!isPaused" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor"/>
            <rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor"/>
          </svg>
          <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M8 5V19L19 12L8 5Z" fill="currentColor"/>
          </svg>
        </button>
        
        <button 
          class="btn btn--secondary btn--icon"
          @click="skipPhase"
          :title="$t('common.skip')"
          aria-label="跳过当前阶段"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 4L15 12L5 20V4Z" fill="currentColor"/>
            <rect x="17" y="4" width="3" height="16" rx="1" fill="currentColor"/>
          </svg>
        </button>
        
        <button 
          class="btn btn--ghost btn--icon"
          @click="showEndConfirm = true"
          :title="$t('common.end')"
          aria-label="结束疗愈"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="4" y="4" width="16" height="16" rx="2" fill="currentColor"/>
          </svg>
        </button>
      </div>
      
      <p class="therapy-page__hint">{{ $t('therapy.pauseHint') }}</p>
    </div>
    
    <!-- 结束确认弹窗 -->
    <div v-if="showEndConfirm" class="therapy-page__modal" role="dialog" aria-modal="true">
      <div class="therapy-page__modal-content card animate-fadeIn">
        <h3>{{ $t('therapy.endConfirm') }}</h3>
        <p>{{ $t('therapy.endHint') }}</p>
        <div class="therapy-page__modal-actions">
          <button class="btn btn--secondary" @click="showEndConfirm = false">
            {{ $t('common.cancel') }}
          </button>
          <button class="btn btn--primary" @click="endTherapy">
            {{ $t('common.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import type { TherapyPhase } from '@/types'

const router = useRouter()
const sessionStore = useSessionStore()

const videoRef = ref<HTMLVideoElement | null>(null)
const showEndConfirm = ref(false)
const currentPhaseIndex = ref(0)
const elapsedTime = ref(0)
const timer = ref<number | null>(null)

const isPaused = computed(() => sessionStore.isPaused)
const currentPlan = computed(() => sessionStore.currentPlan)

const currentPhase = computed<TherapyPhase | null>(() => {
  if (!currentPlan.value?.phases?.length) return null
  return currentPlan.value.phases[currentPhaseIndex.value] || null
})

const totalDuration = computed(() => currentPlan.value?.duration || 900)

const remainingTime = computed(() => {
  return Math.max(0, totalDuration.value - elapsedTime.value)
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
    if (!isPaused.value) {
      elapsedTime.value++
      
      // 检查是否完成
      if (elapsedTime.value >= totalDuration.value) {
        endTherapy()
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

const skipPhase = () => {
  if (currentPlan.value?.phases && currentPhaseIndex.value < currentPlan.value.phases.length - 1) {
    currentPhaseIndex.value++
  }
}

const endTherapy = async () => {
  if (timer.value) {
    clearInterval(timer.value)
  }
  await sessionStore.endSession()
  router.push('/report')
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
    padding: 48px;
    max-width: 400px;
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
    margin-bottom: 32px;
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
  
  &__controls {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
  }
  
  &__hint {
    font-size: 0.875rem;
    color: var(--text-muted);
  }
  
  &__modal {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
  }
  
  &__modal-content {
    max-width: 400px;
    text-align: center;
    
    h3 {
      margin-bottom: 16px;
    }
    
    p {
      color: var(--text-secondary);
      margin-bottom: 24px;
    }
  }
  
  &__modal-actions {
    display: flex;
    gap: 16px;
    justify-content: center;
  }
}
</style>
