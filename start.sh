#!/bin/bash

# ============================================================================
# HSI-Core Quick Start Script
# ============================================================================
# Automatically handles installation and launches the web application
# ============================================================================

set -e  # Exit on any error

clear

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         HSI-Core Hyperspectral Imaging System v3.0             ║"
echo "║                    Quick Start Launcher                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "✓ Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "  Found Python $PYTHON_VERSION"
echo ""

# Create/activate virtual environment
echo "✓ Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created new venv"
fi

source venv/bin/activate
echo "  Activated venv"
echo ""

# Install/update dependencies
echo "✓ Installing dependencies (may take 1-2 minutes)..."
pip install --upgrade pip > /dev/null 2>&1
pip install -q -r requirements.txt

if [ $? -eq 0 ]; then
    echo "  Dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi
echo ""

# Create necessary directories
echo "✓ Setting up directories..."
mkdir -p datasets
mkdir -p scan_images
echo "  Created data directories"
echo ""

# Show system info
echo "═════════════════════════════════════════════════════════════════"
echo "SYSTEM STATUS"
echo "═════════════════════════════════════════════════════════════════"
echo ""

python3 << EOF
import sys
print(f"Python:       {sys.version.split()[0]}")
print(f"Platform:     {sys.platform}")

try:
    import cv2
    print(f"OpenCV:       ✓")
except:
    print(f"OpenCV:       ✗")

try:
    import numpy
    print(f"NumPy:        ✓")
except:
    print(f"NumPy:        ✗")

try:
    import fastapi
    print(f"FastAPI:      ✓")
except:
    print(f"FastAPI:      ✗")

try:
    import PyQt5
    print(f"PyQt5:        ✓")
except:
    print(f"PyQt5:        ✗")
EOF

echo ""
echo "═════════════════════════════════════════════════════════════════"
echo ""

# Ask user which interface to use
echo "Select how to run HSI-Core:"
echo ""
echo "  1) Web Dashboard (Recommended)"
echo "  2) Desktop GUI (PyQt5)"
echo "  3) Command Line (Python)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting Web Server..."
        echo ""
        echo "Server will be available at: http://localhost:8000"
        echo "Press Ctrl+C to stop the server"
        echo ""
        python3 server_enhanced.py
        ;;
    2)
        echo ""
        echo "🚀 Starting Desktop GUI..."
        echo ""
        python3 gui_main.py
        ;;
    3)
        echo ""
        echo "🚀 Starting Interactive Python Shell..."
        echo ""
        python3 -c "
from acquisition.dataset import dataset_manager
from acquisition.analysis import SpectralAnalyzer, ROIAnalyzer
print('HSI-Core Ready')
print('Available:')
print('  - dataset_manager.list_datasets()')
print('  - dataset_manager.load_dataset(name)')
print('  - SpectralAnalyzer.extract_spectrum(cube, x, y)')
print('  - ROIAnalyzer.rectangular_roi(cube, x1, y1, x2, y2)')
print('')
" && python3 -i << EOF
from acquisition.dataset import dataset_manager
from acquisition.analysis import SpectralAnalyzer, ROIAnalyzer
import numpy as np

print('HSI-Core Python Shell')
print('Type help() for more info')
print('Example: datasets = dataset_manager.list_datasets()')
EOF
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
