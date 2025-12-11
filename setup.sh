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

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "Error: Node.js not found. Please install Node.js (https://nodejs.org/)."
    exit 1
fi

echo "[1/6] Creating coordinator virtual environment..."
python3.13 -m venv venv

echo "[2/6] Installing coordinator dependencies..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo
echo "[3/6] Setting up RAG-Langchain submodule..."
cd RAG-Langchain
if [ -d ".venv" ]; then
    echo "RAG-Langchain .venv already exists, skipping..."
else
    python3.13 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
fi
cd ..

echo
echo "[4/6] Setting up picture-generation submodule..."
cd picture-generation-verbose-api-module
if [ -d "myenv" ]; then
    echo "picture-generation myenv already exists, skipping..."
else
    python3.13 -m venv myenv
    source myenv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
fi
cd ..

echo
echo "[5/6] Setting up Node.js dependencies..."
echo "Installing root, backend, and frontend dependencies..."
npm run install-all

echo
echo "[6/6] Creating .env file..."
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
echo "2. Start backend services: source venv/bin/activate && python -m coordinator.main start"
echo "3. Start frontend: cd Spatial-Design-Studio-Frontend/frontend && npm run dev"
echo
echo "For help: python -m coordinator.main --help"
echo
