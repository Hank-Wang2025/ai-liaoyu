# 硬件安装指南 | Hardware Setup Guide

## 概述 | Overview

本文档介绍智能疗愈仓系统的硬件安装和配置流程。

This document describes the hardware installation and configuration process for the Healing Pod System.

---

## 硬件清单 | Hardware Checklist

### 必需设备 | Required Equipment

| 设备 | 规格要求 | 用途 |
|------|----------|------|
| Mac Mini | M4 Pro, 48GB RAM 推荐 | 主控工作站 |
| 显示器 | 4K 分辨率，触摸屏推荐 | 用户界面 |
| USB 麦克风 | 指向性，采样率 ≥44.1kHz | 语音采集 |
| USB 摄像头 | 1080p，30fps | 面部表情捕捉 |
| 音响系统 | 2.1 或 4.0 声道 | 音频输出 |

### 可选设备 | Optional Equipment

| 设备 | 规格要求 | 用途 |
|------|----------|------|
| 心率手环 | 支持 BLE 协议 | 生理信号采集 |
| 智能灯带 | Yeelight / 飞利浦 Hue / 小米米家 / 涂鸦智能 / DMX512 | 氛围灯光 |
| 按摩座椅 | 支持蓝牙控制 | 触觉反馈 |
| 香薰机 | 支持 WiFi 控制 | 嗅觉刺激 |

---

## 安装步骤 | Installation Steps

### 1. Mac Mini 设置

#### 1.1 基础配置

1. 开箱并连接电源
2. 连接显示器（HDMI 或 USB-C）
3. 连接键盘和鼠标（首次设置用）
4. 完成 macOS 初始设置

#### 1.2 系统设置

```bash
# 启用开发者模式（如需要）
sudo spctl --master-disable

# 允许任何来源的应用
sudo spctl --master-enable

# 设置节能选项（防止休眠）
sudo pmset -a sleep 0
sudo pmset -a hibernatemode 0
sudo pmset -a disablesleep 1
```

#### 1.3 网络配置

- 连接到本地网络（WiFi 或以太网）
- 记录 IP 地址用于设备配置
- 建议使用静态 IP 地址

### 2. 音频设备安装

#### 2.1 USB 麦克风

1. 将 USB 麦克风连接到 Mac Mini
2. 打开「系统设置」→「声音」→「输入」
3. 选择 USB 麦克风作为输入设备
4. 调整输入音量至适当水平

#### 2.2 音响系统

1. 连接音响到 Mac Mini（USB 或 3.5mm）
2. 打开「系统设置」→「声音」→「输出」
3. 选择音响作为输出设备
4. 测试音频输出

**测试命令：**
```bash
# 播放测试音频
afplay /System/Library/Sounds/Ping.aiff
```

### 3. 摄像头安装

#### 3.1 USB 摄像头

1. 将 USB 摄像头连接到 Mac Mini
2. 将摄像头安装在用户正前方，距离约 50-80cm
3. 调整角度确保能捕捉完整面部

#### 3.2 权限设置

首次运行应用时，系统会请求摄像头权限。请点击「允许」。

手动检查权限：
1. 打开「系统设置」→「隐私与安全性」→「摄像头」
2. 确保疗愈仓应用已获得权限

### 4. 智能灯光安装

系统支持多种智能灯光品牌，请根据您的设备选择对应的配置方式。

#### 4.1 Yeelight 灯带

1. 按照 Yeelight 说明书安装灯带
2. 使用 Yeelight App 完成初始配置
3. 将灯带连接到与 Mac Mini 相同的 WiFi 网络
4. 在 Yeelight App 中开启「局域网控制」

#### 4.2 飞利浦 Hue

1. 安装 Hue Bridge 并连接到路由器
2. 使用 Hue App 完成灯具配对
3. 在 Hue Bridge 上注册应用获取 API key：
   - 访问 `http://<bridge_ip>/debug/clip.html`
   - POST 到 `/api`，body: `{"devicetype":"healing_pod#device"}`
   - 按下 Bridge 上的按钮后重新发送请求
   - 记录返回的 `username` 作为 API key

#### 4.3 小米米家

1. 使用米家 App 完成灯具配置
2. 获取设备 token（需要使用第三方工具如 miio-cli）
3. 确保设备与 Mac Mini 在同一网络

#### 4.4 涂鸦智能

1. 使用涂鸦智能 App 完成设备配置
2. 通过涂鸦 IoT 平台获取 device_id 和 local_key
3. 确保设备与 Mac Mini 在同一网络

#### 4.5 DMX512 专业灯光

1. 连接 USB-DMX 接口到 Mac Mini
2. 连接 DMX 灯具到 DMX 接口
3. 记录灯具的起始通道号

#### 4.6 获取灯光 IP 地址

```bash
# 扫描局域网设备
arp -a | grep -i "yeelight"

# 或使用 nmap（需先安装）
brew install nmap
nmap -sP 192.168.1.0/24
```

#### 4.7 配置灯光

编辑 `config/devices.yaml`：

```yaml
lights:
  # Yeelight 配置
  - name: "主灯"
    type: "yeelight"
    ip: "192.168.1.xxx"
    enabled: true

  # 飞利浦 Hue 配置
  - name: "Hue灯"
    type: "hue"
    bridge_ip: "192.168.1.xxx"
    api_key: "your_api_key"
    light_id: "1"
    enabled: true

  # 小米米家配置
  - name: "米家灯"
    type: "mihome"
    ip: "192.168.1.xxx"
    token: "your_32_char_token"
    enabled: true

  # 涂鸦智能配置
  - name: "涂鸦灯"
    type: "tuya"
    device_id: "your_device_id"
    ip: "192.168.1.xxx"
    local_key: "your_local_key"
    version: "3.3"
    enabled: true

  # DMX512 配置
  - name: "DMX灯"
    type: "dmx"
    port: "/dev/ttyUSB0"
    start_channel: 1
    enabled: true
```

### 5. 心率设备安装

#### 5.1 BLE 心率带

1. 确保心率带电量充足
2. 佩戴心率带（贴近皮肤）
3. 打开 Mac Mini 蓝牙

#### 5.2 配对设备

```bash
# 扫描 BLE 设备（需要 Python 环境）
source venv/bin/activate
python -c "
import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover()
    for d in devices:
        print(f'{d.name}: {d.address}')

asyncio.run(scan())
"
```

#### 5.3 配置心率设备

编辑 `config/devices.yaml`：

```yaml
heart_rate:
  type: "bluetooth"
  name: "Heart Rate Monitor"
  address: "XX:XX:XX:XX:XX:XX"  # 替换为实际地址
  enabled: true
```

### 6. 按摩座椅安装（可选）

#### 6.1 蓝牙座椅

1. 将座椅放置在疗愈仓内
2. 连接座椅电源
3. 开启座椅蓝牙模式

#### 6.2 配对和配置

使用与心率设备相同的方法扫描和配置。

### 7. 香薰机安装（可选）

#### 7.1 WiFi 香薰机

1. 按照香薰机说明书完成 WiFi 配置
2. 确保与 Mac Mini 在同一网络
3. 获取香薰机 IP 地址

---

## 布局建议 | Layout Recommendations

### 疗愈仓内部布局

```
┌─────────────────────────────────────────┐
│                 显示器                   │
│              ┌─────────┐                │
│              │         │                │
│              │  屏幕   │                │
│              │         │                │
│              └─────────┘                │
│                                         │
│    灯带 ─────────────────────── 灯带    │
│                                         │
│              ┌─────────┐                │
│              │ 摄像头  │                │
│              └─────────┘                │
│                                         │
│         ┌───────────────────┐           │
│         │                   │           │
│         │    按摩座椅       │           │
│         │                   │           │
│         └───────────────────┘           │
│                                         │
│    音响 ─────────────────────── 音响    │
│                                         │
│              [香薰机]                   │
│                                         │
└─────────────────────────────────────────┘
```

### 设备放置要点

1. **摄像头**：正对用户面部，距离 50-80cm
2. **麦克风**：靠近用户，避免音响干扰
3. **灯带**：环绕布置，避免直射眼睛
4. **音响**：左右对称放置，形成立体声场
5. **香薰机**：放置在通风位置

---

## 线缆管理 | Cable Management

### 建议

1. 使用线槽隐藏线缆
2. 为每条线缆贴上标签
3. 预留足够长度便于维护
4. 使用扎带整理多余线缆

### USB 集线器

如果 USB 端口不足，建议使用带电源的 USB 3.0 集线器。

---

## 验证安装 | Verify Installation

### 运行诊断脚本

```bash
# 检查所有设备连接状态
cd /path/to/healing-pod
source venv/bin/activate
python -c "
from backend.services.device_manager import DeviceManager
import asyncio

async def check():
    dm = DeviceManager()
    status = await dm.check_all_devices()
    for device, ok in status.items():
        print(f'{device}: {\"OK\" if ok else \"FAILED\"}')

asyncio.run(check())
"
```

### 检查清单

- [ ] Mac Mini 正常启动
- [ ] 显示器显示正常
- [ ] 麦克风可录音
- [ ] 摄像头可捕捉图像
- [ ] 音响可播放声音
- [ ] 灯光可控制（如已安装）
- [ ] 心率设备可连接（如已安装）
- [ ] 座椅可控制（如已安装）
- [ ] 香薰机可控制（如已安装）

---

## 常见问题 | Troubleshooting

### 摄像头无法识别

1. 尝试更换 USB 端口
2. 检查系统偏好设置中的权限
3. 重启 Mac Mini

### 蓝牙设备无法连接

1. 确保设备在配对模式
2. 重置蓝牙模块：`sudo pkill bluetoothd`
3. 检查设备电量

### 灯光无法控制

1. 确认灯光和 Mac Mini 在同一网络
2. 检查对应 App 中「局域网控制」是否开启
3. 验证 IP 地址是否正确
4. 飞利浦 Hue：确认 API key 有效
5. 小米米家：确认 token 正确（32位十六进制）
6. 涂鸦智能：确认 device_id 和 local_key 正确
7. DMX512：检查串口设备路径和通道配置

### 音频问题

1. 检查音量设置
2. 确认正确的输入/输出设备
3. 测试：`afplay /System/Library/Sounds/Ping.aiff`

---

## 下一步 | Next Steps

硬件安装完成后，请继续阅读：

1. [软件部署指南](./SOFTWARE_DEPLOYMENT.md)
2. [故障排查指南](./TROUBLESHOOTING.md)
