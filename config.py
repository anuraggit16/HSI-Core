# =============================================================================
# HSI-Core — Instrument Configuration
# =============================================================================
# All hardware constants and operational defaults live here.
# Toggle MOCK_MODE to switch between simulated and real hardware.
# =============================================================================

# -----------------------------------------------------------------------------
# OPERATING MODE
# -----------------------------------------------------------------------------

MOCK_MODE = True          # True  → run with simulated hardware (no physical devices needed)
                          # False → connect to real Thorlabs stage + Basler camera

# -----------------------------------------------------------------------------
# HARDWARE IDENTIFIERS
# -----------------------------------------------------------------------------

CONTROLLER_SERIAL_X = "103425854"   # Thorlabs BBD302 channel 1 (X axis)
CONTROLLER_SERIAL_Y = "103425854"   # Thorlabs BBD302 channel 2 (Y axis) — set to same rack

# -----------------------------------------------------------------------------
# STAGE CALIBRATION
# -----------------------------------------------------------------------------

UNITS_PER_MM = 20_000   # Device units per millimetre (experimentally calibrated)
                         # 20 000 units = 1 mm  →  80 mm = 1 600 000 units

# Stage travel limits (mm)
STAGE_X_MIN_MM = 0.0
STAGE_X_MAX_MM = 300.0
STAGE_Y_MIN_MM = 0.0
STAGE_Y_MAX_MM = 300.0

# Stage velocity profile
STAGE_MIN_VELOCITY  = 20_000    # units/s
STAGE_MAX_VELOCITY  = 300_000   # units/s
STAGE_ACCELERATION  = 500_000   # units/s²

# -----------------------------------------------------------------------------
# DEFAULT SCAN PARAMETERS
# -----------------------------------------------------------------------------

SCAN_START_X_MM  = 80.0     # Scan area — X start
SCAN_START_Y_MM  = 80.0     # Scan area — Y start
SCAN_END_X_MM    = 180.0    # Scan area — X end
SCAN_END_Y_MM    = 100.0    # Scan area — Y end (1D → set equal to START_Y)
SCAN_STEP_X_MM   = 0.1      # Step size in X (100 µm)
SCAN_STEP_Y_MM   = 1.0      # Step size in Y (1 mm per row)

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

IMAGE_FORMAT     = ".png"

# -----------------------------------------------------------------------------
# STORAGE
# -----------------------------------------------------------------------------

SAVE_FOLDER      = "scan_images"   # Root folder for all sessions

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
