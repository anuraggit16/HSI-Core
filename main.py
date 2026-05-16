# =========================================================
# FINAL AUTOMATED SCAN CODE
# =========================================================
#
# HARDWARE
# --------
# - Thorlabs BBD302
# - DDS300/M Stage
# - Basler Camera
#
# TASK
# ----
# - Start from 80 mm
# - Capture 1000 images
# - 100 micrometer step size
# - 100 millisecond exposure
#
# IMPORTANT
# ---------
# Your stage is using DEVICE UNITS
#
# Calibration found experimentally:
#
# 20000 units = 1 mm
#
# Therefore:
#
# 80 mm  = 1600000 units
# 0.1 mm = 2000 units
#
# =========================================================

from pylablib.devices import Thorlabs
from pypylon import pylon

import cv2
import os
import time

# =========================================================
# USER SETTINGS
# =========================================================

# ---------------------------------
# CONTROLLER
# ---------------------------------

CONTROLLER_SERIAL = "103425854"

# ---------------------------------
# CALIBRATION
# ---------------------------------

UNITS_PER_MM = 20000

# ---------------------------------
# SCAN SETTINGS
# ---------------------------------

START_MM = 80

STEP_SIZE_MM = 1

NUM_IMAGES = 10

# ---------------------------------
# CAMERA
# ---------------------------------

EXPOSURE_MS = 100

# ---------------------------------
# STAGE SPEED
# ---------------------------------

MAX_VELOCITY = 300000

ACCELERATION = 500000

# ---------------------------------
# WAIT TIME
# ---------------------------------

SETTLING_TIME = 0.1

# ---------------------------------
# SAVE SETTINGS
# ---------------------------------

SAVE_FOLDER = "scan_images"

IMAGE_FORMAT = ".png"

# =========================================================
# UNIT CONVERSION
# =========================================================

START_POSITION = int(START_MM * UNITS_PER_MM)

STEP_SIZE = int(STEP_SIZE_MM * UNITS_PER_MM)

EXPOSURE_US = EXPOSURE_MS * 1000

# =========================================================
# CREATE SAVE FOLDER
# =========================================================

os.makedirs(SAVE_FOLDER, exist_ok=True)

# =========================================================
# START MESSAGE
# =========================================================

print("\n========================================")
print("AUTOMATED HYPERSPECTRAL SCAN")
print("========================================")

print(f"\nStart Position : {START_MM} mm")
print(f"Step Size      : {STEP_SIZE_MM} mm")
print(f"Images          : {NUM_IMAGES}")
print(f"Exposure        : {EXPOSURE_MS} ms")

# =========================================================
# CONNECT STAGE
# =========================================================

print("\nConnecting Stage...")

stage = Thorlabs.KinesisMotor(
    CONTROLLER_SERIAL,
    is_rack_system=True,
    default_channel=1
)

# =========================================================
# SPEED SETTINGS
# =========================================================

# Kinesis minimal velocity is effectively always zero on this controller,
# so we rely on acceleration and max velocity for a faster stage start.
stage.setup_velocity(
    max_velocity=MAX_VELOCITY,
    acceleration=ACCELERATION
)

print("Stage Connected")
print(f"Stage velocity: max={MAX_VELOCITY}, accel={ACCELERATION}")

# =========================================================
# CONNECT CAMERA
# =========================================================

print("\nConnecting Basler Camera...")

camera = pylon.InstantCamera(
    pylon.TlFactory.GetInstance().CreateFirstDevice()
)

camera.Open()

camera.ExposureTime.SetValue(EXPOSURE_US)

print("Camera Connected")

print("Camera Model:")
print(camera.GetDeviceInfo().GetModelName())

# =========================================================
# MOVE TO 80 mm START POSITION
# =========================================================

print("\n========================================")
print("MOVING TO START POSITION")
print("========================================")

print(f"Moving to {START_MM} mm")

stage.move_to(START_POSITION)

stage.wait_move()

time.sleep(2)

print("Reached Start Position")

# =========================================================
# MAIN SCAN LOOP
# =========================================================

for i in range(NUM_IMAGES):

    print("\n----------------------------------------")
    print(f"Image : {i+1} / {NUM_IMAGES}")

    # -----------------------------------------------------
    # CURRENT POSITION
    # -----------------------------------------------------

    current_position_units = (
        START_POSITION + (i * STEP_SIZE)
    )

    current_position_mm = (
        current_position_units / UNITS_PER_MM
    )

    print(f"Position : {current_position_mm:.3f} mm")

    # -----------------------------------------------------
    # MOVE STAGE
    # -----------------------------------------------------

    stage.move_to(current_position_units)

    stage.wait_move()

    # -----------------------------------------------------
    # WAIT FOR STABILITY
    # -----------------------------------------------------

    time.sleep(SETTLING_TIME)

    # -----------------------------------------------------
    # CAPTURE IMAGE
    # -----------------------------------------------------

    grab = camera.GrabOne(5000)

    # -----------------------------------------------------
    # SAVE IMAGE
    # -----------------------------------------------------

    if grab.GrabSucceeded():

        image = grab.Array

        filename = os.path.join(
            SAVE_FOLDER,
            f"img_{i:04d}_{current_position_mm:.3f}mm{IMAGE_FORMAT}"
        )

        cv2.imwrite(filename, image)

        print(f"Saved : {filename}")

    else:

        print("ERROR : Image Capture Failed")

# =========================================================
# CLOSE DEVICES
# =========================================================

print("\nClosing Devices...")

camera.Close()

stage.close()

# =========================================================
# FINISH
# =========================================================

print("\n========================================")
print("SCAN COMPLETED SUCCESSFULLY")
print("========================================")

print(f"\nImages Saved In : {SAVE_FOLDER}")