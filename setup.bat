@echo off
REM Setup script for HKS-Spatial microservices architecture (Windows)
REM Creates virtual environments for each submodule and the coordinator

echo ====================================
echo HKS-Spatial Setup Script
echo ====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python 3.13.
    exit /b 1
)

echo [1/5] Creating coordinator virtual environment...
py -3.13 -m venv venv
if %errorlevel% neq 0 (
    echo Error: Failed to create coordinator venv
    exit /b 1
)

echo [2/5] Installing coordinator dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
call deactivate

echo.
echo [3/5] Setting up RAG-Langchain submodule...
cd RAG-Langchain
if exist .venv (
    echo RAG-Langchain .venv already exists, skipping...
) else (
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    call deactivate
)
cd ..

echo.
echo [4/5] Setting up picture-generation submodule...
cd picture-generation-verbose-api-module
if exist myenv (
    echo picture-generation myenv already exists, skipping...
) else (
    setlocal enabledelayedexpansion
    python -m venv myenv
    call myenv\Scripts\activate.bat
    python -m pip install --upgrade pip

    REM Detect NVIDIA GPU and CUDA support
    echo Detecting NVIDIA GPU and CUDA support...

    REM First check if nvidia-smi exists and can query GPU
    nvidia-smi --query-gpu=driver_version --format=csv,noheader >nul 2>&1
    if %errorlevel% neq 0 (
        echo No NVIDIA GPU detected. Installing CPU-only PyTorch...
        pip install -r requirements-cpu.txt
    ) else (
        REM GPU exists, now verify CUDA is actually available
        echo NVIDIA GPU detected. Verifying CUDA availability...
        python -c "import sys; sys.exit(0)" >nul 2>&1
        if %errorlevel% neq 0 (
            echo Python check failed. Installing CPU-only PyTorch...
            pip install -r requirements-cpu.txt
        ) else (
            REM Try installing CUDA version, fallback to CPU if it fails
            echo Installing CUDA version of PyTorch...
            pip install -r requirements.txt
            if %errorlevel% neq 0 (
                echo CUDA installation failed ^(CUDA toolkit may not be installed^). Installing CPU-only version...
                pip install -r requirements-cpu.txt
            ) else (
                echo Verifying CUDA is accessible to PyTorch...
                python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" >nul 2>&1
                if %errorlevel% neq 0 (
                    echo Warning: PyTorch installed but CUDA not accessible. Reinstalling CPU version...
                    pip uninstall -y torch torchvision
                    pip install -r requirements-cpu.txt
                ) else (
                    echo CUDA installation successful!
                )
            )
        )
    )

    call deactivate
    endlocal
)
cd ..

echo.
echo [5/5] Creating .env file...
if exist .env (
    echo .env already exists, skipping...
) else (
    copy .env.example .env
    echo Please edit .env file and add your API keys
)

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo Next steps:
echo 1. Edit .env file and add your API keys
echo 2. Start services: venv\Scripts\python -m coordinator.main start
echo.
echo For help: venv\Scripts\python -m coordinator.main --help
echo.
