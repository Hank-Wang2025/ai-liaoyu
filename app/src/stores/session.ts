import { defineStore } from "pinia";
import { computed, ref } from "vue";
import type {
  EmotionState,
  Session,
  TherapyAdjustmentDirection,
  TherapyPlan,
  TherapyScreenPrompt,
  TherapyRuntimeAdjustmentResponse,
} from "@/types";
import { reportApi, therapyApi } from "@/api";

const cloneScreenPrompt = (
  prompt: TherapyScreenPrompt,
): TherapyScreenPrompt => ({
  startSecond: prompt.startSecond,
  endSecond: prompt.endSecond,
  title: prompt.title,
  lines: [...prompt.lines],
});

const normalizeScreenPrompts = (
  rawPrompts: any,
  fallbackPrompts: TherapyScreenPrompt[] | undefined,
): TherapyScreenPrompt[] | undefined => {
  if (!Array.isArray(rawPrompts)) {
    return fallbackPrompts?.map(cloneScreenPrompt);
  }

  const normalizedScreenPrompts = rawPrompts
    .map((prompt: any, index: number) => {
      const fallbackPrompt = fallbackPrompts?.[index];
      const linesSource = Array.isArray(prompt?.lines)
        ? prompt.lines
        : (fallbackPrompt?.lines ?? []);

      return {
        startSecond: Number(
          prompt?.startSecond ??
            prompt?.start_second ??
            fallbackPrompt?.startSecond ??
            0,
        ),
        endSecond: Number(
          prompt?.endSecond ??
            prompt?.end_second ??
            fallbackPrompt?.endSecond ??
            0,
        ),
        title: String(prompt?.title ?? fallbackPrompt?.title ?? ""),
        lines: linesSource.filter(
          (line: unknown): line is string => typeof line === "string",
        ),
      };
    })
    .filter((prompt) => {
      return (
        prompt.lines.length > 0 ||
        prompt.title.length > 0 ||
        prompt.startSecond > 0 ||
        prompt.endSecond > 0
      );
    });

  if (!normalizedScreenPrompts.length) {
    return fallbackPrompts?.map(cloneScreenPrompt);
  }

  return normalizedScreenPrompts;
};

export const useSessionStore = defineStore("session", () => {
  const currentSession = ref<Session | null>(null);
  const emotionHistory = ref<EmotionState[]>([]);
  const currentPlan = ref<TherapyPlan | null>(null);
  const isTherapyActive = ref(false);
  const isPaused = ref(false);
  const backendSessionId = ref<string | null>(null);
  const backendPlanId = ref<string | null>(null);
  let pendingStopNowRequest: Promise<void> | null = null;

  const initialEmotion = computed(() => emotionHistory.value[0] || null);
  const latestEmotion = computed(
    () => emotionHistory.value[emotionHistory.value.length - 1] || null,
  );

  const emotionImprovement = computed(() => {
    if (!initialEmotion.value || !latestEmotion.value) return 0;
    return latestEmotion.value.valence - initialEmotion.value.valence;
  });

  function inferRuntimeIntensityLevel(
    intensity: TherapyPlan["intensity"] | undefined,
  ): number {
    if (intensity === "low") return 1;
    if (intensity === "high") return 5;
    return 3;
  }

  function normalizeTherapyPlan(
    rawPlan: any,
    fallbackPlan: TherapyPlan | null,
  ): TherapyPlan | null {
    if (!rawPlan && !fallbackPlan) {
      return null;
    }

    const phasesSource = Array.isArray(rawPlan?.phases)
      ? rawPlan.phases
      : (fallbackPlan?.phases ?? []);
    const screenPromptsSource =
      rawPlan?.screenPrompts ?? rawPlan?.screen_prompts;

    return {
      id: rawPlan?.id ?? fallbackPlan?.id ?? "",
      name: rawPlan?.name ?? fallbackPlan?.name ?? "",
      description: rawPlan?.description ?? fallbackPlan?.description ?? "",
      targetEmotions:
        rawPlan?.targetEmotions ??
        rawPlan?.target_emotions ??
        fallbackPlan?.targetEmotions ??
        [],
      intensity: rawPlan?.intensity ?? fallbackPlan?.intensity ?? "medium",
      runtimeIntensityLevel:
        rawPlan?.runtimeIntensityLevel ??
        rawPlan?.runtime_intensity_level ??
        fallbackPlan?.runtimeIntensityLevel ??
        inferRuntimeIntensityLevel(
          rawPlan?.intensity ?? fallbackPlan?.intensity ?? "medium",
        ),
      style: rawPlan?.style ?? fallbackPlan?.style ?? "modern",
      duration: Number(rawPlan?.duration ?? fallbackPlan?.duration ?? 0),
      phases: phasesSource.map((phase: any, index: number) => ({
        name: phase?.name ?? fallbackPlan?.phases[index]?.name ?? "",
        duration: Number(
          phase?.duration ?? fallbackPlan?.phases[index]?.duration ?? 0,
        ),
        description:
          phase?.description ?? fallbackPlan?.phases[index]?.description,
      })),
      screenPrompts: normalizeScreenPrompts(
        screenPromptsSource,
        fallbackPlan?.screenPrompts,
      ),
    };
  }

  function clearSessionState() {
    currentSession.value = null;
    emotionHistory.value = [];
    currentPlan.value = null;
    isTherapyActive.value = false;
    isPaused.value = false;
    backendSessionId.value = null;
    backendPlanId.value = null;
    pendingStopNowRequest = null;
  }

  async function startSession(emotion: EmotionState, plan: TherapyPlan) {
    const normalizedPlan = normalizeTherapyPlan(plan, null) ?? plan;

    currentSession.value = {
      id: "",
      startTime: new Date(),
      endTime: null,
      initialEmotion: emotion,
      finalEmotion: null,
      planUsed: normalizedPlan,
    };
    emotionHistory.value = [emotion];
    currentPlan.value = normalizedPlan;
    backendPlanId.value = normalizedPlan.id;
    isTherapyActive.value = true;
    isPaused.value = false;
    pendingStopNowRequest = null;

    try {
      const result = await therapyApi.startTherapy(normalizedPlan.id, {
        category: emotion.category,
        intensity: emotion.intensity,
        valence: emotion.valence,
        arousal: emotion.arousal,
      });
      backendSessionId.value = result.session_id;
      if (currentSession.value) {
        currentSession.value.id = result.session_id;
      }
    } catch (err) {
      console.error("Backend therapy start failed, using local fallback:", err);
      const localId = crypto.randomUUID();
      backendSessionId.value = localId;
      if (currentSession.value) {
        currentSession.value.id = localId;
      }
    }
  }

  function addEmotionRecord(emotion: EmotionState) {
    emotionHistory.value.push(emotion);
  }

  async function pauseTherapy() {
    isPaused.value = true;
    if (backendSessionId.value) {
      try {
        await therapyApi.pauseTherapy(backendSessionId.value);
      } catch (err) {
        console.error("Backend pause failed:", err);
      }
    }
  }

  async function resumeTherapy() {
    isPaused.value = false;
    if (backendSessionId.value) {
      try {
        await therapyApi.resumeTherapy(backendSessionId.value);
      } catch (err) {
        console.error("Backend resume failed:", err);
      }
    }
  }

  async function adjustTherapyIntensity(
    direction: TherapyAdjustmentDirection,
  ): Promise<TherapyRuntimeAdjustmentResponse> {
    if (!backendSessionId.value) {
      throw new Error("No active backend session");
    }

    const response = await therapyApi.adjustTherapyIntensity(
      backendSessionId.value,
      direction,
    );
    const normalizedPlan = normalizeTherapyPlan(
      response.plan,
      currentPlan.value,
    );

    if (normalizedPlan) {
      response.plan = normalizedPlan;
    }

    if (response.changed && normalizedPlan) {
      currentPlan.value = normalizedPlan;
      backendPlanId.value = normalizedPlan.id;

      if (currentSession.value) {
        currentSession.value.planUsed = normalizedPlan;
      }
    }

    return response;
  }

  function applyLocalSessionEnd() {
    if (currentSession.value && !currentSession.value.endTime) {
      currentSession.value.endTime = new Date();
      currentSession.value.finalEmotion = latestEmotion.value;
    }

    isTherapyActive.value = false;
    isPaused.value = false;
  }

  async function stopNowSession() {
    if (!backendSessionId.value) {
      return;
    }

    if (pendingStopNowRequest) {
      await pendingStopNowRequest;
      return;
    }

    const sessionId = backendSessionId.value;
    pendingStopNowRequest = therapyApi
      .stopNowTherapy(sessionId)
      .then(() => undefined)
      .catch((err) => {
        console.error("Backend stop-now failed:", err);
      })
      .finally(() => {
        pendingStopNowRequest = null;
      });

    await pendingStopNowRequest;
  }

  async function endSession() {
    applyLocalSessionEnd();
  }

  async function fetchReport() {
    if (!backendSessionId.value) return null;

    try {
      return await reportApi.getReport(backendSessionId.value);
    } catch (err) {
      console.error("Fetch report failed:", err);
      return null;
    }
  }

  function resetSession() {
    clearSessionState();
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
    adjustTherapyIntensity,
    stopNowSession,
    endSession,
    fetchReport,
    resetSession,
  };
});
