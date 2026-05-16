# =============================================================================
# HSI-Core — Hardware Abstraction Layer (HAL)
# =============================================================================
# Provides a unified LabController that works identically in Mock and Real mode.
# All hardware-specific code is encapsulated here. Switch MOCK_MODE in config.py.
# =============================================================================

from __future__ import annotations

import io
import math
import threading
import time
from typing import Optional

import numpy as np

import config

# =============================================================================
# STAGE INTERFACES
# =============================================================================

class MockStage:
    """Simulates a Thorlabs linear stage with realistic velocity-based timing."""

    def __init__(self, name: str = "X"):
        self.name        = name
        self._position   = 0.0       # mm
        self._is_moving  = threading.Event()
        self._lock       = threading.Lock()

    @property
    def position_mm(self) -> float:
        with self._lock:
            return self._position

    @property
    def is_moving(self) -> bool:
        return self._is_moving.is_set()

    def move_to(self, target_mm: float):
        """Non-blocking move; use wait_move() to synchronise."""
        def _run():
            with self._lock:
                start = self._position
            dist   = abs(target_mm - start)
            t_move = dist / config.MOCK_STAGE_VELOCITY_MM_S
            steps  = max(1, int(t_move / 0.02))
            for i in range(steps + 1):
                frac = i / steps
                with self._lock:
                    self._position = start + (target_mm - start) * frac
                time.sleep(t_move / steps)
            self._is_moving.clear()

        self._is_moving.set()
        threading.Thread(target=_run, daemon=True).start()

    def wait_move(self):
        self._is_moving.wait()

    def home(self):
        self.move_to(0.0)

    def close(self):
        pass


class RealStage:
    """Wraps pylablib.Thorlabs.KinesisMotor for a single-axis Thorlabs stage."""

    def __init__(self, serial: str, channel: int = 1):
        from pylablib.devices import Thorlabs  # type: ignore
        self._stage = Thorlabs.KinesisMotor(
            serial,
            is_rack_system=True,
            default_channel=channel
        )
        self._stage.setup_velocity(
            min_velocity  = config.STAGE_MIN_VELOCITY,
            max_velocity  = config.STAGE_MAX_VELOCITY,
            acceleration  = config.STAGE_ACCELERATION,
        )

    @property
    def position_mm(self) -> float:
        raw = self._stage.get_position()
        return raw / config.UNITS_PER_MM

    @property
    def is_moving(self) -> bool:
        try:
            return bool(self._stage.is_moving())
        except Exception:
            return False

    def move_to(self, target_mm: float):
        self._stage.move_to(int(target_mm * config.UNITS_PER_MM))

    def wait_move(self):
        self._stage.wait_move()

    def home(self):
        self._stage.home(sync=True)

    def close(self):
        self._stage.close()


# =============================================================================
# CAMERA INTERFACES
# =============================================================================

class MockCamera:
    """
    Generates synthetic hyperspectral-like frames.
    Produces a Gaussian feature blob with Poisson shot noise and slight drift.
    """

    def __init__(self):
        self._exposure_us = config.EXPOSURE_US
        self._gain_db     = config.CAMERA_GAIN_DB
        self._frame_no    = 0
        self._temperature = config.MOCK_CAMERA_TEMP_CELSIUS

    def set_exposure(self, us: float):
        self._exposure_us = us

    def set_gain(self, db: float):
        self._gain_db = db

    def grab_frame(self) -> np.ndarray:
        """Return a uint8 grayscale frame (H x W)."""
        h, w = config.MOCK_FRAME_HEIGHT, config.MOCK_FRAME_WIDTH
        y, x = np.ogrid[:h, :w]

        # Slowly drifting Gaussian blob
        t    = self._frame_no * 0.05
        cx   = w // 2 + 60 * math.sin(t)
        cy   = h // 2 + 40 * math.cos(t * 0.7)
        blob = 180 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 60 ** 2))

        # Secondary smaller feature
        cx2  = w // 4
        cy2  = h // 3
        blob += 80 * np.exp(-((x - cx2) ** 2 + (y - cy2) ** 2) / (2 * 30 ** 2))

        # Exposure scaling (linear)
        scale = self._exposure_us / 100_000.0
        blob  = blob * scale

        # Poisson shot noise
        frame = np.random.poisson(np.clip(blob, 0, 255)).astype(np.float32)
        frame = np.clip(frame, 0, 255).astype(np.uint8)
        self._frame_no += 1
        return frame

    @property
    def temperature(self) -> float:
        # Slight random walk
        self._temperature += np.random.normal(0, 0.02)
        return round(self._temperature, 2)

    def close(self):
        pass


class RealCamera:
    """Wraps pypylon InstantCamera for Basler GigE/USB3 cameras."""

    def __init__(self):
        from pypylon import pylon  # type: ignore
        self._cam = pylon.InstantCamera(
            pylon.TlFactory.GetInstance().CreateFirstDevice()
        )
        self._cam.Open()
        self._cam.ExposureTime.SetValue(config.EXPOSURE_US)
        self._temperature_ok = hasattr(self._cam, "DeviceTemperature")

    def set_exposure(self, us: float):
        self._cam.ExposureTime.SetValue(us)

    def set_gain(self, db: float):
        try:
            self._cam.Gain.SetValue(db)
        except Exception:
            pass

    def grab_frame(self) -> np.ndarray:
        result = self._cam.GrabOne(5000)
        if result.GrabSucceeded():
            return result.Array
        raise RuntimeError("Camera grab failed")

    @property
    def temperature(self) -> float:
        if self._temperature_ok:
            return float(self._cam.DeviceTemperature.GetValue())
        return -999.0

    def close(self):
        self._cam.Close()


# =============================================================================
# UNIFIED LAB CONTROLLER
# =============================================================================

class LabController:
    """
    Facade over stage(s) and camera. Use this class everywhere in the server —
    never import Real/Mock classes directly.
    """

    def __init__(self):
        self._mock = config.MOCK_MODE

        # -- Stages --------------------------------------------------------
        if self._mock:
            self.stage_x = MockStage("X")
            self.stage_y = MockStage("Y")
        else:
            self.stage_x = RealStage(config.CONTROLLER_SERIAL_X, channel=1)
            self.stage_y = RealStage(config.CONTROLLER_SERIAL_Y, channel=2)

        # -- Camera --------------------------------------------------------
        if self._mock:
            self.camera = MockCamera()
        else:
            self.camera = RealCamera()

        # -- Live frame buffer (refreshed by background thread) -----------
        self._live_frame: Optional[bytes] = None   # JPEG bytes
        self._frame_lock = threading.Lock()
        self._running    = True
        self._cam_thread = threading.Thread(
            target=self._camera_loop, daemon=True
        )
        self._cam_thread.start()

    # ------------------------------------------------------------------
    # BACKGROUND FRAME ACQUISITION THREAD
    # ------------------------------------------------------------------

    def _camera_loop(self):
        import cv2
        while self._running:
            try:
                raw  = self.camera.grab_frame()
                _, buf = cv2.imencode(
                    ".jpg", raw,
                    [cv2.IMWRITE_JPEG_QUALITY, 80]
                )
                with self._frame_lock:
                    self._live_frame = buf.tobytes()
            except Exception:
                pass
            time.sleep(0.05)   # ~20 fps

    def get_live_jpeg(self) -> Optional[bytes]:
        with self._frame_lock:
            return self._live_frame

    # ------------------------------------------------------------------
    # CAMERA CONTROL
    # ------------------------------------------------------------------

    def set_camera_exposure(self, us: float):
        self.camera.set_exposure(us)

    def set_camera_gain(self, db: float):
        self.camera.set_gain(db)

    # ------------------------------------------------------------------
    # STAGE CONTROL
    # ------------------------------------------------------------------

    def jog(self, axis: str, direction: int, step_mm: float):
        """Relative move. axis='x'|'y', direction=+1|-1"""
        if axis.lower() == "x":
            target = self.stage_x.position_mm + direction * step_mm
            target = max(config.STAGE_X_MIN_MM,
                         min(config.STAGE_X_MAX_MM, target))
            self.stage_x.move_to(target)
        else:
            target = self.stage_y.position_mm + direction * step_mm
            target = max(config.STAGE_Y_MIN_MM,
                         min(config.STAGE_Y_MAX_MM, target))
            self.stage_y.move_to(target)

    def goto(self, x_mm: float, y_mm: float):
        x_mm = max(config.STAGE_X_MIN_MM, min(config.STAGE_X_MAX_MM, x_mm))
        y_mm = max(config.STAGE_Y_MIN_MM, min(config.STAGE_Y_MAX_MM, y_mm))
        self.stage_x.move_to(x_mm)
        self.stage_x.wait_move()
        self.stage_y.move_to(y_mm)
        self.stage_y.wait_move()

    def home(self):
        self.stage_x.home()
        self.stage_x.wait_move()
        self.stage_y.home()
        self.stage_y.wait_move()

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def status_dict(self) -> dict:
        with self._frame_lock:
            camera_connected = self._live_frame is not None
        stage_x_moving = bool(getattr(self.stage_x, "is_moving", False))
        stage_y_moving = bool(getattr(self.stage_y, "is_moving", False))
        return {
            "mock_mode"    : self._mock,
            "stage_x_mm"  : round(self.stage_x.position_mm, 4),
            "stage_y_mm"  : round(self.stage_y.position_mm, 4),
            "stage_connected": True,
            "stage_x_moving": stage_x_moving,
            "stage_y_moving": stage_y_moving,
            "camera_temp" : self.camera.temperature,
            "camera_connected": bool(camera_connected),
            "lens_focus"  : -600,      # ppm — from config if encoder available
            "illumination": True,
            "connected"   : True,
        }

    # ------------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------------

    def close(self):
        self._running = False
        self.stage_x.close()
        self.stage_y.close()
        self.camera.close()
