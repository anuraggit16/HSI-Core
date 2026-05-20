from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from hyperspectral_viz.cube import HyperspectralCube
from hyperspectral_viz.io.envi import load_envi
from hyperspectral_viz.io.numpy_cube import load_npy_cube
from hyperspectral_viz.io.stacked_image import ImageStackLayout, load_stacked_image, load_stacked_image_files
from hyperspectral_viz.processing.rgb import rgb_composite
from hyperspectral_viz.processing.spectra import spectrum_at_pixel
from hyperspectral_viz.viz.band_stack_3d import band_stack_figure

pio.templates.default = "plotly_dark"


_MODERN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Plus Jakarta Sans', ui-sans-serif, system-ui, sans-serif;
    }
    .stApp {
        background: radial-gradient(1200px 600px at 10% -10%, rgba(99,102,241,0.18), transparent),
                    radial-gradient(900px 500px at 100% 0%, rgba(56,189,248,0.12), transparent),
                    linear-gradient(180deg, #070a12 0%, #0c1020 35%, #0a0e18 100%);
    }
    header[data-testid="stHeader"] { background: rgba(7,10,18,0.65); backdrop-filter: blur(10px); }
    [data-testid="stSidebar"] {
        background: linear-gradient(185deg, rgba(17,24,39,0.97) 0%, rgba(12,16,28,0.98) 100%);
        border-right: 1px solid rgba(148,163,184,0.12);
    }
    [data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        background: rgba(30,41,59,0.45);
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 14px;
        padding: 10px 12px;
    }
    .hs-title {
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        margin: 0 0 0.35rem 0;
        background: linear-gradient(120deg, #e0e7ff 0%, #a5b4fc 45%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hs-sub {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0 0 1.25rem 0;
    }
    [data-baseweb="tab-list"] { gap: 8px; background: rgba(15,23,42,0.5); border-radius: 12px; padding: 6px; }
    [data-baseweb="tab"] { border-radius: 10px; font-weight: 600; }
</style>
"""


def synthetic_cube(lines: int = 128, samples: int = 128, bands: int = 48) -> HyperspectralCube:
    """Demo cube with smooth gradients and spectral variation."""
    y = np.linspace(0, 1, lines, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, samples, dtype=np.float32)[None, :, None]
    w = np.linspace(0, 1, bands, dtype=np.float32)[None, None, :]
    rings = np.sin((x + y) * np.pi * 6) * 0.15
    spec = np.sin(w * np.pi * 5) * (0.2 + 0.8 * (x + y) / 2)
    data = np.clip(0.15 + 0.35 * y + 0.25 * x + spec + rings, 0, 1).astype(np.float32)
    waves = np.linspace(400.0, 900.0, bands, dtype=np.float32)
    return HyperspectralCube(data=data, wavelengths_nm=waves, meta={"name": "synthetic"})


def _write_temp(name: str, data: bytes) -> Path:
    p = Path(tempfile.gettempdir()) / f"hsviz_{name}"
    p.write_bytes(data)
    return p


def load_from_uploads(files: list, *, image_layout: ImageStackLayout) -> HyperspectralCube:
    """Load cube from Streamlit uploaded file list."""
    if not files:
        raise ValueError("No files uploaded")
    hdr_files = [f for f in files if f.name.lower().endswith(".hdr")]
    if hdr_files:
        hdr_f = hdr_files[0]
        hdr_path = _write_temp(hdr_f.name, hdr_f.getvalue())
        raw_path = None
        stem = Path(hdr_f.name).stem.lower()
        for f in files:
            if f is hdr_f:
                continue
            s = Path(f.name).stem.lower()
            if s == stem or f.name.lower().endswith((".img", ".dat", ".raw", ".bin")):
                raw_path = _write_temp(f.name, f.getvalue())
                break
        try:
            return load_envi(hdr_path, raw_path)
        finally:
            hdr_path.unlink(missing_ok=True)
            if raw_path is not None:
                raw_path.unlink(missing_ok=True)

    npy_names = [f for f in files if f.name.lower().endswith(".npy")]
    if npy_names:
        f = npy_names[0]
        p = _write_temp(f.name, f.getvalue())
        try:
            return load_npy_cube(p)
        finally:
            p.unlink(missing_ok=True)

    image_exts = (".tif", ".tiff", ".png")
    image_files = [f for f in files if f.name.lower().endswith(image_exts)]
    if image_files:
        paths: list[Path] = []
        try:
            for f in sorted(image_files, key=lambda x: x.name.lower()):
                paths.append(_write_temp(f.name, f.getvalue()))
            if len(paths) == 1:
                return load_stacked_image(paths[0], image_layout)
            return load_stacked_image_files(paths, image_layout)
        finally:
            for p in paths:
                p.unlink(missing_ok=True)

    raise ValueError(
        "Upload ENVI (.hdr + image), .npy (lines×samples×bands), or stacked "
        ".tif / .tiff / .png (multi-page TIFF or several image files)."
    )


def run() -> None:
    st.set_page_config(
        page_title="Hyperspectral Studio",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_MODERN_CSS, unsafe_allow_html=True)

    st.markdown('<p class="hs-title">Hyperspectral Studio</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hs-sub">False-colour composites, per-pixel spectra, and a 3D band stack '
        "with a highlighted slice — other bands appear as translucent planes. "
        "Supports ENVI, NumPy, and stacked TIFF/PNG.</p>",
        unsafe_allow_html=True,
    )

    if "cube" not in st.session_state:
        st.session_state.cube = synthetic_cube()

    cube: HyperspectralCube = st.session_state.cube
    n = cube.bands

    with st.sidebar:
        st.markdown("### Controls")
        with st.expander("Data source", expanded=True):
            mode = st.radio(
                "Source",
                ["Demo", "Upload"],
                horizontal=True,
                label_visibility="visible",
            )
            if mode == "Upload":
                img_layout = st.selectbox(
                    "TIFF / PNG band layout",
                    options=[ImageStackLayout.BANDS_FIRST, ImageStackLayout.BANDS_LAST],
                    index=0,
                    help="Multi-page stacks are usually bands-first. Use bands-last for H×W×B cubes or RGB.",
                    format_func=lambda v: (
                        "Bands first (B × lines × samples) — typical stacked TIFF"
                        if v == ImageStackLayout.BANDS_FIRST
                        else "Bands last (lines × samples × B) — planar / RGB-style"
                    ),
                )
                ups = st.file_uploader(
                    "ENVI, NPY, or TIFF/PNG stack",
                    type=["hdr", "img", "dat", "raw", "bin", "npy", "tif", "tiff", "png"],
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                )
                if ups and st.button("Load files", type="primary", use_container_width=True):
                    try:
                        st.session_state.cube = load_from_uploads(
                            list(ups), image_layout=img_layout
                        )
                        st.success("Dataset loaded.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        cube = st.session_state.cube
        n = cube.bands

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Lines", f"{cube.lines:,}")
        with c2:
            st.metric("Samples", f"{cube.samples:,}")
        with c3:
            st.metric("Bands", f"{cube.bands:,}")

        with st.expander("RGB composite", expanded=True):
            br = st.slider("Red band", 0, n - 1, min(n - 1, max(0, n // 3)), key="br")
            bg = st.slider("Green band", 0, n - 1, min(n - 1, max(0, n // 2)), key="bg")
            bb = st.slider("Blue band", 0, n - 1, min(n - 1, n - 1), key="bb")
            lo = st.slider("Stretch low %", 0.0, 20.0, 2.0, key="lo")
            hi = st.slider("Stretch high %", 80.0, 100.0, 98.0, key="hi")

        with st.expander("3D band stack", expanded=False):
            b3d = st.slider(
                "Focused band",
                0,
                n - 1,
                min(n - 1, n // 2),
                help="Fully opaque plane; other bands are drawn semi-transparent.",
                key="b3d",
            )
            ghost = st.slider("Other bands opacity", 0.02, 0.35, 0.10, key="ghost")
            max_planes = st.slider("Max planes drawn", 12, 72, 40, key="mpl")
            max_sp = st.slider("3D spatial resolution (max px)", 96, 360, 200, key="msp")

        with st.expander("Pixel probe", expanded=False):
            li = st.number_input("Line (row)", 0, cube.lines - 1, cube.lines // 2, key="li")
            si = st.number_input("Sample (col)", 0, cube.samples - 1, cube.samples // 2, key="si")

    tab_a, tab_b = st.tabs(["Workspace", "3D band stack"])

    rgb = rgb_composite(cube.data, br, bg, bb, low_pct=lo, high_pct=hi)

    with tab_a:
        c_img, c_spec = st.columns([1.15, 1.0], gap="large")
        with c_img:
            with st.container(border=True):
                st.markdown("##### False-colour RGB")
                disp = (np.clip(rgb, 0.0, 1.0) * 255).astype(np.uint8)
                fig_img = go.Figure(data=go.Image(z=disp, colormodel="rgb"))
                fig_img.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=8, r=8, t=8, b=8),
                    xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                    yaxis=dict(
                        showticklabels=False,
                        showgrid=False,
                        zeroline=False,
                        scaleanchor="x",
                        scaleratio=1,
                    ),
                    height=min(680, max(420, cube.lines)),
                )
                st.plotly_chart(fig_img, use_container_width=True)

        spec = spectrum_at_pixel(cube.data, int(li), int(si))
        with c_spec:
            with st.container(border=True):
                st.markdown(f"##### Spectrum · pixel ({li}, {si})")
                x_axis = (
                    cube.wavelengths_nm
                    if cube.wavelengths_nm is not None
                    else np.arange(len(spec), dtype=np.float32)
                )
                wl_unit = "nm" if cube.wavelengths_nm is not None else "band index"
                fig_spec = go.Figure(
                    data=go.Scatter(
                        x=x_axis,
                        y=spec,
                        mode="lines",
                        line=dict(width=2.4, color="#818cf8"),
                        fill="tozeroy",
                        fillcolor="rgba(129,140,248,0.12)",
                    ),
                )
                fig_spec.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.35)",
                    margin=dict(l=52, r=16, t=28, b=48),
                    xaxis_title=f"Wavelength ({wl_unit})"
                    if cube.wavelengths_nm is not None
                    else "Band",
                    yaxis_title="Response (scaled)",
                    height=420,
                    xaxis=dict(gridcolor="rgba(148,163,184,0.12)"),
                    yaxis=dict(gridcolor="rgba(148,163,184,0.12)"),
                )
                st.plotly_chart(fig_spec, use_container_width=True)

    with tab_b:
        with st.container(border=True):
            st.markdown(
                "##### Volumetric-style view\n"
                "<span style='color:#94a3b8;font-size:0.9rem;'>Drag to rotate. "
                "Scroll to zoom. Each plane is one spectral band; only the focused band is opaque — "
                "the rest stay visible as **translucent** context (subsampled when there are many bands).</span>",
                unsafe_allow_html=True,
            )
            fig_3d = band_stack_figure(
                cube.data,
                int(b3d),
                cube.wavelengths_nm,
                max_planes=int(max_planes),
                ghost_opacity=float(ghost),
                max_height=int(max_sp),
                max_width=int(max_sp),
                stretch_low=float(lo),
                stretch_high=float(hi),
            )
            fig_3d.update_layout(template="plotly_dark")
            st.plotly_chart(fig_3d, use_container_width=True)


def main() -> None:
    run()


if __name__ == "__main__":
    run()
