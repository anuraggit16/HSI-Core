from __future__ import annotations

import numpy as np
import pytest

from hyperspectral_viz.io.envi import load_envi
from hyperspectral_viz.processing.rgb import rgb_composite


def test_load_envi_bsq(tmp_path):
    lines, samples, bands = 2, 3, 4
    # BSQ: band-major
    raw = np.arange(lines * samples * bands, dtype=np.float32).reshape(bands, lines, samples)
    hdr_path = tmp_path / "test.hdr"
    raw_path = tmp_path / "test.img"
    raw.tofile(raw_path)
    hdr_path.write_text(
        "\n".join(
            [
                "ENVI",
                f"samples = {samples}",
                f"lines = {lines}",
                f"bands = {bands}",
                "header offset = 0",
                "file type = ENVI Standard",
                "data type = 4",
                "interleave = bsq",
                "byte order = 0",
            ]
        ),
        encoding="utf-8",
    )
    cube = load_envi(hdr_path)
    assert cube.data.shape == (lines, samples, bands)
    assert np.allclose(cube.data[0, 0, :], raw[:, 0, 0])


def test_rgb_composite_bounds():
    cube = np.random.default_rng(0).random((5, 6, 7), dtype=np.float32)
    rgb = rgb_composite(cube, 0, 1, 2)
    assert rgb.shape == (5, 6, 3)
    assert rgb.dtype == np.float32
    assert rgb.min() >= 0 and rgb.max() <= 1


def test_rgb_bad_band():
    cube = np.zeros((2, 2, 3), dtype=np.float32)
    with pytest.raises(IndexError):
        rgb_composite(cube, 0, 1, 10)
