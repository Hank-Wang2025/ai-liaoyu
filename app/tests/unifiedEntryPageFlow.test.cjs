const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("welcome page keeps branding and exposes a start-only assessment entry", () => {
  const file = path.join(__dirname, "..", "src", "views", "WelcomePage.vue");
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes("$t('welcome.title')"));
  assert.ok(content.includes("$t('welcome.subtitle')"));
  assert.ok(content.includes("$t('welcome.description')"));
  assert.ok(content.includes("welcome-page__language"));
  assert.ok(content.includes("AssessmentEntryPanel"));
  assert.ok(content.includes(':show-back-button="false"'));
  assert.ok(!content.includes("welcome-page__assessment-title"));
  assert.ok(!content.includes("welcome-page__assessment-subtitle"));
  assert.ok(!content.includes("assessmentSubtitleKey"));
  assert.ok(
    !content.includes('@subtitle-change="handleAssessmentSubtitleChange"'),
  );
  assert.ok(content.includes("name: '中文'"));
  assert.ok(!content.includes("name: '����'"));
  assert.ok(!content.includes("ResumeSessionCard"));
  assert.ok(!content.includes("welcome-page__entry-toggle"));
  assert.ok(!content.includes("entry.continuePreviousSession"));
  assert.ok(!content.includes("toggleStartSection"));
});
