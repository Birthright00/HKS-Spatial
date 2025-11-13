#!/bin/bash
# Setup script for HKS-Spatial microservices architecture (Unix/Mac)
# Creates virtual environments for each submodule and the coordinator

set -e

echo "===================================="
echo "HKS-Spatial Setup Script"
echo "===================================="
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3.13."
    exit 1
fi

echo "[1/5] Creating coordinator virtual environment..."
python3.13 -m venv venv

echo "[2/5] Installing coordinator dependencies..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo
echo "[3/5] Setting up RAG-Langchain submodule..."
cd RAG-Langchain
if [ -d ".venv" ]; then
    echo "RAG-Langchain .venv already exists, skipping..."
else
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
fi
cd ..

echo
echo "[4/5] Setting up picture-generation submodule..."
cd picture-generation-verbose-api-module
if [ -d "myenv" ]; then
    echo "picture-generation myenv already exists, skipping..."
else
    python3 -m venv myenv
    source myenv/bin/activate
    python -m pip install --upgrade pip

    # Detect NVIDIA GPU and CUDA support
    echo "Detecting NVIDIA GPU and CUDA support..."

    # First check if nvidia-smi exists and can query GPU
    if ! command -v nvidia-smi &> /dev/null || ! nvidia-smi --query-gpu=driver_version --format=csv,noheader &> /dev/null; then
        echo "No NVIDIA GPU detected. Installing CPU-only PyTorch..."
        pip install -r requirements-cpu.txt
    else
        # GPU exists, now try installing CUDA version and verify
        echo "NVIDIA GPU detected. Installing CUDA version of PyTorch..."
        if pip install -r requirements.txt; then
            # Verify CUDA is accessible to PyTorch
            echo "Verifying CUDA is accessible to PyTorch..."
            if ! python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" &> /dev/null; then
                echo "Warning: PyTorch installed but CUDA not accessible. Reinstalling CPU version..."
                pip uninstall -y torch torchvision
                pip install -r requirements-cpu.txt
            else
                echo "CUDA installation successful!"
            fi
        else
            echo "CUDA installation failed (CUDA toolkit may not be installed). Installing CPU-only version..."
            pip install -r requirements-cpu.txt
        fi
    fi

    deactivate
fi
cd ..

echo
echo "[5/5] Creating .env file..."
if [ -f ".env" ]; then
    echo ".env already exists, skipping..."
else
    cp .env.example .env
    echo "Please edit .env file and add your API keys"
fi

echo
echo "===================================="
echo "Setup Complete!"
echo "===================================="
echo
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Start services: source venv/bin/activate && python -m coordinator.main start"
echo
echo "For help: python -m coordinator.main --help"
echo
