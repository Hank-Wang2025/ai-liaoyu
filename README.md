# 智能疗愈仓系统 (Healing Pod System)

基于 Mac Mini M4 Pro 的本地化心理疗愈解决方案。

## 项目结构

```
├── backend/          # Python 后端服务
│   ├── api/          # FastAPI 路由
│   ├── db/           # 数据库操作
│   ├── models/       # 数据模型
│   └── services/     # 业务逻辑
├── app/              # Electron + Vue 3 前端
├── content/          # 内容资源
│   ├── audio/        # 音频文件
│   ├── visual/       # 视觉资源
│   └── plans/        # 疗愈方案配置
└── config/           # 系统配置
```

## 技术栈

- **后端**: Python + FastAPI
- **前端**: Electron + Vue 3 + TypeScript
- **数据库**: SQLite
- **AI 模型**: SenseVoice, emotion2vec+, CosyVoice 3.0, Qwen3-8B

## 快速开始

### 后端服务

```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

## 许可证

Private - All Rights Reserved
