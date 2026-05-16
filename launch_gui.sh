#!/bin/bash

# HSI-Core GUI Launcher
# =======================

echo "=========================================="
echo "HSI-Core Acquisition GUI v3.0"
echo "=========================================="

# Check Python
echo "Checking Python installation..."
python3 --version

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run GUI
echo ""
echo "Starting GUI..."
python3 gui_main.py
