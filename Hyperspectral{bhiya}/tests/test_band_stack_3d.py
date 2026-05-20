from __future__ import annotations

import numpy as np

from hyperspectral_viz.viz.band_stack_3d import band_stack_figure


def test_band_stack_figure_smoke():
    cube = np.random.default_rng(0).random((24, 32, 18), dtype=np.float32)
    waves = np.linspace(400, 800, 18, dtype=np.float32)
    fig = band_stack_figure(cube, 7, waves, max_planes=12, ghost_opacity=0.1)
    assert len(fig.data) >= 3
    assert len(fig.data) <= 12
