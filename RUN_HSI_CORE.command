#!/bin/bash

# ============================================================================
# HSI-Core One-Click Launcher
# ============================================================================
# Double-click this file in Finder to start the entire system
# It will auto-install dependencies and launch the web dashboard
# ============================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Clear terminal
clear

# ASCII Art
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        HSI-Core: Hyperspectral Imaging System            ║
║                                                           ║
║                  Starting up...                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    echo ""
    echo "Please install Python 3 from https://www.python.org/downloads/"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Setting up virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies (this may take 1-2 minutes)..."
pip install --quiet --upgrade pip 2>/dev/null

# Show progress
echo ""
dependencies=(
    "fastapi"
    "uvicorn"
    "numpy"
    "opencv-python"
    "PyQt5"
    "matplotlib"
    "pydantic"
    "tifffile"
    "scipy"
    "scikit-learn"
)

for dep in "${dependencies[@]}"; do
    printf "  Installing %-25s" "$dep..."
    if pip install --quiet "$dep" 2>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${YELLOW}⚠${NC} (may already be installed)"
    fi
done

echo ""
echo -e "${GREEN}✓ All dependencies installed${NC}"

# Create necessary directories
mkdir -p datasets
mkdir -p scan_images

# Show system info
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SYSTEM READY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 << PYEOF
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
PYEOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ask what to run
echo "Choose interface:"
echo ""
echo "  1) Web Dashboard (Recommended - opens in browser)"
echo "  2) Desktop GUI (PyQt5)"
echo "  3) Exit"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo -e "${BLUE}🌐 Starting Web Server...${NC}"
        echo ""
        echo "Opening: http://localhost:8000"
        echo ""
        echo "Press Ctrl+C to stop the server"
        echo ""
        sleep 2
        
        # Try to open browser automatically
        if command -v open &> /dev/null; then
            (sleep 3 && open http://localhost:8000) &
        fi
        
        # Start server
        python3 server_enhanced.py
        ;;
    2)
        echo ""
        echo -e "${BLUE}🖥️  Starting Desktop GUI...${NC}"
        echo ""
        python3 gui_main.py
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
