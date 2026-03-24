const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("therapy page stops immediately without showing a confirmation modal", () => {
  const file = path.join(__dirname, "..", "src", "views", "TherapyPage.vue");
  const content = fs.readFileSync(file, "utf8");
  const stopNowRequestIndex = content.indexOf(
    "const stopNowRequest = sessionStore.stopNowSession()",
  );
  const endSessionIndex = content.indexOf("await sessionStore.endSession()");
  const routePushIndex = content.indexOf("await router.push('/report')");

  assert.ok(!content.includes("showEndConfirm"));
  assert.ok(!content.includes("$t('therapy.endConfirm')"));
  assert.ok(content.includes('@click="endTherapy"'));
  assert.ok(
    content.includes("const stopNowRequest = sessionStore.stopNowSession()"),
  );
  assert.ok(!content.includes("await sessionStore.stopNowSession()"));
  assert.ok(content.includes("await sessionStore.endSession()"));
  assert.ok(content.includes("await router.push('/report')"));
  assert.ok(stopNowRequestIndex >= 0);
  assert.ok(endSessionIndex > stopNowRequestIndex);
  assert.ok(routePushIndex > endSessionIndex);
});
