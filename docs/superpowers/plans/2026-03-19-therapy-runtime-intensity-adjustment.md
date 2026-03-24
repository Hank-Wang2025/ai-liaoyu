# Therapy Runtime Intensity Adjustment Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把疗愈页的四个控制按钮改成深色药丸按钮，并让“更放松 / 更有力”在疗愈运行中真实调整整体强度，同时保持总时长不变。

**Architecture:** 前端移除“下一曲 / 跳过阶段”，改为调用新的运行中强度调整接口，并用返回的新方案摘要刷新当前疗愈展示。后端新增运行中强度调整 API，通过 PlanManager 选择目标强度方案，并在 TherapyExecutor 中只替换当前和后续阶段配置、保留已执行时间和总时长。

**Tech Stack:** Vue 3、Pinia、TypeScript、FastAPI、Python、node:test、pytest、vue-tsc

---

### Task 1: 先写前端红灯测试锁定按钮和调用链

**Files:**
- Modify: `app/tests/therapyStopNowFlow.test.cjs`
- Create: `app/tests/therapyIntensityControlsFlow.test.cjs`

- [ ] **Step 1: 增加疗愈页按钮结构回归**
- [ ] **Step 2: 断言去掉 nextTrack / skipPhase，改为 relax / intensify**
- [ ] **Step 3: 运行 `node --test app/tests/therapyIntensityControlsFlow.test.cjs app/tests/therapyStopNowFlow.test.cjs`，确认红灯**

### Task 2: 先写后端红灯测试锁定运行中调强度行为

**Files:**
- Create: `backend/tests/test_therapy_runtime_intensity_adjustment.py`

- [ ] **Step 1: 断言 API 能按方向计算目标强度**
- [ ] **Step 2: 断言 executor 运行中调整后总时长不变**
- [ ] **Step 3: 断言找不到候选方案时安全失败**
- [ ] **Step 4: 运行 `pytest backend/tests/test_therapy_runtime_intensity_adjustment.py -v`，确认红灯**

### Task 3: 实现后端运行中强度调整能力

**Files:**
- Modify: `backend/api/therapy.py`
- Modify: `backend/services/plan_manager.py`
- Modify: `backend/services/therapy_executor.py`
- Modify: `backend/services/session_manager.py`

- [ ] **Step 1: 在 PlanManager 增加运行中候选方案选择逻辑**
- [ ] **Step 2: 在 TherapyExecutor 增加不重置总时长的运行中方案调整**
- [ ] **Step 3: 在 therapy API 新增强度调整接口并记录 adjustment**
- [ ] **Step 4: 运行后端测试，确认转绿**

### Task 4: 实现前端按钮改版和新接口接入

**Files:**
- Modify: `app/src/views/TherapyPage.vue`
- Modify: `app/src/stores/session.ts`
- Modify: `app/src/api/index.ts`
- Modify: `app/src/types/index.ts`
- Modify: `app/src/i18n/locales/zh.ts`
- Modify: `app/src/i18n/locales/en.ts`

- [ ] **Step 1: 增加运行中强度调整 API/types/store 方法**
- [ ] **Step 2: 把按钮改成深色药丸按钮和新文案**
- [ ] **Step 3: 增加边界禁用和轻提示**
- [ ] **Step 4: 运行前端测试与 `vue-tsc`，确认转绿**

### Task 5: 收尾验证

**Files:**
- Modify as needed based on verification failures

- [ ] **Step 1: 运行相关 node 测试**
- [ ] **Step 2: 运行相关 pytest**
- [ ] **Step 3: 运行 `Push-Location app; npx vue-tsc --noEmit; Pop-Location`**
