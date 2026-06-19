# =============================================================================
# HSI-Core — Data Cube Manager
# =============================================================================
# Manages hyperspectral data cubes (sessions) on disk.
# Provides 2-D intensity maps for dashboard heatmap rendering and
# per-frame JPEG serving for the dataset browser.
# =============================================================================

from __future__ import annotations

import json
import math
import os
import re
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

import config


class _SessionCube:
    """In-memory accumulator for a single scan session."""

    def __init__(self, session: str, nx: int, ny: int):
        self.session    = session
        self.nx         = nx
        self.ny         = ny
        self.intensity  = np.zeros((ny, nx), dtype=np.float32)
        self.count      = np.zeros((ny, nx), dtype=np.int32)

    def record(self, xi: int, yi: int, intensity: float):
        if 0 <= yi < self.ny and 0 <= xi < self.nx:
            self.intensity[yi, xi] = intensity
            self.count[yi, xi]     = 1

    def intensity_map_normalised(self) -> np.ndarray:
        """Return float32 [0,1] intensity map."""
        img = self.intensity.copy()
        mn, mx = img.min(), img.max()
        if mx > mn:
            img = (img - mn) / (mx - mn)
        return img


class DataCubeManager:
    """
    Singleton that:
    - Tracks active session accumulation (called by ScanEngine during scan)
    - Lists completed sessions (folders in scan_images/)
    - Returns 2-D intensity maps and individual frame JPEGs for API endpoints
    """

    def __init__(self):
        self._lock    = threading.Lock()
        self._cubes   : Dict[str, _SessionCube] = {}
        self._cube_context_cache: dict[str, tuple[float, tuple[str, dict, np.ndarray, str, dict]]] = {}

    # ------------------------------------------------------------------
    # CALLED BY SCAN ENGINE (during acquisition)
    # ------------------------------------------------------------------

    def record_frame(
        self,
        session: str,
        xi: int, yi: int,
        intensity: float,
        nx: int, ny: int,
    ):
        with self._lock:
            if session not in self._cubes:
                self._cubes[session] = _SessionCube(session, nx, ny)
            self._cubes[session].record(xi, yi, intensity)

    def finalize_scan(self, session_path: str, metadata: dict) -> dict:
        """Build a reloadable cube and integrity manifest from saved scan frames."""
        import tifffile

        frames = sorted(
            metadata.get("frames", []),
            key=lambda item: int(item.get("scan_index", item.get("frame_index", 0))),
        )
        expected = int(metadata.get("scan_params", {}).get("number_of_images") or metadata.get("total_frames") or len(frames))
        metadata_dir = os.path.join(session_path, "metadata")
        cube_dir = os.path.join(session_path, "cube")
        os.makedirs(metadata_dir, exist_ok=True)
        os.makedirs(cube_dir, exist_ok=True)
        manifest_path = os.path.join(metadata_dir, "manifest.json")
        cube_path = os.path.join(cube_dir, "data_cube.npy")
        cube_npz_path = os.path.join(cube_dir, "data_cube.npz")
        storage_policy = self._storage_policy()
        keep_npy_cube = bool(storage_policy.get("keep_npy_cube", False))
        keep_npz_cube = bool(storage_policy.get("keep_npz_cube", True))
        compression_enabled = bool(storage_policy.get("compression", True))
        working_cube_path = cube_path if keep_npy_cube else os.path.join(cube_dir, "data_cube.tmp.npy")

        manifest = {
            "schema": "hsi-core.scan-manifest.v1",
            "session_name": metadata.get("session_name"),
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "expected_frames": expected,
            "frames_acquired": len(frames),
            "missing_indices": [],
            "duplicate_indices": [],
            "valid": False,
            "cube": {},
            "frames": [],
            "wavelengths_nm": [],
            "positions_mm": [],
        }

        if not frames:
            manifest["error"] = "No frames recorded in metadata"
            self._write_json(manifest_path, manifest)
            return manifest

        seen = set()
        ordered = []
        for frame in frames:
            idx = int(frame.get("scan_index", frame.get("frame_index", len(ordered))))
            if idx in seen:
                manifest["duplicate_indices"].append(idx)
            seen.add(idx)
            tiff_name = frame.get("tiff")
            if not tiff_name:
                manifest["missing_indices"].append(idx)
                continue
            tiff_path = os.path.join(session_path, tiff_name)
            if not os.path.isfile(tiff_path):
                manifest["missing_indices"].append(idx)
                continue
            ordered.append((idx, frame, tiff_path))

        manifest["missing_indices"].extend([idx for idx in range(expected) if idx not in seen])
        manifest["missing_indices"] = sorted(set(manifest["missing_indices"]))

        if not ordered:
            manifest["error"] = "No readable TIFF frames found"
            self._write_json(manifest_path, manifest)
            return manifest

        first = tifffile.imread(ordered[0][2])
        frame_shape = tuple(int(v) for v in first.shape)
        dtype = first.dtype
        cube_shape = (expected, *frame_shape)
        cube = np.lib.format.open_memmap(working_cube_path, mode="w+", dtype=dtype, shape=cube_shape)
        cube[:] = 0

        intensities = np.zeros((1, expected), dtype=np.float32)
        positions = [None] * expected
        frame_records = []

        for idx, frame, tiff_path in ordered:
            arr = tifffile.imread(tiff_path)
            if tuple(arr.shape) != frame_shape:
                manifest.setdefault("shape_errors", []).append({
                    "scan_index": idx,
                    "shape": list(arr.shape),
                    "expected_shape": list(frame_shape),
                })
                continue
            if 0 <= idx < expected:
                cube[idx] = arr
                intensity = float(frame.get("intensity_mean", float(np.mean(arr))))
                intensities[0, idx] = intensity
                raw_position = frame.get("position_mm")
                positions[idx] = float(raw_position) if raw_position is not None else None
                frame_records.append({
                    "scan_index": idx,
                    "position_mm": positions[idx],
                    "stage_status": frame.get("stage_status"),
                    "tiff": os.path.relpath(tiff_path, session_path),
                    "metadata": frame.get("metadata"),
                    "intensity_mean": round(intensity, 4),
                })

        cube.flush()
        acquired_indices = {record["scan_index"] for record in frame_records}
        manifest["missing_indices"] = sorted(set(manifest["missing_indices"]) | (set(range(expected)) - acquired_indices))
        manifest["frames"] = sorted(frame_records, key=lambda item: item["scan_index"])
        x_axis = [
            float(pos) if pos is not None else float(idx)
            for idx, pos in enumerate(positions)
        ]
        y_axis = list(range(int(frame_shape[0] if frame_shape else 1)))
        manifest["positions_mm"] = positions
        manifest["x_positions"] = x_axis
        manifest["stage_positions"] = positions
        manifest["y_pixels"] = y_axis
        manifest["y_axis"] = y_axis

        spectral_width = frame_shape[-1] if frame_shape else int(getattr(config, "SPECTRAL_BANDS", 1))
        manifest["wavelengths_nm"] = np.linspace(
            float(getattr(config, "SPECTRAL_MIN_NM", 400)),
            float(getattr(config, "SPECTRAL_MAX_NM", 1000)),
            int(max(1, spectral_width)),
        ).round(4).tolist()
        manifest["lambda_axis"] = manifest["wavelengths_nm"]
        manifest["cube_shape"] = list(cube_shape)
        manifest["dimension_order"] = ["x", "y", "wavelength"]
        manifest["frame_count"] = expected
        manifest["source_scan_folder"] = os.path.abspath(session_path)
        manifest["creation_timestamp"] = manifest["created_at"]
        manifest["cube"] = {
            "path": os.path.basename(working_cube_path),
            "relative_path": os.path.relpath(working_cube_path, session_path),
            "shape": list(cube_shape),
            "dtype": str(dtype),
            "axis_order": ["x", "y", "wavelength"],
            "dimension_order": ["x", "y", "wavelength"],
            "bytes": int(os.path.getsize(working_cube_path)),
            "canonical_format": "npy",
        }
        manifest["valid"] = not manifest["missing_indices"] and not manifest.get("shape_errors")

        if keep_npz_cube:
            save_npz = np.savez_compressed if compression_enabled else np.savez
            save_npz(cube_npz_path, cube=cube)
            npz_info = {
                "path": os.path.basename(cube_npz_path),
                "relative_path": os.path.relpath(cube_npz_path, session_path),
                "shape": list(cube_shape),
                "dtype": str(dtype),
                "axis_order": ["x", "y", "wavelength"],
                "dimension_order": ["x", "y", "wavelength"],
                "bytes": int(os.path.getsize(cube_npz_path)),
                "canonical_format": "npz",
                "compression": "zip_deflate" if compression_enabled else "zip_store",
            }
            if keep_npy_cube:
                npz_info["uncompressed_path"] = os.path.basename(cube_path)
                npz_info["uncompressed_relative_path"] = os.path.relpath(cube_path, session_path)
                npz_info["uncompressed_bytes"] = int(os.path.getsize(cube_path))
            manifest["cube"] = npz_info
        elif not keep_npy_cube and working_cube_path != cube_path:
            os.replace(working_cube_path, cube_path)
            manifest["cube"]["path"] = os.path.basename(cube_path)
            manifest["cube"]["relative_path"] = os.path.relpath(cube_path, session_path)
            manifest["cube"]["bytes"] = int(os.path.getsize(cube_path))

        del cube

        if not keep_npy_cube and keep_npz_cube and os.path.isfile(working_cube_path):
            os.remove(working_cube_path)

        if not bool(storage_policy.get("keep_raw_frames", True)) and manifest["valid"]:
            self._cleanup_raw_frames(session_path, manifest)

        with self._lock:
            session = metadata.get("session_name") or os.path.basename(session_path)
            active = _SessionCube(session, expected, 1)
            active.intensity = intensities
            active.count = (intensities > 0).astype(np.int32)
            self._cubes[session] = active

        self._write_json(manifest_path, manifest)
        self._release_cube_cache()
        return manifest

    # ------------------------------------------------------------------
    # DATASET BROWSER (called by API)
    # ------------------------------------------------------------------

    def list_sessions(self) -> List[dict]:
        """List all sessions found in the save folder."""
        root = config.SAVE_FOLDER
        if not os.path.isdir(root):
            return []
        sessions = []
        for name in sorted(os.listdir(root), key=str.lower):
            path = os.path.join(root, name)
            if not os.path.isdir(path) and not self._is_supported_cube_file(path):
                continue
            if os.path.isdir(path):
                frame_dir = os.path.join(path, "images")
                if not os.path.isdir(frame_dir):
                    frame_dir = path
                scientific_frames = [
                    f for f in os.listdir(frame_dir)
                    if f.lower().endswith((".tif", ".tiff"))
                ]
                preview_frames = [
                    f for f in os.listdir(frame_dir)
                    if f.lower().endswith((".png", ".jpg", ".jpeg"))
                ]
                frames = scientific_frames or preview_frames
            else:
                frames = [name]
            # Try to load metadata if it exists
            meta_path = os.path.join(path, "metadata", "metadata.json")
            if not os.path.isfile(meta_path):
                meta_path = os.path.join(path, "metadata.json")
            meta = {}
            if name.lower() == "uploads" and not os.path.isfile(meta_path):
                continue
            if os.path.isfile(meta_path):
                with open(meta_path, encoding="utf-8") as fh:
                    meta = json.load(fh)
                if isinstance(meta.get("analysis"), dict):
                    meta["analysis"].pop("png_base64", None)
            manifest_path = os.path.join(path, "metadata", "manifest.json")
            if not os.path.isfile(manifest_path):
                manifest_path = os.path.join(path, "manifest.json")
            if os.path.isfile(manifest_path):
                with open(manifest_path, encoding="utf-8") as fh:
                    meta["manifest"] = json.load(fh)
            cube_info = self._cube_info(path, meta)
            if cube_info:
                meta["cube"] = {**meta.get("cube", {}), **cube_info}
            created_at = (
                meta.get("creation_timestamp")
                or meta.get("created_at")
                or meta.get("timestamp")
                or (meta.get("analysis", {}) if isinstance(meta.get("analysis"), dict) else {}).get("created_at")
            )
            modified_at = datetime.fromtimestamp(
                os.path.getmtime(path),
                timezone.utc,
            ).astimezone().isoformat(timespec="seconds")
            sessions.append({
                "name"        : name,
                "frame_count" : int(meta.get("frames_acquired") or len(frames)),
                "cube"        : cube_info,
                "metadata"    : meta,
                "created_at"  : created_at or modified_at,
                "modified_at" : modified_at,
                "sort_name"   : name.lower(),
                "source_format": self._source_format_for_path(path, meta),
            })
        sessions.sort(key=lambda item: (item.get("modified_at") or "", item.get("sort_name") or ""), reverse=True)
        return sessions

    def get_cube_summary(self, session: str) -> Optional[dict]:
        context = self._cube_context(session)
        if context is None:
            return None
        session_path, meta, arr, cube_path, cube_meta = context
        wavelengths = cube_meta["wavelengths_nm"]
        band_index = max(0, min(arr.shape[2] - 1, arr.shape[2] // 2))
        plane = np.asarray(arr[:, :, band_index].T, dtype=np.float32)
        profile = self._profile_at(arr, arr.shape[0] // 2, arr.shape[1] // 2)
        hist = self._histogram_for_plane(plane)
        stats = self._plane_stats(plane)
        rgb = self._rgb_preview(arr)
        band = self._png_for_plane(plane)
        return {
            "session": session,
            "shape": cube_meta["cube_shape"],
            "cube_shape": cube_meta["cube_shape"],
            "axis_order": cube_meta["dimension_order"],
            "dimension_order": cube_meta["dimension_order"],
            "width": int(arr.shape[0]),
            "height": int(arr.shape[1]),
            "bands": int(arr.shape[2]),
            "dtype": str(arr.dtype),
            "bytes": int(os.path.getsize(cube_path)),
            "relative_path": os.path.relpath(cube_path, session_path),
            "wavelengths_nm": wavelengths,
            "lambda_axis": cube_meta["lambda_axis"],
            "x_positions": cube_meta["x_positions"],
            "stage_positions": cube_meta["stage_positions"],
            "y_pixels": cube_meta["y_pixels"],
            "y_axis": cube_meta["y_axis"],
            "frame_count": cube_meta["frame_count"],
            "source_scan_folder": cube_meta["source_scan_folder"],
            "creation_timestamp": cube_meta["creation_timestamp"],
            "metadata": cube_meta,
            "band_index": int(band_index),
            "band_png_base64": band,
            "rgb_png_base64": rgb,
            "profile": profile,
            "histogram": hist,
            **stats,
        }

    def get_cube_slice(self, session: str, mode: str, index: int) -> Optional[dict]:
        mode = (mode or "band").lower()
        if mode in {"x", "yl", "y_lambda", "y-lambda"}:
            return self.get_y_lambda_slice(session, index)
        if mode in {"y", "xl", "x_lambda", "x-lambda"}:
            return self.get_x_lambda_slice(session, index)
        return self.get_spatial_slice(session, index)

    def get_cube_spectrum(self, session: str, x: int, y: int) -> Optional[dict]:
        return self.get_spectrum_at(session, x, y)

    def get_cube_volume(self, session: str, max_points: int = 45000) -> Optional[dict]:
        """Return a bounded scalar grid for interactive browser volume rendering."""
        context = self._cube_context(session)
        if context is None:
            return None
        _, _, arr, _, cube_meta = context
        max_points = max(8000, min(int(max_points), 90000))
        target_axis = max(8, int(round(max_points ** (1 / 3))))
        steps = [
            max(1, int(math.ceil(size / target_axis)))
            for size in arr.shape
        ]
        sampled = np.asarray(
            arr[::steps[0], ::steps[1], ::steps[2]],
            dtype=np.float32,
        )
        while sampled.size > max_points:
            largest_axis = int(np.argmax(sampled.shape))
            steps[largest_axis] += 1
            sampled = np.asarray(
                arr[::steps[0], ::steps[1], ::steps[2]],
                dtype=np.float32,
            )

        finite = sampled[np.isfinite(sampled)]
        if finite.size:
            isomin = float(np.percentile(finite, 70))
            isomax = float(np.percentile(finite, 99.5))
            if isomax <= isomin:
                isomin = float(np.min(finite))
                isomax = float(np.max(finite))
        else:
            isomin, isomax = 0.0, 1.0
        if isomax <= isomin:
            isomax = isomin + 1.0

        x_values = np.asarray(cube_meta["x_positions"], dtype=np.float32)[::steps[0]][: sampled.shape[0]]
        y_values = np.asarray(cube_meta["y_axis"], dtype=np.float32)[::steps[1]][: sampled.shape[1]]
        wavelength_values = np.asarray(cube_meta["wavelengths_nm"], dtype=np.float32)[::steps[2]][: sampled.shape[2]]
        x_grid, y_grid, wavelength_grid = np.meshgrid(
            x_values,
            y_values,
            wavelength_values,
            indexing="ij",
        )
        return {
            "session": session,
            "source_shape": [int(value) for value in arr.shape],
            "sampled_shape": [int(value) for value in sampled.shape],
            "sample_steps": [int(value) for value in steps],
            "point_count": int(sampled.size),
            "x": x_grid.ravel().astype(float).tolist(),
            "y": y_grid.ravel().astype(float).tolist(),
            "wavelength": wavelength_grid.ravel().astype(float).tolist(),
            "value": sampled.ravel().astype(float).tolist(),
            "isomin": isomin,
            "isomax": isomax,
            "axis_labels": {
                "x": "Stage position (mm)",
                "y": "Camera row (px)",
                "z": "Wavelength (nm)",
                "value": "Intensity (a.u.)",
            },
        }

    def get_spatial_slice(self, session: str, lambda_index: int) -> Optional[dict]:
        """Return X-Y intensity image at one wavelength index."""
        context = self._cube_context(session)
        if context is None:
            return None
        _, _, arr, _, cube_meta = context
        wi = self._clamp_index(lambda_index, arr.shape[2], "wavelength")
        plane = np.asarray(arr[:, :, wi].T, dtype=np.float32)
        return self._slice_payload(
            session,
            "spatial",
            "lambda",
            wi,
            cube_meta["wavelengths_nm"][wi],
            plane,
            ["y", "x"],
            {
                "x": cube_meta["x_positions"],
                "y": cube_meta["y_axis"],
            },
            {
                "x": "X / stage position",
                "y": "Y pixel",
                "fixed": "Wavelength (nm)",
            },
            cube_meta,
            mode_alias="band",
        )

    def get_spectrum_at(self, session: str, x: int, y: int) -> Optional[dict]:
        """Return wavelength profile at one X,Y pixel."""
        context = self._cube_context(session)
        if context is None:
            return None
        _, _, arr, _, cube_meta = context
        xi = self._clamp_index(x, arr.shape[0], "x")
        yi = self._clamp_index(y, arr.shape[1], "y")
        profile = self._profile_at(arr, xi, yi)
        return {
            "session": session,
            "x": int(xi),
            "y": int(yi),
            "x_value": cube_meta["x_positions"][xi],
            "y_value": cube_meta["y_axis"][yi],
            "wavelengths_nm": cube_meta["wavelengths_nm"],
            "lambda_axis": cube_meta["lambda_axis"],
            "axis_order": ["wavelength"],
            "axis_labels": {
                "x": "Wavelength (nm)",
                "y": "Intensity",
                "fixed": "X,Y pixel",
            },
            "dimension_order": cube_meta["dimension_order"],
            "cube_shape": cube_meta["cube_shape"],
            "intensity": profile,
        }

    def get_y_lambda_slice(self, session: str, x: int) -> Optional[dict]:
        """Return Y-lambda image at one fixed X/stage index."""
        context = self._cube_context(session)
        if context is None:
            return None
        _, _, arr, _, cube_meta = context
        xi = self._clamp_index(x, arr.shape[0], "x")
        plane = np.asarray(arr[xi, :, :], dtype=np.float32)
        return self._slice_payload(
            session,
            "y_lambda",
            "x",
            xi,
            cube_meta["x_positions"][xi],
            plane,
            ["y", "wavelength"],
            {
                "y": cube_meta["y_axis"],
                "wavelength": cube_meta["wavelengths_nm"],
            },
            {
                "x": "Wavelength (nm)",
                "y": "Y pixel",
                "fixed": "X / stage position",
            },
            cube_meta,
            mode_alias="x",
        )

    def get_x_lambda_slice(self, session: str, y: int) -> Optional[dict]:
        """Return X-lambda image at one fixed Y index."""
        context = self._cube_context(session)
        if context is None:
            return None
        _, _, arr, _, cube_meta = context
        yi = self._clamp_index(y, arr.shape[1], "y")
        plane = np.asarray(arr[:, yi, :].T, dtype=np.float32)
        return self._slice_payload(
            session,
            "x_lambda",
            "y",
            yi,
            cube_meta["y_axis"][yi],
            plane,
            ["wavelength", "x"],
            {
                "x": cube_meta["x_positions"],
                "wavelength": cube_meta["wavelengths_nm"],
            },
            {
                "x": "X / stage position",
                "y": "Wavelength (nm)",
                "fixed": "Y pixel",
            },
            cube_meta,
            mode_alias="y",
        )

    def get_intensity_map(self, session: str) -> Optional[np.ndarray]:
        """
        Returns normalised float32 [0,1] 2D intensity map.
        Rebuilds from disk if not in memory.
        """
        with self._lock:
            if session in self._cubes:
                return self._cubes[session].intensity_map_normalised()

        # Try reconstructing from saved PNG files
        return self._rebuild_from_disk(session)

    def get_frame_jpeg(self, session: str, yi: int, xi: int) -> Optional[bytes]:
        """Fetch a specific frame JPEG from disk."""
        import cv2
        path = os.path.join(config.SAVE_FOLDER, session)
        if not os.path.isdir(path):
            return None

        # Find matching file
        meta_frame = self._frame_from_metadata(path, yi, xi)
        if meta_frame:
            img = cv2.imread(meta_frame, cv2.IMREAD_UNCHANGED)
            if img is not None:
                _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return buf.tobytes()

        frame_dir = os.path.join(path, "images")
        if not os.path.isdir(frame_dir):
            frame_dir = path

        for fname in os.listdir(frame_dir):
            legacy_match = f"_y{yi:04d}_x{xi:04d}" in fname
            modern_match = f"_img_{xi + 1:04d}_" in fname and yi == 0
            if legacy_match or modern_match:
                fpath = os.path.join(frame_dir, fname)
                img   = cv2.imread(fpath, cv2.IMREAD_UNCHANGED)
                if img is None:
                    return None
                _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return buf.tobytes()

        fallback_files = [
            f for f in os.listdir(path)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
        ]
        if not fallback_files and frame_dir != path:
            fallback_files = [
                os.path.join("images", f)
                for f in os.listdir(frame_dir)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
            ]
        for fname in sorted(fallback_files):
            fpath = os.path.join(path, fname)
            img = cv2.imread(fpath, cv2.IMREAD_UNCHANGED)
            if img is not None:
                _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return buf.tobytes()
        return None

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _rebuild_from_disk(self, session: str) -> Optional[np.ndarray]:
        """
        Reconstruct the intensity map by reading frame filenames.
        Parses y/x indices from filename pattern: frame_NNNNN_yYYYY_xXXXX.png
        """
        import cv2
        path = os.path.join(config.SAVE_FOLDER, session)
        if not os.path.isdir(path):
            return None

        preview_path = os.path.join(path, "preview.png")
        if os.path.isfile(preview_path):
            img = cv2.imread(preview_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                img = img.astype(np.float32)
                mn, mx = img.min(), img.max()
                if mx > mn:
                    img = (img - mn) / (mx - mn)
                return img

        metadata_map = self._rebuild_from_metadata(path)
        if metadata_map is not None:
            with self._lock:
                self._cubes[session] = metadata_map
            return metadata_map.intensity_map_normalised()

        frame_dir = os.path.join(path, "images")
        if not os.path.isdir(frame_dir):
            frame_dir = path
        scientific_frames = [
            f for f in os.listdir(frame_dir)
            if f.lower().endswith((".tif", ".tiff"))
        ]
        preview_frames = [
            f for f in os.listdir(frame_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        frames = scientific_frames or preview_frames
        if not frames:
            return None

        coords = []
        for f in frames:
            try:
                legacy = re.search(r"_y(\d{4})_x(\d{4})", f)
                modern = re.search(r"_img_(\d{4})_", f)
                if legacy:
                    yi = int(legacy.group(1))
                    xi = int(legacy.group(2))
                elif modern:
                    yi = 0
                    xi = int(modern.group(1)) - 1
                else:
                    continue
                coords.append((yi, xi, f))
            except (IndexError, ValueError):
                pass

        if not coords:
            return None

        max_y = max(c[0] for c in coords) + 1
        max_x = max(c[1] for c in coords) + 1
        cube  = _SessionCube(session, max_x, max_y)

        for yi, xi, fname in coords:
            fpath = os.path.join(frame_dir, fname)
            img   = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                intensity = float(np.mean(img))
                cube.record(xi, yi, intensity)

        with self._lock:
            self._cubes[session] = cube
        return cube.intensity_map_normalised()

    def _load_metadata(self, session_path: str) -> dict:
        meta = {}
        for path in (
            os.path.join(session_path, "metadata", "metadata.json"),
            os.path.join(session_path, "metadata.json"),
        ):
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as fh:
                        meta = json.load(fh)
                    break
                except Exception:
                    meta = {}
                    break
        for path in (
            os.path.join(session_path, "metadata", "manifest.json"),
            os.path.join(session_path, "manifest.json"),
        ):
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as fh:
                        meta["manifest"] = json.load(fh)
                    break
                except Exception:
                    break
        return meta

    def _cube_context(self, session: str) -> Optional[tuple[str, dict, np.ndarray, str, dict]]:
        session_path = os.path.join(config.SAVE_FOLDER, session)
        if not os.path.isdir(session_path) and not self._is_supported_cube_file(session_path):
            return None
        meta = self._load_metadata(session_path) if os.path.isdir(session_path) else {}
        cube_path = self._cube_path(session_path, meta)
        if not cube_path:
            return None
        cache_key = os.path.abspath(cube_path)
        try:
            cache_mtime = os.path.getmtime(cube_path)
            cached = self._cube_context_cache.get(cache_key)
            if cached and cached[0] == cache_mtime:
                return cached[1]
        except OSError:
            cache_mtime = 0.0
        arr = self._normalise_cube_view(self._load_cube_array(cube_path), meta)
        metadata_root = session_path if os.path.isdir(session_path) else os.path.dirname(session_path)
        cube_meta = self._cube_metadata(session, metadata_root, arr, cube_path, meta)
        context = (session_path, meta, arr, cube_path, cube_meta)
        self._cube_context_cache = {cache_key: (cache_mtime, context)}
        return context

    def _cube_info(self, session_path: str, meta: dict) -> Optional[dict]:
        cube_path = self._cube_path(session_path, meta)
        if not cube_path or not os.path.isfile(cube_path):
            return None
        analysis = meta.get("analysis") if isinstance(meta.get("analysis"), dict) else {}
        ext = os.path.splitext(cube_path)[1].lower()
        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        manifest_cube = manifest.get("cube") if isinstance(manifest.get("cube"), dict) else {}
        shape = manifest_cube.get("shape") if isinstance(manifest_cube.get("shape"), list) else None
        if shape:
            normalised_shape = self._normalised_shape_from_metadata([int(v) for v in shape], manifest_cube)
            return {
                "available": True,
                "shape": normalised_shape,
                "cube_shape": normalised_shape,
                "dimension_order": manifest_cube.get("dimension_order") or manifest_cube.get("axis_order") or [],
                "axis_order": manifest_cube.get("axis_order") or manifest_cube.get("dimension_order") or [],
                "dtype": str(manifest_cube.get("dtype") or ""),
                "bytes": int(manifest_cube.get("bytes") or os.path.getsize(cube_path)),
                "relative_path": os.path.relpath(cube_path, session_path) if os.path.isdir(session_path) else os.path.basename(cube_path),
                "width": int(normalised_shape[0]) if len(normalised_shape) >= 1 else 0,
                "height": int(normalised_shape[1]) if len(normalised_shape) >= 2 else 0,
                "bands": int(normalised_shape[2]) if len(normalised_shape) >= 3 else 0,
                "frame_count": int(normalised_shape[0]) if normalised_shape else 0,
                "source_format": ext.lstrip(".").upper() or "NUMPY",
            }
        if ext in {".mat", ".h5", ".hdf5"} and isinstance(analysis.get("shape"), list):
            shape = [int(v) for v in analysis.get("shape", []) if isinstance(v, (int, float))]
            normalised_shape = self._normalised_shape_from_metadata(shape, analysis)
            dimension_order = self._metadata_order_candidate({"analysis": analysis}) or []
            return {
                "available": True,
                "shape": normalised_shape,
                "cube_shape": normalised_shape,
                "dimension_order": dimension_order,
                "axis_order": dimension_order,
                "dtype": str(analysis.get("dtype") or ""),
                "bytes": int(os.path.getsize(cube_path)),
                "relative_path": os.path.relpath(cube_path, session_path) if os.path.isdir(session_path) else os.path.basename(cube_path),
                "width": int(normalised_shape[0]) if len(normalised_shape) >= 1 else 0,
                "height": int(normalised_shape[1]) if len(normalised_shape) >= 2 else 0,
                "bands": int(normalised_shape[2]) if len(normalised_shape) >= 3 else 0,
                "frame_count": int(normalised_shape[0]) if normalised_shape else 0,
                "source_format": analysis.get("source_format") or ext.lstrip(".").upper(),
            }
        try:
            arr = self._load_cube_array(cube_path)
            normalised = self._normalise_cube_view(arr, meta)
            metadata_root = session_path if os.path.isdir(session_path) else os.path.dirname(session_path)
            cube_meta = self._cube_metadata(os.path.basename(session_path), metadata_root, normalised, cube_path, meta)
            return {
                "available": True,
                "shape": [int(v) for v in normalised.shape],
                "cube_shape": cube_meta["cube_shape"],
                "dimension_order": cube_meta["dimension_order"],
                "axis_order": cube_meta["dimension_order"],
                "dtype": str(arr.dtype),
                "bytes": int(os.path.getsize(cube_path)),
                "relative_path": os.path.relpath(cube_path, metadata_root),
                "width": int(normalised.shape[0]),
                "height": int(normalised.shape[1]),
                "bands": int(normalised.shape[2]),
                "frame_count": cube_meta["frame_count"],
                "source_format": ext.lstrip(".").upper() or "NUMPY",
            }
        except Exception:
            return None

    def _cube_path(self, session_path: str, meta: dict) -> Optional[str]:
        if self._is_supported_cube_file(session_path):
            return session_path
        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        cube = meta.get("cube") if isinstance(meta.get("cube"), dict) else {}
        candidates = [
            cube.get("relative_path"),
            manifest.get("cube", {}).get("relative_path") if isinstance(manifest.get("cube"), dict) else None,
            cube.get("compressed_relative_path"),
            manifest.get("cube", {}).get("compressed_relative_path") if isinstance(manifest.get("cube"), dict) else None,
            os.path.join("cube", "data_cube.npz"),
            "data_cube.npz",
            os.path.join("cube", "data_cube.npy"),
            "data_cube.npy",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            path = os.path.join(session_path, candidate)
            if os.path.isfile(path):
                return path
        for folder in (session_path, os.path.join(session_path, "cube")):
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder), key=str.lower):
                candidate = os.path.join(folder, name)
                if self._is_supported_cube_file(candidate):
                    return candidate
        return None

    def _open_cube(self, session_path: str, meta: dict) -> Optional[tuple[np.ndarray, str]]:
        cube_path = self._cube_path(session_path, meta)
        if not cube_path:
            return None
        arr = self._load_cube_array(cube_path)
        return self._normalise_cube_view(arr, meta), cube_path

    def _is_supported_cube_file(self, path: str) -> bool:
        return os.path.isfile(path) and os.path.splitext(path)[1].lower() in {".npy", ".npz", ".mat", ".h5", ".hdf5"}

    def _load_cube_array(self, path: str) -> np.ndarray:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".npy":
            return np.load(path, mmap_mode="r", allow_pickle=False)
        if ext == ".npz":
            with np.load(path, allow_pickle=False) as archive:
                if "cube" in archive.files:
                    return np.asarray(archive["cube"])
                for name in archive.files:
                    arr = np.asarray(archive[name])
                    if arr.ndim >= 2 and np.issubdtype(arr.dtype, np.number):
                        return arr
            raise ValueError("No numeric cube array found in NPZ archive")
        if ext == ".mat":
            return self._load_mat_array(path)
        if ext in {".h5", ".hdf5"}:
            return self._load_hdf5_array(path)
        raise ValueError(f"Unsupported cube file format: {ext}")

    def _storage_policy(self) -> dict:
        policy = dict(getattr(config, "STORAGE_POLICY", {}) or {})
        policy.setdefault("keep_raw_frames", True)
        policy.setdefault("keep_npy_cube", False)
        policy.setdefault("keep_npz_cube", bool(getattr(config, "COMPRESS_CUBES", True)))
        policy.setdefault("compression", True)
        return policy

    def _cleanup_raw_frames(self, session_path: str, manifest: dict) -> None:
        """Delete only current-session raw frames after a valid cube is written."""
        for frame in manifest.get("frames", []):
            rel_path = frame.get("tiff")
            if not rel_path:
                continue
            path = os.path.abspath(os.path.join(session_path, rel_path))
            if not path.startswith(os.path.abspath(session_path) + os.sep):
                continue
            if os.path.isfile(path):
                os.remove(path)

    def _release_cube_cache(self) -> None:
        self._cube_context_cache.clear()
        import gc

        gc.collect()

    def _load_mat_array(self, path: str) -> np.ndarray:
        try:
            from scipy.io import loadmat

            _, arr = self._best_numeric_array(loadmat(path, squeeze_me=True, struct_as_record=False))
            return np.asarray(arr)
        except (NotImplementedError, ValueError, OSError):
            return self._load_hdf5_array(path)

    def _load_hdf5_array(self, path: str) -> np.ndarray:
        import h5py

        with h5py.File(path, "r") as handle:
            _, dataset = self._best_hdf5_dataset(handle)
            return np.asarray(dataset)

    def _best_numeric_array(self, items: dict) -> tuple[str, np.ndarray]:
        candidates = []
        for name, value in items.items():
            if str(name).startswith("__"):
                continue
            arr = np.asarray(value)
            if arr.dtype == object or arr.size == 0 or arr.ndim == 0:
                continue
            if not np.issubdtype(arr.dtype, np.number):
                continue
            candidates.append((arr.ndim, arr.size, str(name), arr))
        if not candidates:
            raise ValueError("No numeric hyperspectral array found in MAT file")
        _, _, name, arr = sorted(candidates, reverse=True)[0]
        return name, arr

    def _best_hdf5_dataset(self, handle) -> tuple[str, object]:
        candidates = []

        def visit(name, obj):
            if hasattr(obj, "shape") and hasattr(obj, "dtype"):
                if obj.shape and np.issubdtype(np.dtype(obj.dtype), np.number):
                    candidates.append((len(obj.shape), int(np.prod(obj.shape)), name, obj))

        handle.visititems(visit)
        if not candidates:
            raise ValueError("No numeric HDF5 dataset found")
        _, _, name, dataset = sorted(candidates, reverse=True)[0]
        return name, dataset

    def _normalised_shape_from_metadata(self, shape: list[int], meta: dict) -> list[int]:
        if not shape:
            return []
        while len(shape) > 3:
            shape = shape[:-1]
        if len(shape) == 2:
            shape = [shape[1], shape[0], 1]
        if len(shape) != 3:
            return shape
        order = meta.get("dimension_order") or meta.get("axis_order")
        if isinstance(order, list) and len(order) >= 3:
            mapped = [self._normalise_axis_name(name, index, 3) for index, name in enumerate(order[:3])]
            if {"x", "y", "wavelength"}.issubset(set(mapped)):
                return [shape[mapped.index("x")], shape[mapped.index("y")], shape[mapped.index("wavelength")]]
        axes = meta.get("axes")
        if isinstance(axes, str):
            mapped = self._axis_string_to_order(axes)
            if len(mapped) >= 3 and {"x", "y", "wavelength"}.issubset(set(mapped)):
                return [shape[mapped.index("x")], shape[mapped.index("y")], shape[mapped.index("wavelength")]]
        return shape

    def _axis_string_to_order(self, axes: str) -> list[str]:
        return [
            self._normalise_axis_name(axis, index, len(axes))
            for index, axis in enumerate(str(axes).strip())
        ]

    def _source_format_for_path(self, path: str, meta: dict) -> str:
        analysis = meta.get("analysis") if isinstance(meta.get("analysis"), dict) else {}
        if analysis.get("source_format"):
            return str(analysis["source_format"])
        cube_path = self._cube_path(path, meta)
        ext = os.path.splitext(cube_path or path)[1].lower().lstrip(".")
        return ext.upper() if ext else "SESSION"

    def _normalise_cube_view(self, arr: np.ndarray, meta: Optional[dict] = None) -> np.ndarray:
        view = arr
        while view.ndim > 3:
            view = view[..., 0]
        if view.ndim == 2:
            view = view[:, :, np.newaxis]
        if view.ndim != 3:
            raise ValueError(f"Cube must be 2-D or 3-D, got shape {arr.shape}")
        dimension_order = self._dimension_order_for_cube(view, meta or {})
        if dimension_order != ["x", "y", "wavelength"]:
            try:
                axes = [
                    dimension_order.index("x"),
                    dimension_order.index("y"),
                    dimension_order.index("wavelength"),
                ]
                view = np.moveaxis(view, axes, [0, 1, 2])
            except ValueError as exc:
                raise ValueError(
                    f"Cannot understand cube dimension_order={dimension_order}"
                ) from exc
        return view

    def _cube_metadata(
        self,
        session: str,
        session_path: str,
        arr: np.ndarray,
        cube_path: str,
        meta: dict,
    ) -> dict:
        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        cube_meta = manifest.get("cube") if isinstance(manifest.get("cube"), dict) else {}
        top_cube = meta.get("cube") if isinstance(meta.get("cube"), dict) else {}
        created_at = (
            manifest.get("creation_timestamp")
            or manifest.get("created_at")
            or meta.get("creation_timestamp")
            or meta.get("created_at")
            or datetime.fromtimestamp(os.path.getmtime(cube_path), timezone.utc).astimezone().isoformat(timespec="seconds")
        )
        x_positions = self._x_positions_for_cube(arr, meta)
        y_axis = self._y_axis_for_cube(arr, meta)
        wavelengths = self._wavelengths_for_cube(arr, meta)
        warnings = []
        if not self._metadata_order_candidate(meta):
            warnings.append("dimension_order was inferred as x/y/wavelength for this loaded cube")
        return {
            "schema": "hsi-core.cube-metadata.v1",
            "session": session,
            "cube_shape": [int(v) for v in arr.shape],
            "raw_cube_shape": [
                int(v)
                for v in (
                    cube_meta.get("shape")
                    or top_cube.get("shape")
                    or arr.shape
                )
            ],
            "dimension_order": ["x", "y", "wavelength"],
            "x_positions": x_positions,
            "stage_positions": x_positions,
            "y_pixels": y_axis,
            "y_axis": y_axis,
            "wavelengths_nm": wavelengths,
            "lambda_axis": wavelengths,
            "frame_count": int(arr.shape[0]),
            "dtype": str(arr.dtype),
            "relative_path": os.path.relpath(cube_path, session_path),
            "source_scan_folder": os.path.abspath(session_path),
            "creation_timestamp": created_at,
            "metadata_warnings": warnings,
        }

    def _metadata_order_candidate(self, meta: dict) -> Optional[list[str]]:
        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        manifest_cube = manifest.get("cube") if isinstance(manifest.get("cube"), dict) else {}
        top_cube = meta.get("cube") if isinstance(meta.get("cube"), dict) else {}
        analysis = meta.get("analysis") if isinstance(meta.get("analysis"), dict) else {}
        for source in (manifest, manifest_cube, top_cube, analysis, meta):
            for key in ("dimension_order", "axis_order"):
                value = source.get(key) if isinstance(source, dict) else None
                if isinstance(value, list) and value:
                    return [str(item) for item in value]
            axes = source.get("axes") if isinstance(source, dict) else None
            if isinstance(axes, str) and axes:
                mapped = self._axis_string_to_order(axes)
                if mapped:
                    return mapped
        return None

    def _dimension_order_for_cube(self, arr: np.ndarray, meta: dict) -> list[str]:
        candidate = self._metadata_order_candidate(meta)
        if candidate:
            mapped = [
                self._normalise_axis_name(name, index, arr.ndim)
                for index, name in enumerate(candidate[: arr.ndim])
            ]
            if {"x", "y", "wavelength"}.issubset(set(mapped)):
                return mapped[: arr.ndim]

        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        wavelengths = manifest.get("wavelengths_nm") if isinstance(manifest.get("wavelengths_nm"), list) else None
        positions = manifest.get("positions_mm") if isinstance(manifest.get("positions_mm"), list) else None
        if wavelengths and positions:
            order: list[Optional[str]] = [None] * arr.ndim
            for axis, size in enumerate(arr.shape):
                if len(wavelengths) == size and "wavelength" not in order:
                    order[axis] = "wavelength"
                elif len(positions) == size and "x" not in order:
                    order[axis] = "x"
            for axis in range(arr.ndim):
                if order[axis] is None:
                    order[axis] = "y"
            mapped = [str(axis) for axis in order]
            if {"x", "y", "wavelength"}.issubset(set(mapped)):
                return mapped

        return ["x", "y", "wavelength"]

    def _normalise_axis_name(self, name: str, index: int, ndim: int) -> str:
        key = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
        if key in {"x", "x_index", "frame", "frame_index", "stage", "stage_position", "stage_positions"}:
            return "x"
        if key in {"y", "y_index", "line", "lines", "row", "rows", "camera_y"}:
            return "y"
        if key in {"wavelength", "lambda", "lambda_axis", "wavelengths_nm", "band", "bands", "spectral", "spectral_axis"}:
            return "wavelength"
        if key in {"z", "z_index"}:
            return "wavelength"
        if key == "samples":
            return "x"
        if key.startswith("camera_axis_"):
            try:
                camera_axis = int(key.rsplit("_", 1)[-1])
            except ValueError:
                camera_axis = index - 1
            if camera_axis <= 0:
                return "y"
            return "wavelength" if ndim <= 3 else f"camera_axis_{camera_axis}"
        return key

    def _wavelengths_for_cube(self, arr: np.ndarray, meta: dict) -> list[float]:
        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        cube = meta.get("cube") if isinstance(meta.get("cube"), dict) else {}
        candidates = [
            manifest.get("wavelengths_nm"),
            manifest.get("lambda_axis"),
            meta.get("wavelengths_nm"),
            meta.get("lambda_axis"),
            cube.get("wavelengths_nm"),
            cube.get("lambda_axis"),
        ]
        for wavelengths in candidates:
            if isinstance(wavelengths, list) and len(wavelengths) == arr.shape[2]:
                return [float(v) for v in wavelengths]
        return np.linspace(
            float(meta.get("wavelength_min_nm") or getattr(config, "SPECTRAL_MIN_NM", 400)),
            float(meta.get("wavelength_max_nm") or getattr(config, "SPECTRAL_MAX_NM", 1000)),
            int(arr.shape[2]),
        ).round(4).tolist()

    def _x_positions_for_cube(self, arr: np.ndarray, meta: dict) -> list[float]:
        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        candidates = [
            manifest.get("x_positions"),
            manifest.get("stage_positions"),
            manifest.get("positions_mm"),
            meta.get("x_positions"),
            meta.get("stage_positions"),
        ]
        frames = manifest.get("frames") if isinstance(manifest.get("frames"), list) else []
        if frames:
            by_index = {}
            for frame in frames:
                try:
                    by_index[int(frame.get("scan_index", frame.get("frame_index", -1)))] = float(frame.get("position_mm"))
                except (TypeError, ValueError):
                    continue
            if by_index:
                candidates.append([by_index.get(index, float(index)) for index in range(arr.shape[0])])
        for positions in candidates:
            if isinstance(positions, list) and len(positions) == arr.shape[0]:
                try:
                    return [float(v) for v in positions]
                except (TypeError, ValueError):
                    continue
        return [float(index) for index in range(arr.shape[0])]

    def _y_axis_for_cube(self, arr: np.ndarray, meta: dict) -> list[int]:
        manifest = meta.get("manifest") if isinstance(meta.get("manifest"), dict) else {}
        candidates = [
            manifest.get("y_axis"),
            manifest.get("y_pixels"),
            meta.get("y_axis"),
            meta.get("y_pixels"),
        ]
        for y_values in candidates:
            if isinstance(y_values, list) and len(y_values) == arr.shape[1]:
                try:
                    return [int(v) for v in y_values]
                except (TypeError, ValueError):
                    continue
        return list(range(int(arr.shape[1])))

    def _profile_at(self, arr: np.ndarray, x: int, y: int) -> list[float]:
        return np.asarray(arr[int(x), int(y), :], dtype=np.float32).round(4).astype(float).tolist()

    def _clamp_index(self, value: int, size: int, axis: str) -> int:
        if size <= 0:
            raise ValueError(f"Cube {axis} axis is empty")
        return max(0, min(size - 1, int(value)))

    def _plane_stats(self, plane: np.ndarray) -> dict:
        plane_float = np.asarray(plane, dtype=np.float32)
        finite = plane_float[np.isfinite(plane_float)]
        if finite.size == 0:
            finite = np.array([0.0], dtype=np.float32)
        return {
            "mean": round(float(np.mean(finite)), 4),
            "min": round(float(np.min(finite)), 4),
            "max": round(float(np.max(finite)), 4),
            "std": round(float(np.std(finite)), 4),
        }

    def _histogram_for_plane(self, plane: np.ndarray) -> list[int]:
        plane_float = np.asarray(plane, dtype=np.float32)
        finite = plane_float[np.isfinite(plane_float)]
        if finite.size == 0:
            finite = np.array([0.0], dtype=np.float32)
        hist, _ = np.histogram(finite, bins=64)
        return hist.astype(int).tolist()

    def _slice_payload(
        self,
        session: str,
        view_mode: str,
        fixed_axis: str,
        fixed_index: int,
        fixed_value: float,
        plane: np.ndarray,
        axis_order: list[str],
        axis_values: dict,
        axis_labels: dict,
        cube_meta: dict,
        *,
        mode_alias: str,
    ) -> dict:
        plane_float = np.asarray(plane, dtype=np.float32)
        return {
            "session": session,
            "view_mode": view_mode,
            "mode": mode_alias,
            "index": int(fixed_index),
            "fixed_axis": fixed_axis,
            "fixed_index": int(fixed_index),
            "fixed_value": float(fixed_value),
            "axes": "-".join(axis_order),
            "axis_order": axis_order,
            "axis_values": axis_values,
            "axis_labels": axis_labels,
            "dimension_order": cube_meta["dimension_order"],
            "cube_shape": cube_meta["cube_shape"],
            "png_base64": self._png_for_plane(plane_float),
            "shape": [int(v) for v in plane_float.shape],
            "width": int(plane_float.shape[1] if plane_float.ndim == 2 else 0),
            "height": int(plane_float.shape[0] if plane_float.ndim == 2 else 0),
            "histogram": self._histogram_for_plane(plane_float),
            **self._plane_stats(plane_float),
        }

    def _png_for_plane(self, plane: np.ndarray) -> str:
        import base64
        import cv2

        sample = np.asarray(plane, dtype=np.float32)
        if sample.ndim != 2:
            sample = np.squeeze(sample)
        finite = sample[np.isfinite(sample)]
        if finite.size == 0:
            finite = np.array([0.0], dtype=np.float32)
        low = float(np.percentile(finite, 1))
        high = float(np.percentile(finite, 99))
        if high <= low:
            low = float(np.min(finite))
            high = float(np.max(finite))
        if high <= low:
            high = low + 1.0
        scaled = np.clip((sample - low) / (high - low), 0, 1)
        img = (scaled * 255).astype(np.uint8)
        ok, buf = cv2.imencode(".png", img)
        return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""

    def _rgb_preview(self, arr: np.ndarray) -> str:
        if arr.shape[2] < 3:
            return self._png_for_plane(arr[:, :, 0].T)
        bands = [
            max(0, int(round((arr.shape[2] - 1) * frac)))
            for frac in (0.15, 0.50, 0.85)
        ]
        planes = [np.asarray(arr[:, :, band].T, dtype=np.float32) for band in bands]
        stack = np.dstack(planes[::-1])
        finite = stack[np.isfinite(stack)]
        low = float(np.percentile(finite, 1)) if finite.size else 0.0
        high = float(np.percentile(finite, 99)) if finite.size else 1.0
        if high <= low:
            high = low + 1.0
        rgb = (np.clip((stack - low) / (high - low), 0, 1) * 255).astype(np.uint8)
        import base64
        import cv2
        ok, buf = cv2.imencode(".png", rgb)
        return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""

    def _frame_from_metadata(self, session_path: str, yi: int, xi: int) -> Optional[str]:
        meta_path = os.path.join(session_path, "metadata", "metadata.json")
        if not os.path.isfile(meta_path):
            meta_path = os.path.join(session_path, "metadata.json")
        if not os.path.isfile(meta_path) or yi != 0:
            return None
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
            for frame in meta.get("frames", []):
                if int(frame.get("scan_index", -1)) == int(xi):
                    name = frame.get("png") or frame.get("tiff")
                    if name:
                        path = os.path.join(session_path, name)
                        if os.path.isfile(path):
                            return path
        except Exception:
            return None
        return None

    def _rebuild_from_metadata(self, session_path: str) -> Optional[_SessionCube]:
        meta_path = os.path.join(session_path, "metadata", "metadata.json")
        if not os.path.isfile(meta_path):
            meta_path = os.path.join(session_path, "metadata.json")
        if not os.path.isfile(meta_path):
            return None
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
            frames = meta.get("frames", [])
            if not frames:
                return None
            nx = int(meta.get("scan_params", {}).get("number_of_images") or len(frames))
            cube = _SessionCube(meta.get("session_name") or os.path.basename(session_path), nx, 1)
            for frame in frames:
                xi = int(frame.get("scan_index", -1))
                if xi < 0:
                    continue
                intensity = frame.get("intensity_mean")
                if intensity is None:
                    path = self._frame_from_metadata(session_path, 0, xi)
                    if not path:
                        continue
                    import cv2
                    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        continue
                    intensity = float(np.mean(img))
                cube.record(xi, 0, float(intensity))
            return cube
        except Exception:
            return None

    def _write_json(self, path: str, payload: dict) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)


# Singleton instance — imported by server.py and scan.py
data_cube_manager = DataCubeManager()
