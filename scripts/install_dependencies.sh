#!/bin/bash

# ============================================================================
# 智能疗愈仓 - 依赖安装脚本
# Healing Pod System - Dependency Installation Script
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

# Check if running on macOS
check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        print_error "This script is designed for macOS only."
        exit 1
    fi
    print_success "Running on macOS $(sw_vers -productVersion)"
}

# Check for Apple Silicon or Intel
check_architecture() {
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        print_info "Detected Apple Silicon (arm64)"
        export HOMEBREW_PREFIX="/opt/homebrew"
    else
        print_info "Detected Intel (x86_64)"
        export HOMEBREW_PREFIX="/usr/local"
    fi
}

# Install Homebrew if not present
install_homebrew() {
    if ! command -v brew &> /dev/null; then
        print_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH
        if [[ "$(uname -m)" == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        print_success "Homebrew installed successfully"
    else
        print_success "Homebrew is already installed"
    fi
}

# Install system dependencies via Homebrew
install_system_deps() {
    print_info "Installing system dependencies..."
    
    # Update Homebrew
    brew update
    
    # Install Python 3.11 (recommended for AI models)
    if ! brew list python@3.11 &> /dev/null; then
        print_info "Installing Python 3.11..."
        brew install python@3.11
    else
        print_success "Python 3.11 is already installed"
    fi
    
    # Install Node.js LTS
    if ! brew list node@20 &> /dev/null; then
        print_info "Installing Node.js 20 LTS..."
        brew install node@20
        brew link --overwrite node@20
    else
        print_success "Node.js is already installed"
    fi
    
    # Install FFmpeg for audio/video processing
    if ! brew list ffmpeg &> /dev/null; then
        print_info "Installing FFmpeg..."
        brew install ffmpeg
    else
        print_success "FFmpeg is already installed"
    fi
    
    # Install PortAudio for audio I/O
    if ! brew list portaudio &> /dev/null; then
        print_info "Installing PortAudio..."
        brew install portaudio
    else
        print_success "PortAudio is already installed"
    fi
    
    # Install OpenCV dependencies
    if ! brew list opencv &> /dev/null; then
        print_info "Installing OpenCV..."
        brew install opencv
    else
        print_success "OpenCV is already installed"
    fi
    
    print_success "System dependencies installed successfully"
}

# Create Python virtual environment
setup_python_env() {
    print_info "Setting up Python virtual environment..."
    
    PYTHON_PATH=$(brew --prefix python@3.11)/bin/python3.11
    
    if [[ ! -d "venv" ]]; then
        $PYTHON_PATH -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Python environment ready"
}

# Install Python dependencies
install_python_deps() {
    print_info "Installing Python dependencies..."
    
    source venv/bin/activate
    
    # Install PyTorch with MPS support for Apple Silicon
    if [[ "$(uname -m)" == "arm64" ]]; then
        print_info "Installing PyTorch with MPS support..."
        pip install torch torchvision torchaudio
    else
        print_info "Installing PyTorch for Intel..."
        pip install torch torchvision torchaudio
    fi
    
    # Install backend requirements
    if [[ -f "backend/requirements.txt" ]]; then
        pip install -r backend/requirements.txt
    else
        print_warning "backend/requirements.txt not found, installing core dependencies..."
        pip install fastapi uvicorn pydantic python-multipart
        pip install numpy scipy pandas
        pip install opencv-python mediapipe
        pip install sounddevice soundfile
        pip install bleak  # BLE support
        pip install aiohttp aiofiles
        pip install pyyaml
        pip install cryptography
        pip install hypothesis pytest pytest-asyncio  # Testing
    fi
    
    print_success "Python dependencies installed successfully"
}

# Install Node.js dependencies
install_node_deps() {
    print_info "Installing Node.js dependencies..."
    
    if [[ -d "app" ]]; then
        cd app
        npm install
        cd ..
        print_success "Node.js dependencies installed successfully"
    else
        print_warning "app directory not found, skipping Node.js dependencies"
    fi
}

# Verify installation
verify_installation() {
    print_info "Verifying installation..."
    
    # Check Python
    source venv/bin/activate
    python --version
    
    # Check PyTorch and MPS
    python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'MPS available: {torch.backends.mps.is_available()}')"
    
    # Check Node.js
    node --version
    npm --version
    
    # Check FFmpeg
    ffmpeg -version | head -1
    
    print_success "All dependencies verified successfully!"
}

# Main installation flow
main() {
    echo "=============================================="
    echo "  智能疗愈仓 - 依赖安装脚本"
    echo "  Healing Pod System - Dependency Installer"
    echo "=============================================="
    echo ""
    
    check_macos
    check_architecture
    install_homebrew
    install_system_deps
    setup_python_env
    install_python_deps
    install_node_deps
    verify_installation
    
    echo ""
    echo "=============================================="
    print_success "Installation completed successfully!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Run './scripts/download_models.sh' to download AI models"
    echo "  2. Run './scripts/init_config.sh' to initialize configuration"
    echo "  3. Run 'source venv/bin/activate' to activate Python environment"
    echo ""
}

# Run main function
main "$@"
