from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


def _downsample_xy(cube: np.ndarray, max_h: int, max_w: int) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
    """Return cube (Lh, Sw, B) and meshgrid X,Y for plotly Surface (x=sample, y=line)."""
    lines, samples, bands = cube.shape
    step_y = max(1, int(np.ceil(lines / max_h)))
    step_x = max(1, int(np.ceil(samples / max_w)))
    small = cube[::step_y, ::step_x, :]
    Ly, Sx, _ = small.shape
    col_idx = np.arange(Sx, dtype=np.float32) * step_x + (step_x - 1) / 2
    row_idx = np.arange(Ly, dtype=np.float32) * step_y + (step_y - 1) / 2
    X, Y = np.meshgrid(col_idx, row_idx)
    return small, (X, Y)


def _stretch_plane(plane: np.ndarray, low_pct: float, high_pct: float) -> np.ndarray:
    p = plane.astype(np.float64, copy=False).ravel()
    lo, hi = np.percentile(p, (low_pct, high_pct))
    hi = max(hi, lo + 1e-9)
    out = (plane.astype(np.float64) - lo) / (hi - lo)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _band_indices_to_plot(n_bands: int, selected: int, max_planes: int) -> list[int]:
    """Evenly subsample band indices, always including ``selected``."""
    max_planes = max(3, int(max_planes))
    if n_bands <= max_planes:
        return list(range(n_bands))
    base = np.unique(
        np.concatenate(
            [
                np.linspace(0, n_bands - 1, max_planes - 1, dtype=int),
                np.array([selected], dtype=int),
            ]
        )
    )
    return sorted(int(x) for x in base)


def band_stack_figure(
    cube: np.ndarray,
    selected_band: int,
    wavelengths_nm: np.ndarray | None,
    *,
    max_planes: int = 48,
    ghost_opacity: float = 0.12,
    selected_opacity: float = 1.0,
    max_height: int = 220,
    max_width: int = 220,
    stretch_low: float = 2.0,
    stretch_high: float = 98.0,
) -> go.Figure:
    """
    Build a 3D figure: stacked spectral planes (XY) along Z (band / wavelength).

    The selected band is drawn at full opacity; other sampled bands use ``ghost_opacity``.
    """
    if cube.ndim != 3:
        raise ValueError("cube must be (lines, samples, bands)")
    lines, samples, bands = cube.shape
    selected_band = int(np.clip(selected_band, 0, bands - 1))

    small, (X, Y) = _downsample_xy(cube, max_height, max_width)
    _, _, bcount = small.shape

    idxs = _band_indices_to_plot(bcount, selected_band, max_planes)
    waves = wavelengths_nm
    if waves is not None and len(waves) != bands:
        waves = None

    fig = go.Figure()
    dark = [[0, "#070a12"], [0.5, "#1c2744"], [1, "#dce7ff"]]

    for b in idxs:
        z_val = float(waves[b]) if waves is not None else float(b)
        plane = small[:, :, b]
        color = _stretch_plane(plane, stretch_low, stretch_high)
        op = float(selected_opacity) if b == selected_band else float(ghost_opacity)
        fig.add_trace(
            go.Surface(
                x=X,
                y=Y,
                z=np.full_like(X, z_val, dtype=np.float32),
                surfacecolor=color,
                colorscale=dark,
                cmin=0.0,
                cmax=1.0,
                showscale=False,
                opacity=op,
                name=f"Band {b}",
                hovertemplate=(
                    f"Line %{{y:.1f}}<br>Sample %{{x:.1f}}<br>"
                    f"{'λ' if waves is not None else 'Band'} {z_val:.2f}"
                    f"{' nm' if waves is not None else ''}<br>value %{{surfacecolor:.3f}}<extra></extra>"
                ),
                lighting=dict(ambient=0.85, diffuse=0.35, specular=0.15),
            )
        )

    z_title = "Wavelength (nm)" if waves is not None else "Band index"
    fig.update_layout(
        scene=dict(
            xaxis_title="Sample (column)",
            yaxis_title="Line (row)",
            zaxis_title=z_title,
            aspectmode="manual",
            aspectratio=dict(x=1.0, y=float(small.shape[0]) / max(small.shape[1], 1), z=0.55),
            bgcolor="rgba(8,10,18,0.4)",
            xaxis=dict(showbackground=False, gridcolor="rgba(120,140,180,0.15)"),
            yaxis=dict(showbackground=False, gridcolor="rgba(120,140,180,0.15)"),
            zaxis=dict(showbackground=False, gridcolor="rgba(120,140,180,0.15)"),
            camera=dict(eye=dict(x=1.45, y=-1.55, z=0.85)),
        ),
        paper_bgcolor="rgba(10,12,20,0)",
        margin=dict(l=0, r=0, t=30, b=0),
        height=560,
        showlegend=False,
        title=dict(
            text=f"3D band stack — highlighted band {selected_band}"
            + (f" ({waves[selected_band]:.1f} nm)" if waves is not None else ""),
            font=dict(size=14, color="#c8d4f0"),
        ),
    )
    return fig
