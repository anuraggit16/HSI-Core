# =============================================================================
# HSI-Core — Professional FastAPI Acquisition Server
# =============================================================================
# Entry point: python3 server_enhanced.py
# Serves the instrument dashboard and exposes hardware, scan, camera, dataset,
# and realtime telemetry APIs backed by the shared HAL + scan engine.
# =============================================================================

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Optional, Set

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from acquisition.data_cube import data_cube_manager
from acquisition.hal import LabController
from acquisition.hardware import HardwareDetector
from acquisition.scan import ScanEngine, ScanParams, ScanState


app = FastAPI(
    title="HSI-Core Acquisition Server",
    version="3.0.0",
    description="Hyperspectral acquisition, instrument control, and analysis server",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

controller = LabController()
scan_engine = ScanEngine(controller)
_ws_clients: Set[WebSocket] = set()


def _safe_session_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return name[:80] or f"session_{int(time.time())}"


def _normalise_save_folder(value: str) -> str:
    folder = os.path.abspath(os.path.expanduser(value.strip() or config.SAVE_FOLDER))
    os.makedirs(folder, exist_ok=True)
    return folder


@app.on_event("startup")
async def _startup():
    os.makedirs(config.SAVE_FOLDER, exist_ok=True)
    asyncio.create_task(_ws_broadcast_loop())


@app.on_event("shutdown")
async def _shutdown():
    controller.close()


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open(os.path.join("static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/api/status")
async def get_status():
    return {
        "hardware": controller.status_dict(),
        "scan": scan_engine.progress_dict(),
        "config": {
            "mock_mode": config.MOCK_MODE,
            "stage_limits_mm": {
                "x": [config.STAGE_X_MIN_MM, config.STAGE_X_MAX_MM],
                "y": [config.STAGE_Y_MIN_MM, config.STAGE_Y_MAX_MM],
            },
            "wavelength_nm": [config.SPECTRAL_MIN_NM, config.SPECTRAL_MAX_NM],
        },
    }


class StorageRequest(BaseModel):
    save_folder: Optional[str] = None
    current_folder: Optional[str] = None


@app.get("/api/storage")
async def get_storage():
    return {
        "save_folder": os.path.abspath(config.SAVE_FOLDER),
    }


@app.post("/api/storage")
async def set_storage(req: StorageRequest):
    if not req.save_folder:
        raise HTTPException(400, "Save folder is required")
    config.SAVE_FOLDER = _normalise_save_folder(req.save_folder)
    return {
        "ok": True,
        "save_folder": config.SAVE_FOLDER,
    }


@app.post("/api/storage/browse")
async def browse_storage(req: StorageRequest):
    try:
        import tkinter as tk
        from tkinter import filedialog

        initial = _normalise_save_folder(req.current_folder or config.SAVE_FOLDER)
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            initialdir=initial,
            title="Select HSI save folder",
        )
        root.destroy()
    except Exception as exc:
        raise HTTPException(500, f"Folder browser unavailable: {exc}") from exc

    if selected:
        config.SAVE_FOLDER = _normalise_save_folder(selected)
    return {
        "ok": bool(selected),
        "save_folder": config.SAVE_FOLDER,
    }


@app.post("/api/storage/open")
async def open_storage(req: StorageRequest):
    folder = _normalise_save_folder(req.save_folder or config.SAVE_FOLDER)
    try:
        if os.name == "nt":
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            raise RuntimeError("Open folder is only configured for Windows")
    except Exception as exc:
        raise HTTPException(500, f"Folder could not be opened: {exc}") from exc
    return {"ok": True, "save_folder": folder}


@app.get("/api/hardware/status")
async def hardware_status():
    status = controller.status_dict()
    detected = HardwareDetector.detect_all()
    return {
        "connected": status["connected"],
        "mock_mode": status["mock_mode"],
        "stage_x": {
            "name": "X Motorized Stage",
            "serial": config.CONTROLLER_SERIAL_X,
            "connected": status["connected"],
            "position_mm": status["stage_x_mm"],
        },
        "stage_y": {
            "name": "Y Motorized Stage",
            "serial": config.CONTROLLER_SERIAL_Y,
            "connected": status["connected"],
            "position_mm": status["stage_y_mm"],
        },
        "camera": {
            "name": "Imaging Camera",
            "serial": detected.get("camera").serial if "camera" in detected else "unknown",
            "connected": status["connected"],
            "temperature_c": status["camera_temp"],
        },
    }


@app.post("/api/hardware/detect")
async def detect_hardware():
    devices = HardwareDetector.detect_all()
    return {key: device.__dict__ for key, device in devices.items()}


@app.get("/api/hardware/ready")
async def hardware_ready():
    status = controller.status_dict()
    return {
        "ready": bool(status["connected"]),
        "mode": "simulation" if status["mock_mode"] else "hardware",
    }


@app.get("/api/camera/stream")
async def camera_stream():
    async def generator():
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        while True:
            frame = controller.get_live_jpeg()
            if frame:
                yield boundary + frame + b"\r\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(
        generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


class CameraSettings(BaseModel):
    exposure_us: Optional[float] = None
    exposure_ms: Optional[float] = None
    gain_db: Optional[float] = None


@app.post("/api/camera/settings")
async def set_camera_settings(settings: CameraSettings):
    if settings.exposure_ms is not None:
        controller.set_camera_exposure(settings.exposure_ms * 1000.0)
    if settings.exposure_us is not None:
        controller.set_camera_exposure(settings.exposure_us)
    if settings.gain_db is not None:
        controller.set_camera_gain(settings.gain_db)
    return {"ok": True, "hardware": controller.status_dict()}


class JogRequest(BaseModel):
    axis: str
    direction: int
    step_mm: float = Field(gt=0)


@app.post("/api/stage/jog")
async def stage_jog(req: JogRequest):
    axis = req.axis.lower()
    if axis not in {"x", "y"}:
        raise HTTPException(400, "axis must be x or y")
    asyncio.get_running_loop().run_in_executor(None, controller.jog, axis, 1 if req.direction >= 0 else -1, req.step_mm)
    return {"ok": True, "hardware": controller.status_dict()}


class GotoRequest(BaseModel):
    x_mm: float
    y_mm: float


@app.post("/api/stage/goto")
async def stage_goto(req: GotoRequest):
    asyncio.get_running_loop().run_in_executor(None, controller.goto, req.x_mm, req.y_mm)
    return {"ok": True}


@app.post("/api/stage/home")
async def stage_home():
    asyncio.get_running_loop().run_in_executor(None, controller.home)
    return {"ok": True}


class ScanStartRequest(BaseModel):
    x_start: float = config.SCAN_START_X_MM
    x_end: float = config.SCAN_END_X_MM
    x_step: float = config.SCAN_STEP_X_MM
    y_start: float = config.SCAN_START_Y_MM
    y_end: float = config.SCAN_END_Y_MM
    y_step: float = config.SCAN_STEP_Y_MM
    exposure_ms: float = config.EXPOSURE_MS
    settling_s: float = config.SETTLING_TIME_S
    raster: Optional[str] = None
    pattern: Optional[str] = None
    session_name: str = ""
    wavelength_min_nm: float = config.SPECTRAL_MIN_NM
    wavelength_max_nm: float = config.SPECTRAL_MAX_NM


@app.post("/api/scan/start")
async def scan_start(req: ScanStartRequest):
    if scan_engine.state != ScanState.IDLE:
        raise HTTPException(409, f"Scan already {scan_engine.state}")

    session = _safe_session_name(req.session_name)
    raster = (req.raster or req.pattern or config.RASTER_PATTERN).lower()
    if raster == "raster":
        raster = "grid"
    if raster not in {"grid", "serpentine"}:
        raise HTTPException(400, "pattern must be serpentine or raster")

    try:
        params = ScanParams(
            x_start=req.x_start,
            x_end=req.x_end,
            x_step=req.x_step,
            y_start=req.y_start,
            y_end=req.y_end,
            y_step=req.y_step,
            exposure_ms=req.exposure_ms,
            settling_s=req.settling_s,
            raster=raster,
            session_name=session,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    controller.set_camera_exposure(req.exposure_ms * 1000.0)
    scan_engine.start(params)
    return {
        "ok": True,
        "session": session,
        "nx": params.nx,
        "ny": params.ny,
        "total_frames": params.total_frames,
    }


@app.post("/api/scan/pause")
async def scan_pause():
    scan_engine.pause()
    return {"ok": True}


@app.post("/api/scan/resume")
async def scan_resume():
    scan_engine.resume()
    return {"ok": True}


@app.post("/api/scan/stop")
async def scan_stop():
    scan_engine.stop()
    return {"ok": True}


@app.post("/api/scan/emergency")
async def scan_emergency():
    scan_engine.emergency_stop()
    return {"ok": True, "message": "EMERGENCY STOP"}


@app.get("/api/datasets")
async def list_datasets():
    return data_cube_manager.list_sessions()


@app.get("/api/datasets/{name}/map")
async def get_dataset_map(name: str):
    intensity = data_cube_manager.get_intensity_map(name)
    if intensity is None:
        raise HTTPException(404, "Dataset not found or empty")

    grey = (intensity * 255).astype(np.uint8)
    colored = cv2.applyColorMap(grey, cv2.COLORMAP_INFERNO)
    _, buf = cv2.imencode(".png", colored)
    return Response(content=buf.tobytes(), media_type="image/png")


@app.get("/api/datasets/{name}/frame/{yi}/{xi}")
async def get_dataset_frame(name: str, yi: int, xi: int):
    jpeg = data_cube_manager.get_frame_jpeg(name, yi, xi)
    if jpeg is None:
        raise HTTPException(404, "Frame not found")
    return Response(content=jpeg, media_type="image/jpeg")


@app.get("/api/analysis/spectrum/live")
async def live_spectrum():
    wavelengths = np.linspace(config.SPECTRAL_MIN_NM, config.SPECTRAL_MAX_NM, config.SPECTRAL_BANDS)
    temp = controller.status_dict()["camera_temp"]
    center = 685 + 14 * np.sin(time.time() / 6.0)
    baseline = 35 + 12 * np.sin(wavelengths / 42.0)
    peak_a = 420 * np.exp(-((wavelengths - center) ** 2) / (2 * 18 ** 2))
    peak_b = 170 * np.exp(-((wavelengths - 545) ** 2) / (2 * 38 ** 2))
    spectrum = np.clip(baseline + peak_a + peak_b + (temp - 22.0) * 2.0, 0, None)
    return {
        "wavelengths_nm": wavelengths.round(2).tolist(),
        "intensity": spectrum.round(2).tolist(),
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(ws)
    except Exception:
        _ws_clients.discard(ws)


async def _ws_broadcast_loop():
    interval = 1.0 / max(1, config.WS_BROADCAST_HZ)
    while True:
        await asyncio.sleep(interval)
        if not _ws_clients:
            continue

        events = []
        while not scan_engine.event_queue.empty():
            try:
                events.append(scan_engine.event_queue.get_nowait())
            except Exception:
                break

        payload = {
            "type": "telemetry",
            "timestamp": time.time(),
            "hardware": controller.status_dict(),
            "scan": scan_engine.progress_dict(),
            "events": events,
        }

        dead = set()
        for ws in list(_ws_clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        _ws_clients.difference_update(dead)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server_enhanced:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=False,
    )
