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
from acquisition.error_logger import log_error


def _mm_to_units(value_mm: float) -> int:
    return int(round(value_mm * config.UNITS_PER_MM))


def _units_to_mm(value_units: int) -> float:
    return round(value_units / config.UNITS_PER_MM, 4)


# =============================================================================
# MOCK STAGE
# =============================================================================

class MockStage:

    def __init__(self, name: str = "X", initial_position_mm: float = 0.0):

        self.name = name

        self._position_units = _mm_to_units(initial_position_mm)

        self._is_moving = threading.Event()

        self._stop_event = threading.Event()

        self._lock = threading.Lock()

    @property
    def position_mm(self) -> float:

        with self._lock:
            return _units_to_mm(self._position_units)

    @property
    def is_moving(self) -> bool:

        return self._is_moving.is_set()

    def move_to(self, target_mm: float):
        target_units = _mm_to_units(target_mm)
        self._stop_event.clear()

        def _run():

            with self._lock:
                start_units = self._position_units

            dist = abs(target_units - start_units) / config.UNITS_PER_MM

            t_move = dist / config.MOCK_STAGE_VELOCITY_MM_S

            steps = max(1, int(t_move / 0.02))

            for i in range(steps + 1):

                if self._stop_event.is_set():
                    break

                frac = i / steps

                with self._lock:
                    self._position_units = int(round(
                        start_units
                        + (target_units - start_units) * frac
                    ))

                if t_move:
                    time.sleep(t_move / steps)

            with self._lock:
                if not self._stop_event.is_set():
                    self._position_units = target_units

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
        self.wait_move()

        with self._lock:
            self._position_units = 0

    def close(self):

        self.stop()

    def stop(self):

        self._stop_event.set()
        self._is_moving.clear()


# =============================================================================
# REAL STAGE
# =============================================================================
class RealStage:
    """Safe Thorlabs Kinesis wrapper (no crash version)."""

    def __init__(self, serial: str | None = None, channel: int = 1):
        from pylablib.devices import Thorlabs
        self._fallback = False
        self._zero_offset_units = 0

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
            log_error("STAGE_ERROR", RuntimeError(f"Stage connection failed: {e}"))

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
            return _units_to_mm(self.position_units)
        except:
            return 0.0

    @property
    def position_units(self) -> int:
        if self._fallback:
            return _mm_to_units(self._stage.position_mm)
        return int(round(self._stage.get_position())) - self._zero_offset_units

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
            target_units = _mm_to_units(target_mm)
            if self._fallback:
                self._stage.move_to(_units_to_mm(target_units))
                return
            self._stage.move_to(target_units + self._zero_offset_units)
        except Exception as exc:
            log_error("STAGE_ERROR", exc)
            raise

    def wait_move(self):
        try:
            if self._fallback:
                self._stage.wait_move()
                return
            self._stage.wait_move()
        except Exception as exc:
            log_error("STAGE_ERROR", exc)
            raise

    def home(self):
        try:
            if self._fallback:
                self._stage.home()
                self._stage.wait_move()
                return
            self._stage.home(sync=True)
            self._stage.wait_move()
            self._zero_offset_units = int(round(self._stage.get_position()))
        except Exception as exc:
            log_error("STAGE_ERROR", exc)
            raise

    def stop(self):
        try:
            stop = getattr(self._stage, "stop", None)
            if callable(stop):
                stop()
        except Exception as exc:
            log_error("STAGE_ERROR", exc)

    def health_check(self) -> bool:
        if self._fallback:
            return False
        try:
            _ = self._stage.get_position()
            return True
        except Exception as exc:
            log_error("STAGE_ERROR", exc)
            return False

    def close(self):
        try:
            self._stage.close()
        except Exception:
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

    def health_check(self) -> bool:

        try:
            if hasattr(self._cam, "IsCameraDeviceRemoved") and self._cam.IsCameraDeviceRemoved():
                return False
            if hasattr(self._cam, "IsOpen") and not self._cam.IsOpen():
                return False
            result = self._cam.GrabOne(1000)
            return bool(result.GrabSucceeded())
        except Exception:
            return False

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
        self._recovery_interval_s = float(
            getattr(config, "HARDWARE_MONITOR_INTERVAL_S", 5.0)
        )
        self._stage_access_lock = threading.RLock()

        # ============================================================
        # STAGE INIT (SAFE)
        # ============================================================

        self.stage = None
        self._stage_physical_connected = False
        self._stage_using_fallback = False
        self._stage_status = "simulation" if self._mock else "initializing"

        if self._mock:
            self.stage = MockStage("X")

        else:
            try:
                self.stage = RealStage(channel=1)
            except Exception as e:
                print(f"[HSI] Stage init failed → switching to MOCK: {e}")
                self.stage = MockStage("X")

        self._stage_using_fallback = bool(
            (
                isinstance(self.stage, MockStage)
                or getattr(self.stage, "fallback", False)
            )
            and not config.MOCK_MODE
        )
        self._stage_physical_connected = bool(
            not config.MOCK_MODE
            and not self._stage_using_fallback
            and self.stage is not None
            and not isinstance(self.stage, MockStage)
        )
        self._stage_status = (
            "fallback"
            if self._stage_using_fallback
            else ("simulation" if config.MOCK_MODE else "connected")
        )
        if self._stage_using_fallback:
            log_error(
                "STAGE_ERROR",
                RuntimeError("Stage fallback active; retrying real stage in background")
            )

        # ============================================================
        # CAMERA INIT (SAFE)
        # ============================================================

        self.camera = None
        self._fallback_camera = None
        self._camera_physical_connected = False
        self._camera_using_fallback = False

        if self._mock:
            self.camera = MockCamera()
            self._camera_status = "simulation"

        else:
            try:
                self.camera = RealCamera()
                if self.camera.health_check():
                    self._camera_status = "connected"
                    self._camera_physical_connected = True
                else:
                    self.camera.close()
                    self.camera = None
                    self._fallback_camera = MockCamera()
                    self._camera_status = "disconnected"
                    self._camera_using_fallback = True
                    log_error("CAMERA_ERROR", RuntimeError("Camera init health check failed"))

            except Exception as e:
                print(f"[HSI] Camera init failed → switching to MOCK: {e}")
                self.camera = None
                self._fallback_camera = MockCamera()
                self._camera_status = "disconnected"
                self._camera_using_fallback = True
                log_error("CAMERA_ERROR", RuntimeError(f"Camera init failed: {e}"))

        if (
            not config.MOCK_MODE
            and isinstance(self.camera, MockCamera)
        ):
            self._fallback_camera = self.camera
            self.camera = None
            self._camera_status = "disconnected"
            self._camera_physical_connected = False
            self._camera_using_fallback = True
            log_error(
                "CAMERA_ERROR",
                RuntimeError("Camera fallback active; retrying real camera in background")
            )

        # ============================================================
        # LIVE FRAME BUFFER
        # ============================================================

        self._live_frame: Optional[bytes] = None
        self._frame_lock = threading.Lock()
        self._camera_access_lock = threading.Lock()
        self._camera_error_count = 0
        self._processing_enabled = False
        self._running = True

        self._cam_thread = threading.Thread(
            target=self._camera_loop,
            daemon=True
        )
        self._cam_thread.start()

        self._watchdog_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True
        )
        self._watchdog_thread.start()

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
                log_error("CAMERA_ERROR", e)

            time.sleep(0.08 if self._processing_enabled else 0.5)

    # ================================================================
    # LIVE STREAM
    # ================================================================

    def get_live_jpeg(self):

        with self._frame_lock:
            frame = self._live_frame

        if frame is not None:
            return frame

        try:
            import cv2

            raw = self.capture_frame()
            ok, buf = cv2.imencode(
                ".jpg",
                raw,
                [cv2.IMWRITE_JPEG_QUALITY, 80]
            )
            if ok:
                frame = buf.tobytes()
                with self._frame_lock:
                    self._live_frame = frame
                return frame
        except Exception as exc:
            log_error("CAMERA_ERROR", exc)

        return None

    def capture_frame(self) -> np.ndarray:

        with self._camera_access_lock:
            try:
                if self.camera is None:
                    if self._fallback_camera is None:
                        self._fallback_camera = MockCamera()
                    if not config.MOCK_MODE:
                        self._camera_status = "disconnected"
                        self._camera_physical_connected = False
                        self._camera_using_fallback = True
                    return self._fallback_camera.grab_frame()
                frame = self.camera.grab_frame()
                self._camera_error_count = 0
                physical_camera = bool(
                    not config.MOCK_MODE
                    and not isinstance(self.camera, MockCamera)
                )
                self._camera_physical_connected = physical_camera
                self._camera_using_fallback = not physical_camera and not config.MOCK_MODE
                if physical_camera:
                    self._camera_status = "connected"
                elif config.MOCK_MODE:
                    self._camera_status = "simulation"
                return frame

            except Exception as e:
                self._camera_error_count += 1
                print("[HSI] Camera capture failed:", e)
                log_error("CAMERA_ERROR", RuntimeError(f"Frame grab failed: {e}"))

                if self._camera_status != "simulation":
                    self._camera_status = "disconnected"
                    self._camera_physical_connected = False
                    self._camera_using_fallback = True

                try:
                    if self.camera is not None:
                        self.camera.close()
                except Exception as close_error:
                    log_error("CAMERA_ERROR", close_error)
                self.camera = None

                if self._fallback_camera is None:
                    self._fallback_camera = MockCamera()

                return self._fallback_camera.grab_frame()

    def _recovery_loop(self):

        while self._running:
            time.sleep(max(
                2.5,
                float(getattr(config, "CAMERA_WATCHDOG_INTERVAL_S", 2.5))
            ))

            try:
                if config.MOCK_MODE:
                    continue

                self._recover_camera()
                self._recover_stage()

            except Exception as exc:
                log_error("SYSTEM_ERROR", exc)

    def _recover_camera(self):

        with self._camera_access_lock:
            healthy = False
            try:
                healthy = bool(
                    self.camera is not None
                    and hasattr(self.camera, "health_check")
                    and self.camera.health_check()
                )
            except Exception as exc:
                log_error("CAMERA_ERROR", exc)

            if healthy:
                self._camera_status = "connected"
                self._camera_physical_connected = True
                self._camera_using_fallback = False
                return

            self._camera_status = "disconnected"
            self._camera_physical_connected = False
            self._camera_using_fallback = True

            try:
                if self.camera is not None:
                    self.camera.close()
            except Exception as exc:
                log_error("CAMERA_ERROR", exc)
            self.camera = None

            try:
                candidate = RealCamera()
                if candidate.health_check():
                    self.camera = candidate
                    self._camera_status = "connected"
                    self._camera_physical_connected = True
                    self._camera_using_fallback = False
                    self._camera_error_count = 0
                    return
                candidate.close()
                raise RuntimeError("Camera reconnect health check failed")
            except Exception as exc:
                log_error("CAMERA_ERROR", RuntimeError(f"Camera reconnect failed: {exc}"))
                self.camera = None
                if self._fallback_camera is None:
                    self._fallback_camera = MockCamera()

    def _recover_stage(self):

        with self._stage_access_lock:
            healthy = False
            try:
                healthy = bool(
                    self.stage is not None
                    and not isinstance(self.stage, MockStage)
                    and hasattr(self.stage, "health_check")
                    and self.stage.health_check()
                )
            except Exception as exc:
                log_error("STAGE_ERROR", exc)

            if healthy:
                self._stage_status = "connected"
                self._stage_physical_connected = True
                self._stage_using_fallback = False
                return

            if (
                self.stage is not None
                and not isinstance(self.stage, MockStage)
            ):
                self._activate_stage_fallback(
                    RuntimeError("Stage health check failed")
                )

            try:
                candidate = RealStage(channel=1)
                if getattr(candidate, "fallback", False):
                    candidate.close()
                    raise RuntimeError("Stage reconnect returned fallback stage")
                if hasattr(candidate, "health_check") and not candidate.health_check():
                    candidate.close()
                    raise RuntimeError("Stage reconnect health check failed")

                old_stage = self.stage
                self.stage = candidate
                self._stage_status = "connected"
                self._stage_physical_connected = True
                self._stage_using_fallback = False
                try:
                    if old_stage is not None and old_stage is not candidate:
                        old_stage.close()
                except Exception:
                    pass
            except Exception as exc:
                log_error("STAGE_ERROR", RuntimeError(f"Stage reconnect failed: {exc}"))
                if self.stage is None or not isinstance(self.stage, MockStage):
                    self._activate_stage_fallback(exc)

    def _activate_stage_fallback(self, error: Exception):

        log_error("STAGE_ERROR", error)
        position_mm = 0.0

        try:
            if self.stage is not None:
                position_mm = float(getattr(self.stage, "position_mm", 0.0))
        except Exception:
            position_mm = 0.0

        try:
            if self.stage is not None and hasattr(self.stage, "stop"):
                self.stage.stop()
        except Exception as exc:
            log_error("STAGE_ERROR", exc)

        try:
            if self.stage is not None:
                self.stage.close()
        except Exception:
            pass

        self.stage = MockStage("X", initial_position_mm=position_mm)
        self._stage_status = "fallback"
        self._stage_physical_connected = False
        self._stage_using_fallback = True

    # ================================================================
    # CAMERA CONTROL
    # ================================================================

    def set_camera_exposure(self, us: float):
        try:
            with self._camera_access_lock:
                target = self.camera or self._fallback_camera
                if target is not None:
                    target.set_exposure(us)
        except Exception as e:
            print("[HSI] Exposure set failed:", e)
            log_error("CAMERA_ERROR", e)

    def set_camera_gain(self, db: float):
        try:
            with self._camera_access_lock:
                target = self.camera or self._fallback_camera
                if target is not None:
                    target.set_gain(db)
        except Exception as e:
            print("[HSI] Gain set failed:", e)
            log_error("CAMERA_ERROR", e)

    # ================================================================
    # STAGE CONTROL (SAFE)
    # ================================================================

    def jog(self, direction: int, step_mm: float):

        try:
            with self._stage_access_lock:
                target = self.stage.position_mm + direction * step_mm

                target = max(
                    config.STAGE_X_MIN_MM,
                    min(config.STAGE_X_MAX_MM, target)
                )

                self.stage.move_to(target)
                self.stage.wait_move()

        except Exception as e:
            print("[HSI] Jog failed:", e)
            self._activate_stage_fallback(e)

    def goto(self, x_mm: float):

        try:
            with self._stage_access_lock:
                x_mm = max(
                    config.STAGE_X_MIN_MM,
                    min(config.STAGE_X_MAX_MM, x_mm)
                )

                self.stage.move_to(x_mm)
                self.stage.wait_move()

        except Exception as e:
            print("[HSI] Goto failed:", e)
            self._activate_stage_fallback(e)
            try:
                self.stage.move_to(x_mm)
                self.stage.wait_move()
            except Exception as fallback_error:
                log_error("STAGE_ERROR", fallback_error)

    def home(self):

        try:
            with self._stage_access_lock:
                self.stage.home()
                self.stage.wait_move()

        except Exception as e:
            print("[HSI] Home failed:", e)
            self._activate_stage_fallback(e)
            try:
                self.stage.home()
                self.stage.wait_move()
            except Exception as fallback_error:
                log_error("STAGE_ERROR", fallback_error)

    def move_and_wait(self, x_mm: float):

        self.goto(x_mm)

    def set_processing_enabled(self, enabled: bool):

        self._processing_enabled = bool(enabled)

    # ================================================================
    # STATUS
    # ================================================================

    def status_dict(self):

        with self._frame_lock:
            stream_available = self._live_frame is not None

        with self._stage_access_lock:
            stage_ok = False
            try:
                _ = self.stage.position_mm
                stage_ok = True
            except Exception:
                stage_ok = False

            try:
                stage_pos = round(getattr(self.stage, "position_mm", 0.0), 4)
            except Exception as exc:
                log_error("STAGE_ERROR", exc)
                stage_pos = 0.0
                stage_ok = False

            try:
                stage_moving = bool(getattr(self.stage, "is_moving", False))
            except Exception as exc:
                log_error("STAGE_ERROR", exc)
                stage_moving = False

        fallback_mode = bool(
            config.MOCK_MODE
            or self._stage_using_fallback
            or self._camera_using_fallback
        )
        camera_connected = bool(self._camera_physical_connected)
        camera_temp_source = self.camera or self._fallback_camera

        return {
            "mock_mode": fallback_mode,
            "stage_mm": stage_pos,
            "stage_x_mm": stage_pos,
            "stage_y_mm": 0.0,
            "stage_connected": bool(self._stage_physical_connected),
            "stage_available": stage_ok,
            "stage_physical_connected": self._stage_physical_connected,
            "stage_fallback": self._stage_using_fallback,
            "stage_moving": stage_moving,
            "stage_x_moving": stage_moving,
            "stage_y_moving": False,
            "stage_status": (
                "moving"
                if stage_moving
                else self._stage_status
            ),
            "camera_temp": getattr(camera_temp_source, "temperature", -1),
            "camera_connected": camera_connected,
            "camera_physical_connected": self._camera_physical_connected,
            "camera_status": self._camera_status,
            "camera_locked": self._camera_status in ("locked", "disconnected"),
            "camera_stream_available": stream_available,
            "camera_fallback_stream": self._camera_using_fallback,
            "processing_enabled": self._processing_enabled,
            "illumination": True,
            "connected": bool(self._stage_physical_connected or camera_connected),
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
        except Exception:
            pass

        try:
            if self._fallback_camera is not None:
                self._fallback_camera.close()
        except Exception:
            pass
