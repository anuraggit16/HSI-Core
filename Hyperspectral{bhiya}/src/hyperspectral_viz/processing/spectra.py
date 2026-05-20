from __future__ import annotations

import numpy as np


def spectrum_at_pixel(cube: np.ndarray, line: int, sample: int) -> np.ndarray:
    """Return 1-D spectrum (bands,) at integer pixel coordinates."""
    if cube.ndim != 3:
        raise ValueError("cube must be (lines, samples, bands)")
    if not (0 <= line < cube.shape[0] and 0 <= sample < cube.shape[1]):
        raise IndexError("line/sample out of bounds")
    return np.asarray(cube[line, sample, :], dtype=np.float32)
