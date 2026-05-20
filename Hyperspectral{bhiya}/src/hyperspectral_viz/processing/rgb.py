from __future__ import annotations

import numpy as np


def percentile_stretch(
    image: np.ndarray,
    low_pct: float = 2.0,
    high_pct: float = 98.0,
) -> np.ndarray:
    """Stretch single- or multi-band image to [0, 1] using percentiles."""
    out = np.empty_like(image, dtype=np.float32)
    for c in range(image.shape[-1]):
        band = image[..., c].astype(np.float64, copy=False).ravel()
        lo, hi = np.percentile(band, (low_pct, high_pct))
        hi = max(hi, lo + 1e-9)
        ch = (image[..., c].astype(np.float64) - lo) / (hi - lo)
        out[..., c] = np.clip(ch, 0.0, 1.0).astype(np.float32)
    return out


def rgb_composite(
    cube: np.ndarray,
    band_r: int,
    band_g: int,
    band_b: int,
    low_pct: float = 2.0,
    high_pct: float = 98.0,
) -> np.ndarray:
    """
    Build an RGB image from cube (lines, samples, bands).

    Returns float32 array (lines, samples, 3) in [0, 1].
    """
    if cube.ndim != 3:
        raise ValueError("cube must be (lines, samples, bands)")
    n = cube.shape[2]
    for b in (band_r, band_g, band_b):
        if not 0 <= b < n:
            raise IndexError(f"Band index {b} out of range for {n} bands")
    stack = np.stack(
        [cube[..., band_r], cube[..., band_g], cube[..., band_b]],
        axis=-1,
    )
    return percentile_stretch(stack, low_pct=low_pct, high_pct=high_pct)
