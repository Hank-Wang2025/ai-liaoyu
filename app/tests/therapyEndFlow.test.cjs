const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("therapy page guards against duplicate fast stop requests and disables controls", () => {
  const file = path.join(__dirname, "..", "src", "views", "TherapyPage.vue");
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes("const isStopping = ref(false)"));
  assert.ok(content.includes("if (isStopping.value) {"));
  assert.ok(content.includes(':disabled="isStopping || isAdjustingIntensity"'));
  assert.ok(
    content.includes("const stopNowRequest = sessionStore.stopNowSession()"),
  );
  assert.ok(!content.includes("await sessionStore.stopNowSession()"));
});
