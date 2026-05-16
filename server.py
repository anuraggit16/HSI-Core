# =============================================================================
# HSI-Core — FastAPI Server
# =============================================================================
# Entry point: uvicorn server:app --reload --host 0.0.0.0 --port 8000
# =============================================================================

from __future__ import annotations

import asyncio
import io
import json
import os
import time
from typing import Set

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from acquisition.hal import LabController
from acquisition.scan import ScanEngine, ScanParams, ScanState
from acquisition.data_cube import data_cube_manager

# =============================================================================
# STARTUP — instantiate global singletons
# =============================================================================

app        = FastAPI(title="HSI-Core Acquisition Server", version="3.0.0")
controller = LabController()
scan_engine = ScanEngine(controller)

_ws_clients: Set[WebSocket] = set()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# =============================================================================
# LIFESPAN EVENTS
# =============================================================================

@app.on_event("startup")
async def _startup():
    asyncio.create_task(_ws_broadcast_loop())

@app.on_event("shutdown")
async def _shutdown():
    controller.close()

# =============================================================================
# ROUTES — Static UI
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open(os.path.join("static", "index.html"), encoding="utf-8") as f:
        return f.read()

# =============================================================================
# ROUTES — Hardware Status
# =============================================================================

@app.get("/api/status")
async def get_status():
    return {
        "hardware" : controller.status_dict(),
        "scan"     : scan_engine.progress_dict(),
    }

# =============================================================================
# ROUTES — Camera
# =============================================================================

@app.get("/api/camera/stream")
async def camera_stream():
    """MJPEG live feed — render in <img src='/api/camera/stream'>"""
    async def generator():
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        while True:
            frame = controller.get_live_jpeg()
            if frame:
                yield boundary + frame + b"\r\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(
        generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

class CameraSettings(BaseModel):
    exposure_us: float | None = None
    gain_db    : float | None = None

@app.post("/api/camera/settings")
async def set_camera_settings(settings: CameraSettings):
    if settings.exposure_us is not None:
        controller.set_camera_exposure(settings.exposure_us)
    if settings.gain_db is not None:
        controller.set_camera_gain(settings.gain_db)
    return {"ok": True}

# =============================================================================
# ROUTES — Stage
# =============================================================================

class JogRequest(BaseModel):
    axis     : str    # "x" | "y"
    direction: int    # +1 | -1
    step_mm  : float

@app.post("/api/stage/jog")
async def stage_jog(req: JogRequest):
    controller.jog(req.axis, req.direction, req.step_mm)
    return {"ok": True}

class GotoRequest(BaseModel):
    x_mm: float
    y_mm: float

@app.post("/api/stage/goto")
async def stage_goto(req: GotoRequest):
    asyncio.get_event_loop().run_in_executor(
        None, controller.goto, req.x_mm, req.y_mm
    )
    return {"ok": True}

@app.post("/api/stage/home")
async def stage_home():
    asyncio.get_event_loop().run_in_executor(None, controller.home)
    return {"ok": True}

# =============================================================================
# ROUTES — Scan Control
# =============================================================================

class ScanStartRequest(BaseModel):
    x_start      : float = config.SCAN_START_X_MM
    x_end        : float = config.SCAN_END_X_MM
    x_step       : float = config.SCAN_STEP_X_MM
    y_start      : float = config.SCAN_START_Y_MM
    y_end        : float = config.SCAN_END_Y_MM
    y_step       : float = config.SCAN_STEP_Y_MM
    exposure_ms  : float = config.EXPOSURE_MS
    settling_s   : float = config.SETTLING_TIME_S
    raster       : str   = config.RASTER_PATTERN
    session_name : str   = ""

@app.post("/api/scan/start")
async def scan_start(req: ScanStartRequest):
    if scan_engine.state != ScanState.IDLE:
        raise HTTPException(409, f"Scan already {scan_engine.state}")

    session = req.session_name or f"session_{int(time.time())}"
    params  = ScanParams(
        x_start      = req.x_start,
        x_end        = req.x_end,
        x_step       = req.x_step,
        y_start      = req.y_start,
        y_end        = req.y_end,
        y_step       = req.y_step,
        exposure_ms  = req.exposure_ms,
        settling_s   = req.settling_s,
        raster       = req.raster,
        session_name = session,
    )
    controller.set_camera_exposure(req.exposure_ms * 1000)
    scan_engine.start(params)
    return {"ok": True, "session": session}

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

# =============================================================================
# ROUTES — Dataset Browser
# =============================================================================

@app.get("/api/datasets")
async def list_datasets():
    return data_cube_manager.list_sessions()

@app.get("/api/datasets/{name}/map")
async def get_dataset_map(name: str):
    """Returns a PNG intensity heatmap of the session."""
    import cv2
    intensity = data_cube_manager.get_intensity_map(name)
    if intensity is None:
        raise HTTPException(404, "Dataset not found or empty")

    # Apply inferno colormap
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

# =============================================================================
# WEBSOCKET — Real-time Telemetry
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global _ws_clients
    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            # Keep connection alive; client sends pings as needed
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(ws)
    except Exception:
        _ws_clients.discard(ws)

async def _ws_broadcast_loop():
    global _ws_clients
    interval = 1.0 / config.WS_BROADCAST_HZ

    while True:
        await asyncio.sleep(interval)
        if not _ws_clients:
            continue

        # Drain scan engine event queue
        events = []
        while not scan_engine.event_queue.empty():
            try:
                events.append(scan_engine.event_queue.get_nowait())
            except Exception:
                break

        payload = {
            "type"     : "telemetry",
            "hardware" : controller.status_dict(),
            "scan"     : scan_engine.progress_dict(),
            "events"   : events,
        }

        dead = set()
        for ws in list(_ws_clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        _ws_clients -= dead

# =============================================================================
# DEV RUNNER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=True,
    )
