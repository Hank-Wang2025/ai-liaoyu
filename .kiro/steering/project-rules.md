# 智能疗愈仓项目规则

## 语言规范

- 与用户对话时使用中文
- 代码注释使用中文
- Git commit 信息使用中文
- 文档使用中文编写

## 项目概述

这是一个智能疗愈仓系统，包含：
- 后端：Python FastAPI
- 前端：Vue 3 + TypeScript + Electron
- 数据库：SQLite (aiosqlite)

## Python 代码规范

### 通用规则
- 使用 Python 3.10+
- 遵循 PEP 8 规范
- 使用 type hints 进行类型标注
- 使用 async/await 处理异步操作
- 使用 loguru 进行日志记录

### 命名规范
- 类名：PascalCase（如 `EmotionAnalyzer`）
- 函数/方法：snake_case（如 `analyze_emotion`）
- 常量：UPPER_SNAKE_CASE（如 `MAX_RETRY_COUNT`）
- 私有成员：前缀下划线（如 `_internal_state`）

### 文件结构
```
backend/
├── api/          # FastAPI 路由
├── services/     # 业务逻辑服务
├── models/       # Pydantic 数据模型
├── db/           # 数据库相关
└── tests/        # 测试文件
```

### 测试规范
- 使用 pytest 进行测试
- 使用 pytest-asyncio 测试异步代码
- 使用 hypothesis 进行属性测试
- 测试文件命名：`test_*.py`

## TypeScript/Vue 代码规范

### 通用规则
- 使用 TypeScript 严格模式
- 使用 Vue 3 Composition API
- 使用 Pinia 进行状态管理
- 使用 SCSS 编写样式

### 命名规范
- 组件名：PascalCase（如 `TherapyPage.vue`）
- 变量/函数：camelCase（如 `startSession`）
- 常量：UPPER_SNAKE_CASE
- 接口/类型：PascalCase（如 `EmotionData`）

### 文件结构
```
app/src/
├── views/        # 页面组件
├── components/   # 可复用组件
├── stores/       # Pinia 状态管理
├── styles/       # 全局样式
└── types/        # TypeScript 类型定义
```

## Git 规范

### Commit 信息格式
```
<类型>: <简短描述>

[可选的详细描述]
```

### 类型
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

## API 规范

- RESTful 风格
- 使用 JSON 格式
- 错误响应包含 `detail` 字段
- 路由前缀：`/api/<模块名>`

## 安全规范

- 敏感配置使用环境变量
- 用户数据加密存储
- API 需要适当的认证
- 日志中不记录敏感信息
