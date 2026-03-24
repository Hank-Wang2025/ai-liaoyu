# 统一入口仅保留开始疗愈实现计划

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前“开始/继续”双入口改回仅保留开始疗愈的统一入口，并彻底移除客户端恢复疗愈能力。

**Architecture:** 保留已经抽出的 `AssessmentEntryPanel.vue` 作为评估流程核心组件，继续使用 `WelcomePage.vue` 承载欢迎品牌壳，但把主体改为默认直出的单一评估卡片。删除 resume snapshot、继续疗愈入口、恢复校验和疗愈页恢复回填逻辑，同时保留 `/assessment` 兼容路由和现有疗愈/报告主流程。

**Tech Stack:** Vue 3、Pinia、TypeScript、Vue Router、Vue I18n、Axios、node:test、vue-tsc

---

## 文件结构

- 修改：`app/src/views/WelcomePage.vue` - 保留欢迎品牌区、副标题、说明文案和语言切换，同时把主体改为默认展开的单一评估卡片
- 修改：`app/src/views/AssessmentPage.vue` - 保持兼容包装页，继续渲染 `AssessmentEntryPanel.vue`
- 修改：`app/src/router/index.ts` - 如兼容路由定义需要微调，保持 `/` 指向欢迎页、`/assessment` 指向包装页
- 修改：`app/src/components/entry/AssessmentEntryPanel.vue` - 只保留开始疗愈相关评估逻辑；必要时补充首页直出所需的小 props
- 删除：`app/src/components/entry/ResumeSessionCard.vue` - 继续疗愈入口组件不再需要
- 修改：`app/src/stores/session.ts` - 删除 resume snapshot、恢复校验、恢复回填逻辑，保留内存态会话与 fast stop
- 删除：`app/src/utils/sessionResume.ts` - 恢复快照工具不再需要
- 修改：`app/src/types/index.ts` - 删除恢复快照相关类型
- 修改：`app/src/api/index.ts` - 删除 `sessionApi.getSession`
- 修改：`app/src/views/TherapyPage.vue` - 删除恢复阶段/时长回填与进度持久化
- 修改：`app/src/i18n/locales/zh.ts`
- 修改：`app/src/i18n/locales/en.ts`
- 新建：`app/tests/startOnlySessionCleanupFlow.test.cjs` - 覆盖 store/api/types 恢复能力已移除
- 新建：`app/tests/assessmentRouteCompatibility.test.cjs` - 覆盖 `/` 与 `/assessment` 的路由意图
- 修改：`app/tests/unifiedEntryPageFlow.test.cjs` - 改成 start-only 首页结构断言
- 修改：`app/tests/assessmentManualLocale.test.cjs` - 去掉 continue 相关 key 断言，改为 start-only 文案断言
- 修改：`app/tests/sessionFastEndFlow.test.cjs` - 改为断言 fast stop 不再耦合 resume 清理
- 修改：`app/tests/therapyResumeStateFlow.test.cjs` - 改为断言疗愈页不再依赖 resume 状态
- 删除：`app/tests/sessionResume.test.ts`
- 删除：`app/tests/sessionResumeStoreFlow.test.cjs`
- 删除：`app/tests/resumeSessionEntryFlow.test.cjs`

说明：用户已明确要求仅保存在本地，不写 git commit 步骤。

## Chunk 1: 首页切回仅开始疗愈

### Task 1: 先把首页与路由回归测试改成 start-only 红灯

**Files:**
- Modify: `app/tests/unifiedEntryPageFlow.test.cjs`
- Modify: `app/tests/assessmentManualLocale.test.cjs`
- Create: `app/tests/assessmentRouteCompatibility.test.cjs`

- [ ] **Step 1: 把首页结构测试改成只允许开始疗愈**

把 `app/tests/unifiedEntryPageFlow.test.cjs` 改成断言：

```js
assert.ok(content.includes("$t('welcome.title')"))
assert.ok(content.includes("$t('welcome.subtitle')"))
assert.ok(content.includes("$t('welcome.description')"))
assert.ok(content.includes("welcome-page__language"))
assert.ok(content.includes('AssessmentEntryPanel'))
assert.ok(content.includes(':show-back-button="false"'))
assert.ok(!content.includes('ResumeSessionCard'))
assert.ok(!content.includes('welcome-page__entry-toggle'))
assert.ok(!content.includes("entry.continuePreviousSession"))
assert.ok(!content.includes('toggleStartSection'))
```

- [ ] **Step 2: 把 locale 回归改成不再依赖 continue 文案**

把 `app/tests/assessmentManualLocale.test.cjs` 改成断言：

```js
assert.ok(content.includes('manualFallbackTitle'))
assert.ok(content.includes('manualFallbackPrompt'))
assert.ok(content.includes('retryMicrophone'))
assert.ok(content.includes('manualContinue'))
assert.ok(!content.includes('continuePreviousSession'))
assert.ok(!content.includes('resumeFailed'))
assert.ok(!content.includes('noResumableSession'))
```

- [ ] **Step 3: 新增 `/assessment` 兼容路由回归**

创建 `app/tests/assessmentRouteCompatibility.test.cjs`：

```js
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
  assert.ok(router.includes("component: () => import('@/views/WelcomePage.vue')"));
  assert.ok(router.includes("path: '/assessment'"));
  assert.ok(router.includes("component: () => import('@/views/AssessmentPage.vue')"));
  assert.ok(assessmentPage.includes("<AssessmentEntryPanel />"));
  assert.ok(assessmentPage.includes("$t('assessment.title')"));
  assert.ok(assessmentPage.includes("$t('assessment.subtitle')"));
  assert.ok(!assessmentPage.includes("$t('welcome.title')"));
});
```

- [ ] **Step 4: 运行首页相关测试并确认红灯**

运行：

```bash
node --test app/tests/unifiedEntryPageFlow.test.cjs app/tests/assessmentManualLocale.test.cjs app/tests/assessmentRouteCompatibility.test.cjs
```

预期：

- `unifiedEntryPageFlow` 因仍存在 `ResumeSessionCard` / `toggleStartSection` 而失败
- `assessmentManualLocale` 因仍保留 continue 文案而失败
- 新路由测试通过或仅作为保护网存在

### Task 2: 实现 start-only 首页与文案收敛

**Files:**
- Modify: `app/src/views/WelcomePage.vue`
- Modify: `app/src/i18n/locales/zh.ts`
- Modify: `app/src/i18n/locales/en.ts`
- Modify: `app/src/views/AssessmentPage.vue`（如需仅做轻微对齐）

- [ ] **Step 1: 保留欢迎壳，只把主体改成默认展开的评估面板**

保留现有的 logo、`welcome.title`、`welcome.subtitle`、`welcome.description` 和语言切换区，只把原来的双卡片 `welcome-page__entry-grid` 替换成单卡片主体，例如：

```vue
<div class="welcome-page__assessment card">
  <h2 class="welcome-page__assessment-title">{{ $t('assessment.title') }}</h2>
  <p class="welcome-page__assessment-subtitle">{{ $t('assessment.subtitle') }}</p>
  <AssessmentEntryPanel :show-back-button="false" />
</div>
```

同时删除：

- `ResumeSessionCard` import
- `useSessionStore()` 与 `sessionStore.refreshResumeSnapshot()`
- `useRouter()` 与继续疗愈相关状态
- `activeSection` / `resumeError` / `isResuming`
- `toggleStartSection()`
- `continuePreviousSession()`
- 仅用于双卡片布局的样式类（如 `welcome-page__entry-grid`、`welcome-page__entry-toggle`）

- [ ] **Step 2: 去掉不再使用的入口文案键并保留现有手动兜底文案**

从 `zh.ts` / `en.ts` 删除此前新增且已无引用的：

```ts
entry: {
  startNewAssessment: ...,
  continuePreviousSession: ...,
  noResumableSession: ...,
  resumeFailed: ...,
}
```

不要删除仍在 `AssessmentEntryPanel.vue` 使用的手动兜底 key；如果首页需要评估区标题，优先复用已有的：

- `assessment.title`
- `assessment.subtitle`

- [ ] **Step 3: 保持 `/assessment` 包装页职责单一**

确认 `AssessmentPage.vue` 继续保持薄包装：

```vue
<h1 class="page__title">{{ $t('assessment.title') }}</h1>
<p class="page__subtitle">{{ $t('assessment.subtitle') }}</p>
<AssessmentEntryPanel />
```

不把欢迎页品牌壳复制进去。

- [ ] **Step 4: 重新运行首页相关测试并确认转绿**

运行：

```bash
node --test app/tests/unifiedEntryPageFlow.test.cjs app/tests/assessmentManualLocale.test.cjs app/tests/assessmentRouteCompatibility.test.cjs
```

预期：全部 PASS

- [ ] **Step 5: 做首页改动的阶段性类型检查**

运行：

```powershell
Push-Location app; npx vue-tsc --noEmit; Pop-Location
```

预期：退出码 `0`

说明：历史 `therapy_resume_snapshot` 清理放在 Chunk 2，与 resume 基础设施删除一起完成。

## Chunk 2: 删除恢复疗愈基础设施

### Task 3: 先写“恢复能力已移除”的红灯测试

**Files:**
- Create: `app/tests/startOnlySessionCleanupFlow.test.cjs`
- Modify: `app/tests/therapyResumeStateFlow.test.cjs`
- Modify: `app/tests/sessionFastEndFlow.test.cjs`

- [ ] **Step 1: 新增 store/api/types/welcome 清理回归**

创建 `app/tests/startOnlySessionCleanupFlow.test.cjs`：

```js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("start-only mode removes resume helpers from store api and types", () => {
  const store = fs.readFileSync(path.join(__dirname, "..", "src", "stores", "session.ts"), "utf8");
  const api = fs.readFileSync(path.join(__dirname, "..", "src", "api", "index.ts"), "utf8");
  const types = fs.readFileSync(path.join(__dirname, "..", "src", "types", "index.ts"), "utf8");
  const welcome = fs.readFileSync(path.join(__dirname, "..", "src", "views", "WelcomePage.vue"), "utf8");

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
```

- [ ] **Step 2: 把疗愈页回归改成断言“不再恢复”**

把 `app/tests/therapyResumeStateFlow.test.cjs` 改成断言：

```js
assert.ok(!therapy.includes("resumeSnapshot?.phaseIndex"))
assert.ok(!therapy.includes("resumeSnapshot?.elapsedSeconds"))
assert.ok(!therapy.includes("resumedPhaseIndex"))
assert.ok(!therapy.includes("resumedElapsedSeconds"))
assert.ok(!therapy.includes("updateResumeProgress("))
```

- [ ] **Step 3: 把 fast stop 回归改成不再依赖 resume 清理**

把 `app/tests/sessionFastEndFlow.test.cjs` 改成断言：

```js
assert.ok(content.includes("let pendingStopNowRequest: Promise<void> | null = null"))
assert.ok(content.includes("function applyLocalSessionEnd()"))
assert.ok(content.includes("async function stopNowSession()"))
assert.ok(content.includes(".stopNowTherapy(sessionId)"))
assert.ok(content.includes("async function endSession()"))
assert.ok(!content.includes("clearResumeSnapshot()"))
assert.ok(!content.includes("clearStoredResumeSnapshot()"))
assert.ok(!content.includes("persistResumeSnapshot()"))
assert.ok(!content.includes("saveCurrentResumeSnapshot("))
assert.ok(!content.includes("therapyApi.endTherapy("))
```

- [ ] **Step 4: 运行清理相关测试并确认红灯**

运行：

```bash
node --test app/tests/startOnlySessionCleanupFlow.test.cjs app/tests/therapyResumeStateFlow.test.cjs app/tests/sessionFastEndFlow.test.cjs
```

预期：

- 新清理回归失败，因为 store/api/types 仍含 resume 代码
- `therapyResumeStateFlow` 因疗愈页仍依赖恢复变量而失败
- `sessionFastEndFlow` 因 store 仍调用 resume 清理辅助逻辑而失败

### Task 4: 真正删除恢复能力并保留旧数据清理

**Files:**
- Modify: `app/src/stores/session.ts`
- Modify: `app/src/views/TherapyPage.vue`
- Modify: `app/src/api/index.ts`
- Modify: `app/src/types/index.ts`
- Modify: `app/src/views/WelcomePage.vue`
- Delete: `app/src/components/entry/ResumeSessionCard.vue`
- Delete: `app/src/utils/sessionResume.ts`
- Delete: `app/tests/sessionResume.test.ts`
- Delete: `app/tests/sessionResumeStoreFlow.test.cjs`
- Delete: `app/tests/resumeSessionEntryFlow.test.cjs`

- [ ] **Step 1: 先把 store 改回纯内存会话**

从 `session.ts` 删除：

- `ResumeSnapshot` / `ResumeSnapshotEmotion` imports
- `sessionApi` import
- `clearResumeSnapshot/loadResumeSnapshot/saveResumeSnapshot` imports
- `buildResumePlan()` / `buildResumeEmotion()`
- `resumeSnapshot` / `hasResumableSession`
- `clearStoredResumeSnapshot()`
- `saveCurrentResumeSnapshot()` / `persistResumeSnapshot()`
- `refreshResumeSnapshot()` / `validateResumeSession()` / `resumeSavedSession()`
- `updateResumeProgress()`

保留并确认还在：

```ts
startSession()
pauseTherapy()
resumeTherapy()
stopNowSession()
endSession()
resetSession()
fetchReport()
```

- [ ] **Step 2: 把疗愈页改回只依赖内存态会话**

从 `TherapyPage.vue` 删除：

- `resumedPhaseIndex`
- `resumedElapsedSeconds`
- `sessionStore.updateResumeProgress(...)`
- `onMounted()` 中的恢复赋值

保留：

```ts
if (!sessionStore.isTherapyActive) {
  router.push('/')
  return
}
```

- [ ] **Step 3: 删除 API 和类型里的恢复残留**

从 `api/index.ts` 删除：

```ts
export const sessionApi = {
  getSession: async (sessionId: string): Promise<any> => { ... }
}
```

从 `types/index.ts` 删除：

- `ResumeSnapshotEmotion`
- `ResumeSnapshot`

- [ ] **Step 4: 处理历史本地存储残留**

在 `WelcomePage.vue` 的 `onMounted()` 中加入最小清理：

```ts
onMounted(() => {
  localStorage.removeItem('therapy_resume_snapshot')
})
```

不要重新引入恢复工具文件，只做一次安全迁移清理。

- [ ] **Step 5: 扫描残留引用并删除已废弃文件**

先在 `app/src` 和 `app/tests` 做一次残留扫描，确认除欢迎页历史 key 清理外，不再需要任何 resume 符号：

```powershell
Get-ChildItem app/src,app/tests -Recurse -File | Select-String -Pattern 'ResumeSessionCard|sessionResume|resumeSavedSession|validateResumeSession|updateResumeProgress|continuePreviousSession|noResumableSession|resumeFailed'
```

预期：只允许看到本 chunk 正在修改的文件命中；完成清理后再次执行应无结果。

然后删除：

- `app/src/components/entry/ResumeSessionCard.vue`
- `app/src/utils/sessionResume.ts`
- `app/tests/sessionResume.test.ts`
- `app/tests/sessionResumeStoreFlow.test.cjs`
- `app/tests/resumeSessionEntryFlow.test.cjs`

- [ ] **Step 6: 重新运行清理相关测试并确认转绿**

运行：

```bash
node --test app/tests/startOnlySessionCleanupFlow.test.cjs app/tests/therapyResumeStateFlow.test.cjs app/tests/sessionFastEndFlow.test.cjs app/tests/therapyEndFlow.test.cjs app/tests/therapyStopNowFlow.test.cjs
```

预期：全部 PASS

- [ ] **Step 7: 做恢复清理的阶段性类型检查**

运行：

```powershell
Push-Location app; npx vue-tsc --noEmit; Pop-Location
```

预期：退出码 `0`

- [ ] **Step 8: 做一次最小 smoke check**

运行开发环境后快速确认：

- 首页已无继续疗愈入口
- 从 `/` 进入疗愈后刷新 `/therapy` 会回到 `/`
- 首页打开时不会因旧 `therapy_resume_snapshot` 残留而报错

## Chunk 3: 收尾验证

### Task 5: 跑完整 start-only 切片回归

**Files:**
- Modify as needed based on verification failures:
  - `app/src/views/WelcomePage.vue`
  - `app/src/views/AssessmentPage.vue`
  - `app/src/router/index.ts`
  - `app/src/components/entry/AssessmentEntryPanel.vue`
  - `app/src/views/TherapyPage.vue`
  - `app/src/stores/session.ts`
  - `app/src/api/index.ts`
  - `app/src/types/index.ts`
  - `app/src/i18n/locales/zh.ts`
  - `app/src/i18n/locales/en.ts`
  - `app/tests/unifiedEntryPageFlow.test.cjs`
  - `app/tests/assessmentManualLocale.test.cjs`
  - `app/tests/startOnlySessionCleanupFlow.test.cjs`
  - `app/tests/assessmentRouteCompatibility.test.cjs`
  - `app/tests/sessionFastEndFlow.test.cjs`

- [ ] **Step 1: 运行全部 start-only 相关 node 测试**

运行：

```bash
node --test app/tests/unifiedEntryPageFlow.test.cjs app/tests/assessmentManualLocale.test.cjs app/tests/assessmentRouteCompatibility.test.cjs app/tests/assessmentPageManualFlow.test.cjs app/tests/startOnlySessionCleanupFlow.test.cjs app/tests/therapyResumeStateFlow.test.cjs app/tests/sessionFastEndFlow.test.cjs app/tests/therapyEndFlow.test.cjs app/tests/therapyStopNowFlow.test.cjs
```

预期：全部 PASS

- [ ] **Step 2: 运行类型检查**

运行：

```powershell
Push-Location app; npx vue-tsc --noEmit; Pop-Location
```

预期：退出码 `0`

- [ ] **Step 3: 运行构建冒烟**

运行：

```powershell
Push-Location app; npm run build; Pop-Location
```

预期：退出码 `0`

- [ ] **Step 4: 手工验证关键行为**

运行 `Push-Location app; npm run electron:dev; Pop-Location`（桌面壳）或至少 `Push-Location app; npm run dev; Pop-Location`（Web）后确认：

- `/` 打开后直接看到评估区域，无需点“开始新评估”
- 首页仍保留欢迎品牌区、副标题、说明文案和语言切换
- 首页不存在“继续上次疗愈”相关卡片、按钮、提示
- 麦克风不可用时仍能切到手动情绪按钮
- 从评估进入疗愈后，刷新 `/therapy` 会回到 `/`
- 如果本地预先写入旧 `therapy_resume_snapshot`，进入首页后不会恢复旧会话，且 key 会被清理
- `/assessment` 仍可打开评估包装页

- [ ] **Step 5: 对照 spec 逐项复核**

核对 `docs/superpowers/specs/2026-03-19-unified-entry-start-only-design.md`：

- `/` 为统一主入口
- 仅保留开始评估
- 首页仍保留欢迎品牌壳与语言切换
- 不再恢复未完成会话
- `/assessment` 仍兼容
- 旧 `therapy_resume_snapshot` 已安全清理
- store / API / types 中恢复逻辑已清理
- locale 中恢复文案已清理
- 废弃组件 / 工具 / 测试文件已清理
