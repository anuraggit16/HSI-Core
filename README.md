# HSI-Core: Professional Hyperspectral Imaging System

**Version 3.0** — Production-grade acquisition, analysis, and visualization platform for hyperspectral imaging in research laboratories.

## Overview

HSI-Core is a complete software suite for **automated hyperspectral data acquisition** with real-time visualization, advanced analysis tools, and professional-grade reliability.

### Key Features

✅ **Hardware Control**
- Automatic detection of Thorlabs motorized stages
- Basler camera integration with live preview
- Hardware health monitoring and auto-reconnection
- Mock mode for development/testing

✅ **Acquisition**
- Multiple scan patterns: raster, serpentine, spiral
- Real-time progress monitoring
- Long-duration stable scanning
- Configurable exposure, settling time, velocity profiles

✅ **Data Management**
- Scientific TIFF stacks with embedded metadata
- Automatic cube compression (.npz)
- Dataset browser and search
- Session save/load with full provenance

✅ **Analysis & Visualization**
- 3D data cube rendering
- Spectral plots and signatures
- ROI analysis tools
- Intensity heatmaps with colormap selection
- Pixel-level spectral extraction
- Statistical analysis (mean, std, percentiles)
- Anomaly detection

✅ **Professional UI**
- Dark-mode scientific dashboard
- Real-time WebSocket telemetry
- Responsive multi-panel layout
- Live camera stream
- Advanced parameter controls

✅ **API**
- RESTful endpoints for all operations
- WebSocket for real-time updates
- Programmatic dataset access
- Integration ready

---

## Installation

### Requirements
- **Python 3.8+** (tested on 3.10, 3.11, 3.14)
- **macOS / Linux / Windows**
- **~2GB disk** for Python packages and datasets

### Quick Start

```bash
# Clone repository
git clone https://github.com/anuraggit16/HSI-Core
cd HSI-Core

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python3 server_enhanced.py

# Open browser to http://localhost:8000
```

## Production Lab Startup

Use only one backend process when real hardware is attached. Multiple Uvicorn
processes can lock FTDI/Kinesis or Basler devices and make the app fall back to
mock mode.

```bash
# Windows PowerShell
venv\Scripts\python.exe -m uvicorn server_enhanced:app --host 127.0.0.1 --port 8000

# macOS/Linux
source venv/bin/activate
python -m uvicorn server_enhanced:app --host 127.0.0.1 --port 8000
```

The UI now trusts the unified `HardwareState` only. A device is shown connected
only after a real stage command or camera frame grab succeeds.

### Mock Mode

Set this in `config.py` for development without lab hardware:

```python
MOCK_MODE = True
DEBUG_MODE = True
```

With `MOCK_MODE = False`, the system tries real hardware first. If stage or
camera health checks fail after 3 attempts, it automatically switches to mock
fallback and records the reason in `logs/hardware_log.jsonl`.

### Hardware Troubleshooting

- Camera says "Busy or Disconnected": close other apps or old server processes
  using the Basler camera, then run `POST /api/hardware/detect`.
- Stage says fallback: confirm the Thorlabs Kinesis service/driver is installed,
  the BBD302/DDS300 serial in `config.py` is correct, and no other backend owns
  the FTDI device.
- Logs: inspect `GET /api/logs/latest` and `GET /api/logs/errors`.
- Safe reset: `POST /api/stage/home` stops an active scan, stops the live stream,
  homes or mock-homes the stage, and returns the UI to Overview.
- Calibration: use `POST /api/stage/zero` or the UI Zero Calibration button.

## One-Click Run (Windows)

Double-click `run_main.bat` in the repository root to launch your existing `main.py` with a single click.

If you use Visual Studio Code:
- Open the project in VS Code
- Open the Run and Debug view (Ctrl+Shift+D)
- Select `Run main.py`
- Click the green run button

Or use the VS Code task:
- Open the Command Palette (Ctrl+Shift+P)
- Run `Tasks: Run Task`
- Choose `Run main.py`

### Docker Setup (Optional)

```bash
docker build -t hsi-core .
docker run -p 8000:8000 hsi-core
```

---

## Usage

### Web Interface

```
http://localhost:8000
```

The web dashboard provides:
- **Hardware Status Panel** - Connection status of all devices
- **Scan Control** - Start/pause/stop acquisition with parameter adjustment
- **Live Camera** - Real-time video stream from imaging camera
- **Scan Progress** - Real-time progress bar and statistics
- **Intensity Map** - 2D visualization of scan region
- **Spectral Display** - Wavelength-domain data

### Python API

```python
from acquisition.dataset import dataset_manager
from acquisition.analysis import SpectralAnalyzer, ROIAnalyzer

# Load dataset
data_cube, metadata = dataset_manager.load_dataset("session_2026")

# Extract spectrum at pixel (100, 50)
spectrum = SpectralAnalyzer.extract_spectrum(data_cube, 100, 50)

# Analyze ROI
roi_stats = ROIAnalyzer.rectangular_roi(data_cube, 10, 10, 50, 50)
print(roi_stats['mean_spectrum'])
```

### REST API

```bash
# Get hardware status
curl http://localhost:8000/api/hardware/status

# Force safe hardware re-detect
curl -X POST http://localhost:8000/api/hardware/detect

# Latest structured hardware logs
curl http://localhost:8000/api/logs/latest

# Camera stream control
curl -X POST http://localhost:8000/api/camera/start
curl -X POST http://localhost:8000/api/camera/stop

# Stage home/move/zero
curl -X POST http://localhost:8000/api/stage/home
curl -X POST http://localhost:8000/api/stage/move \
  -H "Content-Type: application/json" \
  -d '{"x_mm": 10.0}'
curl -X POST http://localhost:8000/api/stage/zero

# Start scan
curl -X POST http://localhost:8000/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "my_scan",
    "pattern": "serpentine",
    "exposure_ms": 100
  }'

# List datasets
curl http://localhost:8000/api/datasets

# Get intensity map
curl http://localhost:8000/api/datasets/my_scan/intensity > map.png

# Analyze ROI
curl -X POST http://localhost:8000/api/analysis/roi \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "my_scan",
    "roi": {"x1": 10, "y1": 10, "x2": 50, "y2": 50}
  }'
```

---

## Architecture

### Project Structure

```
HSI-Core/
├── server_enhanced.py          # Main FastAPI server
├── config.py                   # Configuration & settings
├── requirements.txt            # Python dependencies
│
├── acquisition/                # Core acquisition modules
│   ├── __init__.py
│   ├── hardware.py            # Hardware detection & monitoring
│   ├── hal.py                 # Hardware abstraction layer
│   ├── scan.py                # Scan orchestration
│   ├── patterns.py            # Scan patterns (raster, serpentine)
│   ├── dataset.py             # TIFF storage & management
│   ├── analysis.py            # Spectral analysis tools
│   └── data_cube.py           # Data cube operations
│
├── static/                     # Web UI assets
│   └── index.html             # Frontend (embedded in server)
│
└── datasets/                   # Dataset storage (auto-created)
    └── session_XXXX/
        ├── metadata.json      # Session metadata
        ├── frames/            # Individual TIFF frames
        ├── data_cube.npz      # Compressed cube
        └── ...
```

### Backend Components

**Hardware Abstraction Layer (`hal.py`)**
- Unified interface for mock and real hardware
- Stage control: move, jog, home
- Camera: live preview, capture, settings

**Scan Engine (`scan.py`)**
- State machine: IDLE → RUNNING → PAUSED → STOPPING
- Multi-thread safe orchestration
- Real-time event queue

**Scan Patterns (`patterns.py`)**
- Raster: row-by-row standard scan
- Serpentine: bidirectional efficient scan
- Spiral: center-outward spiral
- Custom ROI patterns: rectangular, circular, polygonal

**Dataset Manager (`dataset.py`)**
- TIFF storage with metadata
- Automatic cube generation
- Dataset versioning
- Load/save with compression

**Analysis Tools (`analysis.py`)**
- Spectral signatures extraction
- ROI analysis (rectangular, circular)
- Intensity maps (total, mean, per-band)
- Spectral angle mapping
- Statistical analysis
- Anomaly detection

---

## Configuration

Edit `config.py` to customize system behavior:

```python
# Hardware
MOCK_MODE = True                    # Use simulated hardware for development
CONTROLLER_SERIAL_X = "103425854"  # Thorlabs stage serial

# Scan defaults
SCAN_START_X_MM = 80.0
SCAN_END_X_MM = 180.0
SCAN_STEP_X_MM = 0.1              # 100 µm steps
SETTLING_TIME_S = 0.1              # Wait after move

# Spectral
SPECTRAL_MIN_NM = 400
SPECTRAL_MAX_NM = 1000

# Storage
DATASET_BASE_PATH = "datasets"
COMPRESS_CUBES = True

# Server
SERVER_PORT = 8000
WS_BROADCAST_HZ = 5                # Update frequency
```

---

## Hardware Support

### Supported Devices

| Component | Model | Status |
|-----------|-------|--------|
| X-Y Stage | Thorlabs BBD302 | ✅ Tested |
| Camera | Basler ace2 Pro | ✅ Tested |
| Stage Controller | Kinesis | ✅ Supported |

### Add New Hardware

1. Create device class in `acquisition/hal.py`:
```python
class MyDevice:
    def __init__(self):
        pass
    
    def connect(self):
        pass
    
    def read_value(self):
        pass
```

2. Register in `HardwareDetector` (`acquisition/hardware.py`)

3. Add to `LabController` in `hal.py`

---

## Analysis Examples

### 1. Extract Spectral Signature

```python
from acquisition.analysis import SpectralAnalyzer

# Get spectrum at pixel (x=100, y=50)
spectrum = SpectralAnalyzer.extract_spectrum(data_cube, 100, 50)

# Plot it
import matplotlib.pyplot as plt
wavelengths = np.linspace(400, 1000, len(spectrum))
plt.plot(wavelengths, spectrum)
plt.xlabel('Wavelength (nm)')
plt.ylabel('Intensity')
plt.show()
```

### 2. ROI Analysis

```python
from acquisition.analysis import ROIAnalyzer

# Analyze rectangular region (x: 50-150, y: 30-130)
roi_stats = ROIAnalyzer.rectangular_roi(data_cube, 50, 30, 150, 130)

print(f"Mean spectrum: {roi_stats['mean_spectrum']}")
print(f"Std spectrum: {roi_stats['std_spectrum']}")
print(f"Pixels in ROI: {roi_stats['pixel_count']}")
```

### 3. Spectral Clustering

```python
from acquisition.analysis import ROIAnalyzer

# Cluster pixels into 5 spectral classes
cluster_map = ROIAnalyzer.spectral_clustering(data_cube, n_clusters=5)

# Visualize
plt.imshow(cluster_map, cmap='tab10')
plt.colorbar(label='Cluster ID')
plt.show()
```

### 4. Intensity Maps

```python
from acquisition.analysis import IntensityMapGenerator
import matplotlib.pyplot as plt

# Total intensity across wavelengths
intensity_total = IntensityMapGenerator.total_intensity(data_cube)

# Mean intensity
intensity_mean = IntensityMapGenerator.mean_intensity(data_cube)

# Normalize to [0, 1]
intensity_norm = IntensityMapGenerator.normalize_0_1(intensity_total)

plt.imshow(intensity_norm, cmap='hot')
plt.colorbar(label='Normalized Intensity')
plt.show()
```

---

## Troubleshooting

### Hardware Not Detected

```bash
# Force detection
curl -X POST http://localhost:8000/api/hardware/detect
```

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Slow Performance

- Increase stage velocity: `STAGE_MAX_VELOCITY` in `config.py`
- Reduce settling time: `SETTLING_TIME_S`
- Use serpentine pattern instead of raster
- Enable data cube compression: `COMPRESS_CUBES = True`

### WebSocket Connection Issues

- Check firewall settings
- Ensure browser supports WebSocket
- Verify server is running: `curl http://localhost:8000/api/hardware/ready`

---

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Code Style

```bash
black acquisition/ server_enhanced.py
pylint acquisition/
```

### Generate Documentation

```bash
pydoc acquisition.analysis > docs/analysis_api.txt
```

---

## Performance

- **Acquisition**: 1000+ images/hour with 100µm steps
- **Streaming**: 30 FPS live preview
- **Processing**: Real-time analysis <100ms per operation
- **Storage**: ~10 MB/session (1000 frames, 640x480 mono)

---

## Publications & Citations

If you use HSI-Core in research, please cite:

```bibtex
@software{hsicore2026,
  title={HSI-Core: Production-Grade Hyperspectral Imaging System},
  author={Anurag Singh Tomar},
  year={2026},
  url={https://github.com/anuraggit16/HSI-Core}
}
```

---

## License

**MIT License** — See `LICENSE` file for details

---

## Support & Contact

- **Issues**: GitHub Issues
- **Documentation**: Full API docs at `/api/docs` (Swagger UI)
- **Email**: anurag@example.com

---

## Roadmap

- [ ] Hyperspectral unmixing algorithms
- [ ] Machine learning classification module
- [ ] Multi-camera synchronization
- [ ] Real-time spectral filtering
- [ ] 3D point cloud export
- [ ] USGS spectral library integration
- [ ] Docker/Kubernetes deployment
- [ ] Mobile app interface

---

**HSI-Core: Making hyperspectral imaging accessible to research labs worldwide** 🔬✨
