#!/bin/bash

# ============================================================================
# 智能疗愈仓 - AI 模型下载脚本
# Healing Pod System - AI Model Download Script
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

# Model directory
MODELS_DIR="${MODELS_DIR:-models}"

# Create models directory
setup_models_dir() {
    print_info "Setting up models directory..."
    mkdir -p "$MODELS_DIR"
    mkdir -p "$MODELS_DIR/sensevoice"
    mkdir -p "$MODELS_DIR/emotion2vec"
    mkdir -p "$MODELS_DIR/cosyvoice"
    mkdir -p "$MODELS_DIR/qwen"
    mkdir -p "$MODELS_DIR/face"
    print_success "Models directory created at $MODELS_DIR"
}

# Check if Python environment is activated
check_python_env() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        if [[ -d "venv" ]]; then
            print_info "Activating Python virtual environment..."
            source venv/bin/activate
        else
            print_error "Python virtual environment not found. Run install_dependencies.sh first."
            exit 1
        fi
    fi
    print_success "Python environment active: $VIRTUAL_ENV"
}

# Install huggingface_hub if not present
install_hf_hub() {
    if ! python -c "import huggingface_hub" 2>/dev/null; then
        print_info "Installing huggingface_hub..."
        pip install huggingface_hub
    fi
}

# Download SenseVoice model
download_sensevoice() {
    print_info "Downloading SenseVoice-Small model..."
    
    python << 'EOF'
import os
from huggingface_hub import snapshot_download

model_dir = os.environ.get('MODELS_DIR', 'models')
target_dir = os.path.join(model_dir, 'sensevoice')

try:
    snapshot_download(
        repo_id="FunAudioLLM/SenseVoiceSmall",
        local_dir=target_dir,
        local_dir_use_symlinks=False
    )
    print(f"SenseVoice model downloaded to {target_dir}")
except Exception as e:
    print(f"Error downloading SenseVoice: {e}")
    print("You can manually download from: https://huggingface.co/FunAudioLLM/SenseVoiceSmall")
EOF
    
    print_success "SenseVoice model download completed"
}

# Download emotion2vec+ model
download_emotion2vec() {
    print_info "Downloading emotion2vec+ large model..."
    
    python << 'EOF'
import os
from huggingface_hub import snapshot_download

model_dir = os.environ.get('MODELS_DIR', 'models')
target_dir = os.path.join(model_dir, 'emotion2vec')

try:
    snapshot_download(
        repo_id="iic/emotion2vec_plus_large",
        local_dir=target_dir,
        local_dir_use_symlinks=False
    )
    print(f"emotion2vec+ model downloaded to {target_dir}")
except Exception as e:
    print(f"Error downloading emotion2vec+: {e}")
    print("You can manually download from: https://huggingface.co/iic/emotion2vec_plus_large")
EOF
    
    print_success "emotion2vec+ model download completed"
}

# Download CosyVoice model
download_cosyvoice() {
    print_info "Downloading CosyVoice model..."
    
    python << 'EOF'
import os
from huggingface_hub import snapshot_download

model_dir = os.environ.get('MODELS_DIR', 'models')
target_dir = os.path.join(model_dir, 'cosyvoice')

try:
    # Download CosyVoice-300M-SFT for Chinese TTS
    snapshot_download(
        repo_id="FunAudioLLM/CosyVoice-300M-SFT",
        local_dir=target_dir,
        local_dir_use_symlinks=False
    )
    print(f"CosyVoice model downloaded to {target_dir}")
except Exception as e:
    print(f"Error downloading CosyVoice: {e}")
    print("You can manually download from: https://huggingface.co/FunAudioLLM/CosyVoice-300M-SFT")
EOF
    
    print_success "CosyVoice model download completed"
}

# Download Qwen3 model
download_qwen() {
    print_info "Downloading Qwen3-8B model..."
    print_warning "This is a large model (~16GB). Download may take a while..."
    
    python << 'EOF'
import os
from huggingface_hub import snapshot_download

model_dir = os.environ.get('MODELS_DIR', 'models')
target_dir = os.path.join(model_dir, 'qwen')

try:
    # Download Qwen2.5-7B-Instruct (smaller alternative that works well)
    snapshot_download(
        repo_id="Qwen/Qwen2.5-7B-Instruct",
        local_dir=target_dir,
        local_dir_use_symlinks=False,
        ignore_patterns=["*.bin"]  # Skip .bin files, use safetensors
    )
    print(f"Qwen model downloaded to {target_dir}")
except Exception as e:
    print(f"Error downloading Qwen: {e}")
    print("You can manually download from: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct")
EOF
    
    print_success "Qwen model download completed"
}

# Download face analysis models
download_face_models() {
    print_info "Downloading face analysis models..."
    
    python << 'EOF'
import os
import urllib.request

model_dir = os.environ.get('MODELS_DIR', 'models')
face_dir = os.path.join(model_dir, 'face')

# Download FER (Facial Expression Recognition) model
# Using a lightweight CNN model for expression classification
fer_url = "https://github.com/oarriaga/face_classification/raw/master/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5"
fer_path = os.path.join(face_dir, "fer_model.hdf5")

if not os.path.exists(fer_path):
    try:
        print("Downloading FER model...")
        urllib.request.urlretrieve(fer_url, fer_path)
        print(f"FER model downloaded to {fer_path}")
    except Exception as e:
        print(f"Error downloading FER model: {e}")
        print("You may need to download manually or use an alternative model")
else:
    print(f"FER model already exists at {fer_path}")

print("Face analysis models setup completed")
EOF
    
    print_success "Face analysis models download completed"
}

# Create model configuration file
create_model_config() {
    print_info "Creating model configuration..."
    
    cat > "$MODELS_DIR/config.yaml" << EOF
# AI Model Configuration
# 智能疗愈仓 AI 模型配置

models:
  sensevoice:
    path: sensevoice
    device: mps  # Use Metal Performance Shaders on Mac
    
  emotion2vec:
    path: emotion2vec
    device: mps
    
  cosyvoice:
    path: cosyvoice
    device: mps
    default_speaker: "中文女"
    
  qwen:
    path: qwen
    device: mps
    max_tokens: 512
    temperature: 0.7
    
  face:
    path: face
    model_file: fer_model.hdf5

# Model loading settings
loading:
  parallel: true
  timeout: 60  # seconds
  retry: 3
EOF
    
    print_success "Model configuration created at $MODELS_DIR/config.yaml"
}

# Verify downloaded models
verify_models() {
    print_info "Verifying downloaded models..."
    
    local all_ok=true
    
    # Check SenseVoice
    if [[ -d "$MODELS_DIR/sensevoice" ]] && [[ -n "$(ls -A $MODELS_DIR/sensevoice 2>/dev/null)" ]]; then
        print_success "SenseVoice model: OK"
    else
        print_warning "SenseVoice model: NOT FOUND"
        all_ok=false
    fi
    
    # Check emotion2vec
    if [[ -d "$MODELS_DIR/emotion2vec" ]] && [[ -n "$(ls -A $MODELS_DIR/emotion2vec 2>/dev/null)" ]]; then
        print_success "emotion2vec+ model: OK"
    else
        print_warning "emotion2vec+ model: NOT FOUND"
        all_ok=false
    fi
    
    # Check CosyVoice
    if [[ -d "$MODELS_DIR/cosyvoice" ]] && [[ -n "$(ls -A $MODELS_DIR/cosyvoice 2>/dev/null)" ]]; then
        print_success "CosyVoice model: OK"
    else
        print_warning "CosyVoice model: NOT FOUND"
        all_ok=false
    fi
    
    # Check Qwen
    if [[ -d "$MODELS_DIR/qwen" ]] && [[ -n "$(ls -A $MODELS_DIR/qwen 2>/dev/null)" ]]; then
        print_success "Qwen model: OK"
    else
        print_warning "Qwen model: NOT FOUND"
        all_ok=false
    fi
    
    # Check face models
    if [[ -f "$MODELS_DIR/face/fer_model.hdf5" ]]; then
        print_success "Face analysis model: OK"
    else
        print_warning "Face analysis model: NOT FOUND"
        all_ok=false
    fi
    
    if $all_ok; then
        print_success "All models verified successfully!"
    else
        print_warning "Some models are missing. The system may run in degraded mode."
    fi
}

# Show disk usage
show_disk_usage() {
    print_info "Model disk usage:"
    du -sh "$MODELS_DIR"/* 2>/dev/null || echo "No models downloaded yet"
    echo ""
    du -sh "$MODELS_DIR" 2>/dev/null || echo "Models directory not found"
}

# Parse command line arguments
parse_args() {
    DOWNLOAD_ALL=true
    DOWNLOAD_SENSEVOICE=false
    DOWNLOAD_EMOTION2VEC=false
    DOWNLOAD_COSYVOICE=false
    DOWNLOAD_QWEN=false
    DOWNLOAD_FACE=false
    VERIFY_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --sensevoice)
                DOWNLOAD_ALL=false
                DOWNLOAD_SENSEVOICE=true
                shift
                ;;
            --emotion2vec)
                DOWNLOAD_ALL=false
                DOWNLOAD_EMOTION2VEC=true
                shift
                ;;
            --cosyvoice)
                DOWNLOAD_ALL=false
                DOWNLOAD_COSYVOICE=true
                shift
                ;;
            --qwen)
                DOWNLOAD_ALL=false
                DOWNLOAD_QWEN=true
                shift
                ;;
            --face)
                DOWNLOAD_ALL=false
                DOWNLOAD_FACE=true
                shift
                ;;
            --verify)
                VERIFY_ONLY=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --sensevoice    Download SenseVoice model only"
                echo "  --emotion2vec   Download emotion2vec+ model only"
                echo "  --cosyvoice     Download CosyVoice model only"
                echo "  --qwen          Download Qwen model only"
                echo "  --face          Download face analysis models only"
                echo "  --verify        Verify existing models without downloading"
                echo "  --help, -h      Show this help message"
                echo ""
                echo "Without options, all models will be downloaded."
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Main function
main() {
    echo "=============================================="
    echo "  智能疗愈仓 - AI 模型下载脚本"
    echo "  Healing Pod System - Model Downloader"
    echo "=============================================="
    echo ""
    
    parse_args "$@"
    
    check_python_env
    install_hf_hub
    setup_models_dir
    
    if $VERIFY_ONLY; then
        verify_models
        show_disk_usage
        exit 0
    fi
    
    if $DOWNLOAD_ALL; then
        download_sensevoice
        download_emotion2vec
        download_cosyvoice
        download_qwen
        download_face_models
    else
        $DOWNLOAD_SENSEVOICE && download_sensevoice
        $DOWNLOAD_EMOTION2VEC && download_emotion2vec
        $DOWNLOAD_COSYVOICE && download_cosyvoice
        $DOWNLOAD_QWEN && download_qwen
        $DOWNLOAD_FACE && download_face_models
    fi
    
    create_model_config
    verify_models
    show_disk_usage
    
    echo ""
    echo "=============================================="
    print_success "Model download completed!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Run './scripts/init_config.sh' to initialize configuration"
    echo "  2. Start the backend: 'cd backend && uvicorn main:app --reload'"
    echo "  3. Start the frontend: 'cd app && npm run electron:dev'"
    echo ""
}

# Run main function
main "$@"
