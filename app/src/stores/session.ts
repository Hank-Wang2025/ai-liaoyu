import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { EmotionState, TherapyPlan, Session } from '@/types'
import { therapyApi, reportApi } from '@/api'

export const useSessionStore = defineStore('session', () => {
  // 状态
  const currentSession = ref<Session | null>(null)
  const emotionHistory = ref<EmotionState[]>([])
  const currentPlan = ref<TherapyPlan | null>(null)
  const isTherapyActive = ref(false)
  const isPaused = ref(false)
  // 后端会话 ID（与后端同步）
  const backendSessionId = ref<string | null>(null)
  // 后端方案 ID
  const backendPlanId = ref<string | null>(null)

  // 计算属性
  const initialEmotion = computed(() => emotionHistory.value[0] || null)
  const latestEmotion = computed(() => emotionHistory.value[emotionHistory.value.length - 1] || null)

  const emotionImprovement = computed(() => {
    if (!initialEmotion.value || !latestEmotion.value) return 0
    // 计算情绪改善程度（效价变化）
    return latestEmotion.value.valence - initialEmotion.value.valence
  })

  // 方法：通过后端启动疗愈会话
  async function startSession(emotion: EmotionState, plan: TherapyPlan) {
    // 本地状态
    currentSession.value = {
      id: '', // 将由后端返回
      startTime: new Date(),
      endTime: null,
      initialEmotion: emotion,
      finalEmotion: null,
      planUsed: plan
    }
    emotionHistory.value = [emotion]
    currentPlan.value = plan
    backendPlanId.value = plan.id

    // 调用后端启动疗愈
    try {
      const result = await therapyApi.startTherapy(plan.id, {
        category: emotion.category,
        intensity: emotion.intensity,
        valence: emotion.valence,
        arousal: emotion.arousal
      })
      backendSessionId.value = result.session_id
      if (currentSession.value) {
        currentSession.value.id = result.session_id
      }
    } catch (err) {
      console.error('后端启动疗愈失败，使用本地模式:', err)
      // 降级：使用本地 ID
      const localId = crypto.randomUUID()
      backendSessionId.value = localId
      if (currentSession.value) {
        currentSession.value.id = localId
      }
    }

    isTherapyActive.value = true
    isPaused.value = false
  }

  function addEmotionRecord(emotion: EmotionState) {
    emotionHistory.value.push(emotion)
  }

  async function pauseTherapy() {
    isPaused.value = true
    if (backendSessionId.value) {
      try {
        await therapyApi.pauseTherapy(backendSessionId.value)
      } catch (err) {
        console.error('后端暂停失败:', err)
      }
    }
  }

  async function resumeTherapy() {
    isPaused.value = false
    if (backendSessionId.value) {
      try {
        await therapyApi.resumeTherapy(backendSessionId.value)
      } catch (err) {
        console.error('后端恢复失败:', err)
      }
    }
  }

  async function endSession() {
    if (currentSession.value) {
      currentSession.value.endTime = new Date()
      currentSession.value.finalEmotion = latestEmotion.value
    }
    // 通知后端结束
    if (backendSessionId.value) {
      try {
        await therapyApi.endTherapy(backendSessionId.value)
      } catch (err) {
        console.error('后端结束会话失败:', err)
      }
    }
    isTherapyActive.value = false
    isPaused.value = false
  }

  // 从后端获取报告
  async function fetchReport() {
    if (!backendSessionId.value) return null
    try {
      return await reportApi.getReport(backendSessionId.value)
    } catch (err) {
      console.error('获取报告失败:', err)
      return null
    }
  }

  function resetSession() {
    currentSession.value = null
    emotionHistory.value = []
    currentPlan.value = null
    isTherapyActive.value = false
    isPaused.value = false
    backendSessionId.value = null
    backendPlanId.value = null
  }

  return {
    currentSession,
    emotionHistory,
    currentPlan,
    isTherapyActive,
    isPaused,
    backendSessionId,
    backendPlanId,
    initialEmotion,
    latestEmotion,
    emotionImprovement,
    startSession,
    addEmotionRecord,
    pauseTherapy,
    resumeTherapy,
    endSession,
    fetchReport,
    resetSession
  }
})
