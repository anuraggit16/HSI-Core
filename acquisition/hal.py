# =============================================================================
# HSI-Core — Hardware Abstraction Layer (HAL)
# =============================================================================
# Single-axis hyperspectral architecture
#
# Spatial scan  -> X stage motion
# Spectral scan -> wavelength dimension
# Camera         -> live acquisition
# =============================================================================

from __future__ import annotations

import math
import threading
import time
from typing import Optional

import numpy as np

import config


# =============================================================================
# MOCK STAGE
# =============================================================================

class MockStage:

    def __init__(self, name: str = "X"):

        self.name = name

        self._position = 0.0

        self._is_moving = threading.Event()

        self._lock = threading.Lock()

    @property
    def position_mm(self) -> float:

        with self._lock:
            return self._position

    @property
    def is_moving(self) -> bool:

        return self._is_moving.is_set()

    def move_to(self, target_mm: float):

        def _run():

            with self._lock:
                start = self._position

            dist = abs(target_mm - start)

            t_move = dist / config.MOCK_STAGE_VELOCITY_MM_S

            steps = max(1, int(t_move / 0.02))

            for i in range(steps + 1):

                frac = i / steps

                with self._lock:
                    self._position = (
                        start
                        + (target_mm - start) * frac
                    )

                time.sleep(t_move / steps)

            self._is_moving.clear()

        self._is_moving.set()

        threading.Thread(
            target=_run,
            daemon=True
        ).start()

    def wait_move(self):

        while self.is_moving:
            time.sleep(0.01)

    def home(self):

        self.move_to(0.0)

    def close(self):

        pass


# =============================================================================
# REAL STAGE
# =============================================================================

class RealStage:
    """
    Real Thorlabs Kinesis stage
    Auto-detects connected controller
    """

    def __init__(self, channel: int = 1):

        from pylablib.devices import Thorlabs

        devices = Thorlabs.list_kinesis_devices()

        print(f"[HSI] Detected Kinesis devices: {devices}")

        if not devices:
            raise RuntimeError(
                "No Thorlabs Kinesis devices detected"
            )

        serial = devices[0][0]

        print(f"[HSI] Using stage serial: {serial}")

        self._stage = Thorlabs.KinesisMotor(
            serial,
            is_rack_system=True,
            default_channel=channel
        )

        self._stage.setup_velocity(
            min_velocity=config.STAGE_MIN_VELOCITY,
            max_velocity=config.STAGE_MAX_VELOCITY,
            acceleration=config.STAGE_ACCELERATION,
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

        self._stage.move_to(
            int(target_mm * config.UNITS_PER_MM)
        )

    def wait_move(self):

        self._stage.wait_move()

    def home(self):

        self._stage.home(sync=True)

    def close(self):

        self._stage.close()


# =============================================================================
# MOCK CAMERA
# =============================================================================

class MockCamera:

    def __init__(self):

        self._exposure_us = config.EXPOSURE_US

        self._gain_db = config.CAMERA_GAIN_DB

        self._frame_no = 0

        self._temperature = (
            config.MOCK_CAMERA_TEMP_CELSIUS
        )

    def set_exposure(self, us: float):

        self._exposure_us = us

    def set_gain(self, db: float):

        self._gain_db = db

    def grab_frame(self) -> np.ndarray:

        h = config.MOCK_FRAME_HEIGHT

        w = config.MOCK_FRAME_WIDTH

        y, x = np.ogrid[:h, :w]

        t = self._frame_no * 0.05

        cx = w // 2 + 60 * math.sin(t)

        cy = h // 2 + 40 * math.cos(t * 0.7)

        blob = 180 * np.exp(
            -(
                (x - cx) ** 2
                + (y - cy) ** 2
            )
            / (2 * 60 ** 2)
        )

        scale = self._exposure_us / 100000.0

        blob *= scale

        frame = np.random.poisson(
            np.clip(blob, 0, 255)
        ).astype(np.float32)

        frame = np.clip(
            frame,
            0,
            255
        ).astype(np.uint8)

        self._frame_no += 1

        return frame

    @property
    def temperature(self) -> float:

        self._temperature += np.random.normal(0, 0.02)

        return round(self._temperature, 2)

    def close(self):

        pass


# =============================================================================
# REAL CAMERA
# =============================================================================

class RealCamera:

    def __init__(self):

        from pypylon import pylon

        self._cam = pylon.InstantCamera(
            pylon.TlFactory.GetInstance().CreateFirstDevice()
        )

        self._cam.Open()

        self._cam.ExposureTime.SetValue(
            config.EXPOSURE_US
        )

        self._temperature_ok = hasattr(
            self._cam,
            "DeviceTemperature"
        )

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

        raise RuntimeError(
            "Camera grab failed"
        )

    @property
    def temperature(self) -> float:

        if self._temperature_ok:

            return float(
                self._cam.DeviceTemperature.GetValue()
            )

        return -999.0

    def close(self):

        self._cam.Close()


# =============================================================================
# LAB CONTROLLER
# =============================================================================

class LabController:
    """
    Single-axis hyperspectral controller
    """

    def __init__(self):

        self._mock = config.MOCK_MODE

        # ============================================================
        # STAGE
        # ============================================================

        if self._mock:

            self.stage = MockStage("X")

        else:

            self.stage = RealStage(channel=1)

        # ============================================================
        # CAMERA
        # ============================================================

        if self._mock:

            self.camera = MockCamera()

        else:

            self.camera = RealCamera()

        # ============================================================
        # LIVE FRAME BUFFER
        # ============================================================

        self._live_frame: Optional[bytes] = None

        self._frame_lock = threading.Lock()

        self._running = True

        self._cam_thread = threading.Thread(
            target=self._camera_loop,
            daemon=True
        )

        self._cam_thread.start()

    # ================================================================
    # CAMERA LOOP
    # ================================================================

    def _camera_loop(self):

        import cv2

        while self._running:

            try:

                raw = self.camera.grab_frame()

                _, buf = cv2.imencode(
                    ".jpg",
                    raw,
                    [cv2.IMWRITE_JPEG_QUALITY, 80]
                )

                with self._frame_lock:

                    self._live_frame = buf.tobytes()

            except Exception as e:

                print("[HSI] Camera loop error:", e)

            time.sleep(0.05)

    def get_live_jpeg(self):

        with self._frame_lock:

            return self._live_frame

    # ================================================================
    # CAMERA CONTROL
    # ================================================================

    def set_camera_exposure(self, us: float):

        self.camera.set_exposure(us)

    def set_camera_gain(self, db: float):

        self.camera.set_gain(db)

    # ================================================================
    # STAGE CONTROL
    # ================================================================

    def jog(
        self,
        direction: int,
        step_mm: float
    ):

        target = (
            self.stage.position_mm
            + direction * step_mm
        )

        target = max(
            config.STAGE_X_MIN_MM,
            min(config.STAGE_X_MAX_MM, target)
        )

        self.stage.move_to(target)

    def goto(self, x_mm: float):

        x_mm = max(
            config.STAGE_X_MIN_MM,
            min(config.STAGE_X_MAX_MM, x_mm)
        )

        self.stage.move_to(x_mm)

        self.stage.wait_move()

    def home(self):

        self.stage.home()

        self.stage.wait_move()

    # ================================================================
    # STATUS
    # ================================================================

    def status_dict(self):

        with self._frame_lock:

            camera_connected = (
                self._live_frame is not None
            )

        return {

            "mock_mode": self._mock,

            "stage_mm": round(
                self.stage.position_mm,
                4
            ),

            "stage_connected": True,

            "stage_moving": bool(
                getattr(self.stage, "is_moving", False)
            ),

            "camera_temp": self.camera.temperature,

            "camera_connected": bool(
                camera_connected
            ),

            "illumination": True,

            "connected": True,
        }

    # ================================================================
    # CLEANUP
    # ================================================================

    def close(self):

        self._running = False

        self.stage.close()

        self.camera.close()