@echo off
setLOCAL EnableDelayedExpansion

echo --- 1. Creating Virtual Environment ---
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b %errorlevel%
)

echo --- 2. Installing Requirements ---
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b %errorlevel%
)

echo --- 3. Checking Ollama ---
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Ollama is not installed. 
    echo Please download and install it from https://ollama.com/download/windows
    echo Once installed, restart this script or run 'ollama pull llama3' manually.
) else (
    echo Ollama is already installed.
    echo --- 4. Pulling Model (llama3.2) ---
    ollama pull llama3.2
)

echo.
echo --- Setup Complete! ---
echo To start:
echo 1. Activate venv: .venv\Scripts\activate
echo 2. Run: python main.py
echo.
pause
