// 情绪类别
export type EmotionCategory = 
  | 'happy' 
  | 'sad' 
  | 'angry' 
  | 'anxious' 
  | 'tired' 
  | 'fearful' 
  | 'surprised' 
  | 'disgusted' 
  | 'neutral'

// 情绪状态
export interface EmotionState {
  category: EmotionCategory
  intensity: number  // 0-1
  valence: number    // -1 到 1
  arousal: number    // 0-1
  confidence: number // 0-1
  timestamp: Date
}

// 疗愈方案
export interface TherapyPlan {
  id: string
  name: string
  description: string
  targetEmotions: EmotionCategory[]
  intensity: 'low' | 'medium' | 'high'
  style: 'chinese' | 'modern'
  duration: number  // 秒
  phases: TherapyPhase[]
}

// 疗愈阶段
export interface TherapyPhase {
  name: string
  duration: number  // 秒
  description?: string
}

// 会话
export interface Session {
  id: string
  startTime: Date
  endTime: Date | null
  initialEmotion: EmotionState
  finalEmotion: EmotionState | null
  planUsed: TherapyPlan
}

// 疗愈报告
export interface TherapyReport {
  sessionId: string
  startTime: Date
  endTime: Date
  duration: number
  initialEmotion: EmotionState
  finalEmotion: EmotionState
  emotionHistory: EmotionState[]
  improvement: number
  summary: string
  suggestions: string[]
}

// API 响应
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

// ============== Admin Types ==============

// 管理员角色
export type AdminRole = 'super_admin' | 'admin' | 'operator'

// 管理员登录请求
export interface AdminLoginRequest {
  username: string
  password: string
}

// 管理员登录响应
export interface AdminLoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

// 管理员信息
export interface AdminInfo {
  username: string
  role: AdminRole
}

// 设备状态
export interface DeviceStatus {
  name: string
  type: string
  connected: boolean
  state?: Record<string, any>
  last_updated?: string
}

// 设备状态响应
export interface DeviceStatusResponse {
  devices: DeviceStatus[]
  total: number
  connected_count: number
}

// 使用统计
export interface UsageStats {
  total_sessions: number
  total_duration_seconds: number
  avg_session_duration_seconds: number
  avg_improvement?: number
  sessions_today: number
  sessions_this_week: number
  sessions_this_month: number
  most_common_emotion?: string
  most_used_plan?: string
  emotion_distribution: Record<string, number>
  daily_sessions: Array<{ date: string; count: number }>
}

// 日志条目
export interface LogEntry {
  id: number
  timestamp: string
  level: string
  module: string
  message: string
  details?: Record<string, any>
}

// 日志查询响应
export interface LogQueryResponse {
  logs: LogEntry[]
  total: number
  page: number
  page_size: number
}

// 疗愈方案配置
export interface TherapyPlanConfig {
  id: string
  name: string
  description?: string
  target_emotions: string[]
  intensity: string
  style: string
  duration: number
  phases?: Array<Record<string, any>>
}

// 内容项
export interface ContentItem {
  id: string
  type: 'audio' | 'visual' | 'plan'
  name: string
  path?: string
  metadata?: Record<string, any>
}

// 会话列表项
export interface SessionListItem {
  id: string
  start_time: string
  end_time?: string
  initial_emotion_category?: string
  initial_emotion_intensity?: number
  final_emotion_category?: string
  final_emotion_intensity?: number
  plan_id?: string
  duration_seconds?: number
}


// ============== Electron API Types ==============

// Electron API 接口定义
export interface ElectronAPI {
  minimizeWindow: () => void
  maximizeWindow: () => void
  closeWindow: () => void
  isMaximized: () => Promise<boolean>
  onMaximizedChange: (callback: (isMaximized: boolean) => void) => void
}

// 扩展 Window 接口
declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}
