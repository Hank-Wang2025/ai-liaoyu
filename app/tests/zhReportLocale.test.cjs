const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");

test("report locale keeps Chinese labels instead of question marks", () => {
  const zhLocalePath = path.join(
    __dirname,
    "..",
    "src",
    "i18n",
    "locales",
    "zh.ts",
  );
  const content = fs.readFileSync(zhLocalePath, "utf8");
  const reportStart = content.indexOf("  report: {");
  const reportEnd = content.indexOf("  emotions: {", reportStart);
  const reportSection = content.slice(reportStart, reportEnd);

  assert.ok(reportSection.includes('title: "疗愈报告"'));
  assert.ok(reportSection.includes('summary: "疗愈总结"'));
  assert.ok(reportSection.includes('improvement: "改善程度"'));
  assert.ok(reportSection.includes('newSession: "开始新的疗愈"'));
  assert.ok(!reportSection.includes("????"));
});

