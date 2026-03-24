const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("start-only mode removes resume helpers from store api and types", () => {
  const store = fs.readFileSync(
    path.join(__dirname, "..", "src", "stores", "session.ts"),
    "utf8",
  );
  const api = fs.readFileSync(
    path.join(__dirname, "..", "src", "api", "index.ts"),
    "utf8",
  );
  const types = fs.readFileSync(
    path.join(__dirname, "..", "src", "types", "index.ts"),
    "utf8",
  );
  const welcome = fs.readFileSync(
    path.join(__dirname, "..", "src", "views", "WelcomePage.vue"),
    "utf8",
  );

  assert.ok(!store.includes("saveResumeSnapshot("));
  assert.ok(!store.includes("loadResumeSnapshot("));
  assert.ok(!store.includes("clearResumeSnapshot("));
  assert.ok(!store.includes("refreshResumeSnapshot"));
  assert.ok(!store.includes("resumeSavedSession"));
  assert.ok(!store.includes("validateResumeSession"));
  assert.ok(!store.includes("resumeSnapshot"));
  assert.ok(!store.includes("hasResumableSession"));
  assert.ok(!api.includes("export const sessionApi"));
  assert.ok(!types.includes("interface ResumeSnapshot"));
  assert.ok(!types.includes("interface ResumeSnapshotEmotion"));
  assert.ok(!welcome.includes("sessionStore.refreshResumeSnapshot()"));
  assert.ok(welcome.includes("localStorage.removeItem('therapy_resume_snapshot')"));
});
