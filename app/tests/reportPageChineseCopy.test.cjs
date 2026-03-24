const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("report page keeps built-in Chinese copy readable", () => {
  const file = path.join(__dirname, "..", "src", "views", "ReportPage.vue");
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes("\u6b63\u5728\u751f\u6210\u62a5\u544a..."));
  assert.ok(content.includes("\u5206\u949f"));
  assert.ok(content.includes("\u79d2"));
  assert.ok(content.includes("\u672c\u6b21\u7597\u6108\u6548\u679c\u663e\u8457"));
  assert.ok(content.includes("\u4fdd\u6301\u89c4\u5f8b\u7684\u4f5c\u606f\u65f6\u95f4"));
  assert.ok(content.includes("\ud83d\ude0a"));
  assert.ok(!content.includes("姝ｅ湪鐢熸垚鎶ュ憡"));
  assert.ok(!content.includes("鏈鐤楁剤"));
  assert.ok(!content.includes("淇濇寔瑙勫緥"));
  assert.ok(!content.includes("鍒?"));
  assert.ok(!content.includes("馃"));
});
