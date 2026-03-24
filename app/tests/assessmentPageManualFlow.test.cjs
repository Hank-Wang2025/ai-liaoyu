const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("assessment page wires the inline manual fallback state", () => {
  const file = path.join(
    __dirname,
    "..",
    "src",
    "components",
    "entry",
    "AssessmentEntryPanel.vue",
  );
  const content = fs.readFileSync(file, "utf8");

  assert.ok(
    content.includes(
      "ref<'voice' | 'manual' | 'analyzing' | 'result'>('voice')",
    ),
  );
  assert.ok(
    content.includes(
      "const selectedManualEmotion = ref<EmotionCategory | null>(null)",
    ),
  );
  assert.ok(content.includes("const showManualFallback = ("));
  assert.ok(content.includes("const showNoVoiceManualFallback = () => {"));
  assert.ok(content.includes("const emit = defineEmits<{"));
  assert.ok(
    content.includes(
      "e: 'subtitle-change', subtitleKey: AssessmentSubtitleKey",
    ),
  );
  assert.ok(content.includes("const setAssessmentSubtitle = ("));
  assert.ok(content.includes("const retryMicrophone = async () => {"));
  assert.ok(
    content.includes("const continueWithManualEmotion = async () => {"),
  );
  assert.ok(content.includes("step === 'manual'"));
  assert.ok(content.includes("MICROPHONE_NO_VOICE_SUBTITLE"));
  assert.ok(content.includes("audioBlob.size === 0"));
  assert.ok(
    content.includes("const isNoVoiceAnalysisResult = (result: any) => {"),
  );
  assert.ok(
    !content.includes("const manualFallbackReason = ref<string | null>(null)"),
  );
  assert.ok(!content.includes("assessment-page__manual-message"));
  assert.ok(!content.includes("{{ manualFallbackReason }}"));
});

test("assessment page defines wrapped halo microphone visuals for the idle state", () => {
  const file = path.join(
    __dirname,
    "..",
    "src",
    "components",
    "entry",
    "AssessmentEntryPanel.vue",
  );
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes("assessment-page__mic-shell"));
  assert.ok(content.includes("assessment-page__mic-halo"));
  assert.ok(content.includes("assessment-page__mic-halo--outer"));
  assert.ok(content.includes("assessment-page__mic-halo--inner"));
  assert.ok(content.includes("@keyframes micButtonBreathe"));
  assert.ok(content.includes("@keyframes micHaloOuterBreathe"));
  assert.ok(content.includes("@keyframes micHaloInnerBreathe"));
});

test("assessment page navigates to therapy before waiting for backend startup to finish", () => {
  const file = path.join(
    __dirname,
    "..",
    "src",
    "components",
    "entry",
    "AssessmentEntryPanel.vue",
  );
  const content = fs.readFileSync(file, "utf8");
  const detailFetchIndex = content.indexOf(
    "await therapyApi.getPlanDetail(summaryPlan.id)",
  );
  const startSessionIndex = content.indexOf(
    "const startSessionPromise = sessionStore.startSession(",
  );
  const routePushIndex = content.indexOf("await router.push('/therapy')");
  const awaitStartSessionIndex = content.indexOf("await startSessionPromise");

  assert.ok(content.includes("const hydrateRecommendedPlan = async ("));
  assert.ok(detailFetchIndex >= 0);
  assert.ok(startSessionIndex > detailFetchIndex);
  assert.ok(routePushIndex > startSessionIndex);
  assert.ok(awaitStartSessionIndex > routePushIndex);
});

test("assessment page disables repeated start clicks while therapy startup is in progress", () => {
  const file = path.join(
    __dirname,
    "..",
    "src",
    "components",
    "entry",
    "AssessmentEntryPanel.vue",
  );
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes("const isStartingTherapy = ref(false)"));
  assert.ok(content.includes(':disabled="isStartingTherapy"'));
  assert.ok(content.includes("if (isStartingTherapy.value) {"));
  assert.ok(content.includes("isStartingTherapy.value = true"));
  assert.ok(content.includes("isStartingTherapy.value = false"));
});

test("assessment page keeps fallback copy readable instead of question marks", () => {
  const file = path.join(
    __dirname,
    "..",
    "src",
    "components",
    "entry",
    "AssessmentEntryPanel.vue",
  );
  const content = fs.readFileSync(file, "utf8");

  assert.ok(!content.includes("???"));
  assert.ok(content.includes("\\u5feb\\u901f\\u5e73\\u9759\\u65b9\\u6848"));
  assert.ok(
    content.includes(
      "\\u540e\\u7aef\\u670d\\u52a1\\u6682\\u4e0d\\u53ef\\u7528",
    ),
  );
});

test("assessment page formats plan summary with localized style, intensity, emotion, and duration labels", () => {
  const file = path.join(
    __dirname,
    "..",
    "src",
    "components",
    "entry",
    "AssessmentEntryPanel.vue",
  );
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes("const formatPlanSummary = ("));
  assert.ok(
    content.includes("styleLabels: Record<TherapyPlan['style'], string>"),
  );
  assert.ok(
    content.includes(
      "intensityLabels: Record<TherapyPlan['intensity'], string>",
    ),
  );
  assert.ok(content.includes("\\u98ce\\u683c"));
  assert.ok(content.includes("\\u5f3a\\u5ea6"));
  assert.ok(content.includes("\\u9002\\u7528\\u60c5\\u7eea"));
  assert.ok(content.includes("\\u65f6\\u957f"));
  assert.ok(content.includes("description: formatPlanSummary("));
});
