from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from hyperspectral_viz.cube import HyperspectralCube

_ENVI_DTYPES: dict[int, np.dtype] = {
    1: np.dtype(np.uint8),
    2: np.dtype(np.int16),
    3: np.dtype(np.int32),
    4: np.dtype(np.float32),
    5: np.dtype(np.float64),
    12: np.dtype(np.uint16),
    13: np.dtype(np.uint32),
    14: np.dtype(np.int64),
    15: np.dtype(np.uint64),
}


def _parse_hdr(text: str) -> dict[str, str]:
    """Parse ENVI header key=value pairs (simplified)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or lines[0].upper() != "ENVI":
        raise ValueError("Not an ENVI header (missing leading ENVI line)")
    out: dict[str, str] = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            if val.startswith("{") and not val.endswith("}"):
                buf = [val]
                i += 1
                while i < len(lines) and not buf[-1].rstrip().endswith("}"):
                    buf.append(lines[i])
                    i += 1
                val = " ".join(buf)
            out[key] = val
        i += 1
    return out


def _parse_int(hdr: dict[str, str], key: str) -> int:
    if key not in hdr:
        raise KeyError(f"Missing required ENVI field: {key}")
    return int(hdr[key].strip())


def _parse_float_list(val: str) -> np.ndarray:
    """Parse ENVI list like {a, b, c} or comma-separated."""
    val = val.strip()
    if val.startswith("{") and val.endswith("}"):
        inner = val[1:-1]
    else:
        inner = val
    parts = re.split(r"[,\s]+", inner.strip())
    nums = [float(p) for p in parts if p]
    return np.array(nums, dtype=np.float64)


def _find_raw_path(hdr_path: Path, hdr: dict[str, str]) -> Path:
    if "file name" in hdr:
        rel = hdr["file name"].strip().strip("'\"")
        p = (hdr_path.parent / rel).resolve()
        if p.is_file():
            return p
    stem = hdr_path.stem
    for ext in (".img", ".dat", ".raw", ".bin", ""):
        cand = hdr_path.with_suffix(ext) if ext else hdr_path.with_suffix("")
        if ext and cand.is_file():
            return cand
    raise FileNotFoundError(
        f"Could not locate binary for {hdr_path}. Place an ENVI image next to the .hdr "
        f"(e.g. {stem}.img) or set 'file name' in the header."
    )


def _to_ls_bands(raw: np.ndarray, interleave: str, lines: int, samples: int, bands: int) -> np.ndarray:
    interleave = interleave.lower()
    if interleave == "bsq":
        # (bands, lines, samples) -> (lines, samples, bands)
        cube = raw.reshape(bands, lines, samples).transpose(1, 2, 0)
    elif interleave == "bil":
        # (lines, bands, samples)
        cube = raw.reshape(lines, bands, samples).transpose(0, 2, 1)
    elif interleave == "bip":
        cube = raw.reshape(lines, samples, bands)
    else:
        raise ValueError(f"Unsupported interleave: {interleave}")
    return np.ascontiguousarray(cube)


def _to_float32(cube: np.ndarray) -> np.ndarray:
    if cube.dtype == np.float32:
        return cube
    if np.issubdtype(cube.dtype, np.floating):
        return cube.astype(np.float32, copy=False)
    info = np.iinfo(cube.dtype) if np.issubdtype(cube.dtype, np.integer) else None
    if info is not None:
        c = cube.astype(np.float64)
        c = (c - info.min) / max(info.max - info.min, 1)
        return c.astype(np.float32)
    c = cube.astype(np.float32)
    return c


def load_envi(hdr_path: str | Path, raw_path: str | Path | None = None) -> HyperspectralCube:
    """
    Load an ENVI cube from a .hdr file (and matching binary).

    Returns float32 array (lines, samples, bands). Integer cubes are scaled to [0, 1].
    """
    hdr_path = Path(hdr_path).expanduser().resolve()
    text = hdr_path.read_text(encoding="utf-8", errors="replace")
    hdr = _parse_hdr(text)
    samples = _parse_int(hdr, "samples")
    lines = _parse_int(hdr, "lines")
    bands = _parse_int(hdr, "bands")
    data_type = _parse_int(hdr, "data type")
    if data_type not in _ENVI_DTYPES:
        raise ValueError(f"Unsupported ENVI data type code: {data_type}")
    dt = _ENVI_DTYPES[data_type]
    interleave = hdr.get("interleave", "bsq").strip().lower()
    header_offset = _parse_int(hdr, "header offset") if "header offset" in hdr else 0
    byte_order = _parse_int(hdr, "byte order") if "byte order" in hdr else 0
    endian = ">" if byte_order == 1 else "<"

    bin_path = Path(raw_path).expanduser().resolve() if raw_path else _find_raw_path(hdr_path, hdr)
    raw_bytes = bin_path.read_bytes()
    if header_offset:
        raw_bytes = raw_bytes[header_offset:]
    count = lines * samples * bands
    arr = np.frombuffer(raw_bytes, dtype=np.dtype(dt).newbyteorder(endian), count=count)
    if arr.size != count:
        raise ValueError(
            f"Binary size mismatch: expected {count} elements, got {arr.size}. "
            "Check samples/lines/bands and header offset."
        )
    cube = _to_ls_bands(arr, interleave, lines, samples, bands)
    cube_f = _to_float32(cube)

    waves = None
    for key in ("wavelength", "wavelengths"):
        if key in hdr:
            waves = _parse_float_list(hdr[key]).astype(np.float32)
            if len(waves) != bands:
                waves = None
            break

    meta = {
        "source_hdr": str(hdr_path),
        "source_raw": str(bin_path),
        "interleave": interleave,
        "data_type": data_type,
    }
    return HyperspectralCube(data=cube_f, wavelengths_nm=waves, meta=meta)
