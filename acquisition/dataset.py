# =============================================================================
# HSI-Core — Scientific TIFF Storage & Dataset Management
# =============================================================================
# Manages TIFF image stacks with embedded metadata (wavelength, position, etc.)
# Supports dataset persistence, loading, and export.
# =============================================================================

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
import tifffile

import config


class TIFFMetadata:
    """Encapsulates metadata for a hyperspectral dataset."""
    
    def __init__(self, session_name: str, x_start: float, y_start: float,
                 x_step: float, y_step: float, num_x: int, num_y: int,
                 wavelength_min: float = 400, wavelength_max: float = 1000,
                 exposure_ms: float = 100):
        self.session_name = session_name
        self.timestamp = datetime.now().isoformat()
        self.x_start = x_start
        self.y_start = y_start
        self.x_step = x_step
        self.y_step = y_step
        self.num_x = num_x
        self.num_y = num_y
        self.wavelength_min = wavelength_min
        self.wavelength_max = wavelength_max
        self.exposure_ms = exposure_ms
        self.total_frames = num_x * num_y
        self.frames_acquired = 0
        self.calibration_data = {}
    
    def to_dict(self) -> Dict:
        """Convert metadata to dictionary for JSON serialization."""
        return {
            'session_name': self.session_name,
            'timestamp': self.timestamp,
            'x_start_mm': self.x_start,
            'y_start_mm': self.y_start,
            'x_step_mm': self.x_step,
            'y_step_mm': self.y_step,
            'num_x': self.num_x,
            'num_y': self.num_y,
            'wavelength_min_nm': self.wavelength_min,
            'wavelength_max_nm': self.wavelength_max,
            'exposure_ms': self.exposure_ms,
            'total_frames': self.total_frames,
            'frames_acquired': self.frames_acquired,
            'calibration_data': self.calibration_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> TIFFMetadata:
        """Reconstruct from dictionary."""
        meta = cls(
            data['session_name'],
            data['x_start_mm'],
            data['y_start_mm'],
            data['x_step_mm'],
            data['y_step_mm'],
            data['num_x'],
            data['num_y'],
            data.get('wavelength_min_nm', 400),
            data.get('wavelength_max_nm', 1000),
            data.get('exposure_ms', 100)
        )
        meta.frames_acquired = data['frames_acquired']
        meta.calibration_data = data.get('calibration_data', {})
        return meta


class DatasetManager:
    """Manages hyperspectral dataset persistence and reconstruction."""
    
    def __init__(self, base_path: str = "datasets"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self._lock = threading.RLock()
        self._active_sessions = {}
    
    def create_session(self, metadata: TIFFMetadata) -> str:
        """Initialize new dataset session. Returns session directory path."""
        session_path = self.base_path / metadata.session_name
        session_path.mkdir(exist_ok=True)
        
        # Save metadata
        meta_file = session_path / "metadata.json"
        with open(meta_file, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        # Create frame directory
        frames_dir = session_path / "frames"
        frames_dir.mkdir(exist_ok=True)
        
        with self._lock:
            self._active_sessions[metadata.session_name] = {
                'path': session_path,
                'metadata': metadata,
                'frame_count': 0
            }
        
        return str(session_path)
    
    def save_frame(self, session_name: str, frame_index: int, 
                   image: np.ndarray, position: Tuple[float, float]):
        """Save individual frame as TIFF with embedded metadata."""
        with self._lock:
            if session_name not in self._active_sessions:
                raise ValueError(f"Session '{session_name}' not found")
            
            session_info = self._active_sessions[session_name]
            frames_dir = session_info['path'] / "frames"
            
            # TIFF with metadata tags
            tiff_path = frames_dir / f"frame_{frame_index:06d}.tiff"
            
            # Convert to uint16 if needed
            if image.dtype != np.uint16:
                image = np.uint16(image)
            
            # Embed metadata in TIFF tags
            metadata_dict = {
                'position_x_mm': float(position[0]),
                'position_y_mm': float(position[1]),
                'frame_index': int(frame_index),
                'timestamp': datetime.now().isoformat()
            }
            
            with tifffile.TiffWriter(str(tiff_path)) as tif:
                tif.write(image, metadata=metadata_dict)
            
            session_info['frame_count'] += 1
            session_info['metadata'].frames_acquired += 1
            
            # Update metadata file
            meta_file = session_info['path'] / "metadata.json"
            with open(meta_file, 'w') as f:
                json.dump(session_info['metadata'].to_dict(), f, indent=2)
    
    def complete_session(self, session_name: str):
        """Mark session as complete and generate cube."""
        with self._lock:
            if session_name not in self._active_sessions:
                return
            
            session_info = self._active_sessions.pop(session_name)
            self._generate_data_cube(session_info)
    
    def _generate_data_cube(self, session_info: Dict):
        """Generate compressed data cube from frame stack."""
        metadata = session_info['metadata']
        frames_dir = session_info['path'] / "frames"
        
        # Load all frames
        frames = []
        frame_files = sorted(frames_dir.glob("frame_*.tiff"))
        
        for frame_file in frame_files:
            with tifffile.TiffFile(str(frame_file)) as tif:
                frames.append(tif.asarray())
        
        if not frames:
            return
        
        # Stack into cube: (num_y, num_x, bands) or similar
        frames = np.array(frames)
        
        # Save compressed cube
        cube_path = session_info['path'] / "data_cube.npz"
        np.savez_compressed(
            str(cube_path),
            cube=frames,
            metadata=metadata.to_dict()
        )
    
    def load_dataset(self, session_name: str) -> Tuple[np.ndarray, TIFFMetadata]:
        """Load complete dataset from disk."""
        session_path = self.base_path / session_name
        
        if not session_path.exists():
            raise FileNotFoundError(f"Dataset '{session_name}' not found")
        
        # Load metadata
        meta_file = session_path / "metadata.json"
        with open(meta_file, 'r') as f:
            meta_dict = json.load(f)
        metadata = TIFFMetadata.from_dict(meta_dict)
        
        # Load data cube
        cube_path = session_path / "data_cube.npz"
        if cube_path.exists():
            data = np.load(cube_path)
            return data['cube'], metadata
        
        # Fallback: reconstruct from frames
        frames_dir = session_path / "frames"
        frames = []
        for frame_file in sorted(frames_dir.glob("frame_*.tiff")):
            with tifffile.TiffFile(str(frame_file)) as tif:
                frames.append(tif.asarray())
        
        if frames:
            return np.array(frames), metadata
        
        raise ValueError(f"No data found in dataset '{session_name}'")
    
    def list_datasets(self) -> List[Dict]:
        """List all available datasets."""
        datasets = []
        for session_dir in self.base_path.iterdir():
            if session_dir.is_dir():
                meta_file = session_dir / "metadata.json"
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        meta = json.load(f)
                    datasets.append({
                        'name': session_dir.name,
                        'timestamp': meta.get('timestamp'),
                        'frames': meta.get('frames_acquired'),
                        'total_frames': meta.get('total_frames')
                    })
        return sorted(datasets, key=lambda x: x['timestamp'], reverse=True)
    
    def get_dataset_info(self, session_name: str) -> Dict:
        """Get detailed info about a dataset."""
        session_path = self.base_path / session_name
        meta_file = session_path / "metadata.json"
        
        if not meta_file.exists():
            raise FileNotFoundError(f"Dataset '{session_name}' not found")
        
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
        
        # Get file sizes
        frames_dir = session_path / "frames"
        frame_count = len(list(frames_dir.glob("frame_*.tiff")))
        
        cube_path = session_path / "data_cube.npz"
        cube_size_mb = cube_path.stat().st_size / 1024 / 1024 if cube_path.exists() else 0
        
        return {
            **metadata,
            'frame_files': frame_count,
            'cube_size_mb': cube_size_mb,
            'dataset_path': str(session_path)
        }


# Global instance
dataset_manager = DatasetManager()
