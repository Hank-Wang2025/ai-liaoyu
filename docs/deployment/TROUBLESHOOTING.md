# 故障排查指南 | Troubleshooting Guide

## 概述 | Overview

本文档提供智能疗愈仓系统常见问题的诊断和解决方案。

This document provides diagnosis and solutions for common issues in the Healing Pod System.

---

## 快速诊断 | Quick Diagnosis

### 运行诊断脚本

```bash
cd healing-pod
source venv/bin/activate

# 运行完整诊断
python -c "
import sys
import os

print('=== 系统诊断 ===')
print(f'Python 版本: {sys.version}')
print(f'工作目录: {os.getcwd()}')

# 检查关键模块
modules = ['torch', 'fastapi', 'cv2', 'numpy', 'sounddevice']
for mod in modules:
    try:
        __import__(mod)
        print(f'{mod}: OK')
    except ImportError as e:
        print(f'{mod}: FAILED - {e}')

# 检查 MPS
try:
    import torch
    print(f'MPS 可用: {torch.backends.mps.is_available()}')
except:
    print('MPS 检查失败')

# 检查配置文件
configs = ['config/config.yaml', 'config/devices.yaml']
for cfg in configs:
    print(f'{cfg}: {\"存在\" if os.path.exists(cfg) else \"不存在\"}')

# 检查数据库
db_path = 'data/healing_pod.db'
print(f'数据库: {\"存在\" if os.path.exists(db_path) else \"不存在\"}')

# 检查模型目录
models_dir = 'models'
if os.path.exists(models_dir):
    models = os.listdir(models_dir)
    print(f'模型目录: {len(models)} 个子目录')
else:
    print('模型目录: 不存在')
"
```

---

## 常见问题 | Common Issues

### 1. 系统启动问题

#### 问题：应用无法启动

**症状：** 双击应用图标后无反应或闪退

**解决方案：**

1. 检查系统要求
```bash
# 检查 macOS 版本
sw_vers

# 检查可用内存
vm_stat | head -5
```

2. 检查应用权限
```bash
# 允许运行未签名应用
sudo spctl --master-disable
```

3. 查看崩溃日志
```bash
# 打开控制台应用
open /Applications/Utilities/Console.app
# 搜索 "healing" 或 "疗愈"
```

4. 从终端启动查看错误
```bash
/Applications/智能疗愈仓.app/Contents/MacOS/智能疗愈仓
```

#### 问题：后端服务无法启动

**症状：** `uvicorn` 启动失败

**解决方案：**

1. 检查端口占用
```bash
lsof -i :8000
# 如果被占用，杀死进程
kill -9 <PID>
```

2. 检查 Python 环境
```bash
which python
python --version
pip list | grep fastapi
```

3. 重新安装依赖
```bash
pip install -r backend/requirements.txt --force-reinstall
```

---

### 2. AI 模型问题

#### 问题：模型加载超时

**症状：** 启动时卡在 "加载模型..." 超过 60 秒

**解决方案：**

1. 检查模型文件完整性
```bash
./scripts/download_models.sh --verify
```

2. 检查磁盘空间
```bash
df -h
```

3. 检查内存使用
```bash
top -l 1 | head -10
```

4. 尝试单独加载模型
```bash
python -c "
import torch
print(f'MPS 可用: {torch.backends.mps.is_available()}')

# 测试加载小模型
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('models/qwen', local_files_only=True)
print('Tokenizer 加载成功')
"
```

#### 问题：MPS 不可用

**症状：** `torch.backends.mps.is_available()` 返回 False

**解决方案：**

1. 确认 Mac 型号支持 MPS（需要 Apple Silicon）
```bash
uname -m  # 应显示 arm64
```

2. 更新 PyTorch
```bash
pip install --upgrade torch torchvision torchaudio
```

3. 检查 macOS 版本（需要 12.3+）
```bash
sw_vers -productVersion
```

#### 问题：语音识别不准确

**症状：** SenseVoice 识别结果错误率高

**解决方案：**

1. 检查音频质量
   - 确保麦克风正常工作
   - 减少环境噪音
   - 调整麦克风位置

2. 检查音频格式
```bash
# 测试录音
python -c "
import sounddevice as sd
import numpy as np

duration = 3
fs = 16000
print('录音 3 秒...')
audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
sd.wait()
print(f'录音完成，形状: {audio.shape}')
print(f'音量范围: {audio.min():.4f} - {audio.max():.4f}')
"
```

3. 重新下载模型
```bash
rm -rf models/sensevoice
./scripts/download_models.sh --sensevoice
```

---

### 3. 设备连接问题

#### 问题：摄像头无法使用

**症状：** 面部分析功能不可用

**解决方案：**

1. 检查摄像头权限
   - 系统设置 → 隐私与安全性 → 摄像头
   - 确保应用已获得权限

2. 测试摄像头
```bash
python -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    ret, frame = cap.read()
    print(f'摄像头正常，分辨率: {frame.shape}')
    cap.release()
else:
    print('无法打开摄像头')
"
```

3. 尝试不同的摄像头索引
```bash
python -c "
import cv2
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f'摄像头 {i}: 可用')
        cap.release()
    else:
        print(f'摄像头 {i}: 不可用')
"
```

#### 问题：蓝牙设备无法连接

**症状：** 心率带或座椅无法配对

**解决方案：**

1. 重置蓝牙
```bash
sudo pkill bluetoothd
```

2. 检查设备状态
```bash
system_profiler SPBluetoothDataType
```

3. 扫描 BLE 设备
```bash
python -c "
import asyncio
from bleak import BleakScanner

async def scan():
    print('扫描 BLE 设备...')
    devices = await BleakScanner.discover(timeout=10)
    for d in devices:
        print(f'  {d.name or \"未知\"}: {d.address}')
    print(f'共发现 {len(devices)} 个设备')

asyncio.run(scan())
"
```

4. 确保设备在配对模式
   - 参考设备说明书进入配对模式
   - 通常需要长按按钮

#### 问题：灯光无法控制

**症状：** Yeelight 灯带不响应

**解决方案：**

1. 检查网络连接
```bash
ping <灯光IP地址>
```

2. 确认局域网控制已开启
   - 打开 Yeelight App
   - 设备设置 → 局域网控制 → 开启

3. 测试灯光控制
```bash
python -c "
from yeelight import Bulb
bulb = Bulb('192.168.1.xxx')  # 替换为实际 IP
try:
    bulb.turn_on()
    print('灯光已开启')
except Exception as e:
    print(f'错误: {e}')
"
```

4. 检查防火墙设置
```bash
# 允许 Yeelight 端口
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
```

---

### 4. 音频问题

#### 问题：无声音输出

**症状：** 疗愈音乐和引导语无声

**解决方案：**

1. 检查系统音量
```bash
osascript -e "output volume of (get volume settings)"
```

2. 检查音频设备
```bash
python -c "
import sounddevice as sd
print('输出设备:')
for i, dev in enumerate(sd.query_devices()):
    if dev['max_output_channels'] > 0:
        print(f'  {i}: {dev[\"name\"]}')
"
```

3. 测试音频播放
```bash
afplay /System/Library/Sounds/Ping.aiff
```

4. 检查应用音频设置
```bash
python -c "
import sounddevice as sd
import numpy as np

# 生成测试音
fs = 44100
duration = 1
t = np.linspace(0, duration, int(fs * duration))
audio = 0.5 * np.sin(2 * np.pi * 440 * t)

print('播放测试音...')
sd.play(audio, fs)
sd.wait()
print('完成')
"
```

#### 问题：麦克风无法录音

**症状：** 语音输入无响应

**解决方案：**

1. 检查麦克风权限
   - 系统设置 → 隐私与安全性 → 麦克风

2. 检查输入设备
```bash
python -c "
import sounddevice as sd
print('输入设备:')
for i, dev in enumerate(sd.query_devices()):
    if dev['max_input_channels'] > 0:
        print(f'  {i}: {dev[\"name\"]}')
"
```

3. 测试录音
```bash
python -c "
import sounddevice as sd
import numpy as np

fs = 16000
duration = 2
print('录音 2 秒...')
audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
sd.wait()
print(f'录音完成')
print(f'音量: {np.abs(audio).mean():.6f}')
if np.abs(audio).mean() < 0.001:
    print('警告: 音量过低，请检查麦克风')
"
```

---

### 5. 数据库问题

#### 问题：数据库损坏

**症状：** 出现 "database is locked" 或 "database disk image is malformed"

**解决方案：**

1. 停止所有服务
```bash
launchctl stop com.healingpod.backend
pkill -f uvicorn
```

2. 检查数据库完整性
```bash
sqlite3 data/healing_pod.db "PRAGMA integrity_check;"
```

3. 尝试修复
```bash
sqlite3 data/healing_pod.db ".recover" | sqlite3 data/healing_pod_recovered.db
mv data/healing_pod.db data/healing_pod_corrupted.db
mv data/healing_pod_recovered.db data/healing_pod.db
```

4. 从备份恢复
```bash
cp data/backups/healing_pod_latest.db data/healing_pod.db
```

#### 问题：数据库文件过大

**症状：** 磁盘空间不足

**解决方案：**

1. 检查数据库大小
```bash
ls -lh data/healing_pod.db
```

2. 清理过期数据
```bash
python -c "
from backend.services.data_retention import DataRetentionService
import asyncio

async def cleanup():
    service = DataRetentionService()
    await service.cleanup_expired_data()
    print('清理完成')

asyncio.run(cleanup())
"
```

3. 压缩数据库
```bash
sqlite3 data/healing_pod.db "VACUUM;"
```

---

### 6. 性能问题

#### 问题：系统响应缓慢

**症状：** 操作延迟明显

**解决方案：**

1. 检查 CPU 和内存使用
```bash
top -l 1 | head -15
```

2. 检查磁盘 I/O
```bash
iostat -d 1 5
```

3. 减少并发模型加载
   - 编辑 `config/config.yaml`
   - 设置 `models.loading.parallel: false`

4. 降低分析频率
   - 编辑 `config/config.yaml`
   - 增加 `emotion.analysis_interval` 值

#### 问题：内存不足

**症状：** 应用崩溃或系统变慢

**解决方案：**

1. 检查内存使用
```bash
vm_stat
```

2. 关闭不必要的应用

3. 减少模型内存占用
```bash
# 使用量化模型（如果可用）
# 或禁用部分模型
```

4. 增加交换空间（不推荐，会影响性能）

---

## 日志分析 | Log Analysis

### 查看应用日志

```bash
# 后端日志
tail -f logs/healing_pod.log

# 系统日志
log show --predicate 'process == "智能疗愈仓"' --last 1h
```

### 常见错误代码

| 错误代码 | 含义 | 解决方案 |
|----------|------|----------|
| E001 | 模型加载失败 | 重新下载模型 |
| E002 | 设备连接失败 | 检查设备状态 |
| E003 | 数据库错误 | 检查数据库完整性 |
| E004 | 配置错误 | 检查配置文件格式 |
| E005 | 权限不足 | 检查文件权限 |

---

## 获取帮助 | Getting Help

### 收集诊断信息

```bash
# 生成诊断报告
./scripts/generate_diagnostic_report.sh > diagnostic_report.txt
```

### 联系支持

1. 查看 FAQ：https://healingpod.com/faq
2. 提交 Issue：https://github.com/your-org/healing-pod/issues
3. 邮件支持：support@healingpod.com

提交问题时请附上：
- 诊断报告
- 错误日志
- 复现步骤
- 系统信息（macOS 版本、Mac 型号）

---

## 重置系统 | System Reset

### 软重置（保留数据）

```bash
# 停止服务
launchctl stop com.healingpod.backend

# 清除缓存
rm -rf ~/.cache/healing-pod

# 重新初始化配置
./scripts/init_config.sh

# 重启服务
launchctl start com.healingpod.backend
```

### 硬重置（清除所有数据）

⚠️ **警告：此操作将删除所有用户数据！**

```bash
# 停止服务
launchctl stop com.healingpod.backend

# 备份数据（可选）
cp -r data data_backup_$(date +%Y%m%d)

# 删除数据
rm -rf data/*
rm -rf config/*

# 重新初始化
./scripts/init_config.sh

# 重启服务
launchctl start com.healingpod.backend
```
