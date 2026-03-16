<template>
  <div class="report-page page">
    <div class="report-page__content animate-fadeIn">
      <h1 class="page__title">{{ $t('report.title') }}</h1>
      
      <!-- 加载中 -->
      <div v-if="loading" class="report-page__loading">
        <div class="report-page__spinner"></div>
        <p>正在生成报告...</p>
      </div>
      
      <template v-else>
        <!-- 情绪变化卡片 -->
        <div class="report-page__emotion-change card">
          <h2>{{ $t('report.emotionChange') }}</h2>
          <div class="report-page__emotions">
            <div class="report-page__emotion-item">
              <span class="report-page__emotion-label">{{ $t('report.initialEmotion') }}</span>
              <span class="report-page__emotion-emoji">{{ getEmotionEmoji(displayInitialEmotion) }}</span>
              <span class="report-page__emotion-name">
                {{ $t(`emotions.${displayInitialEmotion || 'neutral'}`) }}
              </span>
            </div>
            <div class="report-page__arrow">
              <svg width="48" height="24" viewBox="0 0 48 24" fill="none" aria-hidden="true">
                <path d="M0 12H44M44 12L34 2M44 12L34 22" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="report-page__emotion-item">
              <span class="report-page__emotion-label">{{ $t('report.finalEmotion') }}</span>
              <span class="report-page__emotion-emoji">{{ getEmotionEmoji(displayFinalEmotion) }}</span>
              <span class="report-page__emotion-name">
                {{ $t(`emotions.${displayFinalEmotion || 'neutral'}`) }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- 情绪曲线图 -->
        <div class="report-page__chart card">
          <h2>{{ $t('report.emotionCurve') }}</h2>
          <div class="report-page__chart-container">
            <canvas ref="chartRef"></canvas>
          </div>
        </div>
        
        <!-- 统计信息 -->
        <div class="report-page__stats">
          <div class="report-page__stat card">
            <span class="report-page__stat-label">{{ $t('report.duration') }}</span>
            <span class="report-page__stat-value">{{ formatDuration(displayDuration) }}</span>
          </div>
          <div class="report-page__stat card">
            <span class="report-page__stat-label">{{ $t('report.improvement') }}</span>
            <span class="report-page__stat-value" :class="improvementClass">
              {{ improvementText }}
            </span>
          </div>
        </div>
        
        <!-- 总结 -->
        <div class="report-page__summary card">
          <h2>{{ $t('report.summary') }}</h2>
          <p>{{ displaySummary }}</p>
        </div>
        
        <!-- 建议 -->
        <div class="report-page__suggestions card">
          <h2>{{ $t('report.suggestion') }}</h2>
          <ul>
            <li v-for="(suggestion, index) in displaySuggestions" :key="index">
              {{ suggestion }}
            </li>
          </ul>
        </div>
        
        <!-- 操作按钮 -->
        <div class="report-page__actions">
          <button class="btn btn--primary" @click="newSession">
            {{ $t('report.newSession') }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useSessionStore } from '@/stores/session'
import { Chart, registerables } from 'chart.js'
// chart.js 类型已通过 registerables 注册

Chart.register(...registerables)

const router = useRouter()
useI18n()
const sessionStore = useSessionStore()

const chartRef = ref<HTMLCanvasElement | null>(null)
const loading = ref(true)

// 后端报告数据
const backendReport = ref<any>(null)

// 显示用的计算属性：优先使用后端数据，降级到本地数据
const displayInitialEmotion = computed(() => {
  if (backendReport.value?.initial_emotion) {
    return backendReport.value.initial_emotion.category
  }
  return sessionStore.initialEmotion?.category || 'neutral'
})

const displayFinalEmotion = computed(() => {
  if (backendReport.value?.final_emotion) {
    return backendReport.value.final_emotion.category
  }
  return sessionStore.latestEmotion?.category || 'neutral'
})

const displayDuration = computed(() => {
  if (backendReport.value?.duration_minutes) {
    return backendReport.value.duration_minutes * 60
  }
  const session = sessionStore.currentSession
  if (!session?.startTime) return 0
  const end = session.endTime || new Date()
  return Math.round((end.getTime() - new Date(session.startTime).getTime()) / 1000)
})

const improvement = computed(() => {
  if (backendReport.value?.effectiveness?.emotion_improvement != null) {
    return backendReport.value.effectiveness.emotion_improvement
  }
  return sessionStore.emotionImprovement
})

const improvementClass = computed(() => {
  if (improvement.value > 0.2) return 'positive'
  if (improvement.value < -0.2) return 'negative'
  return 'neutral'
})

const improvementText = computed(() => {
  if (backendReport.value?.effectiveness?.rating) {
    return backendReport.value.effectiveness.rating
  }
  const percent = Math.round(Math.abs(improvement.value) * 100)
  if (improvement.value > 0.2) return `+${percent}%`
  if (improvement.value < -0.2) return `-${percent}%`
  return '稳定'
})

const displaySummary = computed(() => {
  if (backendReport.value?.summary_text) {
    return backendReport.value.summary_text
  }
  // 降级：本地生成
  if (improvement.value > 0.3) {
    return '本次疗愈效果显著，您的情绪状态有了明显改善。建议保持良好的作息习惯，继续关注自己的情绪变化。'
  } else if (improvement.value > 0) {
    return '本次疗愈有一定效果，您的情绪状态略有改善。建议可以尝试更长时间的疗愈，或者选择其他疗愈方案。'
  }
  return '本次疗愈过程中您的情绪保持稳定。如果您仍感到不适，建议尝试其他疗愈方案或寻求专业帮助。'
})

const displaySuggestions = computed(() => {
  if (backendReport.value?.recommendations?.length) {
    return backendReport.value.recommendations
  }
  return [
    '保持规律的作息时间，每天保证 7-8 小时的睡眠',
    '适当进行户外活动，接触自然环境有助于放松心情',
    '可以尝试每天进行 10-15 分钟的冥想练习',
    '如果情绪持续低落，建议寻求专业心理咨询师的帮助'
  ]
})

const getEmotionEmoji = (category?: string) => {
  const emojis: Record<string, string> = {
    happy: '😊', sad: '😢', angry: '😠', anxious: '😰',
    tired: '😴', fearful: '😨', surprised: '😲', disgusted: '😖', neutral: '😐'
  }
  return emojis[category || 'neutral'] || '😐'
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins} 分 ${secs} 秒`
}

const initChart = () => {
  if (!chartRef.value) return
  const ctx = chartRef.value.getContext('2d')
  if (!ctx) return

  // 优先使用后端情绪曲线数据
  let labels: string[] = []
  let data: number[] = []

  if (backendReport.value?.emotion_curve?.length) {
    labels = backendReport.value.emotion_curve.map(
      (p: any) => p.phase_name || new Date(p.timestamp).toLocaleTimeString()
    )
    data = backendReport.value.emotion_curve.map((p: any) => p.valence)
  } else {
    // 降级：使用本地 store 数据
    const history = sessionStore.emotionHistory
    labels = history.map((_, i) => `${i + 1}`)
    data = history.map(e => e.valence)
  }

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '情绪效价',
        data,
        borderColor: '#4ecdc4',
        backgroundColor: 'rgba(78, 205, 196, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 6,
        pointBackgroundColor: '#4ecdc4'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: -1, max: 1,
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: '#a0a0a0' }
        },
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.1)' },
          ticks: { color: '#a0a0a0' }
        }
      },
      plugins: { legend: { display: false } }
    }
  })
}

const newSession = () => {
  sessionStore.resetSession()
  router.push('/')
}

onMounted(async () => {
  // 尝试从后端获取报告
  const report = await sessionStore.fetchReport()
  if (report) {
    backendReport.value = report
  }
  loading.value = false

  // 等待 DOM 更新后初始化图表
  setTimeout(() => initChart(), 100)
})
</script>

<style lang="scss" scoped>
.report-page {
  padding: 40px;
  overflow-y: auto;
  
  &__content {
    max-width: 800px;
    margin: 0 auto;
  }
  
  &__loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    padding: 60px 0;
  }
  
  &__spinner {
    width: 48px;
    height: 48px;
    border: 4px solid var(--bg-tertiary);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  &__emotion-change {
    margin-bottom: 24px;
    
    h2 {
      font-size: 1.125rem;
      margin-bottom: 24px;
      color: var(--text-secondary);
    }
  }
  
  &__emotions {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 32px;
  }
  
  &__emotion-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  
  &__emotion-label {
    font-size: 0.875rem;
    color: var(--text-muted);
  }
  
  &__emotion-emoji {
    font-size: 48px;
  }
  
  &__emotion-name {
    font-size: 1.125rem;
    font-weight: 500;
  }
  
  &__arrow {
    color: var(--accent-primary);
  }
  
  &__chart {
    margin-bottom: 24px;
    
    h2 {
      font-size: 1.125rem;
      margin-bottom: 16px;
      color: var(--text-secondary);
    }
  }
  
  &__chart-container {
    height: 200px;
  }
  
  &__stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }
  
  &__stat {
    text-align: center;
  }
  
  &__stat-label {
    display: block;
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: 8px;
  }
  
  &__stat-value {
    font-size: 1.5rem;
    font-weight: 600;
    
    &.positive { color: var(--success); }
    &.negative { color: var(--error); }
    &.neutral { color: var(--text-secondary); }
  }
  
  &__summary,
  &__suggestions {
    margin-bottom: 24px;
    
    h2 {
      font-size: 1.125rem;
      margin-bottom: 16px;
      color: var(--text-secondary);
    }
    
    p {
      line-height: 1.8;
      color: var(--text-primary);
    }
    
    ul {
      list-style: none;
      
      li {
        position: relative;
        padding-left: 24px;
        margin-bottom: 12px;
        line-height: 1.6;
        
        &::before {
          content: '•';
          position: absolute;
          left: 0;
          color: var(--accent-primary);
        }
      }
    }
  }
  
  &__actions {
    display: flex;
    gap: 16px;
    justify-content: center;
    margin-top: 32px;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
