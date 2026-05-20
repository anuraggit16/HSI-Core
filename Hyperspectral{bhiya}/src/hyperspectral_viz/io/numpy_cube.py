from __future__ import annotations

from pathlib import Path

import numpy as np

from hyperspectral_viz.cube import HyperspectralCube
from hyperspectral_viz.io.envi import _to_float32


def load_npy_cube(path: str | Path) -> HyperspectralCube:
    """
    Load a NumPy array saved with numpy.save.

    Expected shape: (lines, samples, bands).
    """
    path = Path(path).expanduser().resolve()
    arr = np.load(path, allow_pickle=False)
    if arr.ndim != 3:
        raise ValueError(f"Expected 3-D array (lines, samples, bands), got shape {arr.shape}")
    data = _to_float32(np.asarray(arr))
    meta = {"source_npy": str(path)}
    return HyperspectralCube(data=data, wavelengths_nm=None, meta=meta)
