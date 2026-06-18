# Analysis Module Changelog

## v1.0.0 - Baseline

Date: 2026-06-18

Commit target: `analysis-v1.0.0-baseline`

### Baseline Scope

- Analysis module versioning starts at `v1.0.0`.
- The application header shows `Analysis v1.0.0` while preserving the existing HSI Acquisition version label.
- Analysis workspace remains separate from Acquisition controls and hardware operation.
- Acquisition, camera, stage, scan, hardware, installer, and backend acquisition logic are outside this baseline scope.

### Baseline Features Recorded

- Dedicated Analysis tab/workspace.
- File upload entry points for TIFF, image, MAT, NPY, HDF5, CSV, ENVI HDR/data pairs.
- Main hyperspectral analysis workbench with large preview/volume area.
- Current frame/band preview panel.
- Spectral profile plot.
- Intensity histogram panel.
- Compact right-side Analysis controls for frame, band, zoom, opacity, floor, ceiling, visible planes, brightness, contrast, gamma, and palette.
- Compact Analysis stats/metadata cards for size, bands, mean, peak, standard deviation, range, SNR, preview mode, source metadata, cursor X/Y, selected band, and cube size.
- Long Analysis source names, preview labels, session names, and metadata values are intended to remain bounded to the Analysis panel width.

### Baseline Screenshot Records

Screenshots captured for this baseline:

- `docs/analysis/screenshots/analysis-v1.0.0-workspace.png` - Analysis workspace baseline.

### Hardware Safety Notes

- No hardware movement behavior changed.
- No camera acquisition behavior changed.
- No scan pipeline behavior changed.
- No websocket acquisition lifecycle behavior changed.
