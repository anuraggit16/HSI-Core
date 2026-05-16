#!/usr/bin/env python3
"""
HSI-Core One-Click Launcher
Double-click to run the entire system
Works on macOS, Linux, and Windows
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Colors
class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header():
    """Print fancy header"""
    header = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🔬 HSI-Core: Hyperspectral Imaging System v3.0         ║
║                                                           ║
║              One-Click Auto-Launcher                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(f"{Color.BOLD}{Color.CYAN}{header}{Color.ENDC}")

def check_python():
    """Check Python version"""
    print(f"{Color.GREEN}✓ Python {sys.version.split()[0]} detected{Color.ENDC}")

def setup_venv():
    """Create and setup virtual environment"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print(f"\n{Color.YELLOW}Setting up virtual environment...{Color.ENDC}")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print(f"{Color.GREEN}✓ Virtual environment created{Color.ENDC}")
    else:
        print(f"{Color.GREEN}✓ Virtual environment exists{Color.ENDC}")

def get_python_cmd():
    """Get python command for current platform"""
    if platform.system() == "Windows":
        return str(Path("venv") / "Scripts" / "python.exe")
    else:
        return str(Path("venv") / "bin" / "python")

def get_pip_cmd():
    """Get pip command for current platform"""
    if platform.system() == "Windows":
        return str(Path("venv") / "Scripts" / "pip.exe")
    else:
        return str(Path("venv") / "bin" / "pip")

def install_dependencies():
    """Install all required packages"""
    print(f"\n{Color.YELLOW}Installing dependencies...{Color.ENDC}")
    
    pip_cmd = get_pip_cmd()
    
    # Upgrade pip first
    subprocess.run([pip_cmd, "install", "--quiet", "--upgrade", "pip"], 
                   capture_output=True)
    
    packages = [
        "fastapi",
        "uvicorn[standard]",
        "numpy",
        "opencv-python",
        "PyQt5",
        "matplotlib",
        "pydantic",
        "tifffile",
        "scipy",
        "scikit-learn",
    ]
    
    for package in packages:
        print(f"  Installing {package:<25}", end="", flush=True)
        result = subprocess.run(
            [pip_cmd, "install", "--quiet", package],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f" {Color.GREEN}✓{Color.ENDC}")
        else:
            print(f" {Color.YELLOW}⚠{Color.ENDC}")
    
    print(f"{Color.GREEN}✓ Dependencies ready{Color.ENDC}")

def create_directories():
    """Create necessary data directories"""
    dirs = ["datasets", "scan_images"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print(f"{Color.GREEN}✓ Data directories ready{Color.ENDC}")

def verify_installation():
    """Verify all packages are installed"""
    print(f"\n{Color.CYAN}System Status:{Color.ENDC}")
    
    checks = {
        "Python": lambda: sys.version.split()[0],
        "Platform": lambda: platform.system(),
        "NumPy": lambda: __import__("numpy").__version__,
        "OpenCV": lambda: __import__("cv2").__version__,
        "FastAPI": lambda: __import__("fastapi").__version__,
    }
    
    for name, check in checks.items():
        try:
            result = check()
            print(f"  {name:<15} {Color.GREEN}✓{Color.ENDC} {result}")
        except Exception as e:
            print(f"  {name:<15} {Color.RED}✗{Color.ENDC} {str(e)}")

def show_menu():
    """Show interface selection menu"""
    print(f"\n{Color.BOLD}Select Interface:{Color.ENDC}\n")
    print("  1) 🌐 Web Dashboard (Recommended)")
    print("     - Professional dark UI")
    print("     - Real-time monitoring")
    print("     - Live camera stream")
    print("     - Opens in browser automatically\n")
    
    print("  2) 🖥️  Desktop GUI")
    print("     - Native PyQt5 app")
    print("     - 3D visualization")
    print("     - No browser needed\n")
    
    print("  3) 🐍 Python Shell")
    print("     - For analysis & scripting")
    print("     - Direct API access\n")
    
    print("  4) ❌ Exit\n")
    
    return input(f"{Color.BOLD}Enter choice (1-4): {Color.ENDC}")

def run_web_server():
    """Run the web server"""
    print(f"\n{Color.BLUE}{'='*60}{Color.ENDC}")
    print(f"{Color.BOLD}{Color.GREEN}🌐 Starting Web Dashboard...{Color.ENDC}")
    print(f"{Color.BLUE}{'='*60}{Color.ENDC}")
    print()
    
    print(f"{Color.CYAN}Server Address: {Color.BOLD}http://localhost:8000{Color.ENDC}")
    print(f"{Color.CYAN}Press Ctrl+C to stop{Color.ENDC}\n")
    
    # Try to open browser on macOS/Linux
    if platform.system() in ["Darwin", "Linux"]:
        os.system("sleep 2 && open http://localhost:8000 2>/dev/null &")
    
    python_cmd = get_python_cmd()
    subprocess.run([python_cmd, "server_enhanced.py"])

def run_gui():
    """Run the PyQt5 GUI"""
    print(f"\n{Color.BLUE}{'='*60}{Color.ENDC}")
    print(f"{Color.BOLD}{Color.GREEN}🖥️  Starting Desktop GUI...{Color.ENDC}")
    print(f"{Color.BLUE}{'='*60}{Color.ENDC}\n")
    
    python_cmd = get_python_cmd()
    subprocess.run([python_cmd, "gui_main.py"])

def run_python_shell():
    """Run interactive Python shell"""
    print(f"\n{Color.BLUE}{'='*60}{Color.ENDC}")
    print(f"{Color.BOLD}{Color.GREEN}🐍 Python Shell Ready{Color.ENDC}")
    print(f"{Color.BLUE}{'='*60}{Color.ENDC}\n")
    
    python_cmd = get_python_cmd()
    
    startup = """
from acquisition.dataset import dataset_manager
from acquisition.analysis import SpectralAnalyzer, ROIAnalyzer
import numpy as np

print("HSI-Core Python Shell")
print("Available modules:")
print("  - dataset_manager")
print("  - SpectralAnalyzer")
print("  - ROIAnalyzer")
print("  - np (numpy)")
print("")
print("Example:")
print("  datasets = dataset_manager.list_datasets()")
print("  cube, meta = dataset_manager.load_dataset('name')")
"""
    
    subprocess.run([python_cmd, "-i", "-c", startup])

def main():
    """Main entry point"""
    # Save current directory
    os.chdir(Path(__file__).parent)
    
    # Show header
    print_header()
    
    # Check Python
    print(f"{Color.GREEN}✓ Checking system...{Color.ENDC}")
    check_python()
    
    # Setup
    setup_venv()
    install_dependencies()
    create_directories()
    
    # Verify
    verify_installation()
    
    # Menu
    while True:
        choice = show_menu()
        
        try:
            if choice == "1":
                run_web_server()
                break
            elif choice == "2":
                run_gui()
                break
            elif choice == "3":
                run_python_shell()
                break
            elif choice == "4":
                print(f"\n{Color.YELLOW}Exiting...{Color.ENDC}\n")
                break
            else:
                print(f"{Color.RED}Invalid choice. Please try again.{Color.ENDC}")
        except KeyboardInterrupt:
            print(f"\n\n{Color.YELLOW}Interrupted by user{Color.ENDC}\n")
            break
        except Exception as e:
            print(f"{Color.RED}Error: {e}{Color.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{Color.RED}Fatal error: {e}{Color.ENDC}")
        sys.exit(1)
