# =============================================================================
# HSI-Core — Data Cube Manager
# =============================================================================
# Manages hyperspectral data cubes (sessions) on disk.
# Provides 2-D intensity maps for dashboard heatmap rendering and
# per-frame JPEG serving for the dataset browser.
# =============================================================================

from __future__ import annotations

import json
import os
import threading
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

    # ------------------------------------------------------------------
    # DATASET BROWSER (called by API)
    # ------------------------------------------------------------------

    def list_sessions(self) -> List[dict]:
        """List all sessions found in the save folder."""
        root = config.SAVE_FOLDER
        if not os.path.isdir(root):
            return []
        sessions = []
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if not os.path.isdir(path):
                continue
            frames = [
                f for f in os.listdir(path)
                if f.endswith(".png") or f.endswith(".jpg")
            ]
            # Try to load metadata if it exists
            meta_path = os.path.join(path, "metadata.json")
            meta = {}
            if os.path.isfile(meta_path):
                with open(meta_path) as fh:
                    meta = json.load(fh)
            sessions.append({
                "name"        : name,
                "frame_count" : len(frames),
                "metadata"    : meta,
            })
        return sessions

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
        for fname in os.listdir(path):
            if f"_y{yi:04d}_x{xi:04d}" in fname:
                fpath = os.path.join(path, fname)
                img   = cv2.imread(fpath, cv2.IMREAD_UNCHANGED)
                if img is None:
                    return None
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

        frames = [f for f in os.listdir(path) if f.endswith(".png")]
        if not frames:
            return None

        coords = []
        for f in frames:
            try:
                parts = f.replace(".png", "").split("_")
                yi = int(parts[-2][1:])   # yYYYY
                xi = int(parts[-1][1:])   # xXXXX
                coords.append((yi, xi, f))
            except (IndexError, ValueError):
                pass

        if not coords:
            return None

        max_y = max(c[0] for c in coords) + 1
        max_x = max(c[1] for c in coords) + 1
        cube  = _SessionCube(session, max_x, max_y)

        for yi, xi, fname in coords:
            fpath = os.path.join(path, fname)
            img   = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                intensity = float(np.mean(img))
                cube.record(xi, yi, intensity)

        with self._lock:
            self._cubes[session] = cube
        return cube.intensity_map_normalised()


# Singleton instance — imported by server.py and scan.py
data_cube_manager = DataCubeManager()
