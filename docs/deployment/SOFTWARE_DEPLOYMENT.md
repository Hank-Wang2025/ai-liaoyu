# 软件部署指南 | Software Deployment Guide

## 概述 | Overview

本文档介绍智能疗愈仓系统的软件安装和部署流程。

This document describes the software installation and deployment process for the Healing Pod System.

---

## 系统要求 | System Requirements

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | Apple M1 | Apple M4 Pro |
| 内存 | 16GB | 48GB |
| 存储 | 256GB SSD | 512GB SSD |
| 显卡 | 集成 GPU | 集成 GPU (MPS) |

### 软件要求

| 软件 | 版本要求 |
|------|----------|
| macOS | 13.0 (Ventura) 或更高 |
| Python | 3.11.x |
| Node.js | 20.x LTS |
| Git | 2.x |

---

## 快速安装 | Quick Installation

### 一键安装

```bash
# 克隆项目
git clone https://github.com/your-org/healing-pod.git
cd healing-pod

# 运行安装脚本
./scripts/install_dependencies.sh
./scripts/download_models.sh
./scripts/init_config.sh
```

---

## 详细安装步骤 | Detailed Installation

### 1. 安装系统依赖

#### 1.1 安装 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Apple Silicon Mac 需要添加到 PATH
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

#### 1.2 安装基础工具

```bash
brew install python@3.11 node@20 git ffmpeg portaudio opencv
```

### 2. 获取源代码

```bash
# 克隆仓库
git clone https://github.com/your-org/healing-pod.git
cd healing-pod

# 或下载发布版本
curl -L https://github.com/your-org/healing-pod/releases/latest/download/healing-pod.tar.gz | tar xz
```

### 3. 配置 Python 环境

```bash
# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r backend/requirements.txt
```

### 4. 下载 AI 模型

```bash
# 下载所有模型（约 30GB，需要较长时间）
./scripts/download_models.sh

# 或分别下载
./scripts/download_models.sh --sensevoice
./scripts/download_models.sh --emotion2vec
./scripts/download_models.sh --cosyvoice
./scripts/download_models.sh --qwen
./scripts/download_models.sh --face

# 验证模型
./scripts/download_models.sh --verify
```

### 5. 初始化配置

```bash
./scripts/init_config.sh
```

这将创建：
- `config/config.yaml` - 主配置文件
- `config/devices.yaml` - 设备配置
- `config/.encryption_key` - 加密密钥
- `data/healing_pod.db` - SQLite 数据库

### 6. 配置设备

编辑 `config/devices.yaml`，填入实际设备信息：

```yaml
lights:
  - name: "主灯"
    type: "yeelight"
    ip: "192.168.1.100"  # 替换为实际 IP
    enabled: true

heart_rate:
  type: "bluetooth"
  address: "AA:BB:CC:DD:EE:FF"  # 替换为实际地址
  enabled: true
```

#### 配置文件查找顺序

系统按以下顺序查找设备配置文件：
1. 环境变量 `HEALING_POD_DEVICE_CONFIG` 指定的路径
2. `config/devices.yaml`
3. `config/devices.yml`
4. `../config/devices.yaml`
5. `devices.yaml`

#### 使用环境变量指定配置

```bash
# 指定自定义配置文件路径
export HEALING_POD_DEVICE_CONFIG=/path/to/custom/devices.yaml
```

#### 设备自动初始化

系统启动时会自动根据配置文件初始化所有设备：

1. 读取 `config/devices.yaml` 配置
2. 按配置并行初始化各类设备（心率、灯光、座椅、香薰、音频）
3. 设备初始化失败时自动启用模拟模式（如果 `enable_mock_fallback: true`）
4. 记录初始化结果到日志

启动日志示例：
```
INFO     开始初始化硬件设备...
INFO     灯光设备 'main_light' (yeelight) 连接成功
WARNING  心率设备连接失败，使用模拟模式
INFO     设备初始化完成: 4/5 成功
```

如果某个设备初始化失败，系统会进入降级模式继续运行，相关功能将使用模拟器代替。

### 7. 安装前端依赖

```bash
cd app
npm install
cd ..
```

### 8. 构建应用

#### 开发模式

```bash
# 启动后端
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 新终端，启动前端（Electron 模式）
cd app
npm run electron:dev
```

#### 纯 Web 模式（无 Electron）

如果不需要 Electron 桌面应用功能，可以使用纯 Web 模式运行前端：

```bash
# 启动后端
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 新终端，启动纯 Web 前端
cd app
npm run dev -- --config vite.config.web.ts
```

纯 Web 模式特点：
- 运行在 `http://localhost:3000`
- 自动代理 `/api` 请求到后端 `http://localhost:8000`
- 适用于浏览器访问和开发调试
- 不包含 Electron 相关功能（如系统托盘、原生菜单等）

#### 生产构建

```bash
# 构建 macOS 桌面应用（Electron）
cd app
npm run electron:build:mac

# 输出位置：app/release/

# 构建纯 Web 版本
cd app
npm run build -- --config vite.config.web.ts

# 输出位置：app/dist/
```

---

## 配置说明 | Configuration

### 主配置文件 (config/config.yaml)

```yaml
# 系统设置
system:
  name: "智能疗愈仓"
  language: "zh"  # zh 或 en
  debug: false

# 服务器设置
server:
  host: "127.0.0.1"
  port: 8000

# AI 模型设置
models:
  device: "mps"  # Apple Silicon 使用 MPS 加速
  
# 情绪分析设置
emotion:
  fusion_weights:
    audio: 0.4
    face: 0.35
    bio: 0.25

# 隐私设置
privacy:
  encryption_enabled: true
  data_retention_days: 30
```

### 设备配置 (config/devices.yaml)

详见 [硬件安装指南](./HARDWARE_SETUP.md)

---

## 服务管理 | Service Management

### 使用 launchd 设置开机自启

#### 创建 plist 文件

```bash
cat > ~/Library/LaunchAgents/com.healingpod.backend.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.healingpod.backend</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/healing-pod/venv/bin/uvicorn</string>
        <string>main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/healing-pod/backend</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/healing-pod/backend/logs/backend.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/healing-pod/backend/logs/backend.error.log</string>
</dict>
</plist>
EOF
```

#### 加载服务

```bash
# 加载服务
launchctl load ~/Library/LaunchAgents/com.healingpod.backend.plist

# 启动服务
launchctl start com.healingpod.backend

# 停止服务
launchctl stop com.healingpod.backend

# 卸载服务
launchctl unload ~/Library/LaunchAgents/com.healingpod.backend.plist
```

### Electron 应用开机自启

应用内置了开机自启功能，可在系统托盘菜单中开启/关闭。

或手动设置：
1. 打开「系统设置」→「通用」→「登录项」
2. 点击「+」添加疗愈仓应用

---

## 数据备份 | Data Backup

### 手动备份

```bash
# 备份数据库
cp data/healing_pod.db data/backups/healing_pod_$(date +%Y%m%d).db

# 备份配置
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/
```

### 自动备份

系统默认每 24 小时自动备份数据库。配置位于 `config/config.yaml`：

```yaml
database:
  backup_enabled: true
  backup_interval: 86400  # 秒
```

### 恢复数据

```bash
# 停止服务
launchctl stop com.healingpod.backend

# 恢复数据库
cp data/backups/healing_pod_20241225.db data/healing_pod.db

# 重启服务
launchctl start com.healingpod.backend
```

---

## 更新升级 | Updates

### 更新应用

```bash
cd healing-pod

# 拉取最新代码
git pull origin main

# 更新 Python 依赖
source venv/bin/activate
pip install -r backend/requirements.txt

# 更新 Node.js 依赖
cd app
npm install
cd ..

# 重新构建
cd app
npm run electron:build:mac
```

### 更新 AI 模型

```bash
# 重新下载指定模型
./scripts/download_models.sh --qwen
```

---

## 安全建议 | Security Recommendations

### 1. 修改默认密码

首次登录管理后台后，立即修改默认密码。

### 2. 保护加密密钥

```bash
# 确保密钥文件权限正确
chmod 600 config/.encryption_key
```

### 3. 网络安全

- 将疗愈仓放置在独立的网络段
- 使用防火墙限制访问
- 定期更新系统和依赖

### 4. 数据安全

- 定期备份数据
- 启用数据加密
- 设置合理的数据保留期限

---

## 验证部署 | Verify Deployment

### 运行测试

```bash
source venv/bin/activate

# 运行后端测试
cd backend
pytest tests/ -v

# 检查服务状态
curl http://localhost:8000/health
```

### 检查清单

- [ ] 后端服务正常运行
- [ ] 前端应用正常启动
- [ ] AI 模型加载成功
- [ ] 数据库连接正常
- [ ] 设备连接正常
- [ ] 管理后台可访问

---

## 下一步 | Next Steps

部署完成后，请阅读：

1. [故障排查指南](./TROUBLESHOOTING.md)
2. [用户使用手册](../user/USER_MANUAL.md)
3. [管理员手册](../admin/ADMIN_MANUAL.md)
