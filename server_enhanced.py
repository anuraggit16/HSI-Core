# =============================================================================
# HSI-Core — Professional FastAPI Acquisition Server
# =============================================================================

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import sys
import time
from typing import Optional, Set

import cv2
import numpy as np

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

import config

from acquisition.data_cube import data_cube_manager
from acquisition.error_logger import (
    get_hardware_errors,
    get_latest_hardware_events,
    get_recent_errors,
    initialize_error_log,
    log_error,
    log_hardware_event,
)
from acquisition.hal import get_lab_controller
from acquisition.hardware import HardwareDetector
from acquisition.scan import ScanEngine, ScanParams, ScanState


# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="HSI-Core Acquisition Server",
    version="4.0.0",
    description="Single-axis hyperspectral acquisition server",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(Exception)
async def _global_exception_handler(request, exc: Exception):

    log_error("SYSTEM_ERROR", exc)

    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "detail": "System error logged; server is still running.",
        },
    )


# =============================================================================
# GLOBAL OBJECTS
# =============================================================================

initialize_error_log()

controller = get_lab_controller()

scan_engine = ScanEngine(controller)

_ws_clients: Set[WebSocket] = set()
_system_mode_state = "LIVE"
_live_processing_enabled = False
_MAX_TIFF_UPLOAD_BYTES = 500 * 1024 * 1024


# =============================================================================
# HELPERS
# =============================================================================

def _safe_session_name(value: str) -> str:

    name = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        value.strip()
    )

    return name[:80] or f"session_{int(time.time())}"


def _normalise_save_folder(value: str) -> str:

    folder = os.path.abspath(
        os.path.expanduser(
            value.strip() or config.SAVE_FOLDER
        )
    )

    os.makedirs(folder, exist_ok=True)

    return folder


def _system_mode(status: dict) -> str:

    return "mock" if status.get("mock_mode") else "real"


def _processing_active() -> bool:

    return (
        scan_engine.state in {ScanState.RUNNING, ScanState.PAUSED}
        or (
            _system_mode_state == "ANALYSIS"
            and _live_processing_enabled
        )
    )


def _sync_processing_state() -> bool:

    global _system_mode_state

    if (
        _system_mode_state == "SCAN"
        and scan_engine.state not in {ScanState.RUNNING, ScanState.PAUSED}
    ):
        _system_mode_state = "LIVE"

    active = _processing_active()

    try:
        controller.set_processing_enabled(active)
    except Exception as exc:
        log_error("SYSTEM_ERROR", exc)

    return active


def _spectral_range() -> dict:

    return {
        "min_wavelength_nm": config.SPECTRAL_MIN_NM,
        "max_wavelength_nm": config.SPECTRAL_MAX_NM,
        "bands": config.SPECTRAL_BANDS,
        "source": "config",
    }


# =============================================================================
# STARTUP / SHUTDOWN
# =============================================================================

@app.on_event("startup")
async def _startup():

    initialize_error_log()

    try:
        os.makedirs(config.SAVE_FOLDER, exist_ok=True)
    except Exception as exc:
        log_error("SYSTEM_ERROR", exc)

    try:
        status = controller.status_dict()
        if status.get("stage_fallback") or not status.get("stage_physical_connected"):
            log_error("STAGE_ERROR", RuntimeError("Startup stage health check is using fallback"))
        if status.get("camera_fallback_stream") or not status.get("camera_physical_connected"):
            log_error("CAMERA_ERROR", RuntimeError("Startup camera health check is using fallback"))
    except Exception as exc:
        log_error("SYSTEM_ERROR", exc)

    _sync_processing_state()

    try:
        asyncio.create_task(_ws_broadcast_loop())
    except Exception as exc:
        log_error("SYSTEM_ERROR", exc)


@app.on_event("shutdown")
async def _shutdown():

    controller.close()


# =============================================================================
# UI
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui():

    with open(
        os.path.join("static", "index.html"),
        encoding="utf-8"
    ) as f:

        return f.read()


# =============================================================================
# STATUS
# =============================================================================

@app.get("/api/status")
async def get_status():

    hardware = controller.status_dict()
    scan = scan_engine.progress_dict()
    spectral = _spectral_range()
    processing_active = _sync_processing_state()

    return {

        "hardware": hardware,

        "scan": scan,

        "system": {

            "mode": _system_mode(hardware),

            "control_mode": _system_mode_state,

            "processing_active": processing_active,

            "live_processing_enabled": _live_processing_enabled,

            "ready": bool(
                hardware.get("stage_connected")
                and hardware.get("camera_connected")
            ),

            "stage_position_mm": hardware.get("stage_mm"),

            "camera_state": hardware.get("camera_status"),

            "scan_state": scan.get("state"),

            "error_count": len(get_recent_errors()),
        },

        "config": {

            "mock_mode": hardware.get("mock_mode"),

            "stage_limits_mm": {

                "x": [
                    config.STAGE_X_MIN_MM,
                    config.STAGE_X_MAX_MM
                ]
            },

            "wavelength_nm": [
                spectral["min_wavelength_nm"],
                spectral["max_wavelength_nm"]
            ],

            "spectral_range": spectral,
            "debug_mode": bool(getattr(config, "DEBUG_MODE", False)),
            "hardware_state": hardware.get("hardware_state", {}),
        },
    }


@app.get("/api/errors")
async def get_errors():

    errors = get_recent_errors()

    return {
        "ok": True,
        "count": len(errors),
        "errors": errors,
    }


@app.get("/api/logs/latest")
async def latest_logs(limit: int = 50):

    events = get_latest_hardware_events(limit)

    return {
        "ok": True,
        "count": len(events),
        "log_file": "logs/hardware_log.jsonl",
        "events": events,
    }


@app.get("/api/logs/errors")
async def hardware_error_logs(limit: int = 50):

    events = get_hardware_errors(limit)

    return {
        "ok": True,
        "count": len(events),
        "log_file": "logs/hardware_log.jsonl",
        "errors": events,
    }


class ClientErrorRequest(BaseModel):

    message: str
    source: str = "ui"
    severity: str = "ERROR"


@app.post("/api/errors/client")
async def log_client_error(req: ClientErrorRequest):

    log_error(
        "UI_ERROR",
        RuntimeError(f"{req.source}: {req.message}"),
        severity=req.severity,
    )

    return {"ok": True}


class ModeRequest(BaseModel):

    mode: str


@app.get("/api/system/mode")
async def get_system_mode():

    return {
        "mode": _system_mode_state,
        "live_processing_enabled": _live_processing_enabled,
        "processing_active": _sync_processing_state(),
    }


@app.post("/api/system/mode")
async def set_system_mode(req: ModeRequest):

    global _system_mode_state

    mode = req.mode.strip().upper()
    if mode not in {"LIVE", "SCAN", "ANALYSIS"}:
        raise HTTPException(400, "Mode must be LIVE, SCAN, or ANALYSIS")

    if mode != "SCAN" and scan_engine.state in {ScanState.RUNNING, ScanState.PAUSED}:
        raise HTTPException(409, "Cannot leave SCAN mode while scan is active")

    _system_mode_state = mode

    return {
        "ok": True,
        "mode": _system_mode_state,
        "live_processing_enabled": _live_processing_enabled,
        "processing_active": _sync_processing_state(),
    }


class ProcessingRequest(BaseModel):

    enabled: bool = False


@app.get("/api/processing")
async def get_processing():

    return {
        "live_processing_enabled": _live_processing_enabled,
        "processing_active": _sync_processing_state(),
    }


@app.post("/api/processing")
async def set_processing(req: ProcessingRequest):

    global _live_processing_enabled

    _live_processing_enabled = bool(req.enabled)

    return {
        "ok": True,
        "live_processing_enabled": _live_processing_enabled,
        "processing_active": _sync_processing_state(),
    }


@app.get("/api/spectral/range")
async def spectral_range():

    return _spectral_range()


# =============================================================================
# STORAGE
# =============================================================================

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
        raise HTTPException(400, "Save folder required")

    config.SAVE_FOLDER = _normalise_save_folder(
        req.save_folder
    )

    return {

        "ok": True,
        "save_folder": config.SAVE_FOLDER,
    }


@app.post("/api/storage/browse")
async def browse_storage(req: StorageRequest):

    folder = _normalise_save_folder(
        req.current_folder or config.SAVE_FOLDER
    )

    return {
        "ok": True,
        "save_folder": folder,
    }


@app.post("/api/storage/open")
async def open_storage(req: StorageRequest):

    folder = _normalise_save_folder(
        req.save_folder or config.SAVE_FOLDER
    )

    if sys.platform.startswith("win"):
        os.startfile(folder)  # type: ignore[attr-defined]

    return {
        "ok": True,
        "save_folder": folder,
    }


# =============================================================================
# HARDWARE
# =============================================================================

@app.get("/api/hardware/status")
async def hardware_status():

    status = controller.status_dict()

    detected = HardwareDetector.detect_all()

    return {

        "connected": status["connected"],

        "mock_mode": status["mock_mode"],

        "stage": {

            "name": "Linear Scan Stage",

            "serial": config.CONTROLLER_SERIAL_X,

            "connected": status["stage_connected"],

            "position_mm": status["stage_mm"],

            "moving": status["stage_moving"],
        },

        "camera": {

            "name": "Imaging Camera",

            "serial": (
                detected.get("camera").serial
                if "camera" in detected
                else "unknown"
            ),

            "connected": status["camera_connected"],

            "temperature_c": status["camera_temp"],
        },
    }


@app.post("/api/hardware/detect")
async def hardware_detect():

    detected = HardwareDetector.detect_all()
    status = controller.detect_hardware()

    return {
        "ok": True,
        "detected": {
            name: {
                "type": device.type,
                "name": device.name,
                "serial": device.serial,
                "connected": device.connected,
                "model": device.model,
                "status": device.status,
            }
            for name, device in detected.items()
        },
        "hardware": status,
    }


@app.get("/api/hardware/ready")
async def hardware_ready():

    status = controller.status_dict()

    return {

        "ready": bool(
            status.get("stage_connected")
            and status.get("camera_connected")
        ),

        "mode": (
            "simulation"
            if status["mock_mode"]
            else "hardware"
        ),
    }


# =============================================================================
# CAMERA STREAM
# =============================================================================

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


@app.get("/api/camera/snapshot")
async def camera_snapshot():

    frame = controller.get_live_jpeg()
    if not frame:
        raise HTTPException(503, "Camera stream is not ready")

    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/camera/start")
async def camera_start():

    controller.start_camera_stream()
    await asyncio.sleep(0.15)

    return {
        "ok": True,
        "hardware": controller.status_dict(),
    }


@app.post("/api/camera/stop")
async def camera_stop():

    controller.stop_camera_stream()

    return {
        "ok": True,
        "hardware": controller.status_dict(),
    }


# =============================================================================
# CAMERA SETTINGS
# =============================================================================

class CameraSettings(BaseModel):

    exposure_us: Optional[float] = None
    exposure_ms: Optional[float] = None
    gain_db: Optional[float] = None


@app.post("/api/camera/settings")
async def set_camera_settings(settings: CameraSettings):

    if settings.exposure_ms is not None:

        controller.set_camera_exposure(
            settings.exposure_ms * 1000.0
        )

    if settings.exposure_us is not None:

        controller.set_camera_exposure(
            settings.exposure_us
        )

    if settings.gain_db is not None:

        controller.set_camera_gain(
            settings.gain_db
        )

    return {

        "ok": True,

        "hardware": controller.status_dict()
    }


# =============================================================================
# STAGE CONTROL
# =============================================================================

class JogRequest(BaseModel):

    direction: int

    step_mm: float = Field(gt=0)


@app.post("/api/stage/jog")
async def stage_jog(req: JogRequest):

    if scan_engine.state in {ScanState.RUNNING, ScanState.PAUSED}:
        raise HTTPException(409, "Stage is reserved by active scan")

    await asyncio.get_running_loop().run_in_executor(

        None,

        controller.jog,

        1 if req.direction >= 0 else -1,

        req.step_mm
    )

    return {

        "ok": True,

        "hardware": controller.status_dict()
    }


class GotoRequest(BaseModel):

    x_mm: float


@app.post("/api/stage/goto")
async def stage_goto(req: GotoRequest):

    if scan_engine.state in {ScanState.RUNNING, ScanState.PAUSED}:
        raise HTTPException(409, "Stage is reserved by active scan")

    await asyncio.get_running_loop().run_in_executor(

        None,

        controller.goto,

        req.x_mm
    )

    return {
        "ok": True,
        "hardware": controller.status_dict()
    }


@app.post("/api/stage/move")
async def stage_move(req: GotoRequest):

    return await stage_goto(req)


@app.post("/api/stage/home")
async def stage_home():

    global _system_mode_state, _live_processing_enabled

    before = controller.status_dict()
    scan_was_active = scan_engine.state in {ScanState.RUNNING, ScanState.PAUSED}
    if scan_was_active:
        scan_engine.stop()

    await asyncio.get_running_loop().run_in_executor(

        None,

        controller.home
    )

    controller.stop_camera_stream()
    _system_mode_state = "LIVE"
    _live_processing_enabled = False
    _sync_processing_state()

    hardware = controller.status_dict()
    physical = bool(hardware.get("stage_physical_connected"))
    fallback = bool(hardware.get("stage_fallback") or hardware.get("stage_status") == "simulation")

    return {
        "ok": True,
        "hardware": hardware,
        "home_applied": True,
        "physical_home": physical,
        "fallback_home": fallback,
        "message": (
            "Physical stage homed"
            if physical
            else (
                "Stage home reset in simulation/fallback mode"
                if fallback
                else "Stage home command completed without physical confirmation"
            )
        ),
        "scan_stopped": scan_was_active,
        "camera_stream_stopped": True,
        "target_page": "overview",
        "previous_position_mm": before.get("stage_x_mm", before.get("stage_mm")),
    }


@app.post("/api/stage/zero")
async def stage_zero():

    result = await asyncio.get_running_loop().run_in_executor(
        None,
        controller.zero_calibration,
    )

    return {
        "ok": True,
        "zero": result,
        "hardware": controller.status_dict(),
    }


# =============================================================================
# SCAN
# =============================================================================

class ScanStartRequest(BaseModel):

    x_start: float = config.SCAN_START_X_MM

    x_end: float = config.SCAN_END_X_MM

    x_step: float = config.SCAN_STEP_X_MM

    start_position_mm: Optional[float] = None

    end_position_mm: Optional[float] = None

    step_size_mm: Optional[float] = None

    step_size_um: Optional[float] = None

    number_of_images: Optional[int] = None

    auto_calculate_images: bool = True

    exposure_ms: float = config.EXPOSURE_MS

    settling_s: float = config.SETTLING_TIME_S

    settling_time_s: Optional[float] = None

    scan_pattern: Optional[str] = None

    raster: Optional[str] = None

    save_png: bool = True

    save_tiff: bool = True

    session_name: str = ""

    wavelength_min_nm: float = config.SPECTRAL_MIN_NM

    wavelength_max_nm: float = config.SPECTRAL_MAX_NM


@app.post("/api/scan/start")
async def scan_start(req: ScanStartRequest):

    global _system_mode_state

    if scan_engine.state in {ScanState.RUNNING, ScanState.PAUSED}:

        raise HTTPException(
            409,
            f"Scan already {scan_engine.state}"
        )

    session = _safe_session_name(
        req.session_name
    )

    try:

        x_start = (
            req.start_position_mm
            if req.start_position_mm is not None
            else req.x_start
        )

        x_end = (
            req.end_position_mm
            if req.end_position_mm is not None
            else req.x_end
        )

        x_step = (
            req.step_size_um / 1000.0
            if req.step_size_um is not None
            else (
                req.step_size_mm
                if req.step_size_mm is not None
                else req.x_step
            )
        )

        pattern = req.scan_pattern or req.raster or config.RASTER_PATTERN
        settling_s = (
            req.settling_time_s
            if req.settling_time_s is not None
            else req.settling_s
        )

        params = ScanParams(

            x_start=x_start,

            x_end=x_end,

            x_step=x_step,

            exposure_ms=req.exposure_ms,

            settling_s=settling_s,

            raster=pattern,

            session_name=session,

            number_of_images=req.number_of_images,

            auto_calculate_images=req.auto_calculate_images,

            save_png=req.save_png,

            save_tiff=req.save_tiff,
        )

    except ValueError as exc:

        raise HTTPException(400, str(exc)) from exc

    controller.start_camera_stream()
    controller.set_camera_exposure(req.exposure_ms * 1000.0)

    _system_mode_state = "SCAN"
    _sync_processing_state()

    scan_engine.start(params)

    return {

        "ok": True,

        "session": session,

        "nx": params.nx,

        "ny": params.ny,

        "total_frames": params.total_frames,

        "scan_params": params.as_dict(),
    }


@app.get("/api/scan/start")
async def scan_start_get(
    x_start: float = config.SCAN_START_X_MM,
    x_end: float = config.SCAN_END_X_MM,
    x_step: float = config.SCAN_STEP_X_MM,
    exposure_ms: float = config.EXPOSURE_MS,
    number_of_images: Optional[int] = None,
    session_name: str = "",
):

    return await scan_start(
        ScanStartRequest(
            x_start=x_start,
            x_end=x_end,
            x_step=x_step,
            exposure_ms=exposure_ms,
            number_of_images=number_of_images,
            session_name=session_name,
        )
    )


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

    global _system_mode_state

    scan_engine.stop()
    _system_mode_state = "LIVE"
    _sync_processing_state()

    return {"ok": True}


@app.get("/api/scan/stop")
async def scan_stop_get():

    return await scan_stop()


@app.post("/api/scan/emergency")
async def scan_emergency():

    global _system_mode_state

    scan_engine.emergency_stop()
    _system_mode_state = "LIVE"
    _sync_processing_state()

    return {

        "ok": True,

        "message": "EMERGENCY STOP"
    }


# =============================================================================
# DATASETS
# =============================================================================

@app.get("/api/datasets")
async def list_datasets():

    return data_cube_manager.list_sessions()


@app.get("/api/datasets/{name}/map")
async def get_dataset_map(name: str):

    intensity = data_cube_manager.get_intensity_map(name)

    if intensity is None:

        raise HTTPException(
            404,
            "Dataset not found"
        )

    grey = (intensity * 255).astype(np.uint8)

    colored = cv2.applyColorMap(
        grey,
        cv2.COLORMAP_INFERNO
    )

    _, buf = cv2.imencode(".png", colored)

    return Response(
        content=buf.tobytes(),
        media_type="image/png"
    )


@app.get("/api/datasets/{name}/frame/{yi}/{xi}")
async def get_dataset_frame(
    name: str,
    yi: int,
    xi: int
):

    jpeg = data_cube_manager.get_frame_jpeg(
        name,
        yi,
        xi
    )

    if jpeg is None:

        raise HTTPException(
            404,
            "Frame not found"
        )

    return Response(
        content=jpeg,
        media_type="image/jpeg"
    )


# =============================================================================
# LIVE SPECTRUM
# =============================================================================

@app.get("/api/analysis/spectrum/live")
async def live_spectrum():

    if not _processing_active():
        return {
            "processing_active": False,
            "wavelengths_nm": [],
            "intensity": [],
        }

    wavelengths = np.linspace(

        config.SPECTRAL_MIN_NM,

        config.SPECTRAL_MAX_NM,

        config.SPECTRAL_BANDS
    )

    temp = controller.status_dict()["camera_temp"]

    center = 685 + 14 * np.sin(time.time() / 6.0)

    baseline = 35 + 12 * np.sin(
        wavelengths / 42.0
    )

    peak_a = 420 * np.exp(
        -((wavelengths - center) ** 2) / (2 * 18 ** 2)
    )

    peak_b = 170 * np.exp(
        -((wavelengths - 545) ** 2) / (2 * 38 ** 2)
    )

    spectrum = np.clip(

        baseline
        + peak_a
        + peak_b
        + (temp - 22.0) * 2.0,

        0,

        None
    )

    return {

        "processing_active": True,

        "wavelengths_nm": wavelengths.round(2).tolist(),

        "intensity": spectrum.round(2).tolist(),
    }


class TiffInspectRequest(BaseModel):

    filename: str
    data_base64: str


def _safe_upload_name(filename: str) -> str:

    stem, ext = os.path.splitext(filename or "upload.tiff")
    ext = ext.lower() if ext.lower() in {".tif", ".tiff"} else ".tiff"

    return f"{_safe_session_name(stem)}_{int(time.time())}{ext}"


def _tiff_dimensions(shape: list[int], axes: str) -> dict:

    axes = axes or ""
    height = shape[-2] if len(shape) >= 2 else (shape[0] if shape else 0)
    width = shape[-1] if len(shape) >= 2 else 0

    if "Y" in axes:
        height = shape[axes.index("Y")]
    if "X" in axes:
        width = shape[axes.index("X")]

    spectral_axes = [
        index
        for index, axis in enumerate(axes)
        if axis not in {"Y", "X"}
    ]
    bands = 1
    for index in spectral_axes:
        bands *= int(shape[index])

    if not spectral_axes and len(shape) >= 3:
        bands = int(shape[0])

    return {
        "width": int(width),
        "height": int(height),
        "bands": int(max(1, bands)),
        "axes": axes or "unknown",
        "shape": shape,
    }


def _scale_to_u8(values: np.ndarray) -> tuple[np.ndarray, dict]:

    arr = np.asarray(values, dtype=np.float32)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        finite = np.array([0.0], dtype=np.float32)

    low = float(np.percentile(finite, 1))
    high = float(np.percentile(finite, 99))
    if high <= low:
        low = float(np.min(finite))
        high = float(np.max(finite))
    if high <= low:
        high = low + 1.0

    scaled = np.clip((arr - low) / (high - low), 0, 1)
    return (scaled * 255.0).astype(np.uint8), {
        "display_min": round(low, 4),
        "display_max": round(high, 4),
    }


def _axis_plan(shape: tuple[int, ...], axes: str) -> tuple[int, int, Optional[int]]:

    if axes and "Y" in axes and "X" in axes:
        y_axis = axes.index("Y")
        x_axis = axes.index("X")
        spectral = [
            index
            for index in range(len(shape))
            if index not in {y_axis, x_axis}
        ]
        return y_axis, x_axis, spectral[0] if spectral else None

    if len(shape) >= 3:
        if shape[-1] <= 16 and shape[-2] > 16:
            return 0, 1, 2
        return len(shape) - 2, len(shape) - 1, 0

    return 0, 1, None


def _sample_2d(arr: np.ndarray, axes: str, band_index: Optional[int] = None) -> np.ndarray:

    if arr.ndim == 2:
        plane = arr
    else:
        y_axis, x_axis, spectral_axis = _axis_plan(arr.shape, axes)
        index = [slice(None)] * arr.ndim

        if spectral_axis is not None:
            index[spectral_axis] = (
                int(band_index)
                if band_index is not None
                else arr.shape[spectral_axis] // 2
            )

        for axis in range(arr.ndim):
            if axis not in {y_axis, x_axis, spectral_axis}:
                index[axis] = 0

        plane = arr[tuple(index)]

        remaining_axes = [
            axis
            for axis in range(arr.ndim)
            if isinstance(index[axis], slice)
        ]
        if len(remaining_axes) == 2 and remaining_axes != [y_axis, x_axis]:
            current_y = remaining_axes.index(y_axis)
            current_x = remaining_axes.index(x_axis)
            plane = np.moveaxis(plane, [current_y, current_x], [0, 1])

    while plane.ndim > 2:
        plane = plane[0]

    y_step = max(1, plane.shape[0] // 900)
    x_step = max(1, plane.shape[1] // 1200)
    return np.asarray(plane[::y_step, ::x_step])


def _preview_png(arr: np.ndarray, axes: str) -> tuple[str | None, dict]:

    if arr.ndim >= 3:
        _, _, spectral_axis = _axis_plan(arr.shape, axes)
    else:
        spectral_axis = None

    if spectral_axis is not None and arr.shape[spectral_axis] >= 3:
        band_count = arr.shape[spectral_axis]
        band_indices = [
            max(0, int(round((band_count - 1) * frac)))
            for frac in (0.12, 0.50, 0.88)
        ]
        planes = [_sample_2d(arr, axes, band) for band in band_indices]
        stacked = np.dstack(planes[::-1])
        preview, display = _scale_to_u8(stacked)
        mode = f"false color bands {band_indices[0] + 1}/{band_indices[1] + 1}/{band_indices[2] + 1}"
    else:
        plane = _sample_2d(arr, axes)
        preview, display = _scale_to_u8(plane)
        mode = "single plane"

    ok, buf = cv2.imencode(".png", preview)
    if not ok or buf is None:
        return None, {"preview_mode": mode, **display}

    return base64.b64encode(buf.tobytes()).decode("ascii"), {
        "preview_mode": mode,
        **display,
    }


def _spectral_profile(arr: np.ndarray, axes: str) -> list[float]:

    if arr.ndim < 3:
        return []

    y_axis, x_axis, spectral_axis = _axis_plan(arr.shape, axes)
    if spectral_axis is None:
        return []

    band_count = arr.shape[spectral_axis]
    band_step = max(1, band_count // 512)
    y_step = max(1, arr.shape[y_axis] // 220)
    x_step = max(1, arr.shape[x_axis] // 220)
    profile = []

    for band in range(0, band_count, band_step):
        index = [slice(None)] * arr.ndim
        index[spectral_axis] = band
        index[y_axis] = slice(None, None, y_step)
        index[x_axis] = slice(None, None, x_step)
        for axis in range(arr.ndim):
            if axis not in {y_axis, x_axis, spectral_axis}:
                index[axis] = 0
        sample = np.asarray(arr[tuple(index)], dtype=np.float32)
        profile.append(round(float(np.nanmean(sample)), 4))

    return profile


def _inspect_tiff_path(path: str) -> dict:

    import tifffile

    with tifffile.TiffFile(path) as tif:
        series = tif.series[0]
        shape = list(series.shape)
        axes = getattr(series, "axes", "") or ""
        dtype = str(series.dtype)
        pages = len(tif.pages)

    result = {
        "shape": shape,
        **_tiff_dimensions(shape, axes),
        "dtype": dtype,
        "pages": pages,
        "png_base64": None,
        "profile": [],
        "histogram": [],
        "preview_available": False,
    }

    try:
        try:
            image = tifffile.memmap(path)
        except Exception:
            image = tifffile.imread(path)

        arr = np.asarray(image)
        plane = _sample_2d(arr, axes)
        sample_float = np.asarray(plane, dtype=np.float32)
        min_val = float(np.min(sample_float))
        max_val = float(np.max(sample_float))

        png_base64, preview_meta = _preview_png(arr, axes)
        if png_base64:
            result["png_base64"] = png_base64
            result["preview_available"] = True

        hist, _ = np.histogram(sample_float, bins=64)
        profile = _spectral_profile(arr, axes)
        if not profile:
            center_row = sample_float[sample_float.shape[0] // 2, :]
            step = max(1, len(center_row) // 256)
            profile = center_row[::step].astype(float).round(4).tolist()

        result.update(preview_meta)
        result["profile"] = profile
        result["histogram"] = hist.astype(int).tolist()
        result["min"] = round(min_val, 4)
        result["max"] = round(max_val, 4)
        result["mean"] = round(float(np.mean(sample_float)), 4)
        result["std"] = round(float(np.std(sample_float)), 4)
        result["dynamic_range"] = round(max_val - min_val, 4)
        result["snr_estimate"] = round(
            float(np.mean(sample_float) / max(1e-6, np.std(sample_float))),
            4,
        )

    except Exception as exc:
        log_error(
            "UPLOAD_ERROR",
            RuntimeError(f"TIFF preview skipped for {os.path.basename(path)}: {exc}"),
            severity="WARNING",
        )

    return result


def _inspect_array_payload(arr: np.ndarray, source: str, axes: str = "") -> dict:

    arr = np.asarray(arr)
    if arr.dtype == object:
        raise ValueError("Object arrays are not supported")

    if arr.ndim == 1:
        profile = arr.astype(np.float32)
        hist, _ = np.histogram(profile, bins=64)
        preview_arr = profile.reshape(1, -1)
        png_arr, display = _scale_to_u8(preview_arr)
        ok, buf = cv2.imencode(".png", png_arr)
        png_base64 = base64.b64encode(buf.tobytes()).decode("ascii") if ok else None
        mean = float(np.mean(profile))
        std = float(np.std(profile))
        return {
            "shape": list(arr.shape),
            "width": 1,
            "height": 1,
            "bands": int(arr.shape[0]),
            "axes": "Z",
            "dtype": str(arr.dtype),
            "pages": 1,
            "png_base64": png_base64,
            "profile": profile.round(4).astype(float).tolist(),
            "histogram": hist.astype(int).tolist(),
            "preview_available": bool(png_base64),
            "preview_mode": source,
            "min": round(float(np.min(profile)), 4),
            "max": round(float(np.max(profile)), 4),
            "mean": round(mean, 4),
            "std": round(std, 4),
            "dynamic_range": round(float(np.max(profile) - np.min(profile)), 4),
            "snr_estimate": round(mean / max(1e-6, std), 4),
            **display,
        }

    shape = list(arr.shape)
    if not axes:
        axes = "ZYX" if arr.ndim >= 3 else "YX"
    plane = _sample_2d(arr, axes)
    plane_float = np.asarray(plane, dtype=np.float32)
    hist, _ = np.histogram(plane_float, bins=64)
    png_base64, preview_meta = _preview_png(arr, axes)
    profile = _spectral_profile(arr, axes)
    if not profile:
        center = plane_float[plane_float.shape[0] // 2]
        step = max(1, len(center) // 256)
        profile = center[::step].astype(float).round(4).tolist()
    mean = float(np.mean(plane_float))
    std = float(np.std(plane_float))
    return {
        "shape": shape,
        **_tiff_dimensions(shape, axes),
        "dtype": str(arr.dtype),
        "pages": 1,
        "png_base64": png_base64,
        "profile": profile,
        "histogram": hist.astype(int).tolist(),
        "preview_available": bool(png_base64),
        "source_format": source,
        "min": round(float(np.min(plane_float)), 4),
        "max": round(float(np.max(plane_float)), 4),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "dynamic_range": round(float(np.max(plane_float) - np.min(plane_float)), 4),
        "snr_estimate": round(mean / max(1e-6, std), 4),
        **preview_meta,
    }


def _parse_envi_header(path: str) -> dict:

    meta: dict[str, str] = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.upper() == "ENVI" or "=" not in line:
                continue
            key, value = line.split("=", 1)
            meta[key.strip().lower()] = value.strip().strip("{}")
    return meta


def _inspect_envi_pair(hdr_path: str, data_path: str) -> dict:

    hdr = _parse_envi_header(hdr_path)
    samples = int(hdr.get("samples", 0))
    lines = int(hdr.get("lines", 0))
    bands = int(hdr.get("bands", 0))
    if not samples or not lines or not bands:
        raise ValueError("ENVI header missing samples/lines/bands")

    dtype_map = {
        "1": np.uint8,
        "2": np.int16,
        "3": np.int32,
        "4": np.float32,
        "5": np.float64,
        "12": np.uint16,
        "13": np.uint32,
        "14": np.int64,
        "15": np.uint64,
    }
    dtype = dtype_map.get(str(hdr.get("data type", "")).strip())
    if dtype is None:
        raise ValueError(f"Unsupported ENVI data type {hdr.get('data type')}")
    if hdr.get("byte order", "0").strip() == "1":
        dtype = np.dtype(dtype).newbyteorder(">")

    offset = int(hdr.get("header offset", 0) or 0)
    interleave = hdr.get("interleave", "bsq").strip().lower()
    if interleave == "bsq":
        shape = (bands, lines, samples)
        axes = "ZYX"
    elif interleave == "bil":
        shape = (lines, bands, samples)
        axes = "YZX"
    elif interleave == "bip":
        shape = (lines, samples, bands)
        axes = "YXZ"
    else:
        raise ValueError(f"Unsupported ENVI interleave {interleave}")

    arr = np.memmap(data_path, dtype=dtype, mode="r", offset=offset, shape=shape)
    metadata = _inspect_array_payload(arr, "ENVI", axes=axes)
    metadata["envi"] = {
        "interleave": interleave,
        "samples": samples,
        "lines": lines,
        "bands": bands,
    }
    return metadata


def _write_analysis_session(
    upload_dir: str,
    session_name: str,
    original_filename: str,
    source_files: list[str],
    total_bytes: int,
    metadata: dict,
) -> dict:

    metadata_path = os.path.join(upload_dir, "metadata.json")
    preview_path = os.path.join(upload_dir, "preview.png")

    if metadata.get("png_base64"):
        try:
            with open(preview_path, "wb") as preview:
                preview.write(base64.b64decode(metadata["png_base64"]))
        except Exception as exc:
            log_error("UPLOAD_ERROR", exc, severity="WARNING")

    metadata_for_disk = dict(metadata)
    metadata_for_disk.pop("png_base64", None)

    session_metadata = {
        "session_name": session_name,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "state": "ANALYSIS_READY",
        "source_file": os.path.basename(source_files[0]) if source_files else "",
        "source_files": [os.path.basename(path) for path in source_files],
        "original_filename": original_filename,
        "bytes": total_bytes,
        "frames_acquired": int(metadata.get("bands") or metadata.get("pages") or 1),
        "nx": int(metadata.get("width") or 0),
        "ny": int(metadata.get("height") or 0),
        "wavelength_min_nm": config.SPECTRAL_MIN_NM,
        "wavelength_max_nm": config.SPECTRAL_MAX_NM,
        "spectral_bands": int(metadata.get("bands") or config.SPECTRAL_BANDS),
        "analysis": metadata_for_disk,
        "frames": [
            {
                "tiff": os.path.basename(source_files[0]) if source_files else None,
                "preview": "preview.png" if metadata.get("png_base64") else None,
                "intensity_mean": metadata.get("mean"),
            }
        ],
    }
    with open(metadata_path, "w", encoding="utf-8") as fh:
        json.dump(session_metadata, fh, indent=2)

    return session_metadata


async def _save_upload_stream(file: UploadFile, target_path: str, max_bytes: int) -> int:

    size = 0
    with open(target_path, "wb") as fh:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(413, "Upload exceeds 500 MB limit")
            fh.write(chunk)
    return size


async def _analysis_upload_impl(files: list[UploadFile]) -> dict:

    global _system_mode_state

    if not files:
        raise HTTPException(400, "No file uploaded")

    root = _normalise_save_folder(config.SAVE_FOLDER)
    primary_name = files[0].filename or "upload"
    session_name = f"analysis_{_safe_session_name(os.path.splitext(primary_name)[0])}_{int(time.time())}"
    upload_dir = os.path.join(root, session_name)
    os.makedirs(upload_dir, exist_ok=True)
    saved: dict[str, str] = {}
    total_size = 0

    try:
        for file in files:
            filename = file.filename or "upload.bin"
            ext = os.path.splitext(filename)[1].lower()
            if ext not in {".tif", ".tiff", ".npy", ".csv", ".hdr", ".img", ".dat"}:
                raise HTTPException(400, f"Unsupported file format: {ext}")
            safe_name = (
                f"source{ext}"
                if ext in {".tif", ".tiff", ".npy", ".csv", ".hdr"}
                else _safe_session_name(filename)
            )
            target = os.path.join(upload_dir, safe_name)
            total_size += await _save_upload_stream(file, target, _MAX_TIFF_UPLOAD_BYTES)
            saved[ext] = target

        if ".tif" in saved or ".tiff" in saved:
            source_path = saved.get(".tif") or saved[".tiff"]
            metadata = _inspect_tiff_path(source_path)
        elif ".npy" in saved:
            arr = np.load(saved[".npy"], mmap_mode="r", allow_pickle=False)
            metadata = _inspect_array_payload(arr, "NPY")
        elif ".csv" in saved:
            try:
                arr = np.loadtxt(saved[".csv"], delimiter=",")
            except Exception:
                arr = np.loadtxt(saved[".csv"])
            metadata = _inspect_array_payload(arr, "CSV spectral")
        elif ".hdr" in saved:
            data_path = saved.get(".img") or saved.get(".dat")
            if not data_path:
                candidates = [
                    os.path.join(upload_dir, name)
                    for name in os.listdir(upload_dir)
                    if os.path.splitext(name)[1].lower() in {".img", ".dat"}
                ]
                data_path = candidates[0] if candidates else None
            if not data_path:
                raise HTTPException(400, "ENVI upload requires .hdr plus .img/.dat data file")
            metadata = _inspect_envi_pair(saved[".hdr"], data_path)
        else:
            raise HTTPException(400, "Upload must include TIFF, NPY, CSV, or ENVI HDR")

        source_files = list(saved.values())
        _write_analysis_session(
            upload_dir,
            session_name,
            primary_name,
            source_files,
            total_size,
            metadata,
        )

        _system_mode_state = "ANALYSIS"
        _sync_processing_state()

        return {
            "ok": True,
            "filename": primary_name,
            "session": session_name,
            "stored_as": [os.path.relpath(path, root) for path in source_files],
            "bytes": total_size,
            "metadata": metadata,
            "png_base64": metadata.get("png_base64"),
            "profile": metadata.get("profile", []),
            "histogram": metadata.get("histogram", []),
        }

    except HTTPException:
        try:
            for name in os.listdir(upload_dir):
                os.remove(os.path.join(upload_dir, name))
            os.rmdir(upload_dir)
        except Exception:
            pass
        raise

    except Exception as exc:
        log_error("UPLOAD_ERROR", exc)
        try:
            for name in os.listdir(upload_dir):
                os.remove(os.path.join(upload_dir, name))
            os.rmdir(upload_dir)
        except Exception:
            pass
        raise HTTPException(400, f"Upload analysis failed: {exc}") from exc

    finally:
        for file in files:
            try:
                await file.close()
            except Exception:
                pass


@app.post("/api/analysis/tiff/upload")
async def upload_tiff(file: UploadFile = File(...)):

    filename = file.filename or "upload.tiff"
    if not filename.lower().endswith((".tif", ".tiff")):
        raise HTTPException(400, "Only .tif and .tiff files are supported")
    return await _analysis_upload_impl([file])


@app.post("/api/analysis/upload")
async def upload_analysis(files: list[UploadFile] = File(...)):

    return await _analysis_upload_impl(files)


@app.post("/api/analysis/tiff/inspect")
async def inspect_tiff(req: TiffInspectRequest):

    global _system_mode_state

    try:
        if len(req.data_base64) > 25 * 1024 * 1024:
            raise HTTPException(413, "Use streaming TIFF upload for large files")

        import tifffile

        raw = base64.b64decode(req.data_base64)
        with tifffile.TiffFile(io.BytesIO(raw)) as tif:
            series = tif.series[0]
            axes = getattr(series, "axes", "") or ""
            dtype = str(series.dtype)
            pages = len(tif.pages)
            arr = np.asarray(series.asarray())

        plane = _sample_2d(arr, axes)
        arr_float = np.asarray(plane, dtype=np.float32)
        min_val = float(np.min(arr_float))
        max_val = float(np.max(arr_float))
        hist, _ = np.histogram(arr_float, bins=64)
        png_base64, preview_meta = _preview_png(arr, axes)

        _system_mode_state = "ANALYSIS"

        return {
            "ok": True,
            "filename": req.filename,
            "metadata": {
                "shape": list(arr.shape),
                **_tiff_dimensions(list(arr.shape), axes),
                "dtype": dtype,
                "pages": pages,
                "min": round(min_val, 4),
                "max": round(max_val, 4),
                "mean": round(float(np.mean(arr_float)), 4),
                "std": round(float(np.std(arr_float)), 4),
                "histogram": hist.astype(int).tolist(),
                **preview_meta,
            },
            "png_base64": png_base64,
            "profile": _spectral_profile(arr, axes),
            "histogram": hist.astype(int).tolist(),
        }

    except HTTPException:
        raise

    except Exception as exc:
        log_error("SYSTEM_ERROR", exc)
        raise HTTPException(400, f"TIFF could not be decoded: {exc}") from exc


# =============================================================================
# WEBSOCKET
# =============================================================================

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

    interval = 1.0 / max(
        1,
        config.WS_BROADCAST_HZ
    )

    while True:

        try:
            await asyncio.sleep(interval)

            if not _ws_clients:
                continue

            events = []

            while not scan_engine.event_queue.empty():

                try:

                    events.append(
                        scan_engine.event_queue.get_nowait()
                    )

                except Exception as exc:
                    log_error("SYSTEM_ERROR", exc)
                    break

            payload = {

                "type": "telemetry",

                "timestamp": time.time(),

                "hardware": controller.status_dict(),

                "scan": scan_engine.progress_dict(),

                "system": {
                    "control_mode": _system_mode_state,
                    "processing_active": _sync_processing_state(),
                    "live_processing_enabled": _live_processing_enabled,
                    "error_count": len(get_recent_errors()),
                },

                "events": events,
            }

            dead = set()

            for ws in list(_ws_clients):

                try:

                    await ws.send_json(payload)

                except Exception:

                    dead.add(ws)

            _ws_clients.difference_update(dead)

        except Exception as exc:
            log_error("SYSTEM_ERROR", exc)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "server_enhanced:app",

        host=config.SERVER_HOST,

        port=config.SERVER_PORT,

        reload=False,
    )
