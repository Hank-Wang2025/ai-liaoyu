const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("therapy page panel uses the same width cap as the welcome assessment card", () => {
  const welcome = fs.readFileSync(
    path.join(__dirname, "..", "src", "views", "WelcomePage.vue"),
    "utf8",
  );
  const therapy = fs.readFileSync(
    path.join(__dirname, "..", "src", "views", "TherapyPage.vue"),
    "utf8",
  );

  assert.ok(welcome.includes("max-width: 720px;"));
  assert.ok(therapy.includes("width: 100%;"));
  assert.ok(therapy.includes("max-width: 720px;"));
  assert.ok(!therapy.includes("max-width: 400px;"));
});
