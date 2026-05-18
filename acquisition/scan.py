# =============================================================================
# HSI-Core - Scan Engine
# =============================================================================
# Background scan orchestrator for a single physical X stage.
# Uses integer stage units for scan positions to avoid cumulative drift.
# =============================================================================

from __future__ import annotations

import json
import os
import queue
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import numpy as np

import config
from acquisition.error_logger import log_error


class ScanState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


def _mm_to_units(value_mm: float) -> int:
    return int(round(value_mm * config.UNITS_PER_MM))


def _units_to_mm(value_units: int) -> float:
    return round(value_units / config.UNITS_PER_MM, 4)


def _iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _safe_timestamp(value: str) -> str:
    return (
        value.replace(":", "-")
        .replace("+", "p")
        .replace("-", "-", 2)
    )


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
        number_of_images: Optional[int] = None,
        auto_calculate_images: bool = True,
        save_png: bool = True,
        save_tiff: bool = True,
    ):
        if x_step <= 0:
            raise ValueError("Step size must be positive")
        if x_end < x_start:
            raise ValueError("End position must be >= start position")
        if exposure_ms <= 0:
            raise ValueError("Exposure must be positive")
        if settling_s < 0:
            raise ValueError("Settling time cannot be negative")
        if not (config.STAGE_X_MIN_MM <= x_start <= config.STAGE_X_MAX_MM):
            raise ValueError("Start position is outside stage limits")
        if not (config.STAGE_X_MIN_MM <= x_end <= config.STAGE_X_MAX_MM):
            raise ValueError("End position is outside stage limits")
        if raster not in ("raster", "serpentine", "grid"):
            raise ValueError("Scan pattern must be raster or serpentine")

        self.x_start = round(x_start, 4)
        self.x_end = round(x_end, 4)
        self.x_step = round(x_step, 4)
        self.exposure_ms = exposure_ms
        self.settling_s = settling_s
        self.raster = "raster" if raster == "grid" else raster
        self.session_name = session_name
        self.save_png = save_png
        self.save_tiff = save_tiff

        auto_count = int(round((self.x_end - self.x_start) / self.x_step)) + 1
        if number_of_images and number_of_images > 0 and not auto_calculate_images:
            self.number_of_images = int(number_of_images)
            if self.number_of_images == 1:
                self.x_step = 0.0
            else:
                self.x_step = round((self.x_end - self.x_start) / (self.number_of_images - 1), 4)
        else:
            self.number_of_images = max(1, auto_count)

        self.start_units = _mm_to_units(self.x_start)
        self.end_units = _mm_to_units(self.x_end)
        self.step_units = max(1, _mm_to_units(self.x_step)) if self.number_of_images > 1 else 0

        if self.number_of_images == 1:
            self.positions_units = [self.start_units]
        else:
            self.positions_units = [
                self.start_units + idx * self.step_units
                for idx in range(self.number_of_images)
            ]
            self.positions_units[-1] = self.end_units

    @property
    def nx(self) -> int:
        return len(self.positions_units)

    @property
    def ny(self) -> int:
        return 1

    @property
    def total_frames(self) -> int:
        return len(self.positions_units)

    def as_dict(self) -> dict:
        return {
            "session_name": self.session_name,
            "start_position_mm": self.x_start,
            "end_position_mm": self.x_end,
            "step_size_mm": self.x_step,
            "number_of_images": self.number_of_images,
            "exposure_ms": self.exposure_ms,
            "settling_time_s": self.settling_s,
            "scan_pattern": self.raster,
            "save_png": self.save_png,
            "save_tiff": self.save_tiff,
        }


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
        self._current_position_mm = 0.0
        self._start_time: Optional[float] = None
        self._last_reason = ""
        self._last_error = ""
        self._last_failed_index: Optional[int] = None

    def start(self, params: ScanParams):
        if self.state in (ScanState.RUNNING, ScanState.PAUSED):
            raise RuntimeError(f"Cannot start - engine is {self.state.value}")

        self._params = params
        self._frames_done = 0
        self._cur_xi = 0
        self._cur_yi = 0
        self._current_position_mm = params.x_start
        self._last_reason = ""
        self._last_error = ""
        self._last_failed_index = None
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
            self._log("Scan paused")

    def resume(self):
        if self.state == ScanState.PAUSED:
            self._pause_event.set()
            self.state = ScanState.RUNNING
            self._log("Scan resumed")

    def stop(self):
        if self.state in (ScanState.RUNNING, ScanState.PAUSED):
            self._stop_event.set()
            self._pause_event.set()
            self._log("Scan stop requested")
        elif self.state == ScanState.IDLE:
            self.state = ScanState.STOPPED

    def emergency_stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.state = ScanState.ERROR
        self._last_reason = "EMERGENCY"
        self._log("EMERGENCY STOP ACTIVATED")

    def progress_dict(self) -> dict:
        with self._lock:
            done = self._frames_done
            xi = self._cur_xi
            yi = self._cur_yi
            pos = self._current_position_mm

        total = self._params.total_frames if self._params else 0
        pct = round(100.0 * done / total, 1) if total else 0.0

        elapsed = time.time() - self._start_time if self._start_time else 0
        eta_s = 0
        if done > 0 and total > done:
            eta_s = int(elapsed / done * (total - done))

        return {
            "state": self.state.value,
            "frames_done": done,
            "total_frames": total,
            "percent": pct,
            "eta_seconds": eta_s,
            "cur_xi": xi,
            "cur_yi": yi,
            "current_position_mm": pos,
            "nx": self._params.nx if self._params else 0,
            "ny": self._params.ny if self._params else 0,
            "session_name": self._params.session_name if self._params else "",
            "last_reason": self._last_reason,
            "last_error": self._last_error,
            "last_failed_index": self._last_failed_index,
            "resume_from_index": done,
        }

    def _run_scan(self):
        p = self._params
        if p is None:
            return

        try:
            import cv2
            import tifffile
            from acquisition.data_cube import data_cube_manager

            session_path = os.path.join(config.SAVE_FOLDER, p.session_name)
            os.makedirs(session_path, exist_ok=True)
            metadata_path = os.path.join(session_path, "metadata.json")

            metadata = {
                "session_name": p.session_name,
                "started_at": _iso_now(),
                "state": "RUNNING",
                "scan_params": p.as_dict(),
                "wavelength_min_nm": config.SPECTRAL_MIN_NM,
                "wavelength_max_nm": config.SPECTRAL_MAX_NM,
                "spectral_bands": config.SPECTRAL_BANDS,
                "frames_acquired": 0,
                "frames": [],
                "mock_mode": config.MOCK_MODE,
            }
            self._write_json(metadata_path, metadata)
        except Exception as exc:
            log_error("SCAN_ERROR", exc)
            self._last_error = str(exc)
            self._last_reason = "STARTUP_ERROR"
            self.state = ScanState.PAUSED
            self._pause_event.clear()
            self._log(f"Scan paused during startup: {exc}")
            return

        self._log(f"Scan started: {p.total_frames} images")
        self._log(f"Session: {p.session_name}")

        scan_index = 0
        while scan_index < len(p.positions_units):
            self._pause_event.wait()

            if self._stop_event.is_set():
                self._finish("STOPPED", metadata_path)
                return

            position_units = p.positions_units[scan_index]
            position_mm = _units_to_mm(position_units)

            with self._lock:
                self._cur_xi = scan_index
                self._cur_yi = 0
                self._current_position_mm = position_mm

            try:
                self._ctrl.move_and_wait(position_mm)
                time.sleep(p.settling_s)

                raw = self._ctrl.capture_frame()
                timestamp = _iso_now()
                safe_time = _safe_timestamp(timestamp)
                file_stem = (
                    f"{p.session_name}_img_{scan_index + 1:04d}_"
                    f"{position_mm:.4f}mm_{safe_time}"
                )

                frame_meta = {
                    "timestamp": timestamp,
                    "position_mm": position_mm,
                    "scan_index": scan_index,
                    "session_name": p.session_name,
                    "exposure_ms": p.exposure_ms,
                    "scan_params": p.as_dict(),
                }

                tiff_name = None
                png_name = None

                if p.save_tiff:
                    tiff_name = os.path.join(session_path, f"{file_stem}.tiff")
                    tifffile.imwrite(tiff_name, raw, metadata=frame_meta)

                if p.save_png:
                    png_name = os.path.join(session_path, f"{file_stem}.png")
                    cv2.imwrite(png_name, raw)

                sidecar_name = os.path.join(session_path, f"{file_stem}.json")
                self._write_json(sidecar_name, frame_meta)

                h, w = raw.shape[:2]
                crop = raw[h//4:3*h//4, w//4:3*w//4]
                intensity = float(np.mean(crop))

                data_cube_manager.record_frame(
                    session=p.session_name,
                    xi=scan_index,
                    yi=0,
                    intensity=intensity,
                    nx=p.nx,
                    ny=p.ny,
                )

                with self._lock:
                    self._frames_done = scan_index + 1
                    self._cur_xi = scan_index
                    self._cur_yi = 0
                    self._current_position_mm = position_mm

                metadata["state"] = "RUNNING"
                metadata["frames_acquired"] = scan_index + 1
                metadata["last_position_mm"] = position_mm
                metadata["frames"].append({
                    **frame_meta,
                    "intensity_mean": round(intensity, 4),
                    "tiff": os.path.basename(tiff_name) if tiff_name else None,
                    "png": os.path.basename(png_name) if png_name else None,
                    "metadata": os.path.basename(sidecar_name),
                })

                if (scan_index + 1) % 5 == 0 or scan_index + 1 == p.total_frames:
                    self._write_json(metadata_path, metadata)

                self.event_queue.put({
                    "type": "frame",
                    "frame_idx": scan_index,
                    "xi": scan_index,
                    "yi": 0,
                    "x_mm": position_mm,
                    "position_mm": position_mm,
                    "intensity": round(intensity, 2),
                    "nx": p.nx,
                    "ny": p.ny,
                })

                scan_index += 1

            except Exception as exc:
                self._pause_after_error(
                    exc,
                    metadata_path,
                    metadata,
                    scan_index,
                    position_mm,
                )

        self._finish("STOPPED", metadata_path, reason="COMPLETED")

    def _pause_after_error(
        self,
        exc: Exception,
        metadata_path: str,
        metadata: dict,
        scan_index: int,
        position_mm: float,
    ):
        log_error("SCAN_ERROR", RuntimeError(
            f"Step {scan_index + 1} at {position_mm:.4f} mm failed: {exc}"
        ))

        self._last_failed_index = scan_index
        self._last_error = str(exc)
        self._last_reason = "PAUSED_AFTER_ERROR"
        self.state = ScanState.PAUSED
        self._pause_event.clear()

        metadata["state"] = self.state.value
        metadata["reason"] = self._last_reason
        metadata["last_failed_index"] = scan_index
        metadata["last_position_mm"] = position_mm
        metadata["error"] = self._last_error

        try:
            self._write_json(metadata_path, metadata)
        except Exception as write_error:
            log_error("SCAN_ERROR", write_error)

        self._log(
            f"Scan paused at image {scan_index + 1} "
            f"({position_mm:.4f} mm): {exc}"
        )
        self.event_queue.put({
            "type": "error",
            "module": "SCAN_ERROR",
            "message": self._last_error,
            "scan_index": scan_index,
            "position_mm": position_mm,
        })

    def _finish(self, state: str, metadata_path: str, reason: str = ""):
        self.state = ScanState.ERROR if state == "ERROR" else ScanState.STOPPED
        self._last_reason = reason or state
        self._start_time = None

        if os.path.isfile(metadata_path):
            try:
                with open(metadata_path, encoding="utf-8") as fh:
                    metadata = json.load(fh)
                metadata["state"] = self.state.value
                metadata["reason"] = self._last_reason
                metadata["frames_acquired"] = self._frames_done
                metadata["finished_at"] = _iso_now()
                if self._last_error:
                    metadata["error"] = self._last_error
                self._write_json(metadata_path, metadata)
            except Exception as exc:
                log_error("SCAN_ERROR", exc)

        self._log(f"Scan finished: {self._last_reason}")

    def _write_json(self, path: str, payload: dict):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def _log(self, msg: str):
        self.event_queue.put({"type": "log", "message": msg})
