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
    """Safe Thorlabs Kinesis wrapper (no crash version)."""

    def __init__(self, serial: str | None = None, channel: int = 1):
        from pylablib.devices import Thorlabs
        self._fallback = False

        print("\n[HSI] Searching for Kinesis devices...")

        try:
            devices = Thorlabs.list_kinesis_devices()
            print("[HSI] Found devices:", devices)

            if not devices:
                raise RuntimeError("No Kinesis devices found")

            if serial is None:
                serial = devices[0][0]

            print(f"[HSI] Connecting to serial: {serial}")

            # ✅ IMPORTANT: NO backend override (this was breaking everything)
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

            print("[HSI] Stage connected")

        except Exception as e:
            print("[HSI] Stage connection failed:", e)
            print("[HSI] Switching to MOCK stage automatically")

            from acquisition.hal import MockStage
            self._stage = MockStage("X")
            self._fallback = True

    @property
    def fallback(self) -> bool:
        return self._fallback

    @property
    def position_mm(self):
        try:
            if self._fallback:
                return self._stage.position_mm
            return self._stage.get_position() / config.UNITS_PER_MM
        except:
            return 0.0

    @property
    def is_moving(self):
        try:
            if self._fallback:
                return self._stage.is_moving
            return bool(self._stage.is_moving())
        except:
            return False

    def move_to(self, target_mm: float):
        try:
            if self._fallback:
                self._stage.move_to(target_mm)
                return
            self._stage.move_to(int(target_mm * config.UNITS_PER_MM))
        except:
            pass

    def wait_move(self):
        try:
            if self._fallback:
                self._stage.wait_move()
                return
            self._stage.wait_move()
        except:
            pass

    def home(self):
        try:
            if self._fallback:
                self._stage.home()
                return
            self._stage.home(sync=True)
        except:
            pass

    def close(self):
        try:
            self._stage.close()
        except:
            pass

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
    Single-axis hyperspectral controller (SAFE VERSION)

    - Auto-fallback to Mock if hardware fails
    - Prevents server crash on stage/camera errors
    - Stable for production FastAPI
    """

    def __init__(self):

        self._mock = config.MOCK_MODE

        # ============================================================
        # STAGE INIT (SAFE)
        # ============================================================

        self.stage = None

        if self._mock:
            self.stage = MockStage("X")

        else:
            try:
                self.stage = RealStage(channel=1)
                if getattr(self.stage, "fallback", False):
                    self._mock = True

            except Exception as e:
                print(f"[HSI] Stage init failed → switching to MOCK: {e}")
                self._mock = True
                self.stage = MockStage("X")

        # ============================================================
        # CAMERA INIT (SAFE)
        # ============================================================

        self.camera = None

        if self._mock:
            self.camera = MockCamera()
            self._camera_status = "mock"

        else:
            try:
                self.camera = RealCamera()
                self._camera_status = "connected"

            except Exception as e:
                print(f"[HSI] Camera init failed → switching to MOCK: {e}")
                self.camera = MockCamera()
                self._camera_status = "failed"

        # ============================================================
        # LIVE FRAME BUFFER
        # ============================================================

        self._live_frame: Optional[bytes] = None
        self._frame_lock = threading.Lock()
        self._camera_access_lock = threading.Lock()
        self._camera_error_count = 0
        self._running = True

        self._cam_thread = threading.Thread(
            target=self._camera_loop,
            daemon=True
        )
        self._cam_thread.start()

        print("[HSI] LabController initialized successfully")

    # ================================================================
    # CAMERA LOOP
    # ================================================================

    def _camera_loop(self):

        import cv2

        while self._running:

            try:
                raw = self.capture_frame()

                ok, buf = cv2.imencode(
                    ".jpg",
                    raw,
                    [cv2.IMWRITE_JPEG_QUALITY, 80]
                )

                if ok:
                    with self._frame_lock:
                        self._live_frame = buf.tobytes()

            except Exception as e:
                print("[HSI] Camera loop error:", e)

            time.sleep(0.05)

    # ================================================================
    # LIVE STREAM
    # ================================================================

    def get_live_jpeg(self):

        with self._frame_lock:
            return self._live_frame

    def capture_frame(self) -> np.ndarray:

        with self._camera_access_lock:
            try:
                frame = self.camera.grab_frame()
                self._camera_error_count = 0
                if self._camera_status not in ("mock", "failed"):
                    self._camera_status = "connected"
                return frame

            except Exception as e:
                self._camera_error_count += 1
                print("[HSI] Camera capture failed:", e)

                if self._camera_status != "mock":
                    self._camera_status = "locked"

                if self._camera_error_count >= 3 and not isinstance(self.camera, MockCamera):
                    print("[HSI] Camera locked - switching to safe fallback stream")
                    try:
                        self.camera.close()
                    except Exception:
                        pass
                    self.camera = MockCamera()

                return self.camera.grab_frame()

    # ================================================================
    # CAMERA CONTROL
    # ================================================================

    def set_camera_exposure(self, us: float):
        try:
            with self._camera_access_lock:
                self.camera.set_exposure(us)
        except Exception as e:
            print("[HSI] Exposure set failed:", e)

    def set_camera_gain(self, db: float):
        try:
            with self._camera_access_lock:
                self.camera.set_gain(db)
        except Exception as e:
            print("[HSI] Gain set failed:", e)

    # ================================================================
    # STAGE CONTROL (SAFE)
    # ================================================================

    def jog(self, direction: int, step_mm: float):

        try:
            target = self.stage.position_mm + direction * step_mm

            target = max(
                config.STAGE_X_MIN_MM,
                min(config.STAGE_X_MAX_MM, target)
            )

            self.stage.move_to(target)

        except Exception as e:
            print("[HSI] Jog failed:", e)

    def goto(self, x_mm: float):

        try:
            x_mm = max(
                config.STAGE_X_MIN_MM,
                min(config.STAGE_X_MAX_MM, x_mm)
            )

            self.stage.move_to(x_mm)
            self.stage.wait_move()

        except Exception as e:
            print("[HSI] Goto failed:", e)

    def home(self):

        try:
            self.stage.home()
            self.stage.wait_move()

        except Exception as e:
            print("[HSI] Home failed:", e)

    def move_and_wait(self, x_mm: float):

        self.goto(x_mm)

    # ================================================================
    # STATUS
    # ================================================================

    def status_dict(self):

        with self._frame_lock:
            camera_connected = self._live_frame is not None

        stage_ok = False
        try:
            _ = self.stage.position_mm
            stage_ok = True
        except:
            stage_ok = False

        stage_pos = round(getattr(self.stage, "position_mm", 0.0), 4)
        stage_moving = bool(getattr(self.stage, "is_moving", False))

        return {
            "mock_mode": self._mock,
            "stage_mm": stage_pos,
            "stage_x_mm": stage_pos,
            "stage_y_mm": 0.0,
            "stage_connected": stage_ok,
            "stage_moving": stage_moving,
            "stage_x_moving": stage_moving,
            "stage_y_moving": False,
            "stage_status": (
                "moving"
                if stage_moving
                else ("connected" if stage_ok else "error")
            ),
            "camera_temp": getattr(self.camera, "temperature", -1),
            "camera_connected": camera_connected,
            "camera_status": self._camera_status,
            "camera_locked": self._camera_status == "locked",
            "illumination": True,
            "connected": stage_ok or camera_connected,
        }

    # ================================================================
    # CLEANUP
    # ================================================================

    def close(self):

        self._running = False

        try:
            self.stage.close()
        except:
            pass

        try:
            self.camera.close()
        except:
            pass
