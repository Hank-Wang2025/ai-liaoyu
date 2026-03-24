const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("therapy types define a canonical camelCase screen prompt model", () => {
  const content = fs.readFileSync(
    path.join(__dirname, "..", "src", "types", "index.ts"),
    "utf8",
  );

  assert.ok(content.includes("export interface TherapyScreenPrompt"));
  assert.ok(content.includes("startSecond: number;"));
  assert.ok(content.includes("endSecond: number;"));
  assert.ok(content.includes("lines: string[];"));
  assert.ok(content.includes("screenPrompts?: TherapyScreenPrompt[];"));
});

test("session store normalizes backend and frontend prompt payloads into camelCase only", () => {
  const content = fs.readFileSync(
    path.join(__dirname, "..", "src", "stores", "session.ts"),
    "utf8",
  );

  assert.ok(content.includes("const screenPromptsSource ="));
  assert.ok(
    content.includes("rawPlan?.screenPrompts ?? rawPlan?.screen_prompts"),
  );
  assert.ok(content.includes("const normalizeScreenPrompts = ("));
  assert.ok(content.includes("startSecond: Number("));
  assert.ok(content.includes("endSecond: Number("));
  assert.ok(content.includes("screenPrompts: normalizeScreenPrompts("));
  assert.ok(content.includes("screenPromptsSource,"));
  assert.ok(content.includes("fallbackPlan?.screenPrompts"));
  assert.ok(content.includes("planUsed: normalizedPlan"));
  assert.ok(content.includes("currentPlan.value = normalizedPlan"));
});

test("assessment page hydrates plan detail before starting therapy and only falls back on required-field failures", () => {
  const content = fs.readFileSync(
    path.join(
      __dirname,
      "..",
      "src",
      "components",
      "entry",
      "AssessmentEntryPanel.vue",
    ),
    "utf8",
  );

  const detailFetchIndex = content.indexOf(
    "await therapyApi.getPlanDetail(summaryPlan.id)",
  );
  const startSessionIndex = content.indexOf(
    "const startSessionPromise = sessionStore.startSession(",
  );
  const routePushIndex = content.indexOf("await router.push('/therapy')");
  const awaitStartSessionIndex = content.indexOf("await startSessionPromise");

  assert.ok(
    content.includes(
      "const isHydratedPlanDetail = (plan: any): plan is TherapyPlan => {",
    ),
  );
  assert.ok(content.includes("typeof plan?.id === 'string'"));
  assert.ok(content.includes("typeof plan?.style === 'string'"));
  assert.ok(content.includes("typeof plan?.intensity === 'string'"));
  assert.ok(content.includes("Number.isFinite(Number(plan?.duration))"));
  assert.ok(content.includes("Array.isArray(plan?.phases)"));
  assert.ok(detailFetchIndex >= 0);
  assert.ok(startSessionIndex > detailFetchIndex);
  assert.ok(routePushIndex > startSessionIndex);
  assert.ok(awaitStartSessionIndex > routePushIndex);
});

test("therapy page renders active prompt content with boundary matching and fallback", () => {
  const content = fs.readFileSync(
    path.join(__dirname, "..", "src", "views", "TherapyPage.vue"),
    "utf8",
  );

  assert.ok(content.includes("const isValidScreenPromptTimeline = ("));
  assert.ok(
    content.includes("const validatedScreenPrompts = computed(() => {"),
  );
  assert.ok(
    content.includes(
      "const activeScreenPrompt = computed<TherapyScreenPrompt | null>(() => {",
    ),
  );
  assert.ok(content.includes("prompt.startSecond <= elapsedTime.value"));
  assert.ok(content.includes("elapsedTime.value < prompt.endSecond"));
  assert.ok(content.includes('v-if="activeScreenPrompt"'));
  assert.ok(content.includes('class="therapy-page__prompt-title"'));
  assert.ok(content.includes('v-for="line in activeScreenPrompt.lines"'));
  assert.ok(content.includes('class="therapy-page__prompt-line"'));
  assert.ok(content.includes("currentPhase?.name || $t('common.loading')"));
  assert.ok(content.includes("if (!isPaused.value) {"));
});
