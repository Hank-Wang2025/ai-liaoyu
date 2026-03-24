const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

function readLocale(name) {
  return fs.readFileSync(
    path.join(__dirname, "..", "src", "i18n", "locales", name),
    "utf8",
  );
}

test("assessment manual fallback locale keys exist in zh and en", () => {
  const zh = readLocale("zh.ts");
  const en = readLocale("en.ts");

  for (const content of [zh, en]) {
    assert.ok(content.includes("manualFallbackTitle"));
    assert.ok(content.includes("manualFallbackPrompt"));
    assert.ok(content.includes("microphoneNoVoice"));
    assert.ok(content.includes("retryMicrophone"));
    assert.ok(content.includes("manualContinue"));
    assert.ok(!content.includes("continuePreviousSession"));
    assert.ok(!content.includes("resumeFailed"));
    assert.ok(!content.includes("noResumableSession"));
  }

  assert.ok(zh.includes('start: "开始疗愈"'));
  assert.ok(en.includes('start: "Start Healing"'));
});
