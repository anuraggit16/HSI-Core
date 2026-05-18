# =============================================================================
# HSI-Core - Hardware Abstraction Layer
# =============================================================================
# Owns the only stage/camera instances in this Python process.
# Hardware is marked connected only after a command/grab succeeds.
# =============================================================================

from __future__ import annotations

import atexit
import json
import math
import os
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np

import config
from acquisition.error_logger import log_error, log_hardware_event


def _mm_to_units(value_mm: float) -> int:
    return int(round(value_mm * config.UNITS_PER_MM))


def _units_to_mm(value_units: int) -> float:
    return round(value_units / config.UNITS_PER_MM, 5)


def _as_number(value) -> float:
    if isinstance(value, (tuple, list)):
        return float(value[0])
    return float(value)


@dataclass
class HardwareState:
    stage_connected: bool = False
    stage_moving: bool = False
    camera_connected: bool = False
    camera_streaming: bool = False
    last_error: str = ""
    mode: str = "MOCK"

    def as_dict(self) -> dict:
        return asdict(self)


class HardwareProcessLock:
    """Best-effort inter-process lock so only one backend owns lab hardware."""

    def __init__(self, path: str):
        self.path = path
        self._fh = None
        self._locked = False

    @property
    def locked(self) -> bool:
        return self._locked

    def acquire(self) -> bool:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._fh = open(self.path, "a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._locked = True
            self._fh.seek(0)
            self._fh.truncate()
            self._fh.write(json.dumps({"pid": os.getpid(), "timestamp": time.time()}))
            self._fh.flush()
            return True
        except OSError:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None
            self._locked = False
            return False

    def release(self) -> None:
        if not self._fh:
            return
        try:
            if self._locked:
                if os.name == "nt":
                    import msvcrt

                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            self._fh.close()
        except Exception:
            pass
        self._fh = None
        self._locked = False


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

    def move_to(self, target_mm: float) -> None:
        target_units = _mm_to_units(target_mm)
        self._stop_event.clear()

        def _run() -> None:
            with self._lock:
                start_units = self._position_units
            distance_mm = abs(target_units - start_units) / config.UNITS_PER_MM
            duration_s = distance_mm / max(0.001, config.MOCK_STAGE_VELOCITY_MM_S)
            steps = max(1, int(duration_s / 0.02))
            for i in range(steps + 1):
                if self._stop_event.is_set():
                    break
                frac = i / steps
                with self._lock:
                    self._position_units = int(round(start_units + (target_units - start_units) * frac))
                if duration_s:
                    time.sleep(duration_s / steps)
            with self._lock:
                if not self._stop_event.is_set():
                    self._position_units = target_units
            self._is_moving.clear()

        self._is_moving.set()
        threading.Thread(target=_run, daemon=True).start()

    def wait_move(self, timeout_s: Optional[float] = None) -> None:
        start = time.time()
        while self.is_moving:
            if timeout_s and time.time() - start > timeout_s:
                raise TimeoutError("Mock stage move timed out")
            time.sleep(0.01)

    def home(self) -> None:
        self.move_to(0.0)
        self.wait_move()
        with self._lock:
            self._position_units = 0

    def zero_here(self) -> None:
        with self._lock:
            self._position_units = 0

    def stop(self) -> None:
        self._stop_event.set()
        self._is_moving.clear()

    def close(self) -> None:
        self.stop()


class RealStage:
    """Thorlabs Kinesis stage wrapper. Never hides failures as connected."""

    def __init__(self, serial: str | None = None, channel: int = 1):
        from pylablib.devices import Thorlabs

        serial = serial or config.CONTROLLER_SERIAL_X
        devices = Thorlabs.list_kinesis_devices()
        if not devices:
            raise RuntimeError("No Kinesis devices found")

        available_serials = {str(device[0]) for device in devices}
        if serial and str(serial) not in available_serials:
            raise RuntimeError(f"Kinesis serial {serial} not found; available={sorted(available_serials)}")

        self.serial = str(serial or devices[0][0])
        self.channel = channel
        self._stage = Thorlabs.KinesisMotor(
            self.serial,
            is_rack_system=True,
            default_channel=channel,
        )
        self._zero_offset_units = 0
        self._last_direction = 0
        self._stage.setup_velocity(
            min_velocity=config.STAGE_MIN_VELOCITY,
            max_velocity=config.STAGE_MAX_VELOCITY,
            acceleration=config.STAGE_ACCELERATION,
        )

    @property
    def position_units(self) -> int:
        return int(round(_as_number(self._stage.get_position()))) - self._zero_offset_units

    @property
    def position_mm(self) -> float:
        return _units_to_mm(self.position_units)

    @property
    def is_moving(self) -> bool:
        moving = getattr(self._stage, "is_moving", None)
        return bool(moving() if callable(moving) else False)

    def _commanded_units(self, target_mm: float) -> int:
        corrected_mm = float(target_mm) - float(getattr(config, "STAGE_CALIBRATION_OFFSET_MM", 0.0))
        return _mm_to_units(corrected_mm) + self._zero_offset_units

    def _raw_units(self) -> int:
        return int(round(_as_number(self._stage.get_position())))

    def _move_to_units(self, target_units: int) -> None:
        self._stage.move_to(int(target_units))

    def move_to(self, target_mm: float) -> None:
        current = self.position_mm
        direction = 1 if target_mm > current else (-1 if target_mm < current else 0)
        backlash_enabled = bool(getattr(config, "STAGE_BACKLASH_CORRECTION_ENABLED", False))
        backlash_mm = float(getattr(config, "STAGE_BACKLASH_CORRECTION_MM", 0.0))

        if backlash_enabled and direction and backlash_mm > 0:
            pre_target = target_mm + direction * backlash_mm
            pre_target = max(config.STAGE_X_MIN_MM, min(config.STAGE_X_MAX_MM, pre_target))
            if abs(pre_target - target_mm) > 1e-6:
                self._move_to_units(self._commanded_units(pre_target))
                self.wait_move()

        self._move_to_units(self._commanded_units(target_mm))
        self._last_direction = direction

    def wait_move(self, timeout_s: Optional[float] = None) -> None:
        timeout_s = timeout_s or float(getattr(config, "STAGE_MOVE_TIMEOUT_S", 60.0))
        started = time.time()
        wait_move = getattr(self._stage, "wait_move", None)
        if callable(wait_move):
            try:
                wait_move()
                return
            except TypeError:
                pass
        while self.is_moving:
            if time.time() - started > timeout_s:
                raise TimeoutError("Stage move timed out")
            time.sleep(0.02)

    def confirm_position(self, target_mm: float) -> float:
        actual = self.position_mm
        tolerance = float(getattr(config, "STAGE_POSITION_TOLERANCE_MM", 0.002))
        if abs(actual - target_mm) > tolerance:
            raise RuntimeError(
                f"Stage read-back mismatch: commanded {target_mm:.5f} mm, actual {actual:.5f} mm"
            )
        return actual

    def home(self) -> None:
        home = getattr(self._stage, "home", None)
        if not callable(home):
            raise RuntimeError("Stage does not expose home()")
        try:
            home(sync=True)
        except TypeError:
            home()
        self.wait_move()
        self._zero_offset_units = self._raw_units()

    def zero_here(self) -> None:
        self._zero_offset_units = self._raw_units()

    def stop(self) -> None:
        stop = getattr(self._stage, "stop", None)
        if callable(stop):
            stop()

    def health_check(self) -> bool:
        raw = self._raw_units()
        self._move_to_units(raw)
        self.wait_move(timeout_s=10)
        confirmed = self._raw_units()
        tolerance_units = max(1, _mm_to_units(float(getattr(config, "STAGE_POSITION_TOLERANCE_MM", 0.002))))
        return abs(confirmed - raw) <= tolerance_units

    def close(self) -> None:
        try:
            self.stop()
        except Exception:
            pass
        try:
            close = getattr(self._stage, "close", None)
            if callable(close):
                close()
        except Exception:
            pass


class MockCamera:
    def __init__(self):
        self._exposure_us = config.EXPOSURE_US
        self._gain_db = config.CAMERA_GAIN_DB
        self._frame_no = 0
        self._temperature = config.MOCK_CAMERA_TEMP_CELSIUS

    def set_exposure(self, us: float) -> None:
        self._exposure_us = float(us)

    def set_gain(self, db: float) -> None:
        self._gain_db = float(db)

    def grab_frame(self, timeout_ms: int = 1000) -> np.ndarray:
        h = config.MOCK_FRAME_HEIGHT
        w = config.MOCK_FRAME_WIDTH
        y, x = np.ogrid[:h, :w]
        t = self._frame_no * 0.05
        cx = w // 2 + 60 * math.sin(t)
        cy = h // 2 + 40 * math.cos(t * 0.7)
        blob = 180 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 60 ** 2))
        blob *= self._exposure_us / 100000.0
        frame = np.random.poisson(np.clip(blob, 0, 255)).astype(np.float32)
        self._frame_no += 1
        return np.clip(frame, 0, 255).astype(np.uint8)

    def health_check(self) -> bool:
        return self.grab_frame().size > 0

    @property
    def temperature(self) -> float:
        self._temperature += np.random.normal(0, 0.02)
        return round(self._temperature, 2)

    def close(self) -> None:
        pass


class RealCamera:
    def __init__(self):
        from pypylon import pylon

        factory = pylon.TlFactory.GetInstance()
        devices = factory.EnumerateDevices()
        if not devices:
            raise RuntimeError("No Basler camera detected")
        self._cam = pylon.InstantCamera(factory.CreateDevice(devices[0]))
        self._cam.Open()
        self._cam.ExposureTime.SetValue(config.EXPOSURE_US)
        self._temperature_ok = hasattr(self._cam, "DeviceTemperature")

    def set_exposure(self, us: float) -> None:
        self._cam.ExposureTime.SetValue(float(us))

    def set_gain(self, db: float) -> None:
        try:
            self._cam.Gain.SetValue(float(db))
        except Exception:
            pass

    def grab_frame(self, timeout_ms: int = 5000) -> np.ndarray:
        result = self._cam.GrabOne(int(timeout_ms))
        try:
            if result.GrabSucceeded():
                return np.array(result.Array, copy=True)
            raise RuntimeError("Camera grab failed")
        finally:
            try:
                result.Release()
            except Exception:
                pass

    def health_check(self) -> bool:
        if hasattr(self._cam, "IsCameraDeviceRemoved") and self._cam.IsCameraDeviceRemoved():
            return False
        if hasattr(self._cam, "IsOpen") and not self._cam.IsOpen():
            return False
        frame = self.grab_frame(timeout_ms=1000)
        return frame.size > 0

    @property
    def temperature(self) -> float:
        if self._temperature_ok:
            return float(self._cam.DeviceTemperature.GetValue())
        return -999.0

    def close(self) -> None:
        try:
            if hasattr(self._cam, "StopGrabbing") and self._cam.IsGrabbing():
                self._cam.StopGrabbing()
        except Exception:
            pass
        try:
            if hasattr(self._cam, "IsOpen") and self._cam.IsOpen():
                self._cam.Close()
        except Exception:
            pass


class LabController:
    """Singleton-safe lab controller with real health checks and mock fallback."""

    _instance: "LabController | None" = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    @classmethod
    def instance(cls) -> "LabController":
        return cls()

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._closed = False
        self._running = True
        self._stage_access_lock = threading.RLock()
        self._camera_access_lock = threading.RLock()
        self._frame_lock = threading.RLock()
        self._hardware_lock = HardwareProcessLock(getattr(config, "HARDWARE_LOCK_PATH", "logs/hardware_owner.lock"))
        self._real_hw_allowed = False
        self._last_error = ""
        self._processing_enabled = False
        self._camera_stream_enabled = True

        self.stage: MockStage | RealStage | None = None
        self.camera: RealCamera | None = None
        self._fallback_camera: MockCamera = MockCamera()
        self._stage_physical_connected = False
        self._stage_using_fallback = False
        self._camera_physical_connected = False
        self._camera_using_fallback = True
        self._stage_status = "initializing"
        self._camera_status = "initializing"

        self._live_frame: Optional[bytes] = None
        self._last_frame_ts = 0.0
        self._frame_times = deque(maxlen=30)

        self._initialize_hardware()
        self._cam_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._cam_thread.start()
        self._watchdog_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        self._watchdog_thread.start()
        atexit.register(self.close)

    def _set_last_error(self, message: str) -> None:
        self._last_error = message

    def _initialize_hardware(self) -> None:
        if config.MOCK_MODE:
            self._real_hw_allowed = False
            log_hardware_event("system", "MOCK_MODE enabled; using simulated hardware", severity="INFO")
        else:
            self._real_hw_allowed = self._hardware_lock.acquire()
            if not self._real_hw_allowed:
                self._set_last_error("Another backend process owns the hardware lock")
                log_hardware_event(
                    "system",
                    "Another backend process owns the hardware lock; using mock fallback",
                    error_code="HARDWARE_LOCKED",
                    severity="ERROR",
                )

        if self._real_hw_allowed:
            self._connect_stage_with_retries()
            self._connect_camera_with_retries()
        else:
            self._activate_stage_fallback(RuntimeError(self._last_error or "Mock mode active"))
            self._activate_camera_fallback(RuntimeError(self._last_error or "Mock mode active"))

    def _connect_stage_with_retries(self) -> bool:
        attempts = max(1, int(getattr(config, "HARDWARE_RETRY_COUNT", 3)))
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                candidate = RealStage(serial=config.CONTROLLER_SERIAL_X, channel=1)
                if not candidate.health_check():
                    candidate.close()
                    raise RuntimeError("Stage no-op move health check failed")
                with self._stage_access_lock:
                    old = self.stage
                    self.stage = candidate
                    self._stage_physical_connected = True
                    self._stage_using_fallback = False
                    self._stage_status = "connected"
                if old and old is not candidate:
                    old.close()
                log_hardware_event("stage", "Stage connected and health check passed", severity="INFO")
                return True
            except Exception as exc:
                last_exc = exc
                self._set_last_error(f"Stage connect attempt {attempt} failed: {exc}")
                log_hardware_event(
                    "stage",
                    f"Stage connect attempt {attempt}/{attempts} failed",
                    error=exc,
                    error_code="STAGE_CONNECT_FAILED",
                )
                time.sleep(0.35)
        self._activate_stage_fallback(last_exc or RuntimeError("Stage unavailable"))
        return False

    def _connect_camera_with_retries(self) -> bool:
        attempts = max(1, int(getattr(config, "HARDWARE_RETRY_COUNT", 3)))
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                candidate = RealCamera()
                frame = candidate.grab_frame(timeout_ms=1500)
                if frame.size == 0:
                    candidate.close()
                    raise RuntimeError("Camera health check returned empty frame")
                with self._camera_access_lock:
                    old = self.camera
                    self.camera = candidate
                    self._camera_physical_connected = True
                    self._camera_using_fallback = False
                    self._camera_status = "connected"
                if old and old is not candidate:
                    old.close()
                log_hardware_event("camera", "Camera connected and frame grab health check passed", severity="INFO")
                return True
            except Exception as exc:
                last_exc = exc
                self._set_last_error(f"Camera connect attempt {attempt} failed: {exc}")
                log_hardware_event(
                    "camera",
                    f"Camera connect attempt {attempt}/{attempts} failed",
                    error=exc,
                    error_code="CAMERA_CONNECT_FAILED",
                )
                time.sleep(0.35)
        self._activate_camera_fallback(last_exc or RuntimeError("Camera unavailable"))
        return False

    def _activate_stage_fallback(self, error: Exception) -> None:
        self._set_last_error(str(error))
        log_hardware_event(
            "stage",
            "Stage switched to mock fallback",
            error=error,
            error_code="STAGE_FALLBACK",
            severity="WARNING" if config.MOCK_MODE else "ERROR",
        )
        position_mm = 0.0
        try:
            if self.stage is not None:
                position_mm = float(getattr(self.stage, "position_mm", 0.0))
                self.stage.close()
        except Exception:
            position_mm = 0.0
        self.stage = MockStage("X", initial_position_mm=position_mm)
        self._stage_physical_connected = False
        self._stage_using_fallback = True
        self._stage_status = "simulation" if config.MOCK_MODE else "fallback"

    def _activate_camera_fallback(self, error: Exception) -> None:
        self._set_last_error(str(error))
        log_hardware_event(
            "camera",
            "Camera switched to mock fallback",
            error=error,
            error_code="CAMERA_FALLBACK",
            severity="WARNING" if config.MOCK_MODE else "ERROR",
        )
        try:
            if self.camera is not None:
                self.camera.close()
        except Exception:
            pass
        self.camera = None
        self._camera_physical_connected = False
        self._camera_using_fallback = True
        self._camera_status = "mock" if config.MOCK_MODE else "busy_disconnected"
        if self._fallback_camera is None:
            self._fallback_camera = MockCamera()

    def _camera_loop(self) -> None:
        import cv2

        while self._running:
            if not self._camera_stream_enabled:
                time.sleep(0.1)
                continue
            try:
                raw = self.capture_frame(fail_on_real_error=False)
                ok, buf = cv2.imencode(".jpg", raw, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    self._record_live_frame(buf.tobytes())
            except Exception as exc:
                self._set_last_error(str(exc))
                log_hardware_event("camera", "Camera live loop failed", error=exc, error_code="CAMERA_LOOP")
            time.sleep(0.08 if self._processing_enabled else 0.25)

    def _record_live_frame(self, frame: bytes) -> None:
        now = time.time()
        with self._frame_lock:
            self._live_frame = frame
            self._last_frame_ts = now
            self._frame_times.append(now)

    def _camera_fps(self) -> float:
        with self._frame_lock:
            times = list(self._frame_times)
        if len(times) < 2:
            return 0.0
        elapsed = max(1e-6, times[-1] - times[0])
        return round((len(times) - 1) / elapsed, 2)

    def _camera_frame_fresh(self) -> bool:
        fps = self._camera_fps()
        with self._frame_lock:
            age = time.time() - self._last_frame_ts if self._last_frame_ts else 999.0
            has_frame = self._live_frame is not None
        return bool(
            self._camera_stream_enabled
            and has_frame
            and age < float(getattr(config, "CAMERA_FRAME_STALE_SECONDS", 1.0))
            and fps > float(getattr(config, "CAMERA_MIN_FPS", 0.1))
        )

    def _recovery_loop(self) -> None:
        while self._running:
            time.sleep(max(1.0, float(getattr(config, "HARDWARE_MONITOR_INTERVAL_S", 5.0))))
            if not self._real_hw_allowed or config.MOCK_MODE:
                continue
            try:
                if self._stage_using_fallback:
                    self._connect_stage_with_retries()
                if self._camera_using_fallback and self._camera_stream_enabled:
                    self._connect_camera_with_retries()
            except Exception as exc:
                self._set_last_error(str(exc))
                log_hardware_event("system", "Hardware recovery loop failed", error=exc)

    def detect_hardware(self) -> dict:
        if self._real_hw_allowed and not config.MOCK_MODE:
            if self._stage_using_fallback:
                self._connect_stage_with_retries()
            if self._camera_using_fallback:
                self._connect_camera_with_retries()
        return self.status_dict()

    def capture_frame(self, fail_on_real_error: bool = False) -> np.ndarray:
        with self._camera_access_lock:
            if self.camera is not None and self._camera_physical_connected:
                try:
                    frame = self.camera.grab_frame()
                    self._camera_status = "connected"
                    self._camera_using_fallback = False
                    return frame
                except Exception as exc:
                    self._activate_camera_fallback(exc)
                    if fail_on_real_error:
                        raise RuntimeError(f"Camera frame failure: {exc}") from exc

            try:
                self._camera_using_fallback = True
                self._camera_status = "mock" if config.MOCK_MODE else "busy_disconnected"
                return self._fallback_camera.grab_frame()
            except Exception as exc:
                self._set_last_error(str(exc))
                log_hardware_event("camera", "Mock camera frame failed", error=exc, error_code="MOCK_CAMERA_FAILED")
                raise

    def get_live_jpeg(self) -> Optional[bytes]:
        if not self._camera_frame_fresh():
            return None
        with self._frame_lock:
            return self._live_frame

    def start_camera_stream(self) -> None:
        self._camera_stream_enabled = True
        if self._camera_using_fallback and self._real_hw_allowed and not config.MOCK_MODE:
            self._camera_status = "reconnecting"

    def stop_camera_stream(self) -> None:
        self._camera_stream_enabled = False
        with self._frame_lock:
            self._live_frame = None
            self._last_frame_ts = 0.0
            self._frame_times.clear()
        self._camera_status = "disconnected"

    def set_camera_exposure(self, us: float) -> None:
        with self._camera_access_lock:
            target = self.camera or self._fallback_camera
            target.set_exposure(us)

    def set_camera_gain(self, db: float) -> None:
        with self._camera_access_lock:
            target = self.camera or self._fallback_camera
            target.set_gain(db)

    def _validate_x(self, x_mm: float) -> float:
        value = float(x_mm)
        if value < config.STAGE_X_MIN_MM or value > config.STAGE_X_MAX_MM:
            raise ValueError(
                f"Stage target {value:.5f} mm outside limits "
                f"{config.STAGE_X_MIN_MM:.3f}-{config.STAGE_X_MAX_MM:.3f} mm"
            )
        return value

    def jog(self, direction: int, step_mm: float) -> dict:
        with self._stage_access_lock:
            current = float(getattr(self.stage, "position_mm", 0.0))
            target = self._validate_x(current + (1 if direction >= 0 else -1) * float(step_mm))
        return self.goto(target)

    def goto(self, x_mm: float, fail_on_real_error: bool = False) -> dict:
        target = self._validate_x(x_mm)
        with self._stage_access_lock:
            was_physical = self._stage_physical_connected and isinstance(self.stage, RealStage)
            try:
                self.stage.move_to(target)
                self.stage.wait_move(float(getattr(config, "STAGE_MOVE_TIMEOUT_S", 60.0)))
                actual = (
                    self.stage.confirm_position(target)
                    if isinstance(self.stage, RealStage)
                    else float(self.stage.position_mm)
                )
                log_hardware_event(
                    "stage",
                    "Stage move confirmed",
                    severity="INFO",
                    extra={"commanded_mm": target, "actual_mm": actual},
                )
                return {"commanded_mm": target, "actual_mm": actual}
            except Exception as exc:
                self._activate_stage_fallback(exc)
                if fail_on_real_error and was_physical:
                    raise RuntimeError(f"Stage move failure: {exc}") from exc
                self.stage.move_to(target)
                self.stage.wait_move()
                actual = float(self.stage.position_mm)
                log_hardware_event(
                    "stage",
                    "Fallback stage move confirmed",
                    severity="WARNING",
                    extra={"commanded_mm": target, "actual_mm": actual},
                )
                return {"commanded_mm": target, "actual_mm": actual}

    def home(self) -> dict:
        with self._stage_access_lock:
            try:
                self.stage.home()
                self.stage.wait_move()
                actual = float(self.stage.position_mm)
                log_hardware_event("stage", "Stage home confirmed", severity="INFO", extra={"actual_mm": actual})
                return {"actual_mm": actual, "fallback": self._stage_using_fallback}
            except Exception as exc:
                self._activate_stage_fallback(exc)
                self.stage.home()
                actual = float(self.stage.position_mm)
                log_hardware_event("stage", "Fallback stage home confirmed", severity="WARNING", extra={"actual_mm": actual})
                return {"actual_mm": actual, "fallback": True}

    def zero_calibration(self) -> dict:
        with self._stage_access_lock:
            try:
                if hasattr(self.stage, "zero_here"):
                    self.stage.zero_here()
                actual = float(getattr(self.stage, "position_mm", 0.0))
                log_hardware_event("stage", "Stage zero calibration applied", severity="INFO", extra={"actual_mm": actual})
                return {"actual_mm": actual}
            except Exception as exc:
                self._set_last_error(str(exc))
                log_hardware_event("stage", "Stage zero calibration failed", error=exc, error_code="ZERO_CALIBRATION_FAILED")
                raise

    def move_and_wait(self, x_mm: float, fail_on_real_error: bool = False) -> dict:
        return self.goto(x_mm, fail_on_real_error=fail_on_real_error)

    def set_processing_enabled(self, enabled: bool) -> None:
        self._processing_enabled = bool(enabled)

    def hardware_state(self) -> HardwareState:
        with self._stage_access_lock:
            try:
                stage_moving = bool(getattr(self.stage, "is_moving", False))
            except Exception:
                stage_moving = False

        camera_streaming = self._camera_frame_fresh()
        camera_connected = bool(self._camera_physical_connected and camera_streaming)
        stage_connected = bool(self._stage_physical_connected)
        mode = "REAL" if stage_connected and camera_connected else "MOCK"
        return HardwareState(
            stage_connected=stage_connected,
            stage_moving=stage_moving,
            camera_connected=camera_connected,
            camera_streaming=camera_streaming,
            last_error=self._last_error,
            mode=mode,
        )

    def status_dict(self) -> dict:
        hw_state = self.hardware_state()
        with self._stage_access_lock:
            try:
                stage_pos = round(float(getattr(self.stage, "position_mm", 0.0)), 5)
            except Exception as exc:
                self._set_last_error(str(exc))
                stage_pos = 0.0
            stage_available = bool(hw_state.stage_connected or self._stage_using_fallback)

        with self._frame_lock:
            frame_age = round(time.time() - self._last_frame_ts, 3) if self._last_frame_ts else None

        camera_temp_source = self.camera if self.camera is not None else self._fallback_camera
        camera_status = self._camera_status
        if not self._camera_stream_enabled:
            camera_status = "disconnected"
        elif hw_state.camera_connected:
            camera_status = "connected"
        elif self._camera_using_fallback:
            camera_status = "mock" if config.MOCK_MODE else "busy_disconnected"
        elif self._camera_stream_enabled:
            camera_status = "reconnecting"

        return {
            **hw_state.as_dict(),
            "mock_mode": hw_state.mode == "MOCK",
            "stage_mm": stage_pos,
            "stage_x_mm": stage_pos,
            "stage_y_mm": 0.0,
            "stage_available": stage_available,
            "stage_physical_connected": self._stage_physical_connected,
            "stage_fallback": self._stage_using_fallback,
            "stage_x_moving": hw_state.stage_moving,
            "stage_y_moving": False,
            "stage_status": "moving" if hw_state.stage_moving else self._stage_status,
            "camera_temp": getattr(camera_temp_source, "temperature", -1),
            "camera_physical_connected": self._camera_physical_connected,
            "camera_status": camera_status,
            "camera_locked": "busy" in camera_status or "exclusively" in self._last_error.lower(),
            "camera_stream_available": hw_state.camera_streaming,
            "camera_streaming": hw_state.camera_streaming,
            "camera_frame_rate": self._camera_fps(),
            "camera_frame_age_s": frame_age,
            "camera_fallback_stream": bool(self._camera_using_fallback and hw_state.camera_streaming),
            "camera_stream_enabled": self._camera_stream_enabled,
            "processing_enabled": self._processing_enabled,
            "illumination": True,
            "connected": bool(hw_state.stage_connected and hw_state.camera_connected),
            "hardware_state": hw_state.as_dict(),
        }

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._running = False
        try:
            if self.stage is not None:
                self.stage.close()
        except Exception as exc:
            log_error("STAGE_ERROR", exc)
        try:
            if self.camera is not None:
                self.camera.close()
        except Exception as exc:
            log_error("CAMERA_ERROR", exc)
        try:
            if self._fallback_camera is not None:
                self._fallback_camera.close()
        except Exception:
            pass
        self._hardware_lock.release()


def get_lab_controller() -> LabController:
    return LabController.instance()
