const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("router keeps / as welcome entry and /assessment as compatibility wrapper", () => {
  const router = fs.readFileSync(
    path.join(__dirname, "..", "src", "router", "index.ts"),
    "utf8",
  );
  const assessmentPage = fs.readFileSync(
    path.join(__dirname, "..", "src", "views", "AssessmentPage.vue"),
    "utf8",
  );

  assert.ok(router.includes("path: '/'"));
  assert.ok(
    router.includes("component: () => import('@/views/WelcomePage.vue')"),
  );
  assert.ok(router.includes("path: '/assessment'"));
  assert.ok(
    router.includes("component: () => import('@/views/AssessmentPage.vue')"),
  );
  assert.ok(router.includes("meta: { title: '欢迎' }"));
  assert.ok(router.includes("meta: { title: '情绪评估' }"));
  assert.ok(router.includes("meta: { title: '疗愈进行' }"));
  assert.ok(router.includes("meta: { title: '疗愈报告' }"));
  assert.ok(
    assessmentPage.includes(
      '<AssessmentEntryPanel @subtitle-change="handleAssessmentSubtitleChange" />',
    ),
  );
  assert.ok(assessmentPage.includes("$t('assessment.title')"));
  assert.ok(
    assessmentPage.includes(
      '@subtitle-change="handleAssessmentSubtitleChange"',
    ),
  );
  assert.ok(assessmentPage.includes("$t(assessmentSubtitleKey)"));
  assert.ok(
    !assessmentPage.includes(
      "<p class=\"page__subtitle\">{{ $t('assessment.subtitle') }}</p>",
    ),
  );
  assert.ok(!assessmentPage.includes("$t('welcome.title')"));
});
