#!/bin/bash

# ============================================================================
# 智能疗愈仓 - 诊断报告生成脚本
# Healing Pod System - Diagnostic Report Generator
# ============================================================================

echo "=============================================="
echo "  智能疗愈仓 - 诊断报告"
echo "  Healing Pod System - Diagnostic Report"
echo "  生成时间: $(date)"
echo "=============================================="
echo ""

# System Information
echo "=== 系统信息 ==="
echo "macOS 版本: $(sw_vers -productVersion)"
echo "Mac 型号: $(sysctl -n hw.model)"
echo "CPU: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple Silicon')"
echo "架构: $(uname -m)"
echo "内存: $(sysctl -n hw.memsize | awk '{print $0/1024/1024/1024 " GB"}')"
echo ""

# Disk Space
echo "=== 磁盘空间 ==="
df -h / | tail -1
echo ""

# Python Environment
echo "=== Python 环境 ==="
if [[ -d "venv" ]]; then
    source venv/bin/activate 2>/dev/null
    echo "Python 版本: $(python --version 2>&1)"
    echo "pip 版本: $(pip --version 2>&1)"
    echo ""
    echo "关键包版本:"
    pip show torch fastapi uvicorn numpy opencv-python 2>/dev/null | grep -E "^(Name|Version):" | paste - -
else
    echo "虚拟环境未找到"
fi
echo ""

# Node.js Environment
echo "=== Node.js 环境 ==="
echo "Node 版本: $(node --version 2>/dev/null || echo '未安装')"
echo "npm 版本: $(npm --version 2>/dev/null || echo '未安装')"
echo ""

# Configuration Files
echo "=== 配置文件 ==="
for file in config/config.yaml config/devices.yaml config/data_retention.yaml; do
    if [[ -f "$file" ]]; then
        echo "$file: 存在 ($(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null) bytes)"
    else
        echo "$file: 不存在"
    fi
done
echo ""

# Database
echo "=== 数据库 ==="
if [[ -f "data/healing_pod.db" ]]; then
    echo "数据库文件: 存在 ($(ls -lh data/healing_pod.db | awk '{print $5}'))"
    echo "完整性检查: $(sqlite3 data/healing_pod.db 'PRAGMA integrity_check;' 2>&1)"
    echo "表数量: $(sqlite3 data/healing_pod.db '.tables' 2>/dev/null | wc -w)"
else
    echo "数据库文件: 不存在"
fi
echo ""

# AI Models
echo "=== AI 模型 ==="
if [[ -d "models" ]]; then
    for model_dir in models/*/; do
        if [[ -d "$model_dir" ]]; then
            model_name=$(basename "$model_dir")
            file_count=$(find "$model_dir" -type f | wc -l)
            size=$(du -sh "$model_dir" 2>/dev/null | cut -f1)
            echo "$model_name: $file_count 文件, $size"
        fi
    done
else
    echo "模型目录不存在"
fi
echo ""

# Services Status
echo "=== 服务状态 ==="
if pgrep -f "uvicorn" > /dev/null; then
    echo "后端服务: 运行中 (PID: $(pgrep -f 'uvicorn'))"
else
    echo "后端服务: 未运行"
fi

if pgrep -f "Electron" > /dev/null; then
    echo "前端应用: 运行中"
else
    echo "前端应用: 未运行"
fi
echo ""

# Port Status
echo "=== 端口状态 ==="
echo "端口 8000 (后端): $(lsof -i :8000 > /dev/null 2>&1 && echo '占用' || echo '空闲')"
echo "端口 3000 (前端开发): $(lsof -i :3000 > /dev/null 2>&1 && echo '占用' || echo '空闲')"
echo ""

# Hardware Devices
echo "=== 硬件设备 ==="
echo "USB 设备:"
system_profiler SPUSBDataType 2>/dev/null | grep -E "^\s+(Product ID|Vendor ID|Serial Number|Camera|Microphone|Audio)" | head -20
echo ""
echo "蓝牙状态: $(system_profiler SPBluetoothDataType 2>/dev/null | grep -E "State:" | head -1)"
echo ""

# Recent Logs
echo "=== 最近日志 (最后 20 行) ==="
if [[ -f "backend/logs/healing_pod.log" ]]; then
    tail -20 backend/logs/healing_pod.log
else
    echo "日志文件不存在"
fi
echo ""

# MPS Check
echo "=== MPS (Metal Performance Shaders) 检查 ==="
if [[ -d "venv" ]]; then
    source venv/bin/activate 2>/dev/null
    python -c "
import torch
print(f'PyTorch 版本: {torch.__version__}')
print(f'MPS 可用: {torch.backends.mps.is_available()}')
print(f'MPS 已构建: {torch.backends.mps.is_built()}')
" 2>&1
else
    echo "无法检查 (虚拟环境未找到)"
fi
echo ""

echo "=============================================="
echo "  诊断报告生成完成"
echo "=============================================="
