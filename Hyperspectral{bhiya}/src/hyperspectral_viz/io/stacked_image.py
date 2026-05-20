from __future__ import annotations

from enum import Enum
from pathlib import Path

import numpy as np
import tifffile

from hyperspectral_viz.cube import HyperspectralCube
from hyperspectral_viz.io.envi import _to_float32


class ImageStackLayout(str, Enum):
    """How spectral bands are arranged in the file(s)."""

    BANDS_FIRST = "bands_first"  # (bands, lines, samples) — common multi-page TIFF
    BANDS_LAST = "bands_last"  # (lines, samples, bands)


def _to_lsb(arr: np.ndarray, layout: ImageStackLayout) -> np.ndarray:
    """Return array shaped (lines, samples, bands)."""
    x = np.asarray(arr)
    if x.ndim == 2:
        return x[..., np.newaxis]
    if x.ndim == 3:
        if layout == ImageStackLayout.BANDS_FIRST:
            b, lines, samples = x.shape
            return np.transpose(x, (1, 2, 0))
        lines, samples, bands = x.shape
        return x
    if x.ndim == 4:
        x = np.squeeze(x)
        if x.ndim == 3:
            return _to_lsb(x, layout)
        raise ValueError(f"Cannot reduce 4-D image array to a cube: original shape {arr.shape}")
    raise ValueError(f"Expected 2-D or 3-D image data, got shape {x.shape}")


def load_stacked_image(path: str | Path, layout: ImageStackLayout = ImageStackLayout.BANDS_FIRST) -> HyperspectralCube:
    """
    Load a single multi-page TIFF or a PNG/TIFF volume.

    Multi-page grayscale stacks are usually ``(bands, height, width)`` → use
    ``ImageStackLayout.BANDS_FIRST``. RGB/planar ``(height, width, bands)`` →
    ``BANDS_LAST``.
    """
    path = Path(path).expanduser().resolve()
    try:
        arr = tifffile.imread(path)
    except Exception as e:
        raise OSError(f"Could not read image {path}: {e}") from e
    data = _to_float32(_to_lsb(arr, layout))
    meta = {"source_image": str(path), "layout": layout.value}
    return HyperspectralCube(data=data, wavelengths_nm=None, meta=meta)


def load_stacked_image_files(
    paths: list[str | Path],
    layout: ImageStackLayout = ImageStackLayout.BANDS_FIRST,
) -> HyperspectralCube:
    """
    Load several TIFF/PNG files and stack them along the spectral axis (sorted by path).

    Each file must yield the same spatial size after conversion to (lines, samples, ?).
    A 2-D file becomes one band; a 3-D file becomes multiple bands on the last axis
    (when using ``BANDS_LAST``) or first axis (``BANDS_FIRST``).
    """
    if not paths:
        raise ValueError("No paths given")
    paths_sorted = sorted(Path(p).expanduser().resolve() for p in paths)
    planes: list[np.ndarray] = []
    for p in paths_sorted:
        if p.suffix.lower() not in {".tif", ".tiff", ".png"}:
            raise ValueError(f"Unsupported extension for stack: {p.name}")
        try:
            arr = tifffile.imread(p)
        except Exception as e:
            raise OSError(f"Could not read {p}: {e}") from e
        cube = _to_lsb(np.asarray(arr), layout)
        planes.append(cube)

    lines, samples, ref_b = planes[0].shape
    out_bands: list[np.ndarray] = []
    for i, c in enumerate(planes):
        if c.shape[0] != lines or c.shape[1] != samples:
            raise ValueError(
                f"Spatial shape mismatch at {paths_sorted[i].name}: "
                f"{c.shape[:2]} vs {(lines, samples)}"
            )
        out_bands.append(c)
    stacked = np.concatenate(out_bands, axis=2)
    data = _to_float32(stacked)
    names = ", ".join(p.name for p in paths_sorted[:5])
    if len(paths_sorted) > 5:
        names += ", …"
    meta = {
        "source_image_stack": names,
        "n_files": len(paths_sorted),
        "layout": layout.value,
    }
    return HyperspectralCube(data=data, wavelengths_nm=None, meta=meta)
