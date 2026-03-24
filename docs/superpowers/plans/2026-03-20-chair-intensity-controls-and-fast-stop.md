# Chair Intensity Controls And Fast Stop Implementation Plan

> **For agentic workers:** REQUIRED: Use $subagent-driven-development (if subagents available) or $executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把疗愈页里的“更放松 / 更有力”从切歌式方案切换改成真实的按摩椅力度调节，并复核停止链路的体感响应。

**Architecture:** 保留前端现有四按钮布局和接口入口，但把后端 `adjust-intensity` 的语义收窄为“仅调整按摩椅力度档位”。启动疗愈时给执行器注入可用的座椅控制器，运行中直接更新当前与后续 phase 的 `chair.intensity`，只重下发 chair 配置，不重播音频、不重切方案。停止链路保持“先跳报告页、后台收尾”，并补测试确认它没有重新退化为阻塞式结束。

**Tech Stack:** Vue 3、Pinia、TypeScript、FastAPI、Python、pytest、node:test、vue-tsc

---

## Chunk 1: Lock Down The Bug With Tests

### Task 1: 后端锁定“调力度不能切歌”

**Files:**
- Modify: `backend/tests/test_therapy_runtime_intensity_adjustment.py`
- Modify: `backend/tests/test_therapy_api_executor_lifecycle.py`

- [ ] **Step 1: 为运行中调节新增红灯测试，断言只更新 chair intensity**

```python
async def test_adjust_therapy_intensity_changes_chair_only(...):
    response = await therapy_api.adjust_therapy_intensity(...)
    assert response["changed"] is True
    assert response["plan"]["intensity"] == "low"
    assert fake_executor.adjust_chair_calls == ["relax"]
```

- [ ] **Step 2: 为执行器新增红灯测试，断言调节时不触发音频重载**

```python
async def test_adjust_chair_intensity_does_not_reload_audio():
    await executor.adjust_chair_intensity("relax")
    assert audio_calls == []
    assert chair_calls == [expected_intensity]
```

- [ ] **Step 3: 为启动链路新增红灯测试，断言 `TherapyExecutor` 能拿到 chair manager**

Run: `backend\venv\Scripts\pytest.exe backend/tests/test_therapy_api_executor_lifecycle.py -v`
Expected: FAIL，提示执行器未注入座椅控制依赖或不存在新方法

- [ ] **Step 4: 跑新增后端测试确认红灯**

Run: `backend\venv\Scripts\pytest.exe backend/tests/test_therapy_runtime_intensity_adjustment.py -v`
Expected: FAIL，提示仍走旧的整方案切换语义

### Task 2: 前端锁定停止链路不能回退成阻塞

**Files:**
- Modify: `app/tests/therapyStopNowFlow.test.cjs`

- [ ] **Step 1: 写红灯测试，断言点击结束后先跳报告页，再等待后台 stop**

```javascript
test('therapy page navigates before stop-now settles', async () => {
  const timeline = []
  // record push/report before stop promise resolve
})
```

- [ ] **Step 2: 跑前端测试确认红灯**

Run: `node --test app/tests/therapyStopNowFlow.test.cjs`
Expected: FAIL，若当前实现被阻塞会在断言顺序处失败

---

## Chunk 2: Implement Chair-Only Runtime Intensity Adjustment

### Task 3: 给执行器增加“只调座椅力度”的运行中能力

**Files:**
- Modify: `backend/services/therapy_executor.py`

- [ ] **Step 1: 写最小实现接口 `adjust_chair_intensity(direction)`**

```python
async def adjust_chair_intensity(self, direction: str) -> dict[str, Any]:
    ...
```

- [ ] **Step 2: 只更新当前和后续 phase 的 `chair.intensity`，不改 `audio.file`**

```python
current_phase.chair.intensity = target_intensity
for phase in future_phases:
    if phase.chair:
        phase.chair.intensity = target_intensity
```

- [ ] **Step 3: 只重下发当前 chair 配置，不调用 `_apply_audio_config` 或整套 `_apply_phase_config`**

```python
if current_phase.chair and self._chair_manager:
    await self._apply_chair_config(current_phase.chair)
```

- [ ] **Step 4: 发出 `chair_intensity_adjusted` 事件并返回当前档位摘要**

- [ ] **Step 5: 跑执行器测试转绿**

Run: `backend\venv\Scripts\pytest.exe backend/tests/test_therapy_runtime_intensity_adjustment.py -v`
Expected: PASS

### Task 4: 启动疗愈时真正接入座椅控制器

**Files:**
- Modify: `backend/api/therapy.py`
- Reference: `backend/services/device_initializer.py`
- Reference: `backend/services/chair_controller.py`

- [ ] **Step 1: 提取执行器创建逻辑，集中组装 `audio_player` + `chair_manager`**

```python
async def _build_therapy_executor() -> TherapyExecutor:
    ...
```

- [ ] **Step 2: 从 `get_device_initializer()` 获取已初始化的 chair controller；若存在则包进 `ChairControllerManager`**

```python
initializer = get_device_initializer()
chair_controller = initializer.get_chair_controller()
```

- [ ] **Step 3: `start_therapy` 使用新的执行器构建函数**

- [ ] **Step 4: `adjust_therapy_intensity` 改为调用 `executor.adjust_chair_intensity(direction)`，不再走候选方案切换**

- [ ] **Step 5: 返回给前端的 `plan` 保持当前 plan 基本信息，但强度字段用新的 chair 档位映射刷新**

- [ ] **Step 6: 跑 API 生命周期测试转绿**

Run: `backend\venv\Scripts\pytest.exe backend/tests/test_therapy_api_executor_lifecycle.py -v`
Expected: PASS

### Task 5: 收窄 API 响应语义并保留边界提示

**Files:**
- Modify: `backend/api/therapy.py`
- Modify: `backend/tests/test_therapy_runtime_intensity_adjustment.py`

- [ ] **Step 1: 保留 `targetIntensity / changed / atBoundary` 响应结构**
- [ ] **Step 2: 调整测试，让 `plan.id` 不再要求切到另一套方案，但要断言 `plan.intensity` 和 chair 配置已更新**
- [ ] **Step 3: 边界时继续返回 `changed = false`**
- [ ] **Step 4: 跑相关后端测试**

Run: `backend\venv\Scripts\pytest.exe backend/tests/test_therapy_runtime_intensity_adjustment.py -v`
Expected: PASS

---

## Chunk 3: Verify Frontend Behavior And Stop Responsiveness

### Task 6: 保持前端按钮链路不变，但验证体感响应

**Files:**
- Modify: `app/src/views/TherapyPage.vue` (only if stop path ordering needs adjustment)
- Modify: `app/tests/therapyIntensityControlsFlow.test.cjs` (only if response handling changes)
- Modify: `app/tests/therapyStopNowFlow.test.cjs`

- [ ] **Step 1: 先不改前端交互语义，只在需要时微调 `endTherapy()` 的调用顺序**
- [ ] **Step 2: 确保结束按钮仍然是“立即切页，后台 stop-now 收尾”**
- [ ] **Step 3: 跑前端相关测试**

Run: `node --test app/tests/therapyIntensityControlsFlow.test.cjs app/tests/therapyStopNowFlow.test.cjs app/tests/therapyEndFlow.test.cjs app/tests/sessionFastEndFlow.test.cjs`
Expected: PASS

### Task 7: 全量回归并重启服务

**Files:**
- Modify as needed based on failures

- [ ] **Step 1: 跑后端回归**

Run: `backend\venv\Scripts\pytest.exe backend/tests/test_therapy_runtime_intensity_adjustment.py backend/tests/test_therapy_api_executor_lifecycle.py backend/tests/test_therapy_executor_pause_resume.py -v`
Expected: PASS

- [ ] **Step 2: 跑前端类型检查**

Run: `Push-Location app; npx vue-tsc --noEmit; Pop-Location`
Expected: PASS

- [ ] **Step 3: 重启前后端服务并做一次手工验证**

Checklist:
- 点击“更放松”后音乐不中断、座椅力度降低
- 点击“更有力”后音乐不中断、座椅力度升高
- 点击“结束”后页面立即进入报告页
