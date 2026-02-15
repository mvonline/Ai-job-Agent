#!/bin/bash

echo "--- 1. Creating Virtual Environment ---"
python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create virtual environment."
    exit 1
fi

echo "--- 2. Installing Requirements ---"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi

echo "--- 3. Checking Ollama ---"
if ! command -v ollama &> /dev/null; then
    echo "[INFO] Ollama is not installed. Attempting installation..."
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "[WARNING] Automatic Ollama installation failed."
        echo "Please install it manually from https://ollama.com"
    fi
else
    echo "Ollama is already installed."
fi

echo "--- 4. Pulling Model (llama3.2) ---"
if command -v ollama &> /dev/null; then
    ollama pull llama3.2
else
    echo "[WARNING] Cannot pull model because Ollama is not available."
fi

echo ""
echo "--- Setup Complete! ---"
echo "To start:"
echo "1. Activate venv: source .venv/bin/activate"
echo "2. Run: python3 main.py"
echo ""
