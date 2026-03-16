#!/bin/bash

# ============================================================================
# 智能疗愈仓 - 配置初始化脚本
# Healing Pod System - Configuration Initialization Script
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration directory
CONFIG_DIR="${CONFIG_DIR:-config}"
DATA_DIR="${DATA_DIR:-data}"
LOGS_DIR="${LOGS_DIR:-backend/logs}"

# Create directory structure
create_directories() {
    print_info "Creating directory structure..."
    
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "content/audio"
    mkdir -p "content/visual"
    mkdir -p "content/plans"
    mkdir -p "content/community"
    
    print_success "Directory structure created"
}

# Generate secure encryption key
generate_encryption_key() {
    print_info "Generating encryption key..."
    
    # Generate a 32-byte (256-bit) key for AES-256
    ENCRYPTION_KEY=$(openssl rand -base64 32)
    
    echo "$ENCRYPTION_KEY" > "$CONFIG_DIR/.encryption_key"
    chmod 600 "$CONFIG_DIR/.encryption_key"
    
    print_success "Encryption key generated and saved"
}

# Create main configuration file
create_main_config() {
    print_info "Creating main configuration file..."
    
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# ============================================================================
# 智能疗愈仓系统配置
# Healing Pod System Configuration
# ============================================================================

# 系统基本设置
system:
  name: "智能疗愈仓"
  version: "1.0.0"
  language: "zh"  # zh, en
  debug: false
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR

# API 服务器设置
server:
  host: "127.0.0.1"
  port: 8000
  cors_origins:
    - "http://localhost:3000"
    - "http://127.0.0.1:3000"

# 数据库设置
database:
  path: "data/healing_pod.db"
  backup_enabled: true
  backup_interval: 86400  # 24 hours in seconds

# AI 模型设置
models:
  base_path: "models"
  device: "mps"  # mps for Apple Silicon, cpu for fallback
  
  sensevoice:
    enabled: true
    model_path: "sensevoice"
    language: "auto"
    
  emotion2vec:
    enabled: true
    model_path: "emotion2vec"
    
  cosyvoice:
    enabled: true
    model_path: "cosyvoice"
    default_speaker: "中文女"
    
  qwen:
    enabled: true
    model_path: "qwen"
    max_tokens: 512
    temperature: 0.7

# 情绪分析设置
emotion:
  # 多模态融合权重
  fusion_weights:
    audio: 0.4
    face: 0.35
    bio: 0.25
  
  # 分析间隔（秒）
  analysis_interval: 10
  
  # 情绪变化阈值
  change_threshold: 0.1

# 疗愈引擎设置
therapy:
  # 默认疗愈时长（分钟）
  default_duration: 20
  
  # 无效果自动切换时间（秒）
  auto_switch_timeout: 180
  
  # 默认风格
  default_style: "modern"  # chinese, modern

# 设备控制设置
devices:
  # 灯光设备
  lights:
    enabled: true
    type: "yeelight"
    discovery_timeout: 5
    default_brightness: 70
    transition_time: 3000  # ms
    
  # 音频设备
  audio:
    enabled: true
    sample_rate: 44100
    channels: 2
    default_volume: 0.7
    fade_duration: 2000  # ms
    
  # 座椅设备
  chair:
    enabled: false
    type: "bluetooth"
    address: ""  # BLE address
    default_intensity: 5
    
  # 香薰设备
  scent:
    enabled: false
    type: "wifi"
    address: ""  # IP address

# 隐私与安全设置
privacy:
  # 数据加密
  encryption_enabled: true
  encryption_key_file: ".encryption_key"
  
  # 数据保留期限（天）
  data_retention_days: 30
  
  # 自动清理
  auto_cleanup_enabled: true
  cleanup_time: "03:00"  # 每天凌晨3点

# 管理后台设置
admin:
  # 默认管理员密码（首次使用后请修改）
  default_password: "admin123"
  
  # JWT 设置
  jwt_secret: ""  # 留空将自动生成
  jwt_expire_hours: 24
  
  # 访问控制
  max_login_attempts: 5
  lockout_duration: 300  # seconds

# 日志设置
logging:
  # 日志文件路径
  file_path: "backend/logs/healing_pod.log"
  
  # 日志轮转
  max_size: 10485760  # 10MB
  backup_count: 5
  
  # 控制台输出
  console_enabled: true
EOF
    
    print_success "Main configuration file created at $CONFIG_DIR/config.yaml"
}

# Create device configuration file
create_device_config() {
    print_info "Creating device configuration file..."
    
    cat > "$CONFIG_DIR/devices.yaml" << 'EOF'
# ============================================================================
# 设备配置文件
# Device Configuration
# ============================================================================

# 灯光设备列表
lights:
  - name: "主灯"
    type: "yeelight"
    ip: ""  # 填入设备 IP
    enabled: false
    
  - name: "氛围灯带"
    type: "yeelight"
    ip: ""
    enabled: false

# 音频设备
audio:
  output_device: "default"
  input_device: "default"
  
# 摄像头设备
camera:
  device_id: 0
  resolution:
    width: 1280
    height: 720
  fps: 30

# 心率设备
heart_rate:
  type: "bluetooth"
  name: ""  # 设备名称
  address: ""  # BLE 地址
  enabled: false

# 按摩座椅
chair:
  type: "bluetooth"
  name: ""
  address: ""
  enabled: false
  
# 香薰机
scent:
  type: "wifi"
  ip: ""
  enabled: false

# 设备发现设置
discovery:
  # BLE 扫描超时（秒）
  ble_timeout: 10
  
  # WiFi 设备发现超时（秒）
  wifi_timeout: 5
  
  # 自动重连
  auto_reconnect: true
  reconnect_interval: 30
EOF
    
    print_success "Device configuration file created at $CONFIG_DIR/devices.yaml"
}

# Create data retention configuration
create_retention_config() {
    print_info "Creating data retention configuration..."
    
    # Check if file already exists
    if [[ -f "$CONFIG_DIR/data_retention.yaml" ]]; then
        print_warning "Data retention config already exists, skipping..."
        return
    fi
    
    cat > "$CONFIG_DIR/data_retention.yaml" << 'EOF'
# ============================================================================
# 数据保留策略配置
# Data Retention Policy Configuration
# ============================================================================

# 全局设置
global:
  enabled: true
  default_retention_days: 30

# 各类数据的保留策略
policies:
  # 会话数据
  sessions:
    retention_days: 30
    archive_before_delete: true
    
  # 情绪历史
  emotion_history:
    retention_days: 30
    archive_before_delete: false
    
  # 系统日志
  system_logs:
    retention_days: 7
    archive_before_delete: false
    
  # 使用统计
  usage_stats:
    retention_days: 90
    archive_before_delete: true

# 清理任务设置
cleanup:
  # 执行时间（每天）
  schedule: "03:00"
  
  # 批量删除大小
  batch_size: 100
  
  # 清理前备份
  backup_enabled: true
  backup_path: "data/backups"
EOF
    
    print_success "Data retention configuration created"
}

# Generate JWT secret
generate_jwt_secret() {
    print_info "Generating JWT secret..."
    
    JWT_SECRET=$(openssl rand -hex 32)
    
    # Update config file with JWT secret
    if [[ -f "$CONFIG_DIR/config.yaml" ]]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/jwt_secret: \"\"/jwt_secret: \"$JWT_SECRET\"/" "$CONFIG_DIR/config.yaml"
        else
            sed -i "s/jwt_secret: \"\"/jwt_secret: \"$JWT_SECRET\"/" "$CONFIG_DIR/config.yaml"
        fi
    fi
    
    print_success "JWT secret generated"
}

# Initialize database
init_database() {
    print_info "Initializing database..."
    
    # Check if Python environment is available
    if [[ -d "venv" ]]; then
        source venv/bin/activate
        
        # Create database initialization script
        python << 'EOF'
import sqlite3
import os

db_path = os.path.join(os.environ.get('DATA_DIR', 'data'), 'healing_pod.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables
cursor.executescript('''
-- 用户会话表
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    initial_emotion_category TEXT,
    initial_emotion_intensity REAL,
    final_emotion_category TEXT,
    final_emotion_intensity REAL,
    plan_id TEXT,
    duration_seconds INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 情绪历史表
CREATE TABLE IF NOT EXISTS emotion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    category TEXT,
    intensity REAL,
    valence REAL,
    arousal REAL,
    audio_data TEXT,
    face_data TEXT,
    bio_data TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 疗愈方案表
CREATE TABLE IF NOT EXISTS therapy_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    target_emotions TEXT,
    intensity TEXT,
    style TEXT,
    duration INTEGER,
    phases TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- 使用统计表
CREATE TABLE IF NOT EXISTS usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    total_duration INTEGER DEFAULT 0,
    avg_improvement REAL,
    most_common_emotion TEXT,
    most_used_plan TEXT
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    module TEXT,
    message TEXT,
    details TEXT
);

-- 管理员表
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_emotion_history_session ON emotion_history(session_id);
CREATE INDEX IF NOT EXISTS idx_emotion_history_timestamp ON emotion_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_stats_date ON usage_stats(date);
''')

conn.commit()
conn.close()

print(f"Database initialized at {db_path}")
EOF
        
        print_success "Database initialized"
    else
        print_warning "Python environment not found, skipping database initialization"
    fi
}

# Set file permissions
set_permissions() {
    print_info "Setting file permissions..."
    
    # Make scripts executable
    chmod +x scripts/*.sh 2>/dev/null || true
    
    # Protect sensitive files
    chmod 600 "$CONFIG_DIR/.encryption_key" 2>/dev/null || true
    
    # Set directory permissions
    chmod 755 "$CONFIG_DIR" "$DATA_DIR" "$LOGS_DIR" 2>/dev/null || true
    
    print_success "File permissions set"
}

# Verify configuration
verify_config() {
    print_info "Verifying configuration..."
    
    local all_ok=true
    
    # Check main config
    if [[ -f "$CONFIG_DIR/config.yaml" ]]; then
        print_success "Main config: OK"
    else
        print_error "Main config: NOT FOUND"
        all_ok=false
    fi
    
    # Check device config
    if [[ -f "$CONFIG_DIR/devices.yaml" ]]; then
        print_success "Device config: OK"
    else
        print_error "Device config: NOT FOUND"
        all_ok=false
    fi
    
    # Check encryption key
    if [[ -f "$CONFIG_DIR/.encryption_key" ]]; then
        print_success "Encryption key: OK"
    else
        print_error "Encryption key: NOT FOUND"
        all_ok=false
    fi
    
    # Check database
    if [[ -f "$DATA_DIR/healing_pod.db" ]]; then
        print_success "Database: OK"
    else
        print_warning "Database: NOT INITIALIZED"
    fi
    
    if $all_ok; then
        print_success "Configuration verified successfully!"
    else
        print_warning "Some configuration files are missing"
    fi
}

# Main function
main() {
    echo "=============================================="
    echo "  智能疗愈仓 - 配置初始化脚本"
    echo "  Healing Pod System - Config Initializer"
    echo "=============================================="
    echo ""
    
    create_directories
    generate_encryption_key
    create_main_config
    create_device_config
    create_retention_config
    generate_jwt_secret
    init_database
    set_permissions
    verify_config
    
    echo ""
    echo "=============================================="
    print_success "Configuration initialization completed!"
    echo "=============================================="
    echo ""
    echo "Important:"
    echo "  1. Edit $CONFIG_DIR/config.yaml to customize settings"
    echo "  2. Edit $CONFIG_DIR/devices.yaml to configure hardware"
    echo "  3. Change the default admin password after first login"
    echo ""
    echo "Next steps:"
    echo "  1. Start the backend: 'cd backend && uvicorn main:app --reload'"
    echo "  2. Start the frontend: 'cd app && npm run electron:dev'"
    echo ""
}

# Run main function
main "$@"
