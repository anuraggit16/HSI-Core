# =============================================================================
# HSI-Core — Scan Engine
# =============================================================================
# Stateful 2-D raster scan orchestrator. Runs in a background daemon thread.
# Supports START / PAUSE / RESUME / STOP / EMERGENCY_STOP state transitions.
# Emits telemetry events to an external queue for WebSocket broadcast.
# =============================================================================

from __future__ import annotations

import queue
import threading
import time
from enum import Enum
from typing import Optional

import numpy as np

import config

# =============================================================================
# SCAN STATE MACHINE
# =============================================================================

class ScanState(str, Enum):
    IDLE      = "IDLE"
    RUNNING   = "RUNNING"
    PAUSED    = "PAUSED"
    STOPPING  = "STOPPING"
    EMERGENCY = "EMERGENCY"


# =============================================================================
# SCAN PARAMETERS (validated before use)
# =============================================================================

class ScanParams:
    def __init__(
        self,
        x_start: float, x_end: float, x_step: float,
        y_start: float, y_end: float, y_step: float,
        exposure_ms: float,
        settling_s: float,
        raster: str,
        session_name: str,
    ):
        if x_step <= 0 or y_step <= 0:
            raise ValueError("Step sizes must be positive")
        if x_end < x_start or y_end < y_start:
            raise ValueError("End position must be >= start position")

        self.x_start     = x_start
        self.x_end       = x_end
        self.x_step      = x_step
        self.y_start     = y_start
        self.y_end       = y_end
        self.y_step      = y_step
        self.exposure_ms = exposure_ms
        self.settling_s  = settling_s
        self.raster      = raster          # "serpentine" | "grid"
        self.session_name = session_name

    @property
    def nx(self) -> int:
        return max(1, int(round((self.x_end - self.x_start) / self.x_step)) + 1)

    @property
    def ny(self) -> int:
        return max(1, int(round((self.y_end - self.y_start) / self.y_step)) + 1)

    @property
    def total_frames(self) -> int:
        return self.nx * self.ny


# =============================================================================
# SCAN ENGINE
# =============================================================================

class ScanEngine:

    def __init__(self, controller):
        self._ctrl        = controller
        self.state        = ScanState.IDLE
        self.event_queue  = queue.Queue()   # consumed by WS broadcast loop
        self._pause_event = threading.Event()
        self._pause_event.set()             # "not paused" by default
        self._stop_event  = threading.Event()

        self._params      : Optional[ScanParams] = None
        self._thread      : Optional[threading.Thread] = None

        # Mutable progress (read by API from any thread)
        self._lock       = threading.Lock()
        self._frames_done = 0
        self._cur_xi     = 0
        self._cur_yi     = 0
        self._start_time : Optional[float] = None

    # ------------------------------------------------------------------
    # PUBLIC CONTROL API
    # ------------------------------------------------------------------

    def start(self, params: ScanParams):
        if self.state != ScanState.IDLE:
            raise RuntimeError(f"Cannot start — engine is {self.state}")

        self._params       = params
        self._frames_done  = 0
        self._cur_xi       = 0
        self._cur_yi       = 0
        self._stop_event.clear()
        self._pause_event.set()
        self.state         = ScanState.RUNNING
        self._start_time   = time.time()

        self._thread = threading.Thread(
            target=self._run_scan, daemon=True
        )
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
            self._pause_event.set()   # unblock if paused
            self.state = ScanState.STOPPING
            self._log("Scan stop requested")

    def emergency_stop(self):
        """Immediately mark as emergency — bypasses state machine."""
        self.state = ScanState.EMERGENCY
        self._stop_event.set()
        self._pause_event.set()
        self._log("⚠ EMERGENCY STOP ACTIVATED")

    # ------------------------------------------------------------------
    # PROGRESS / STATUS (thread-safe reads)
    # ------------------------------------------------------------------

    def progress_dict(self) -> dict:
        with self._lock:
            done  = self._frames_done
            xi    = self._cur_xi
            yi    = self._cur_yi

        total = self._params.total_frames if self._params else 1
        pct   = round(100.0 * done / total, 1) if total else 0.0

        elapsed = time.time() - self._start_time if self._start_time else 0
        eta_s   = 0
        if done > 0 and total > done:
            eta_s = int(elapsed / done * (total - done))

        return {
            "state"         : self.state,
            "frames_done"   : done,
            "total_frames"  : total,
            "percent"       : pct,
            "eta_seconds"   : eta_s,
            "cur_xi"        : xi,
            "cur_yi"        : yi,
            "nx"            : self._params.nx if self._params else 0,
            "ny"            : self._params.ny if self._params else 0,
            "session_name"  : self._params.session_name if self._params else "",
        }

    # ------------------------------------------------------------------
    # INTERNAL SCAN LOOP
    # ------------------------------------------------------------------

    def _run_scan(self):
        p = self._params
        import cv2, os
        from acquisition.data_cube import data_cube_manager

        session_path = os.path.join(config.SAVE_FOLDER, p.session_name)
        os.makedirs(session_path, exist_ok=True)

        self._log(f"Scan started: {p.nx}×{p.ny} = {p.total_frames} frames")
        self._log(f"Session: {p.session_name}")

        frame_idx = 0

        for yi in range(p.ny):
            # Serpentine: reverse X direction on odd rows
            x_range = range(p.nx)
            if p.raster == "serpentine" and yi % 2 == 1:
                x_range = range(p.nx - 1, -1, -1)

            for xi in x_range:
                # Pause gate
                self._pause_event.wait()

                # Stop gate
                if self._stop_event.is_set():
                    self._finish("STOPPED")
                    return

                x_mm = p.x_start + xi * p.x_step
                y_mm = p.y_start + yi * p.y_step

                # Move
                self._ctrl.stage_x.move_to(x_mm)
                self._ctrl.stage_x.wait_move()
                self._ctrl.stage_y.move_to(y_mm)
                self._ctrl.stage_y.wait_move()

                # Settle
                time.sleep(p.settling_s)

                # Capture
                raw = self._ctrl.camera.grab_frame()

                # Compute representative intensity (mean of centre crop)
                h, w   = raw.shape[:2]
                crop   = raw[h//4:3*h//4, w//4:3*w//4]
                intensity = float(np.mean(crop))

                # Save frame
                fname = os.path.join(
                    session_path,
                    f"frame_{frame_idx:05d}_y{yi:04d}_x{xi:04d}.png"
                )
                cv2.imwrite(fname, raw)

                # Register with cube manager
                data_cube_manager.record_frame(
                    session=p.session_name,
                    xi=xi, yi=yi,
                    intensity=intensity,
                    nx=p.nx, ny=p.ny,
                )

                # Update progress
                with self._lock:
                    self._frames_done = frame_idx + 1
                    self._cur_xi      = xi
                    self._cur_yi      = yi

                # Emit telemetry event
                self.event_queue.put({
                    "type"      : "frame",
                    "frame_idx" : frame_idx,
                    "xi"        : xi,
                    "yi"        : yi,
                    "x_mm"      : round(x_mm, 4),
                    "y_mm"      : round(y_mm, 4),
                    "intensity" : round(intensity, 2),
                })

                frame_idx += 1

        self._finish("COMPLETED")

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _finish(self, reason: str):
        self.state       = ScanState.IDLE
        self._start_time = None
        self._log(f"Scan finished: {reason}")

    def _log(self, msg: str):
        self.event_queue.put({"type": "log", "message": msg})
