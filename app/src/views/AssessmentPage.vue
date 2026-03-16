<template>
  <div class="assessment-page page">
    <div class="assessment-page__content animate-fadeIn">
      <h1 class="page__title">{{ $t('assessment.title') }}</h1>
      <p class="page__subtitle">{{ $t('assessment.subtitle') }}</p>
      
      <!-- 语音录制区域 -->
      <div v-if="step === 'voice'" class="assessment-page__voice">
        <p class="assessment-page__prompt">{{ $t('assessment.voicePrompt') }}</p>
        
        <button 
          class="assessment-page__mic-btn"
          :class="{ 'recording': isRecording }"
          @click="toggleRecording"
          :aria-label="isRecording ? '停止录音' : '开始录音'"
        >
          <svg v-if="!isRecording" width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
            <path d="M24 4C20.6863 4 18 6.68629 18 10V24C18 27.3137 20.6863 30 24 30C27.3137 30 30 27.3137 30 24V10C30 6.68629 27.3137 4 24 4Z" 
                  stroke="currentColor" stroke-width="3"/>
            <path d="M12 22V24C12 30.6274 17.3726 36 24 36C30.6274 36 36 30.6274 36 24V22" 
                  stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            <path d="M24 36V44M18 44H30" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          </svg>
          <svg v-else width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
            <rect x="14" y="14" width="20" height="20" rx="4" fill="currentColor"/>
          </svg>
        </button>
        
        <p v-if="isRecording" class="assessment-page__status animate-pulse">
          {{ $t('assessment.recording') }}
        </p>
        
        <!-- 录音波形 -->
        <div v-if="isRecording" class="assessment-page__waveform">
          <div v-for="i in 5" :key="i" class="assessment-page__wave-bar"></div>
        </div>
      </div>
      
      <!-- 分析中 -->
      <div v-else-if="step === 'analyzing'" class="assessment-page__analyzing">
        <div class="assessment-page__spinner"></div>
        <p>{{ $t('assessment.analyzing') }}</p>
        <p v-if="analysisError" class="assessment-page__error">{{ analysisError }}</p>
      </div>
      
      <!-- 结果展示 -->
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
        
        <div class="assessment-page__plan card" v-if="recommendedPlan">
          <p class="assessment-page__plan-label">{{ $t('assessment.suggestion') }}</p>
          <p class="assessment-page__plan-name">{{ recommendedPlan.name }}</p>
          <p class="assessment-page__plan-desc">{{ recommendedPlan.description }}</p>
        </div>
        
        <button class="btn btn--primary btn--large" @click="startTherapy">
          {{ $t('common.start') }}
        </button>
      </div>
      
      <!-- 返回按钮 -->
      <button class="btn btn--ghost assessment-page__back" @click="goBack">
        {{ $t('common.back') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { emotionApi, therapyApi } from '@/api'
import type { EmotionState, TherapyPlan, EmotionCategory } from '@/types'

const router = useRouter()
const sessionStore = useSessionStore()

const step = ref<'voice' | 'analyzing' | 'result'>('voice')
const isRecording = ref(false)
const emotionResult = ref<EmotionState | null>(null)
const recommendedPlan = ref<TherapyPlan | null>(null)
const analysisError = ref<string | null>(null)

// 录音相关
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

const getEmotionEmoji = (category?: EmotionCategory) => {
  const emojis: Record<EmotionCategory, string> = {
    happy: '😊', sad: '😢', angry: '😠', anxious: '😰',
    tired: '😴', fearful: '😨', surprised: '😲', disgusted: '😖', neutral: '😐'
  }
  return emojis[category || 'neutral']
}

// emotion2vec 情绪类别映射到前端 EmotionCategory
const mapEmotion2vecCategory = (emotion: string): EmotionCategory => {
  const mapping: Record<string, EmotionCategory> = {
    'happy': 'happy', 'angry': 'angry', 'sad': 'sad',
    'surprised': 'surprised', 'disgusted': 'disgusted', 'fearful': 'fearful',
    'neutral': 'neutral', 'anxious': 'anxious', 'tired': 'tired',
    // emotion2vec 可能返回的其他标签
    'excited': 'happy', 'contempt': 'disgusted', 'other': 'neutral'
  }
  return mapping[emotion] || 'neutral'
}

const toggleRecording = async () => {
  if (isRecording.value) {
    // 停止录音
    isRecording.value = false
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
  } else {
    // 开始录音
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder = new MediaRecorder(stream)
      audioChunks = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // 停止所有音轨
        stream.getTracks().forEach(track => track.stop())
        // 合成音频 Blob
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
        await analyzeAudio(audioBlob)
      }

      mediaRecorder.start()
      isRecording.value = true
    } catch (err) {
      console.error('无法访问麦克风:', err)
      analysisError.value = '无法访问麦克风，请检查权限设置'
    }
  }
}

const analyzeAudio = async (audioBlob: Blob) => {
  step.value = 'analyzing'
  analysisError.value = null

  try {
    // 调用后端综合音频分析 API
    const result = await emotionApi.analyzeCombined(audioBlob)

    // 从 emotion2vec 结果构建情绪状态
    const category = mapEmotion2vecCategory(result.emotion2vec_emotion)
    emotionResult.value = {
      category,
      intensity: result.intensity,
      valence: result.valence,
      arousal: result.arousal,
      confidence: result.confidence,
      timestamp: new Date()
    }

    // 调用后端方案推荐 API
    await matchPlan(category, result.intensity, result.valence, result.arousal)

    step.value = 'result'
  } catch (err: any) {
    console.error('音频分析失败:', err)
    // 降级：使用模拟数据
    await fallbackAnalysis()
  }
}

const matchPlan = async (
  category: string, intensity: number, valence: number, arousal: number
) => {
  try {
    const matchResult = await therapyApi.getRecommendedPlan({
      category, intensity, valence, arousal, confidence: 0.8
    })

    if (matchResult.best_match && matchResult.matched_plans?.length > 0) {
      const best = matchResult.matched_plans[0]
      recommendedPlan.value = {
        id: best.id,
        name: best.name,
        description: `匹配度: ${Math.round(best.score * 100)}% | 风格: ${best.style} | 时长: ${Math.round(best.duration / 60)}分钟`,
        targetEmotions: [],
        intensity: best.intensity as any,
        style: best.style as any,
        duration: best.duration,
        phases: []
      }
    }
  } catch (err) {
    console.error('方案匹配失败，使用默认方案:', err)
    recommendedPlan.value = {
      id: 'quick_calm',
      name: '快速平静方案',
      description: '通过深呼吸引导和舒缓音乐，帮助您放松身心',
      targetEmotions: [category as EmotionCategory],
      intensity: 'medium',
      style: 'modern',
      duration: 900,
      phases: []
    }
  }
}

// 降级：当后端不可用时使用模拟分析
const fallbackAnalysis = async () => {
  analysisError.value = '后端服务暂不可用，使用本地评估'
  await new Promise(resolve => setTimeout(resolve, 1500))

  emotionResult.value = {
    category: 'neutral',
    intensity: 0.5,
    valence: 0.0,
    arousal: 0.5,
    confidence: 0.5,
    timestamp: new Date()
  }

  recommendedPlan.value = {
    id: 'quick_calm',
    name: '快速平静方案',
    description: '通过深呼吸引导和舒缓音乐，帮助您放松身心',
    targetEmotions: ['neutral'],
    intensity: 'medium',
    style: 'modern',
    duration: 900,
    phases: []
  }

  step.value = 'result'
}

const startTherapy = () => {
  if (emotionResult.value && recommendedPlan.value) {
    sessionStore.startSession(emotionResult.value, recommendedPlan.value)
    router.push('/therapy')
  }
}

const goBack = () => {
  if (step.value === 'voice') {
    router.push('/')
  } else {
    step.value = 'voice'
  }
}
</script>

<style lang="scss" scoped>
.assessment-page {
  &__content {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    max-width: 600px;
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
  }
  
  &__mic-btn {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: var(--bg-tertiary);
    border: 3px solid var(--border-color);
    color: var(--text-primary);
    cursor: pointer;
    transition: all var(--transition-normal);
    
    &:hover {
      border-color: var(--accent-primary);
      transform: scale(1.05);
    }
    
    &.recording {
      background: var(--error);
      border-color: var(--error);
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
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
