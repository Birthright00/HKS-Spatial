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
    pip install -r requirements.txt
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
