const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("therapy page uses runtime intensity controls instead of next-track and skip", () => {
  const therapy = fs.readFileSync(
    path.join(__dirname, "..", "src", "views", "TherapyPage.vue"),
    "utf8",
  );
  const types = fs.readFileSync(
    path.join(__dirname, "..", "src", "types", "index.ts"),
    "utf8",
  );
  const store = fs.readFileSync(
    path.join(__dirname, "..", "src", "stores", "session.ts"),
    "utf8",
  );
  const api = fs.readFileSync(
    path.join(__dirname, "..", "src", "api", "index.ts"),
    "utf8",
  );

  assert.ok(therapy.includes("$t('therapy.relaxMore')"));
  assert.ok(therapy.includes("$t('therapy.intensifyMore')"));
  assert.ok(therapy.includes(`@click="adjustIntensity('relax')"`));
  assert.ok(therapy.includes(`@click="adjustIntensity('intensify')"`));
  assert.ok(therapy.includes("const isAdjustingIntensity = ref(false)"));
  assert.ok(therapy.includes("const canRelaxMore = computed(() =>"));
  assert.ok(therapy.includes("const canIntensifyMore = computed(() =>"));
  assert.ok(therapy.includes("currentPlan.value?.runtimeIntensityLevel"));
  assert.ok(
    therapy.includes("await sessionStore.adjustTherapyIntensity(direction)"),
  );
  assert.ok(!therapy.includes("$t('therapy.nextTrack')"));
  assert.ok(!therapy.includes("const nextTrack = async () =>"));
  assert.ok(!therapy.includes("const skipPhase = async () =>"));

  assert.ok(store.includes("async function adjustTherapyIntensity("));
  assert.ok(
    store.includes("const response = await therapyApi.adjustTherapyIntensity("),
  );
  assert.ok(store.includes("runtimeIntensityLevel"));
  assert.ok(store.includes("currentPlan.value = normalizedPlan"));

  assert.ok(types.includes("runtimeIntensityLevel?: number;"));
  assert.ok(api.includes("adjustTherapyIntensity: async ("));
});
