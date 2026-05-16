# 🎯 Single-Click Launch Guide

## Choose Your Operating System

---

## 🍎 **macOS (Recommended)**

### Option 1: Python Launcher (Best)
1. **Double-click** `HSI-Core.py` in Finder
2. A terminal opens with a nice menu
3. Choose: 1 (Web), 2 (GUI), or 3 (Python)
4. Done! ✅

### Option 2: Shell Script
1. **Double-click** `RUN_HSI_CORE.command` in Finder
2. Terminal opens, auto-installs everything
3. Choose your interface
4. Done! ✅

### Option 3: From Terminal (If above doesn't work)
```bash
cd /Users/anurag/Desktop/HSI-Core
python3 HSI-Core.py
```

---

## 🪟 **Windows**

### Option 1: Batch File (Easiest)
1. **Double-click** `RUN_HSI_CORE.bat` on your Desktop
2. Command prompt opens
3. Everything auto-installs
4. Choose your interface (1 or 2)
5. Done! ✅

### Option 2: Python Launcher
1. **Double-click** `HSI-Core.py`
2. Same as macOS
3. Done! ✅

---

## 🐧 **Linux**

### Option 1: Python Launcher (Recommended)
```bash
cd /Users/anurag/Desktop/HSI-Core
python3 HSI-Core.py
```

### Option 2: Shell Script
```bash
cd /Users/anurag/Desktop/HSI-Core
bash RUN_HSI_CORE.command
```

---

## 📱 What Each Launcher Does

All launchers automatically:

✅ Check for Python installation
✅ Create virtual environment (if needed)
✅ Install all 10 dependencies
✅ Create data directories
✅ Show system status
✅ Let you choose your interface

Then you pick:
- **1 = Web Dashboard** (Open in browser automatically)
- **2 = Desktop GUI** (PyQt5 native app)
- **3 = Python Shell** (For advanced users)

---

## 🌟 Creating Desktop Shortcuts

### macOS
```bash
# Drag HSI-Core.py to your Desktop
# Or: cp HSI-Core.py ~/Desktop/
```

Then **double-click** anytime!

### Windows
```
1. Right-click HSI-Core.py or RUN_HSI_CORE.bat
2. Send to → Desktop (create shortcut)
3. Double-click shortcut to launch
```

### Linux (GNOME/KDE)
```bash
# Create desktop file
cat > ~/.local/share/applications/hsi-core.desktop << EOF
[Desktop Entry]
Name=HSI-Core
Exec=python3 /path/to/HSI-Core.py
Icon=utilities-system-monitor
Terminal=true
Type=Application
EOF

# Then it appears in Applications menu
```

---

## 🔍 Troubleshooting

### "Command not found" on macOS
```bash
# Make it executable
chmod +x HSI-Core.py
chmod +x RUN_HSI_CORE.command

# Then double-click again
```

### "Python not found" on Windows
```
1. Install Python from python.org
2. During install, CHECK "Add Python to PATH"
3. Restart computer
4. Try again
```

### "Permission denied" on Linux
```bash
chmod +x HSI-Core.py
./HSI-Core.py
```

---

## 💡 What Actually Happens

When you double-click the launcher:

```
1. Auto-detect Python version
2. Create venv/ folder (once)
3. Install packages to venv (once)
4. Show system status
5. Display menu
6. Launch chosen interface
7. Auto-open browser (web only)
```

**Next time you run:** ⚡ Much faster (skip install steps)

---

## 🎯 Recommended Workflow

### First Time:
```
double-click HSI-Core.py → choice 1 → browser opens → DONE
```

### Regular Use:
```
double-click HSI-Core.py → choice 1 → http://localhost:8000
```

### Python Analysis:
```
double-click HSI-Core.py → choice 3 → interactive shell
```

---

## 🚀 Quick Reference

| OS | File | Action |
|----|------|--------|
| macOS | `HSI-Core.py` | Double-click |
| macOS | `RUN_HSI_CORE.command` | Double-click |
| Windows | `RUN_HSI_CORE.bat` | Double-click |
| Linux | `HSI-Core.py` | `./HSI-Core.py` |

---

## ✨ That's It!

No need to:
- ❌ Open Terminal manually
- ❌ Run install commands
- ❌ Activate virtual environment
- ❌ Know Python paths
- ❌ Understand pip

Just **double-click** and go! 🎉

---

## 📞 Still Having Issues?

```bash
# Open Terminal and debug
cd /Users/anurag/Desktop/HSI-Core
python3 HSI-Core.py

# Or run with explicit python
/usr/local/bin/python3 HSI-Core.py

# Check Python version
python3 --version

# Check pip
python3 -m pip --version
```

**Everything should work now!** ✅
