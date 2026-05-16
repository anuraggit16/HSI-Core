# =============================================================================
# HSI-Core — Enhanced Hardware Detection & Auto-Connection
# =============================================================================
# Automatically detects and connects to available lab hardware.
# Provides unified interface for both mock and real devices.
# =============================================================================

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Tuple

import config

logger = logging.getLogger(__name__)


class HardwareType(str, Enum):
    STAGE_X = "stage_x"
    STAGE_Y = "stage_y"
    CAMERA = "camera"


@dataclass
class HardwareDevice:
    type: HardwareType
    name: str
    serial: str
    connected: bool
    model: Optional[str] = None
    status: str = "idle"


class HardwareDetector:
    """Scans for and detects connected lab hardware."""
    
    @staticmethod
    def detect_thorlabs_stage(serial: str) -> Optional[HardwareDevice]:
        """Attempt to detect Thorlabs BBD302 stage."""
        try:
            if config.MOCK_MODE:
                return HardwareDevice(
                    type=HardwareType.STAGE_X,
                    name="Thorlabs BBD302 (X axis)",
                    serial=serial,
                    connected=True,
                    model="BBD302"
                )
            
            from pylablib.devices import Thorlabs
            stage = Thorlabs.KinesisMotor(serial, is_rack_system=True, default_channel=1)
            stage.close()
            
            return HardwareDevice(
                type=HardwareType.STAGE_X,
                name="Thorlabs BBD302 (X axis)",
                serial=serial,
                connected=True,
                model="BBD302"
            )
        except Exception as e:
            logger.warning(f"Failed to detect Thorlabs stage {serial}: {e}")
            return None
    
    @staticmethod
    def detect_basler_camera() -> Optional[HardwareDevice]:
        """Attempt to detect Basler camera."""
        try:
            if config.MOCK_MODE:
                return HardwareDevice(
                    type=HardwareType.CAMERA,
                    name="Basler Camera",
                    serial="mock-camera",
                    connected=True,
                    model="Basler ace2 Pro"
                )
            
            from pypylon import pylon
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            if devices:
                device_info = devices[0]
                return HardwareDevice(
                    type=HardwareType.CAMERA,
                    name="Basler Camera",
                    serial=device_info.GetSerialNumber(),
                    connected=True,
                    model=device_info.GetModelName()
                )
        except Exception as e:
            logger.warning(f"Failed to detect Basler camera: {e}")
        
        return None
    
    @staticmethod
    def detect_all() -> Dict[str, HardwareDevice]:
        """Perform full hardware detection scan."""
        devices = {}
        
        # Detect stages
        stage_x = HardwareDetector.detect_thorlabs_stage(config.CONTROLLER_SERIAL_X)
        if stage_x:
            devices['stage_x'] = stage_x
        
        stage_y = HardwareDetector.detect_thorlabs_stage(config.CONTROLLER_SERIAL_Y)
        if stage_y:
            devices['stage_y'] = stage_y
        
        # Detect camera
        camera = HardwareDetector.detect_basler_camera()
        if camera:
            devices['camera'] = camera
        
        logger.info(f"Hardware detection complete: {len(devices)} devices found")
        return devices


class HardwareMonitor:
    """Continuously monitors hardware health and connection status."""
    
    def __init__(self, check_interval_s: float = 5.0):
        self.check_interval_s = check_interval_s
        self.devices: Dict[str, HardwareDevice] = {}
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
    
    def start_monitoring(self):
        """Start background hardware monitor thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Hardware monitor started")
    
    def stop_monitoring(self):
        """Stop hardware monitor thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Hardware monitor stopped")
    
    def _monitor_loop(self):
        """Background thread that periodically checks hardware."""
        while self._running:
            try:
                detected = HardwareDetector.detect_all()
                
                with self._lock:
                    # Update connection status
                    for key in list(self.devices.keys()):
                        if key not in detected:
                            self.devices[key].connected = False
                    
                    # Add newly detected devices
                    self.devices.update(detected)
                
                time.sleep(self.check_interval_s)
            
            except Exception as e:
                logger.error(f"Hardware monitor error: {e}")
                time.sleep(self.check_interval_s)
    
    def get_status(self) -> Dict[str, HardwareDevice]:
        """Get current hardware status."""
        with self._lock:
            return dict(self.devices)
    
    def is_ready(self) -> bool:
        """Check if all required hardware is connected."""
        with self._lock:
            has_stage = any(d.connected and 'stage' in k for k, d in self.devices.items())
            has_camera = any(d.connected and 'camera' in k for k, d in self.devices.items())
            return has_stage and has_camera


# Global monitor instance
hardware_monitor = HardwareMonitor()
