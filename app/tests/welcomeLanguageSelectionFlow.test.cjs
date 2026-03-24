const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("welcome page only shows the language picker until the customer makes a selection", () => {
  const file = path.join(__dirname, "..", "src", "views", "WelcomePage.vue");
  const content = fs.readFileSync(file, "utf8");

  assert.ok(content.includes('v-if="showLanguageSelector"'));
  assert.ok(content.includes("const showLanguageSelector = ref(true)"));
  assert.ok(content.includes("showLanguageSelector.value = false"));
  assert.ok(content.includes("localStorage.setItem('locale', lang)"));
});
