import axios from 'axios'
import type { 
  AdminLoginRequest,
  AdminLoginResponse,
  AdminInfo,
  DeviceStatusResponse,
  UsageStats,
  LogQueryResponse,
  TherapyPlanConfig,
  ContentItem,
  SessionListItem
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Token management
const TOKEN_KEY = 'admin_token'

export const getStoredToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY)
}

export const setStoredToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token)
}

export const removeStoredToken = (): void => {
  localStorage.removeItem(TOKEN_KEY)
}

// Add auth interceptor
api.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token && config.url?.startsWith('/admin')) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 情绪分析 API
export const emotionApi = {
  // 分析音频（SenseVoice 语音识别）
  analyzeAudio: async (audioBlob: Blob): Promise<any> => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.wav')
    const response = await api.post('/emotion/analyze/audio', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // 分析音频情绪（emotion2vec+ 细粒度情绪）
  analyzeEmotion2vec: async (audioBlob: Blob): Promise<any> => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.wav')
    const response = await api.post('/emotion/analyze/emotion2vec', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // 综合音频分析（SenseVoice + emotion2vec+）
  analyzeCombined: async (audioBlob: Blob, language = 'auto'): Promise<any> => {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.wav')
    formData.append('language', language)
    const response = await api.post('/emotion/analyze/combined', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // 分析面部表情（图片文件上传）
  analyzeFace: async (imageBlob: Blob): Promise<any> => {
    const formData = new FormData()
    formData.append('image', imageBlob, 'capture.jpg')
    const response = await api.post('/emotion/analyze/face', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // 分析面部表情（Base64 编码）
  analyzeFaceBase64: async (imageData: string): Promise<any> => {
    const formData = new FormData()
    formData.append('image_data', imageData)
    const response = await api.post('/emotion/analyze/face/base64', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // 分析生理信号（HRV）
  analyzeBio: async (rrIntervals: number[], heartRate?: number): Promise<any> => {
    const response = await api.post('/emotion/analyze/bio', {
      rr_intervals: rrIntervals,
      heart_rate: heartRate
    })
    return response.data
  },

  // 多模态情绪融合
  fuseEmotions: async (data: {
    audio_emotion?: string
    audio_scores?: Record<string, number>
    audio_intensity?: number
    face_expression?: string
    face_scores?: Record<string, number>
    face_confidence?: number
    face_detected?: boolean
    bio_stress_index?: number
    bio_is_valid?: boolean
    bio_heart_rate?: number
  }): Promise<any> => {
    const response = await api.post('/emotion/fuse', data)
    return response.data
  }
}

// 疗愈 API
export const therapyApi = {
  // 获取推荐方案（基于情绪匹配）
  getRecommendedPlan: async (emotion: {
    category: string
    intensity: number
    valence?: number
    arousal?: number
    confidence?: number
  }, style?: string): Promise<any> => {
    const response = await api.post('/therapy/recommend', {
      emotion: {
        category: emotion.category,
        intensity: emotion.intensity,
        valence: emotion.valence ?? 0.0,
        arousal: emotion.arousal ?? 0.5,
        confidence: emotion.confidence ?? 0.8
      },
      style
    })
    return response.data
  },

  // 获取所有方案
  getAllPlans: async (): Promise<any> => {
    const response = await api.get('/therapy/plans')
    return response.data
  },

  // 获取方案详情
  getPlanDetail: async (planId: string): Promise<any> => {
    const response = await api.get(`/therapy/plans/${planId}`)
    return response.data
  },

  // 开始疗愈（创建会话并执行方案）
  startTherapy: async (planId: string, emotion?: {
    category: string
    intensity?: number
    valence?: number
    arousal?: number
  }): Promise<any> => {
    const response = await api.post('/therapy/start', {
      plan_id: planId,
      emotion_category: emotion?.category,
      emotion_intensity: emotion?.intensity,
      emotion_valence: emotion?.valence,
      emotion_arousal: emotion?.arousal
    })
    return response.data
  },

  // 暂停疗愈
  pauseTherapy: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/pause/${sessionId}`)
    return response.data
  },

  // 继续疗愈
  resumeTherapy: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/resume/${sessionId}`)
    return response.data
  },

  // 结束疗愈
  endTherapy: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/end/${sessionId}`)
    return response.data
  }
}

// 报告 API
export const reportApi = {
  // 获取报告
  getReport: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/session/${sessionId}/report`)
    return response.data
  }
}

// 管理后台 API
export const adminApi = {
  // 登录
  login: async (credentials: AdminLoginRequest): Promise<AdminLoginResponse> => {
    const response = await api.post('/admin/login', credentials)
    return response.data
  },
  
  // 登出
  logout: async (): Promise<void> => {
    await api.post('/admin/logout')
    removeStoredToken()
  },
  
  // 验证 token
  verifyToken: async (): Promise<AdminInfo> => {
    const response = await api.get('/admin/verify')
    return response.data
  },
  
  // 获取设备状态
  getDeviceStatus: async (): Promise<DeviceStatusResponse> => {
    const response = await api.get('/admin/devices')
    return response.data
  },
  
  // 获取使用统计
  getUsageStats: async (): Promise<UsageStats> => {
    const response = await api.get('/admin/stats')
    return response.data
  },
  
  // 获取系统日志
  getLogs: async (params: {
    level?: string
    module?: string
    page?: number
    page_size?: number
  }): Promise<LogQueryResponse> => {
    const response = await api.get('/admin/logs', { params })
    return response.data
  },
  
  // 获取日志级别列表
  getLogLevels: async (): Promise<{ levels: string[] }> => {
    const response = await api.get('/admin/logs/levels')
    return response.data
  },
  
  // 获取日志模块列表
  getLogModules: async (): Promise<{ modules: string[] }> => {
    const response = await api.get('/admin/logs/modules')
    return response.data
  },
  
  // 获取疗愈方案列表
  getTherapyPlans: async (): Promise<{ plans: TherapyPlanConfig[]; total: number }> => {
    const response = await api.get('/admin/config/plans')
    return response.data
  },
  
  // 创建疗愈方案
  createTherapyPlan: async (plan: TherapyPlanConfig): Promise<{ message: string; id: string }> => {
    const response = await api.post('/admin/config/plans', plan)
    return response.data
  },
  
  // 更新疗愈方案
  updateTherapyPlan: async (planId: string, plan: TherapyPlanConfig): Promise<{ message: string }> => {
    const response = await api.put(`/admin/config/plans/${planId}`, plan)
    return response.data
  },
  
  // 删除疗愈方案
  deleteTherapyPlan: async (planId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/admin/config/plans/${planId}`)
    return response.data
  },
  
  // 获取设备配置
  getDeviceConfig: async (): Promise<{ devices: Record<string, any> }> => {
    const response = await api.get('/admin/config/devices')
    return response.data
  },
  
  // 更新设备配置
  updateDeviceConfig: async (deviceType: string, settings: Record<string, any>): Promise<{ message: string }> => {
    const response = await api.put('/admin/config/devices', { device_type: deviceType, settings })
    return response.data
  },
  
  // 获取内容库
  getContentLibrary: async (contentType?: string): Promise<{ content: ContentItem[]; total: number }> => {
    const response = await api.get('/admin/config/content', { params: { content_type: contentType } })
    return response.data
  },
  
  // 获取会话列表
  getSessions: async (params: { page?: number; page_size?: number }): Promise<{
    sessions: SessionListItem[]
    total: number
    page: number
    page_size: number
  }> => {
    const response = await api.get('/admin/sessions', { params })
    return response.data
  },
  
  // 获取会话详情
  getSessionDetail: async (sessionId: string): Promise<{ session: SessionListItem; adjustments: any[] }> => {
    const response = await api.get(`/admin/sessions/${sessionId}`)
    return response.data
  }
}

export default api
