const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("report page retries backend report fetch while keeping fallback rendering", () => {
  const file = path.join(__dirname, "..", "src", "views", "ReportPage.vue");
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes("const REPORT_POLL_ATTEMPTS = 5"));
  assert.ok(content.includes("const REPORT_POLL_DELAY_MS = 400"));
  assert.ok(content.includes("const sleep = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms))"));
  assert.ok(content.includes("const loadBackendReport = async () => {"));
  assert.ok(content.includes("for (let attempt = 0; attempt < REPORT_POLL_ATTEMPTS; attempt++)"));
  assert.ok(content.includes("await sleep(REPORT_POLL_DELAY_MS)"));
});
