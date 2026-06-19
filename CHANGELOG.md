# Changelog

## 2026-06-19

- Added `STORAGE_AUDIT_REPORT.md` documenting generated scan, cube, log, build,
  and git-index storage pressure.
- Added a config-based storage policy that keeps raw scientific frames by
  default while making compressed `.npz` the canonical new cube output and
  keeping duplicate `.npy` cubes opt-in.
- Added `.npz` cube loading support and lightweight cube-context caching so
  repeated preview requests do not repeatedly decompress the same cube.
- Added size-based rotation for generated system, hardware, and error
  knowledge-base logs.
- Added `scripts/storage_audit.py` and `scripts/cleanup_generated_data.py` for
  dry-run-first storage inspection and cleanup.
- Updated generated-data `.gitignore` hygiene and kept `scans/`, `data/`, and
  `logs/` placeholders.

## 2026-06-18

- Added a replaceable startup splash asset directory at
  `frontend/assets/splash/` with configurable video, poster, timing, and
  fallback behavior.
- Added a professional splash overlay that plays the intro once, fades away
  from the final video frame, shows a compact loading state while the backend
  starts, and unloads video resources after the dashboard is ready.
- Added read-only `GET /api/health` startup readiness reporting and static
  serving for `frontend/` assets without initializing hardware or changing
  acquisition, camera, stage, scan, websocket telemetry, cube loading, or
  Analysis behavior.
- Set the replaceable splash video to request audio and run for 9 seconds
  before fading to the backend-waiting state.

## 2026-06-06

- Changed normal Windows browser launch to use the detected LAN dashboard by
  default, added `--local` to force loopback access, and retained automatic
  local fallback when no LAN IPv4 address is available.
- Changed the Windows launcher and startup redirect to open
  `http://127.0.0.1:8000` for reliable same-PC dashboard access while keeping
  the backend bound to `0.0.0.0:8000` for optional LAN access.
- Added detected LAN URL, firewall guidance, port 8000 PID/process reporting,
  and `/api/status` health diagnostics to normal startup and `--check`.
- Added explicit `--allow-lan-firewall` mode that creates only the
  `HSI-Core Dashboard TCP 8000` inbound rule for Private Windows network
  profiles, with administrator, network-profile, and trusted-network warnings.
- Made `RUN_HSI_CORE.bat` portable across Windows PCs by resolving project
  paths from `%~dp0` and selecting Python through `py -3.12`, `py -3`, or
  `python`.
- Added detection and automatic recreation of copied or broken `.venv`
  environments before invoking pip.
- Added clear Python, virtual-environment, and failing dependency command
  output, plus a non-starting `--check` verification mode.
- Added the known-working Basler `pypylon 26.4.1` and Thorlabs
  `pylablib 1.4.5` runtime dependencies to `requirements.txt` so a rebuilt
  environment preserves hardware support.

## 2026-06-05

- Added mode-specific cube viewer controls:
  - Spatial X-Y at lambda activates only the wavelength selector.
  - Spectrum at X,Y activates only X and Y selectors.
  - Y-lambda at X activates only the X selector.
  - X-lambda at Y activates only the Y selector.
- Added normalized cube metadata fields to saved cube generation and cube API responses, including `cube_shape`, `dimension_order`, axis arrays, frame count, dtype, source folder, and creation timestamp.
- Added explicit backend cube slice helpers for spatial slices, spectra, Y-lambda slices, and X-lambda slices.
- Added frontend debouncing and small slice/spectrum caches to avoid excessive rerenders while moving controls.
- Preserved scan, camera, stage, frame saving, and `.npy` generation behavior.
