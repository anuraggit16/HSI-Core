from __future__ import annotations

import numpy as np
import pytest
import tifffile

from hyperspectral_viz.io.stacked_image import ImageStackLayout, load_stacked_image, load_stacked_image_files


def test_multipage_tiff_bands_first(tmp_path):
    bands, h, w = 5, 8, 6
    data = np.random.RandomState(0).rand(bands, h, w).astype(np.float32)
    path = tmp_path / "stack.tif"
    tifffile.imwrite(path, data)
    cube = load_stacked_image(path, ImageStackLayout.BANDS_FIRST)
    assert cube.data.shape == (h, w, bands)
    assert cube.data.dtype == np.float32


def test_volume_bands_last(tmp_path):
    h, w, b = 7, 9, 4
    data = np.random.RandomState(1).rand(h, w, b).astype(np.float32)
    path = tmp_path / "lsb.tif"
    tifffile.imwrite(path, data, photometric="minisblack")
    cube = load_stacked_image(path, ImageStackLayout.BANDS_LAST)
    assert cube.data.shape == (h, w, b)


def test_multi_file_stack(tmp_path):
    h, w = 4, 5
    p1 = tmp_path / "b00.tif"
    p2 = tmp_path / "b01.tif"
    tifffile.imwrite(p1, (np.random.rand(h, w) * 255).astype(np.uint8))
    tifffile.imwrite(p2, (np.random.rand(h, w) * 255).astype(np.uint8))
    cube = load_stacked_image_files([p2, p1], ImageStackLayout.BANDS_LAST)
    assert cube.data.shape == (h, w, 2)


def test_shape_mismatch_raises(tmp_path):
    tifffile.imwrite(tmp_path / "a.tif", np.zeros((3, 3), dtype=np.uint8))
    tifffile.imwrite(tmp_path / "b.tif", np.zeros((4, 4), dtype=np.uint8))
    with pytest.raises(ValueError, match="Spatial shape mismatch"):
        load_stacked_image_files([tmp_path / "a.tif", tmp_path / "b.tif"], ImageStackLayout.BANDS_LAST)
