const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("session store separates fast stop from local session completion", () => {
  const file = path.join(__dirname, "..", "src", "stores", "session.ts");
  const content = fs.readFileSync(file, "utf8");

  assert.ok(
    content.includes("let pendingStopNowRequest: Promise<void> | null = null"),
  );
  assert.ok(content.includes("function applyLocalSessionEnd()"));
  assert.ok(content.includes("async function stopNowSession()"));
  assert.ok(content.includes(".stopNowTherapy(sessionId)"));
  assert.ok(content.includes("async function endSession()"));
  assert.ok(!content.includes("clearResumeSnapshot()"));
  assert.ok(!content.includes("clearStoredResumeSnapshot()"));
  assert.ok(!content.includes("persistResumeSnapshot()"));
  assert.ok(!content.includes("saveCurrentResumeSnapshot("));
  assert.ok(!content.includes("therapyApi.endTherapy("));
});
