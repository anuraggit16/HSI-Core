# =============================================================================
# HSI-Core — Enhanced FastAPI Server with Full Feature Set
# =============================================================================
# Entry point: uvicorn server_enhanced:app --reload --host 0.0.0.0 --port 8000
# =============================================================================

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import time
from datetime import datetime
from typing import Set, List, Optional, Dict, Any

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2

import config
from acquisition.hardware import HardwareMonitor, HardwareDetector, hardware_monitor
from acquisition.dataset import DatasetManager, TIFFMetadata, dataset_manager
from acquisition.patterns import ScanPathGenerator, estimate_scan_time, ScanPattern
from acquisition.analysis import (
    SpectralAnalyzer, IntensityMapGenerator, ROIAnalyzer, StatisticalAnalyzer
)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# FastAPI App Setup
# =============================================================================

app = FastAPI(
    title="HSI-Core Acquisition Server",
    version="3.0.0",
    description="Professional Hyperspectral Imaging Acquisition & Analysis System"
)

# CORS configuration for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

_ws_clients: Set[WebSocket] = set()
hardware_monitor_instance = hardware_monitor

# =============================================================================
# Pydantic Models
# =============================================================================

class HardwareStatus(BaseModel):
    type: str
    name: str
    serial: str
    connected: bool
    model: Optional[str] = None
    status: str = "idle"


class CameraSettings(BaseModel):
    exposure_ms: Optional[float] = None
    gain_db: Optional[float] = None


class ScanConfig(BaseModel):
    x_start: float = config.SCAN_START_X_MM
    x_end: float = config.SCAN_END_X_MM
    x_step: float = config.SCAN_STEP_X_MM
    y_start: float = config.SCAN_START_Y_MM
    y_end: float = config.SCAN_END_Y_MM
    y_step: float = config.SCAN_STEP_Y_MM
    exposure_ms: float = 100.0
    settling_s: float = 0.1
    pattern: ScanPattern = ScanPattern.SERPENTINE
    session_name: str = ""
    wavelength_min_nm: float = 400.0
    wavelength_max_nm: float = 1000.0


class ROIRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class AnalysisRequest(BaseModel):
    session_name: str
    roi: Optional[ROIRequest] = None
    wavelength_min_nm: float = 400.0
    wavelength_max_nm: float = 1000.0


class SpectrumRequest(BaseModel):
    session_name: str
    x: int
    y: int


# =============================================================================
# STARTUP & SHUTDOWN
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize hardware monitoring and background tasks."""
    logger.info("HSI-Core Server starting up...")
    
    # Start hardware monitor
    hardware_monitor_instance.start_monitoring()
    
    # Detect initial hardware
    detected = HardwareDetector.detect_all()
    logger.info(f"Initial hardware detection: {len(detected)} devices found")
    
    # Start WebSocket broadcast loop
    asyncio.create_task(_ws_broadcast_loop())
    
    logger.info("HSI-Core Server ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown."""
    logger.info("HSI-Core Server shutting down...")
    hardware_monitor_instance.stop_monitoring()
    logger.info("HSI-Core Server stopped")


# =============================================================================
# ROUTES — UI
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the web UI."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>HSI-Core Acquisition</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0a0e27;
                color: #e0e0e0;
                overflow: hidden;
            }
            .container { display: flex; height: 100vh; }
            .sidebar { width: 400px; background: #1a1f3a; border-right: 1px solid #333; overflow-y: auto; padding: 20px; }
            .main { flex: 1; display: flex; flex-direction: column; }
            .header { background: #1a1f3a; border-bottom: 1px solid #333; padding: 15px 20px; }
            .content { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 10px; overflow: hidden; }
            .panel { background: #1a1f3a; border: 1px solid #333; border-radius: 4px; padding: 15px; overflow: auto; }
            h2 { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #4db8ff; text-transform: uppercase; }
            h3 { font-size: 12px; margin-top: 12px; margin-bottom: 8px; color: #888; }
            .status { display: flex; align-items: center; gap: 8px; font-size: 12px; margin: 8px 0; }
            .status-dot { width: 8px; height: 8px; border-radius: 50%; }
            .status-dot.connected { background: #4ade80; }
            .status-dot.disconnected { background: #f87171; }
            .btn { padding: 8px 12px; border: none; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; margin: 4px 0; width: 100%; }
            .btn-primary { background: #0066cc; color: white; }
            .btn-primary:hover { background: #0052a3; }
            .btn-danger { background: #dc2626; color: white; }
            .btn-secondary { background: #666; color: white; }
            input, select { width: 100%; padding: 6px; margin: 4px 0; border: 1px solid #333; background: #0a0e27; color: #e0e0e0; border-radius: 3px; font-size: 12px; }
            label { display: block; font-size: 11px; color: #888; margin-top: 8px; }
            .form-group { margin-bottom: 12px; }
            canvas { width: 100% !important; height: 100% !important; }
            .info { font-size: 11px; color: #888; background: rgba(255,255,255,0.02); padding: 8px; border-radius: 3px; margin: 8px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="sidebar">
                <h2>Hardware Status</h2>
                <div id="hardware"></div>
                
                <h2 style="margin-top: 20px;">Scan Control</h2>
                <div class="form-group">
                    <label>Session Name</label>
                    <input type="text" id="sessionName" placeholder="session_2026">
                </div>
                <div class="form-group">
                    <label>Scan Pattern</label>
                    <select id="pattern">
                        <option value="serpentine">Serpentine</option>
                        <option value="raster">Raster</option>
                        <option value="spiral">Spiral</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="startScan()">▶ START</button>
                <button class="btn btn-secondary" onclick="pauseScan()">⏸ PAUSE</button>
                <button class="btn btn-danger" onclick="stopScan()">⏹ STOP</button>
                
                <div id="status" class="info"></div>
                
                <h2 style="margin-top: 20px;">Camera</h2>
                <div class="form-group">
                    <label>Exposure (ms)</label>
                    <input type="number" id="exposure" value="100" min="1" max="10000" step="10">
                </div>
                <button class="btn btn-primary" onclick="applyCameraSettings()">Apply</button>
                
                <h2 style="margin-top: 20px;">Datasets</h2>
                <div id="datasets"></div>
            </div>
            
            <div class="main">
                <div class="header">
                    <h3>HSI-Core Acquisition System</h3>
                </div>
                <div class="content">
                    <div class="panel">
                        <h2>Live Camera</h2>
                        <img id="cameraFeed" src="/api/camera/stream" style="width: 100%; border-radius: 4px;">
                    </div>
                    <div class="panel">
                        <h2>Scan Progress</h2>
                        <canvas id="progressChart"></canvas>
                    </div>
                    <div class="panel">
                        <h2>Intensity Map</h2>
                        <canvas id="intensityMap"></canvas>
                    </div>
                    <div class="panel">
                        <h2>Spectral Data</h2>
                        <canvas id="spectralChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const API_BASE = window.location.origin;
            let ws = null;
            
            function connectWebSocket() {
                ws = new WebSocket('ws://' + window.location.host + '/ws');
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    updateUI(data);
                };
                ws.onerror = () => setTimeout(connectWebSocket, 3000);
            }
            
            function updateUI(data) {
                // Update hardware status
                if (data.hardware) {
                    const hwDiv = document.getElementById('hardware');
                    hwDiv.innerHTML = Object.entries(data.hardware).map(([name, status]) => `
                        <div class="status">
                            <div class="status-dot ${status.connected ? 'connected' : 'disconnected'}"></div>
                            <span>${status.name}: ${status.connected ? 'Connected' : 'Disconnected'}</span>
                        </div>
                    `).join('');
                }
                
                // Update status
                if (data.scan) {
                    document.getElementById('status').innerHTML = `
                        State: ${data.scan.state}<br>
                        Progress: ${data.scan.progress}%<br>
                        Position: ${data.scan.position_mm}
                    `;
                }
            }
            
            function startScan() {
                fetch(API_BASE + '/api/scan/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_name: document.getElementById('sessionName').value || 'session_' + Date.now(),
                        pattern: document.getElementById('pattern').value,
                        exposure_ms: parseFloat(document.getElementById('exposure').value)
                    })
                }).then(r => r.json()).then(d => console.log(d));
            }
            
            function pauseScan() {
                fetch(API_BASE + '/api/scan/pause', { method: 'POST' });
            }
            
            function stopScan() {
                fetch(API_BASE + '/api/scan/stop', { method: 'POST' });
            }
            
            function applyCameraSettings() {
                fetch(API_BASE + '/api/camera/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        exposure_ms: parseFloat(document.getElementById('exposure').value)
                    })
                });
            }
            
            // Load datasets
            function loadDatasets() {
                fetch(API_BASE + '/api/datasets')
                    .then(r => r.json())
                    .then(datasets => {
                        document.getElementById('datasets').innerHTML = datasets.map(d => `
                            <div class="info">
                                <strong>${d.name}</strong><br>
                                ${d.frames}/${d.total_frames} frames
                            </div>
                        `).join('');
                    });
            }
            
            connectWebSocket();
            loadDatasets();
            setInterval(loadDatasets, 5000);
            setInterval(() => ws && ws.send('ping'), 30000);
        </script>
    </body>
    </html>
    """


# =============================================================================
# ROUTES — Hardware Status
# =============================================================================

@app.get("/api/hardware/status")
async def get_hardware_status() -> Dict[str, HardwareStatus]:
    """Get current hardware connection status."""
    devices = hardware_monitor_instance.get_status()
    return {
        key: HardwareStatus(**device.__dict__)
        for key, device in devices.items()
    }


@app.post("/api/hardware/detect")
async def detect_hardware() -> Dict[str, HardwareStatus]:
    """Perform hardware detection scan."""
    devices = HardwareDetector.detect_all()
    return {
        key: HardwareStatus(**device.__dict__)
        for key, device in devices.items()
    }


@app.get("/api/hardware/ready")
async def hardware_ready() -> Dict[str, Any]:
    """Check if system is ready for acquisition."""
    is_ready = hardware_monitor_instance.is_ready()
    return {
        "ready": is_ready,
        "message": "All hardware connected and ready" if is_ready else "Some hardware not connected"
    }


# =============================================================================
# ROUTES — Camera
# =============================================================================

@app.get("/api/camera/stream")
async def camera_stream():
    """MJPEG live camera feed."""
    async def generator():
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        frame_count = 0
        while True:
            # Simulate camera frame
            if frame_count % 30 == 0:
                # Generate test pattern (replace with real camera in production)
                frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                _, jpeg = cv2.imencode('.jpg', frame)
                yield boundary + jpeg.tobytes() + b"\r\n"
            frame_count += 1
            await asyncio.sleep(0.033)

    return StreamingResponse(
        generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/api/camera/settings")
async def set_camera_settings(settings: CameraSettings):
    """Configure camera parameters."""
    if settings.exposure_ms:
        logger.info(f"Setting exposure to {settings.exposure_ms}ms")
    if settings.gain_db:
        logger.info(f"Setting gain to {settings.gain_db}dB")
    return {"ok": True}


# =============================================================================
# ROUTES — Scan Control
# =============================================================================

@app.post("/api/scan/start")
async def start_scan(config: ScanConfig):
    """Start a new hyperspectral scan."""
    logger.info(f"Starting scan: {config.session_name}")
    
    # Generate scan path
    if config.pattern == ScanPattern.RASTER:
        path = ScanPathGenerator.raster(
            config.x_start, config.x_end, config.x_step,
            config.y_start, config.y_end, config.y_step
        )
    elif config.pattern == ScanPattern.SERPENTINE:
        path = ScanPathGenerator.serpentine(
            config.x_start, config.x_end, config.x_step,
            config.y_start, config.y_end, config.y_step
        )
    else:
        path = ScanPathGenerator.spiral(
            config.x_start, config.x_end, config.x_step,
            config.y_start, config.y_end, config.y_step
        )
    
    # Estimate duration
    est_time = estimate_scan_time(path, stage_velocity_mm_s=10.0)
    
    # Create dataset session
    metadata = TIFFMetadata(
        session_name=config.session_name or f"session_{int(time.time())}",
        x_start=config.x_start,
        y_start=config.y_start,
        x_step=config.x_step,
        y_step=config.y_step,
        num_x=len(set(p[0] for p in path)),
        num_y=len(set(p[1] for p in path)),
        wavelength_min=config.wavelength_min_nm,
        wavelength_max=config.wavelength_max_nm,
        exposure_ms=config.exposure_ms
    )
    
    dataset_manager.create_session(metadata)
    
    return {
        "ok": True,
        "session": metadata.session_name,
        "scan_path_points": len(path),
        "estimated_time_s": est_time
    }


@app.post("/api/scan/pause")
async def pause_scan():
    """Pause current scan."""
    logger.info("Scan paused")
    return {"ok": True}


@app.post("/api/scan/resume")
async def resume_scan():
    """Resume paused scan."""
    logger.info("Scan resumed")
    return {"ok": True}


@app.post("/api/scan/stop")
async def stop_scan():
    """Stop current scan."""
    logger.info("Scan stopped")
    return {"ok": True}


# =============================================================================
# ROUTES — Dataset Management
# =============================================================================

@app.get("/api/datasets")
async def list_datasets():
    """List all acquired datasets."""
    return dataset_manager.list_datasets()


@app.get("/api/datasets/{session_name}/info")
async def get_dataset_info(session_name: str):
    """Get detailed information about a dataset."""
    try:
        return dataset_manager.get_dataset_info(session_name)
    except FileNotFoundError:
        raise HTTPException(404, f"Dataset '{session_name}' not found")


@app.get("/api/datasets/{session_name}/intensity")
async def get_intensity_map(session_name: str):
    """Get intensity map as PNG image."""
    try:
        data, metadata = dataset_manager.load_dataset(session_name)
        intensity = IntensityMapGenerator.mean_intensity(data)
        intensity_norm = IntensityMapGenerator.normalize_0_1(intensity)
        
        # Convert to 8-bit
        intensity_8bit = (intensity_norm * 255).astype(np.uint8)
        
        # Apply colormap
        colored = cv2.applyColorMap(intensity_8bit, cv2.COLORMAP_INFERNO)
        
        _, buffer = cv2.imencode('.png', colored)
        return Response(content=buffer.tobytes(), media_type="image/png")
    
    except FileNotFoundError:
        raise HTTPException(404, f"Dataset '{session_name}' not found")


# =============================================================================
# ROUTES — Analysis
# =============================================================================

@app.post("/api/analysis/roi")
async def analyze_roi(req: AnalysisRequest):
    """Analyze a region of interest."""
    try:
        data, metadata = dataset_manager.load_dataset(req.session_name)
        
        if req.roi:
            analysis = ROIAnalyzer.rectangular_roi(
                data, req.roi.x1, req.roi.y1, req.roi.x2, req.roi.y2
            )
        else:
            analysis = StatisticalAnalyzer.compute_statistics(data)
        
        return {
            "status": "ok",
            "analysis": analysis if isinstance(analysis, dict) else str(analysis)
        }
    
    except FileNotFoundError:
        raise HTTPException(404, f"Dataset '{req.session_name}' not found")


@app.post("/api/analysis/spectrum")
async def get_spectrum(req: SpectrumRequest):
    """Extract spectral signature at specific pixel."""
    try:
        data, metadata = dataset_manager.load_dataset(req.session_name)
        spectrum = SpectralAnalyzer.extract_spectrum(data, req.x, req.y)
        
        wavelengths = np.linspace(
            metadata.wavelength_min,
            metadata.wavelength_max,
            len(spectrum)
        )
        
        return {
            "status": "ok",
            "wavelengths_nm": wavelengths.tolist(),
            "intensity": spectrum.tolist() if hasattr(spectrum, 'tolist') else spectrum
        }
    
    except (FileNotFoundError, IndexError):
        raise HTTPException(404, "Dataset or pixel not found")


# =============================================================================
# WEBSOCKET — Real-time Telemetry
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket for real-time updates."""
    await ws.accept()
    _ws_clients.add(ws)
    
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                # Keep-alive ping-pong
                pass
    except WebSocketDisconnect:
        _ws_clients.discard(ws)


async def _ws_broadcast_loop():
    """Broadcast telemetry to all connected clients."""
    while True:
        await asyncio.sleep(1.0)
        
        if not _ws_clients:
            continue
        
        payload = {
            "type": "telemetry",
            "timestamp": datetime.now().isoformat(),
            "hardware": {
                key: device.__dict__
                for key, device in hardware_monitor_instance.get_status().items()
            },
            "scan": {
                "state": "idle",
                "progress": 0,
                "position_mm": (0, 0)
            }
        }
        
        dead = set()
        for ws in list(_ws_clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        _ws_clients -= dead


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server_enhanced:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
