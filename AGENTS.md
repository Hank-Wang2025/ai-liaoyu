# 仓库指南

## 项目结构与模块组织
`backend/` 是 FastAPI 后端；`api/` 放路由，`services/` 放设备控制和疗愈流程，`db/` 负责 SQLite 访问，`tests/` 覆盖单元、集成和性质测试。`app/` 是 Electron + Vue 客户端；`src/` 放页面、组件、Pinia 状态和 API 封装，`electron/` 放桌面端入口。运行时资源在 `content/`，配置模板在 `config/`，本地数据在 `data/`，部署和说明文档在 `docs/`。

## 构建、测试与开发命令
后端初始化：
`cd backend`
`python -m venv venv`
macOS/Linux 用 `source venv/bin/activate`，Windows 用 `venv\Scripts\activate`
`pip install -r requirements.txt`
`uvicorn main:app --reload` 启动本地 API。

后端测试：
`pytest` 运行全部测试。
`pytest backend/tests/test_database_crud.py -v` 运行单个模块。
`pytest -k integration` 运行集成测试。

前端开发：
`cd app && npm install`
`npm run dev` 启动 Web 界面。
`npm run electron:dev` 启动桌面壳。
`npm run build` 会执行 `vue-tsc --noEmit`、Vite 构建和 Electron 打包。
`npm run preview` 预览构建产物。

## 代码风格与命名约定
Python 遵循 PEP 8，使用 4 空格缩进、`snake_case` 模块名、必要的类型注解，以及简短明了的 docstring。新增后端文件应延续现有拆分方式，例如 `backend/services/device_manager.py`。Vue 代码使用 `<script setup lang="ts">`，采用 2 空格缩进，组件名用 `PascalCase`，状态与工具函数用 `camelCase`。新增样式前，优先复用 `app/src/styles/main.scss` 中的公共样式。

## 测试规范
后端测试放在 `backend/tests/`，文件名使用 `test_<subject>.py` 或 `test_<subject>_properties.py`。异步流程使用 `pytest-asyncio`，性质测试尽量紧贴对应行为。提交 PR 前至少运行一次完整 `pytest`。前端目前以手工验证为主；涉及界面改动时，请在 `npm run dev` 或 `npm run electron:dev` 中实际走通相关页面，并在 PR 中写明验证步骤。

## 提交与 Pull Request 规范
提交信息遵循现有 Conventional Commits 风格，例如 `feat: 初始化智能疗愈仓项目`。每次提交只聚焦一个逻辑变更。PR 需要说明影响范围、列出实际执行过的验证命令、关联任务或问题；如果改动涉及可见界面，还应附上截图。
