# Project Structure

This file records user-facing project directories that are relevant for running
or customizing HSI-Core.

## Startup UI

- `frontend/assets/splash/` - replaceable startup splash assets.
  - `splash.mp4` - primary startup intro video.
  - `splash.webm` - optional fallback video; add this file when a WebM fallback
    is needed.
  - `splash-poster.png` - poster image shown before video playback begins.
  - `splash-config.json` - splash timing and asset selection.
- `static/css/splash.css` - splash overlay styling.
- `static/js/splash.js` - splash asset loading, backend health polling, video
  cleanup, and transition timing.

## Dashboard Shell

- `static/index.html` - main dashboard HTML shell.
- `static/style.css` - main dashboard styling.
- `static/css/sections.css` - section-specific layout styling.
- `static/app.js` - main dashboard application logic.

## Backend

- `server_enhanced.py` - FastAPI application, static asset mounting, dashboard
  serving, and API routes.

## Generated Runtime Data

- `scans/` - generated scan sessions, raw frames, metadata, manifests, and
  canonical cube files. Ignored by git except `scans/.gitkeep`.
- `data/` - local generated data root for future/operator-managed outputs.
  Ignored by git except `data/.gitkeep`.
- `logs/` - generated runtime logs. Ignored by git except `logs/.gitkeep`.
- `dist/`, `build/`, `.venv/`, `venv/`, `cache/`, `.cache/`, and `temp/` -
  generated local build/runtime folders that should not be committed.

## Storage Tools

- `scripts/storage_audit.py` - reports scan sizes, cube duplication, log size,
  cache/build size, and tracked generated files without deleting data.
- `scripts/cleanup_generated_data.py` - dry-run-first cleanup for generated
  temp/cache/build outputs; scan deletion requires both `--delete-scans` and
  `--yes`.
