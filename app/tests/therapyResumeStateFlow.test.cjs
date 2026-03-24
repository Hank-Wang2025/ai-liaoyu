const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("therapy page no longer restores or persists resume progress state", () => {
  const therapy = fs.readFileSync(
    path.join(__dirname, "..", "src", "views", "TherapyPage.vue"),
    "utf8",
  );

  assert.ok(!therapy.includes("resumeSnapshot?.phaseIndex"));
  assert.ok(!therapy.includes("resumeSnapshot?.elapsedSeconds"));
  assert.ok(!therapy.includes("resumedPhaseIndex"));
  assert.ok(!therapy.includes("resumedElapsedSeconds"));
  assert.ok(!therapy.includes("updateResumeProgress("));
  assert.ok(therapy.includes("currentPhase?.name || $t('common.loading')"));
});
