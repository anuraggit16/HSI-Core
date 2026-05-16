# 🚀 HSI-Core Quick Start Guide

## सबसे आसान तरीका — Fastest Way to Run

### Option 1: One-Command Start (Recommended)

```bash
cd /Users/anurag/Desktop/HSI-Core
chmod +x start.sh
./start.sh
```

यह automatically सब कुछ setup करेगा और आपको विकल्प देगा। ✅

---

## Manual Installation (अगर start.sh न चले)

### Step 1: Navigate to folder
```bash
cd /Users/anurag/Desktop/HSI-Core
```

### Step 2: Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

यह 2-5 minutes ले सकता है (internet speed पर निर्भर)।

---

## Run करने के तरीके

### Method 1: Web Dashboard (सबसे अच्छा ✨)

```bash
python3 server_enhanced.py
```

फिर browser में खोलें:
```
http://localhost:8000
```

**फायदे:**
- Dark professional UI
- Real-time monitoring
- Live camera stream
- All controls in one place
- किसी भी device से access कर सकते हो

---

### Method 2: Desktop GUI (PyQt5)

```bash
python3 gui_main.py
```

**फायदे:**
- No browser needed
- Native desktop app
- 3D visualization
- Responsive controls

---

### Method 3: Python Command Line

```bash
python3
```

फिर यह करो:
```python
from acquisition.dataset import dataset_manager
from acquisition.analysis import SpectralAnalyzer, ROIAnalyzer

# Datasets देखो
datasets = dataset_manager.list_datasets()
print(datasets)

# Dataset load करो
data_cube, metadata = dataset_manager.load_dataset("my_session")

# Analysis करो
spectrum = SpectralAnalyzer.extract_spectrum(data_cube, 100, 50)
roi = ROIAnalyzer.rectangular_roi(data_cube, 10, 10, 50, 50)

print(roi['mean_spectrum'])
```

---

### Method 4: Command Line Script

```bash
# Scan details देखो
python3 -c "from acquisition.dataset import dataset_manager; print(dataset_manager.list_datasets())"

# New scan start करो
curl -X POST http://localhost:8000/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{"session_name": "test_scan"}'
```

---

## 🔧 Common Tasks

### 1️⃣ पहला scan शुरू करो

**Web Dashboard से:**
1. `http://localhost:8000` खोलो
2. Left side में "Session Name" दो (या default रहने दो)
3. **▶ START** button दबाओ
4. Progress देखो real-time में

**Command से:**
```bash
curl -X POST http://localhost:8000/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "my_first_scan",
    "pattern": "serpentine",
    "exposure_ms": 100
  }'
```

---

### 2️⃣ पिछले scan को देखो

**Web Dashboard से:**
1. Left side में "Datasets" section देखो
2. सभी previous scans listed हैं

**Python से:**
```python
from acquisition.dataset import dataset_manager

# सभी datasets
datasets = dataset_manager.list_datasets()
for d in datasets:
    print(f"{d['name']}: {d['frames']}/{d['total_frames']} frames")

# एक को load करो
data_cube, metadata = dataset_manager.load_dataset("my_first_scan")
print(f"Shape: {data_cube.shape}")
print(f"Wavelength: {metadata.wavelength_min_nm}-{metadata.wavelength_max_nm} nm")
```

---

### 3️⃣ Intensity map देखो

**Web Dashboard से:**
1. Right side में tabs देखो
2. "Intensity Map" tab click करो

**Terminal से:**
```bash
# PNG image download करो
curl http://localhost:8000/api/datasets/my_first_scan/intensity > intensity_map.png
# फिर खोलो: open intensity_map.png
```

---

### 4️⃣ Spectral analysis करो

**Python से:**
```python
from acquisition.dataset import dataset_manager
from acquisition.analysis import SpectralAnalyzer, ROIAnalyzer

# Load करो
data_cube, metadata = dataset_manager.load_dataset("my_first_scan")

# एक pixel का spectrum निकालो
spectrum = SpectralAnalyzer.extract_spectrum(data_cube, x=100, y=50)

# ROI analysis करो (rectangle)
roi_stats = ROIAnalyzer.rectangular_roi(data_cube, x1=10, y1=10, x2=50, y2=50)
print(f"Mean spectrum: {roi_stats['mean_spectrum']}")
print(f"Pixels in ROI: {roi_stats['pixel_count']}")

# Circular ROI
roi_circle = ROIAnalyzer.circular_roi(data_cube, center_x=100, center_y=100, radius=20)
print(f"Circle mean: {roi_circle['mean_spectrum']}")
```

---

### 5️⃣ Scan parameters change करो

**Web Dashboard से:**
1. Left panel में "Scan Settings" देखो
2. Values change करो:
   - Start Position: कहाँ से शुरू करना है
   - Step Size: कितने distance पर image capture करना है
   - Number of Images: कितने images लेने हैं
   - Exposure: कितने time के लिए capture करना है

---

## 📊 Structure समझो

```
HSI-Core/
├── server_enhanced.py       ← Web server शुरू करो इससे
├── gui_main.py              ← Desktop GUI चलाओ इससे
├── main.py                  ← Original automated scan
├── config.py                ← Settings सब यहाँ हैं
│
├── acquisition/             ← Core modules
│   ├── hardware.py         (hardware detection)
│   ├── patterns.py         (scan patterns: raster/serpentine/spiral)
│   ├── dataset.py          (TIFF storage)
│   └── analysis.py         (spectral analysis)
│
├── datasets/                ← Scan data automatically save होता है यहाँ
│   └── session_XXX/
│       ├── metadata.json
│       ├── frames/         (individual TIFF files)
│       └── data_cube.npz   (compressed)
│
└── static/                  ← Web UI files
    └── index.html
```

---

## ⚙️ Configuration बदलो

`config.py` में अपनी settings बदल सकते हो:

```python
# Mock mode (real hardware नहीं है तो True रखो)
MOCK_MODE = True

# Scan defaults
SCAN_START_X_MM = 80.0
SCAN_END_X_MM = 180.0
SCAN_STEP_X_MM = 0.1       # 100 micrometers

# Spectral range
SPECTRAL_MIN_NM = 400
SPECTRAL_MAX_NM = 1000

# Server port
SERVER_PORT = 8000

# Dataset path
DATASET_BASE_PATH = "datasets"
```

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError"

```bash
# सभी dependencies फिर से install करो
pip install -r requirements.txt

# या एक-एक करके
pip install fastapi uvicorn numpy opencv-python PyQt5
```

### Error: "Address already in use"

Port 8000 already use हो रहा है। तीन options:

**Option 1:** दूसरा process बंद करो
```bash
lsof -i :8000  # देखो कौन use कर रहा है
kill -9 <PID>  # PID को kill करो
```

**Option 2:** दूसरा port use करो
Edit `config.py`:
```python
SERVER_PORT = 8001  # या कोई अन्य port
```

**Option 3:** terminal restart करो
```bash
pkill -f server_enhanced.py
python3 server_enhanced.py
```

### Error: "Camera not detected"

यह normal है अगर camera connect नहीं है। `MOCK_MODE = True` रखो config में।

```python
# config.py में
MOCK_MODE = True  # Simulated hardware चलेगा
```

---

## 🎯 Next Steps

1. **Web dashboard open करो:**
   ```
   http://localhost:8000
   ```

2. **पहला scan शुरू करो:**
   - Session name दो (या skip करो default के लिए)
   - Pattern select करो (serpentine recommended)
   - START button दबाओ

3. **Results analyze करो:**
   - Datasets tab से देखो
   - Intensity map देखो
   - Spectral data explore करो

4. **Advanced analysis करो:**
   ```python
   # Python में
   from acquisition.analysis import ROIAnalyzer
   roi = ROIAnalyzer.spectral_clustering(data_cube, n_clusters=5)
   ```

---

## 📞 Help की जरूरत है?

1. **Logs देखो:**
   ```bash
   tail -f server_enhanced.py  # Live logs
   ```

2. **API documentation:**
   ```
   http://localhost:8000/docs
   ```

3. **Code examples:**
   README.md देखो

4. **Test करो:**
   ```bash
   python3 -c "import fastapi; print('FastAPI OK')"
   ```

---

## ✨ तो चलो शुरू करते हैं!

```bash
cd /Users/anurag/Desktop/HSI-Core
./start.sh
```

या

```bash
python3 server_enhanced.py
```

फिर browser में: **http://localhost:8000** खोलो 🎉
