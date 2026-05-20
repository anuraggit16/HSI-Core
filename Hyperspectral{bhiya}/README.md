# Hyperspectral visualiser

Python package with a **Streamlit** UI to explore hyperspectral cubes: false-colour RGB composites, percentile stretch, and per-pixel spectra.

## Layout

- `src/hyperspectral_viz/` — application and library code  
  - `io/` — ENVI, `.npy`, stacked TIFF/PNG  
  - `processing/` — RGB compositing and spectra  
  - `app.py` — Streamlit UI  
  - `cli.py` — launcher  
- `tests/` — pytest unit tests  
- `Launch Web App.bat` — one-click local web server (Windows)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Run (single click, Windows)

Double-click **`Launch Web App.bat`** in this folder. The first run creates `.venv`, installs dependencies, then opens the app in your browser (usually http://localhost:8501). Keep the window open while you use the app; closing it stops the server.

## Run (command line)

```bash
streamlit run src/hyperspectral_viz/app.py
```

Or after editable install:

```bash
hyperspectral-viz
```

## Data formats

1. **ENVI**: upload the `.hdr` together with the image file (e.g. `.img` / `.dat`) with matching base name, or as listed in the header `file name` field.  
2. **NumPy**: `.npy` array shaped **(lines, samples, bands)**.  
3. **Stacked TIFF / PNG**: one **multi-page** `.tif` / `.tiff` (often **bands × height × width**), or **several** `.tif` / `.tiff` / `.png` files of the same height and width (sorted by file name and stacked as bands). In the app sidebar, pick **Bands first** or **Bands last** to match how your stack is stored.

Integer ENVI cubes are normalised to float32 in roughly \([0, 1]\) per dynamic range for display.
