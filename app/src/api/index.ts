import axios from "axios";
import type {
  AdminInfo,
  AdminLoginRequest,
  AdminLoginResponse,
  ContentItem,
  DeviceStatusResponse,
  LogQueryResponse,
  SessionListItem,
  TherapyAdjustmentDirection,
  TherapyPlanConfig,
  TherapyPlan,
  TherapyRuntimeAdjustmentResponse,
  UsageStats,
} from "@/types";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

const TOKEN_KEY = "admin_token";
type TherapyPlanDetailResponse = Partial<TherapyPlan> & Record<string, any>;

export const getStoredToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setStoredToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const removeStoredToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token && config.url?.startsWith("/admin")) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const emotionApi = {
  analyzeAudio: async (audioBlob: Blob): Promise<any> => {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.wav");
    const response = await api.post("/emotion/analyze/audio", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  analyzeEmotion2vec: async (audioBlob: Blob): Promise<any> => {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.wav");
    const response = await api.post("/emotion/analyze/emotion2vec", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  analyzeCombined: async (audioBlob: Blob, language = "auto"): Promise<any> => {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.wav");
    formData.append("language", language);
    const response = await api.post("/emotion/analyze/combined", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  analyzeFace: async (imageBlob: Blob): Promise<any> => {
    const formData = new FormData();
    formData.append("image", imageBlob, "capture.jpg");
    const response = await api.post("/emotion/analyze/face", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  analyzeFaceBase64: async (imageData: string): Promise<any> => {
    const formData = new FormData();
    formData.append("image_data", imageData);
    const response = await api.post("/emotion/analyze/face/base64", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  analyzeBio: async (
    rrIntervals: number[],
    heartRate?: number,
  ): Promise<any> => {
    const response = await api.post("/emotion/analyze/bio", {
      rr_intervals: rrIntervals,
      heart_rate: heartRate,
    });
    return response.data;
  },

  fuseEmotions: async (data: {
    audio_emotion?: string;
    audio_scores?: Record<string, number>;
    audio_intensity?: number;
    face_expression?: string;
    face_scores?: Record<string, number>;
    face_confidence?: number;
    face_detected?: boolean;
    bio_stress_index?: number;
    bio_is_valid?: boolean;
    bio_heart_rate?: number;
  }): Promise<any> => {
    const response = await api.post("/emotion/fuse", data);
    return response.data;
  },
};

export const therapyApi = {
  getRecommendedPlan: async (
    emotion: {
      category: string;
      intensity: number;
      valence?: number;
      arousal?: number;
      confidence?: number;
    },
    style?: string,
  ): Promise<any> => {
    const response = await api.post("/therapy/recommend", {
      emotion: {
        category: emotion.category,
        intensity: emotion.intensity,
        valence: emotion.valence ?? 0,
        arousal: emotion.arousal ?? 0.5,
        confidence: emotion.confidence ?? 0.8,
      },
      style,
    });
    return response.data;
  },

  getAllPlans: async (): Promise<any> => {
    const response = await api.get("/therapy/plans");
    return response.data;
  },

  getPlanDetail: async (planId: string): Promise<TherapyPlanDetailResponse> => {
    const response = await api.get(`/therapy/plans/${planId}`);
    return response.data;
  },

  startTherapy: async (
    planId: string,
    emotion?: {
      category: string;
      intensity?: number;
      valence?: number;
      arousal?: number;
    },
  ): Promise<any> => {
    const response = await api.post("/therapy/start", {
      plan_id: planId,
      emotion_category: emotion?.category,
      emotion_intensity: emotion?.intensity,
      emotion_valence: emotion?.valence,
      emotion_arousal: emotion?.arousal,
    });
    return response.data;
  },

  pauseTherapy: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/pause/${sessionId}`);
    return response.data;
  },

  resumeTherapy: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/resume/${sessionId}`);
    return response.data;
  },

  skipTherapyPhase: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/skip/${sessionId}`);
    return response.data;
  },

  endTherapy: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/end/${sessionId}`);
    return response.data;
  },

  stopNowTherapy: async (sessionId: string): Promise<any> => {
    const response = await api.post(`/therapy/stop-now/${sessionId}`);
    return response.data;
  },

  adjustTherapyIntensity: async (
    sessionId: string,
    direction: TherapyAdjustmentDirection,
  ): Promise<TherapyRuntimeAdjustmentResponse> => {
    const response = await api.post(`/therapy/adjust-intensity/${sessionId}`, {
      direction,
    });
    return response.data;
  },
};

export const deviceApi = {
  nextTrack: async (): Promise<any> => {
    const response = await api.post("/device/audio", {
      action: "next",
    });
    return response.data;
  },
};

export const reportApi = {
  getReport: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/session/${sessionId}/report`);
    return response.data;
  },
};

export const adminApi = {
  login: async (
    credentials: AdminLoginRequest,
  ): Promise<AdminLoginResponse> => {
    const response = await api.post("/admin/login", credentials);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post("/admin/logout");
    removeStoredToken();
  },

  verifyToken: async (): Promise<AdminInfo> => {
    const response = await api.get("/admin/verify");
    return response.data;
  },

  getDeviceStatus: async (): Promise<DeviceStatusResponse> => {
    const response = await api.get("/admin/devices");
    return response.data;
  },

  getUsageStats: async (): Promise<UsageStats> => {
    const response = await api.get("/admin/stats");
    return response.data;
  },

  getLogs: async (params: {
    level?: string;
    module?: string;
    page?: number;
    page_size?: number;
  }): Promise<LogQueryResponse> => {
    const response = await api.get("/admin/logs", { params });
    return response.data;
  },

  getLogLevels: async (): Promise<{ levels: string[] }> => {
    const response = await api.get("/admin/logs/levels");
    return response.data;
  },

  getLogModules: async (): Promise<{ modules: string[] }> => {
    const response = await api.get("/admin/logs/modules");
    return response.data;
  },

  getTherapyPlans: async (): Promise<{
    plans: TherapyPlanConfig[];
    total: number;
  }> => {
    const response = await api.get("/admin/config/plans");
    return response.data;
  },

  createTherapyPlan: async (
    plan: TherapyPlanConfig,
  ): Promise<{ message: string; id: string }> => {
    const response = await api.post("/admin/config/plans", plan);
    return response.data;
  },

  updateTherapyPlan: async (
    planId: string,
    plan: TherapyPlanConfig,
  ): Promise<{ message: string }> => {
    const response = await api.put(`/admin/config/plans/${planId}`, plan);
    return response.data;
  },

  deleteTherapyPlan: async (planId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/admin/config/plans/${planId}`);
    return response.data;
  },

  getDeviceConfig: async (): Promise<{ devices: Record<string, any> }> => {
    const response = await api.get("/admin/config/devices");
    return response.data;
  },

  updateDeviceConfig: async (
    deviceType: string,
    settings: Record<string, any>,
  ): Promise<{ message: string }> => {
    const response = await api.put("/admin/config/devices", {
      device_type: deviceType,
      settings,
    });
    return response.data;
  },

  getContentLibrary: async (
    contentType?: string,
  ): Promise<{ content: ContentItem[]; total: number }> => {
    const response = await api.get("/admin/config/content", {
      params: { content_type: contentType },
    });
    return response.data;
  },

  getSessions: async (params: {
    page?: number;
    page_size?: number;
  }): Promise<{
    sessions: SessionListItem[];
    total: number;
    page: number;
    page_size: number;
  }> => {
    const response = await api.get("/admin/sessions", { params });
    return response.data;
  },

  getSessionDetail: async (
    sessionId: string,
  ): Promise<{ session: SessionListItem; adjustments: any[] }> => {
    const response = await api.get(`/admin/sessions/${sessionId}`);
    return response.data;
  },
};

export default api;
