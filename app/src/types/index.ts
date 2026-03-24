export type EmotionCategory =
  | "happy"
  | "sad"
  | "angry"
  | "anxious"
  | "tired"
  | "fearful"
  | "surprised"
  | "disgusted"
  | "neutral";

export interface EmotionState {
  category: EmotionCategory;
  intensity: number;
  valence: number;
  arousal: number;
  confidence: number;
  timestamp: Date;
}

export interface TherapyScreenPrompt {
  startSecond: number;
  endSecond: number;
  title: string;
  lines: string[];
}

export interface TherapyPlan {
  id: string;
  name: string;
  description: string;
  targetEmotions: EmotionCategory[];
  intensity: "low" | "medium" | "high";
  runtimeIntensityLevel?: number;
  style: "chinese" | "modern";
  duration: number;
  phases: TherapyPhase[];
  screenPrompts?: TherapyScreenPrompt[];
}

export interface TherapyPhase {
  name: string;
  duration: number;
  description?: string;
}

export type TherapyAdjustmentDirection = "relax" | "intensify";

export interface TherapyRuntimeAdjustmentResponse {
  success: boolean;
  changed: boolean;
  atBoundary?: boolean;
  targetIntensity: TherapyPlan["intensity"];
  plan?: TherapyPlan;
  message?: string;
}

export interface Session {
  id: string;
  startTime: Date;
  endTime: Date | null;
  initialEmotion: EmotionState;
  finalEmotion: EmotionState | null;
  planUsed: TherapyPlan;
}

export interface TherapyReport {
  sessionId: string;
  startTime: Date;
  endTime: Date;
  duration: number;
  initialEmotion: EmotionState;
  finalEmotion: EmotionState;
  emotionHistory: EmotionState[];
  improvement: number;
  summary: string;
  suggestions: string[];
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export type AdminRole = "super_admin" | "admin" | "operator";

export interface AdminLoginRequest {
  username: string;
  password: string;
}

export interface AdminLoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AdminInfo {
  username: string;
  role: AdminRole;
}

export interface DeviceStatus {
  name: string;
  type: string;
  connected: boolean;
  state?: Record<string, any>;
  last_updated?: string;
}

export interface DeviceStatusResponse {
  devices: DeviceStatus[];
  total: number;
  connected_count: number;
}

export interface UsageStats {
  total_sessions: number;
  total_duration_seconds: number;
  avg_session_duration_seconds: number;
  avg_improvement?: number;
  sessions_today: number;
  sessions_this_week: number;
  sessions_this_month: number;
  most_common_emotion?: string;
  most_used_plan?: string;
  emotion_distribution: Record<string, number>;
  daily_sessions: Array<{ date: string; count: number }>;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  level: string;
  module: string;
  message: string;
  details?: Record<string, any>;
}

export interface LogQueryResponse {
  logs: LogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface TherapyPlanConfig {
  id: string;
  name: string;
  description?: string;
  target_emotions: string[];
  intensity: string;
  style: string;
  duration: number;
  phases?: Array<Record<string, any>>;
}

export interface ContentItem {
  id: string;
  type: "audio" | "visual" | "plan";
  name: string;
  path?: string;
  metadata?: Record<string, any>;
}

export interface SessionListItem {
  id: string;
  start_time: string;
  end_time?: string;
  initial_emotion_category?: string;
  initial_emotion_intensity?: number;
  final_emotion_category?: string;
  final_emotion_intensity?: number;
  plan_id?: string;
  duration_seconds?: number;
}

export interface ElectronAPI {
  minimizeWindow: () => void;
  maximizeWindow: () => void;
  closeWindow: () => void;
  isMaximized: () => Promise<boolean>;
  onMaximizedChange: (callback: (isMaximized: boolean) => void) => void;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}
