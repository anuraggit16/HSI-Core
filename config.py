# =============================================================================
# HSI-Core — Instrument Configuration
# =============================================================================
# All hardware constants and operational defaults live here.
# Toggle MOCK_MODE to switch between simulated and real hardware.
# =============================================================================

# -----------------------------------------------------------------------------
# OPERATING MODE
# -----------------------------------------------------------------------------

MOCK_MODE = False          # True  -> run with simulated hardware (no physical devices needed)
                          # False -> connect to real Thorlabs stage + Basler camera
DEBUG_MODE = False         # True -> expose extra diagnostics in logs/API responses
AUTO_FALLBACK_TO_MOCK = False
HARDWARE_RETRY_COUNT = 5
HARDWARE_LOCK_PATH = "logs/hardware_owner.lock"

# -----------------------------------------------------------------------------
# HARDWARE IDENTIFIERS
# -----------------------------------------------------------------------------

CONTROLLER_SERIAL_X = "103425854"   # 0-300 mm linear stage
CONTROLLER_SERIAL_Y = ""            # 0-600 mm linear stage; blank auto-detects the second serial
CONTROLLER_CHANNEL_X = 0             # 0 = auto-detect Channel 1 or Channel 2
CAMERA_SERIAL = "40700005"

# Prefer the official Thorlabs Kinesis C API installed with Kinesis on Windows.
KINESIS_USE_OFFICIAL_SDK = True
KINESIS_ALLOW_PYLABLIB_FALLBACK = False
KINESIS_INSTALL_DIR = r"C:\Program Files\Thorlabs\Kinesis"
KINESIS_POLL_INTERVAL_MS = 100

# -----------------------------------------------------------------------------
# STAGE CALIBRATION
# -----------------------------------------------------------------------------

UNITS_PER_MM = 20_000   # Device units per millimetre (experimentally calibrated)
                         # 20 000 units = 1 mm  →  80 mm = 1 600 000 units

# Corrects the observed +0.00010 mm systematic offset by commanding target-offset.
STAGE_CALIBRATION_OFFSET_MM = 0.00010
STAGE_POSITION_TOLERANCE_MM = 0.002
STAGE_MOVE_TIMEOUT_S = 60.0
STAGE_HOME_TIMEOUT_S = 90.0
STAGE_HOME_TOLERANCE_MM = 0.002
STAGE_POSITION_POLL_INTERVAL_S = 0.2
STAGE_POLL_ERROR_LOG_INTERVAL_S = 5.0
STAGE_ERROR_LOG_THROTTLE_S = 30.0
STAGE_BACKGROUND_POLL_ENABLED = False
STAGE_POSITION_STALE_SECONDS = 1.5
STAGE_BACKLASH_CORRECTION_ENABLED = False
STAGE_BACKLASH_CORRECTION_MM = 0.02

# Stage travel limits (mm)
STAGE_X_MIN_MM = 0.0
STAGE_X_MAX_MM = 300.0
STAGE_Y_MIN_MM = 0.0
STAGE_Y_MAX_MM = 600.0

# Stage velocity profile
# Change these two limits here if the BBD302/DDS300 safe motion ceiling must be raised.
STAGE_SAFE_MAX_VELOCITY_MM_S = 50.0
STAGE_SAFE_MAX_ACCELERATION_MM_S2 = 1000.0
STAGE_MIN_VELOCITY  = 20_000    # units/s
STAGE_MAX_VELOCITY  = int(round(STAGE_SAFE_MAX_VELOCITY_MM_S * UNITS_PER_MM))
STAGE_SCAN_VELOCITY_MM_S = 8.0   # Default commanded scan speed in mm/s
STAGE_MIN_VELOCITY_MM_S = 0.01   # Non-zero UI/API safety floor
STAGE_MAX_VELOCITY_MM_S = STAGE_SAFE_MAX_VELOCITY_MM_S
STAGE_MIN_ACCELERATION_MM_S2 = 0.1
STAGE_MAX_ACCELERATION_MM_S2 = STAGE_SAFE_MAX_ACCELERATION_MM_S2
STAGE_JOG_VELOCITY_MM_S = 10.0
STAGE_JOG_ACCELERATION_MM_S2 = 100.0
STAGE_JOG_MIN_STEP_MM = 0.0001
STAGE_JOG_MAX_STEP_MM = 25.0
STAGE_ACCELERATION  = int(round(STAGE_JOG_ACCELERATION_MM_S2 * UNITS_PER_MM))   # units/s²

# -----------------------------------------------------------------------------
# DEFAULT SCAN PARAMETERS
# -----------------------------------------------------------------------------

SCAN_START_X_MM  = 80.0     # Scan area — X start
SCAN_START_Y_MM  = 80.0     # Scan area — Y start
SCAN_END_X_MM    = 180.0    # Scan area — X end
SCAN_END_Y_MM    = 100.0    # Scan area — Y end (1D → set equal to START_Y)
SCAN_STEP_X_MM   = 0.1      # Step size in X (100 µm)
SCAN_STEP_Y_MM   = 1.0      # Step size in Y (1 mm per row)
SCAN_MAX_FRAMES  = 10000    # Hard safety limit for one scan plan
SCAN_STORAGE_WARN_MB = 2048 # UI/API warning threshold for estimated output size

SETTLING_TIME_S  = 0.1      # Seconds to wait after move before capture

RASTER_PATTERN   = "serpentine"   # "serpentine" or "grid"

# -----------------------------------------------------------------------------
# SPECTRAL AXIS
# -----------------------------------------------------------------------------

SPECTRAL_MIN_NM  = 400     # Minimum wavelength (nm)
SPECTRAL_MAX_NM  = 1000    # Maximum wavelength (nm)
SPECTRAL_BANDS   = 120     # Number of spectral bands (mock mode synthesises these)

# -----------------------------------------------------------------------------
# CAMERA
# -----------------------------------------------------------------------------

EXPOSURE_MS      = 100          # Default exposure in milliseconds
EXPOSURE_US      = EXPOSURE_MS * 1000   # Converted to microseconds for pypylon
CAMERA_GAIN_DB   = 0.0          # Default analogue gain
CAMERA_MIN_EXPOSURE_MS = 0.01   # Real Basler limits are read from pypylon when available
CAMERA_MAX_EXPOSURE_MS = 20000.0
CAMERA_EXPOSURE_TIMEOUT_MARGIN_MS = 2000.0
CAMERA_MIN_GAIN_DB = 0.0
CAMERA_MAX_GAIN_DB = 24.0
CAMERA_FRAME_STALE_SECONDS = 1.0
CAMERA_MIN_FPS = 0.1
CAMERA_ERROR_LOG_INTERVAL_S = 10.0
CAMERA_FEATURE_MAX_NODES = 600

IMAGE_FORMAT     = ".png"

# -----------------------------------------------------------------------------
# STORAGE
# -----------------------------------------------------------------------------

SAVE_FOLDER      = "scans"         # Root folder for timestamped scan and analysis sessions
MAX_UPLOAD_BYTES = 4 * 1024 * 1024 * 1024

# Generated-data policy. Defaults preserve raw scientific frames and avoid
# duplicate full-size cube formats for new scans.
STORAGE_POLICY = {
    "keep_raw_frames": True,
    "keep_npy_cube": False,
    "keep_npz_cube": True,
    "compression": True,
    "preview_downsample": True,
    "max_log_mb": 10,
    "backup_before_cleanup": False,
}

# -----------------------------------------------------------------------------
# MOCK SIMULATION PARAMETERS
# -----------------------------------------------------------------------------

MOCK_STAGE_VELOCITY_MM_S = 10.0   # Simulated stage speed
MOCK_FRAME_WIDTH         = 640
MOCK_FRAME_HEIGHT        = 480
MOCK_CAMERA_TEMP_CELSIUS = 22.5   # Simulated sensor temperature

# -----------------------------------------------------------------------------
# SERVER
# -----------------------------------------------------------------------------

SERVER_HOST      = "0.0.0.0"
SERVER_PORT      = 8000
WS_BROADCAST_HZ  = 5           # WebSocket telemetry broadcast frequency

# =============================================================================
# ENHANCED FEATURES — Dataset & Analysis
# =============================================================================

# Dataset Storage
DATASET_BASE_PATH = "datasets"   # Root directory for TIFF stacks
COMPRESS_CUBES = True             # Backward-compatible alias for compressed .npz output
CUBE_COMPRESS_MAX_BYTES = 512 * 1024 * 1024
MAX_DATASET_AGE_DAYS = 90         # Auto-archive old datasets

# Analysis Configuration
ROI_EXPORT_FORMAT = "tiff"        # "tiff" or "hdf5"
ENABLE_SPECTRAL_CLUSTERING = True
CLUSTERING_ALGORITHMS = ["kmeans", "dbscan"]

# UI/UX Configuration
DARK_MODE = True
ENABLE_ADVANCED_ANALYSIS = True
CHART_UPDATE_INTERVAL_MS = 500
MAX_WEBSOCKET_CLIENTS = 100

# Hardware Monitoring
HARDWARE_MONITOR_INTERVAL_S = 5.0
CAMERA_WATCHDOG_INTERVAL_S = 2.5
AUTO_DETECT_HARDWARE = True
AUTO_RECONNECT_ENABLED = True
