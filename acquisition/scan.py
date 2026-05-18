# =============================================================================
# HSI-Core - Scan Engine
# =============================================================================
# Background scan orchestrator for a single physical X stage.
# Supports START / PAUSE / RESUME / STOP / EMERGENCY state transitions and
# emits scan telemetry for the WebSocket loop.
# =============================================================================

from __future__ import annotations

import json
import queue
import threading
import time
from enum import Enum
from typing import Optional

import numpy as np

import config


class ScanState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    EMERGENCY = "EMERGENCY"


class ScanParams:
    def __init__(
        self,
        x_start: float,
        x_end: float,
        x_step: float,
        exposure_ms: float = config.EXPOSURE_MS,
        settling_s: float = config.SETTLING_TIME_S,
        raster: str = config.RASTER_PATTERN,
        session_name: str = "",
        y_start: float = 0.0,
        y_end: float = 0.0,
        y_step: float = 1.0,
    ):
        if x_step <= 0:
            raise ValueError("Step size must be positive")
        if y_step <= 0:
            raise ValueError("Y step size must be positive")
        if x_end < x_start:
            raise ValueError("End position must be >= start position")
        if not (config.STAGE_X_MIN_MM <= x_start <= config.STAGE_X_MAX_MM):
            raise ValueError("Start position is outside stage limits")
        if not (config.STAGE_X_MIN_MM <= x_end <= config.STAGE_X_MAX_MM):
            raise ValueError("End position is outside stage limits")
        if raster not in ("raster", "serpentine", "grid"):
            raise ValueError("Scan pattern must be raster or serpentine")

        self.x_start = x_start
        self.x_end = x_end
        self.x_step = x_step
        self.y_start = y_start
        self.y_end = y_end
        self.y_step = y_step
        self.exposure_ms = exposure_ms
        self.settling_s = settling_s
        self.raster = "raster" if raster == "grid" else raster
        self.session_name = session_name

    @property
    def nx(self) -> int:
        return max(1, int(round((self.x_end - self.x_start) / self.x_step)) + 1)

    @property
    def ny(self) -> int:
        return 1

    @property
    def total_frames(self) -> int:
        return self.nx


class ScanEngine:
    def __init__(self, controller):
        self._ctrl = controller
        self.state = ScanState.IDLE
        self.event_queue = queue.Queue()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event = threading.Event()

        self._params: Optional[ScanParams] = None
        self._thread: Optional[threading.Thread] = None

        self._lock = threading.Lock()
        self._frames_done = 0
        self._cur_xi = 0
        self._cur_yi = 0
        self._start_time: Optional[float] = None

    def start(self, params: ScanParams):
        if self.state != ScanState.IDLE:
            raise RuntimeError(f"Cannot start - engine is {self.state}")

        self._params = params
        self._frames_done = 0
        self._cur_xi = 0
        self._cur_yi = 0
        self._stop_event.clear()
        self._pause_event.set()
        self.state = ScanState.RUNNING
        self._start_time = time.time()

        self._thread = threading.Thread(target=self._run_scan, daemon=True)
        self._thread.start()

    def pause(self):
        if self.state == ScanState.RUNNING:
            self._pause_event.clear()
            self.state = ScanState.PAUSED
            self._log("Scan paused by operator")

    def resume(self):
        if self.state == ScanState.PAUSED:
            self._pause_event.set()
            self.state = ScanState.RUNNING
            self._log("Scan resumed")

    def stop(self):
        if self.state in (ScanState.RUNNING, ScanState.PAUSED):
            self._stop_event.set()
            self._pause_event.set()
            self.state = ScanState.STOPPING
            self._log("Scan stop requested")

    def emergency_stop(self):
        self.state = ScanState.EMERGENCY
        self._stop_event.set()
        self._pause_event.set()
        self._log("EMERGENCY STOP ACTIVATED")

    def progress_dict(self) -> dict:
        with self._lock:
            done = self._frames_done
            xi = self._cur_xi
            yi = self._cur_yi

        total = self._params.total_frames if self._params else 1
        pct = round(100.0 * done / total, 1) if total else 0.0

        elapsed = time.time() - self._start_time if self._start_time else 0
        eta_s = 0
        if done > 0 and total > done:
            eta_s = int(elapsed / done * (total - done))

        return {
            "state": self.state,
            "frames_done": done,
            "total_frames": total,
            "percent": pct,
            "eta_seconds": eta_s,
            "cur_xi": xi,
            "cur_yi": yi,
            "nx": self._params.nx if self._params else 0,
            "ny": self._params.ny if self._params else 0,
            "session_name": self._params.session_name if self._params else "",
        }

    def _run_scan(self):
        p = self._params
        import cv2
        import os
        import tifffile
        from acquisition.data_cube import data_cube_manager

        session_path = os.path.join(config.SAVE_FOLDER, p.session_name)
        os.makedirs(session_path, exist_ok=True)
        metadata_path = os.path.join(session_path, "metadata.json")

        metadata = {
            "session_name": p.session_name,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "state": "RUNNING",
            "x_start_mm": p.x_start,
            "x_end_mm": p.x_end,
            "x_step_mm": p.x_step,
            "nx": p.nx,
            "ny": p.ny,
            "total_frames": p.total_frames,
            "frames_acquired": 0,
            "exposure_ms": p.exposure_ms,
            "settling_s": p.settling_s,
            "raster": p.raster,
            "wavelength_min_nm": config.SPECTRAL_MIN_NM,
            "wavelength_max_nm": config.SPECTRAL_MAX_NM,
            "spectral_bands": config.SPECTRAL_BANDS,
            "image_format": "tiff",
            "mock_mode": config.MOCK_MODE,
        }
        with open(metadata_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2)

        self._log(f"Scan started: {p.nx} positions = {p.total_frames} frames")
        self._log(f"Session: {p.session_name}")

        frame_idx = 0

        try:
            for xi in range(p.nx):
                self._pause_event.wait()

                if self._stop_event.is_set():
                    self._finish("STOPPED")
                    return

                yi = 0
                x_mm = p.x_start + xi * p.x_step

                self._ctrl.move_and_wait(x_mm)
                time.sleep(p.settling_s)

                raw = self._ctrl.capture_frame()
                h, w = raw.shape[:2]
                crop = raw[h//4:3*h//4, w//4:3*w//4]
                intensity = float(np.mean(crop))

                frame_meta = {
                    "frame_index": frame_idx,
                    "x_index": xi,
                    "y_index": yi,
                    "x_mm": round(x_mm, 6),
                    "exposure_ms": p.exposure_ms,
                    "wavelength_min_nm": config.SPECTRAL_MIN_NM,
                    "wavelength_max_nm": config.SPECTRAL_MAX_NM,
                    "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                }

                tiff_name = os.path.join(
                    session_path,
                    f"frame_{frame_idx:05d}_y{yi:04d}_x{xi:04d}.tiff",
                )
                tifffile.imwrite(tiff_name, raw, metadata=frame_meta)

                preview_name = os.path.join(
                    session_path,
                    f"frame_{frame_idx:05d}_y{yi:04d}_x{xi:04d}.png",
                )
                cv2.imwrite(preview_name, raw)

                data_cube_manager.record_frame(
                    session=p.session_name,
                    xi=xi,
                    yi=yi,
                    intensity=intensity,
                    nx=p.nx,
                    ny=p.ny,
                )

                with self._lock:
                    self._frames_done = frame_idx + 1
                    self._cur_xi = xi
                    self._cur_yi = yi

                self.event_queue.put({
                    "type": "frame",
                    "frame_idx": frame_idx,
                    "xi": xi,
                    "yi": yi,
                    "x_mm": round(x_mm, 4),
                    "intensity": round(intensity, 2),
                    "nx": p.nx,
                    "ny": p.ny,
                })

                frame_idx += 1
                if frame_idx % 10 == 0 or frame_idx == p.total_frames:
                    metadata["frames_acquired"] = frame_idx
                    with open(metadata_path, "w", encoding="utf-8") as fh:
                        json.dump(metadata, fh, indent=2)

        except Exception as exc:
            self._log(f"Scan failed: {exc}")
            self._finish("FAILED")
            return

        self._finish("COMPLETED")

    def _finish(self, reason: str):
        p = self._params
        if p:
            import os
            session_path = os.path.join(config.SAVE_FOLDER, p.session_name)
            metadata_path = os.path.join(session_path, "metadata.json")
            if os.path.isfile(metadata_path):
                try:
                    with open(metadata_path, encoding="utf-8") as fh:
                        metadata = json.load(fh)
                    metadata["state"] = reason
                    metadata["frames_acquired"] = self._frames_done
                    metadata["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                    with open(metadata_path, "w", encoding="utf-8") as fh:
                        json.dump(metadata, fh, indent=2)
                except Exception:
                    pass
        self.state = ScanState.IDLE
        self._start_time = None
        self._log(f"Scan finished: {reason}")

    def _log(self, msg: str):
        self.event_queue.put({"type": "log", "message": msg})
