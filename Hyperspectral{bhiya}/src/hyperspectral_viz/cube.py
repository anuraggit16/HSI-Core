from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class HyperspectralCube:
    """A hyperspectral image cube with shape (lines, samples, bands)."""

    data: np.ndarray  # float32, shape (lines, samples, bands)
    wavelengths_nm: np.ndarray | None = None
    meta: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.data.ndim != 3:
            raise ValueError("data must have shape (lines, samples, bands)")
        if self.data.dtype != np.float32:
            raise TypeError("data must be float32")
        if self.wavelengths_nm is not None and len(self.wavelengths_nm) != self.data.shape[2]:
            raise ValueError("wavelengths length must match number of bands")

    @property
    def lines(self) -> int:
        return int(self.data.shape[0])

    @property
    def samples(self) -> int:
        return int(self.data.shape[1])

    @property
    def bands(self) -> int:
        return int(self.data.shape[2])
