# =============================================================================
# HSI-Core — Advanced Analysis & Visualization
# =============================================================================
# Provides ROI analysis, spectral plotting, data cube visualization,
# intensity maps, and statistical analysis.
# =============================================================================

from __future__ import annotations

from typing import Dict, Tuple, Optional

import numpy as np
from scipy import ndimage
from scipy.ndimage import label


class SpectralAnalyzer:
    """Performs spectral analysis on hyperspectral data."""
    
    @staticmethod
    def extract_spectrum(data_cube: np.ndarray, x: int, y: int) -> np.ndarray:
        """Extract spectral signature at pixel (x, y)."""
        if len(data_cube.shape) == 3:
            return data_cube[y, x, :] if data_cube.shape[2] > 1 else data_cube[y, x]
        return data_cube[y, x]
    
    @staticmethod
    def mean_spectrum(data_cube: np.ndarray) -> np.ndarray:
        """Compute mean spectrum across all pixels."""
        return np.mean(data_cube, axis=(0, 1))
    
    @staticmethod
    def spectral_distance(spec1: np.ndarray, spec2: np.ndarray) -> float:
        """Euclidean distance between two spectra (spectral angle mapper)."""
        return np.linalg.norm(spec1 - spec2)
    
    @staticmethod
    def spectral_angle_mapper(data_cube: np.ndarray, 
                             reference_spectrum: np.ndarray) -> np.ndarray:
        """Compute spectral angle between each pixel and reference."""
        if len(data_cube.shape) != 3:
            return np.zeros((data_cube.shape[0], data_cube.shape[1]))
        
        h, w, b = data_cube.shape
        result = np.zeros((h, w))
        
        for i in range(h):
            for j in range(w):
                pixel_spectrum = data_cube[i, j, :]
                norm1 = np.linalg.norm(pixel_spectrum)
                norm2 = np.linalg.norm(reference_spectrum)
                
                if norm1 > 0 and norm2 > 0:
                    cos_angle = np.dot(pixel_spectrum, reference_spectrum) / (norm1 * norm2)
                    cos_angle = np.clip(cos_angle, -1, 1)
                    result[i, j] = np.arccos(cos_angle)
        
        return result
    
    @staticmethod
    def ndvi(nir_band: np.ndarray, red_band: np.ndarray) -> np.ndarray:
        """
        Compute Normalized Difference Vegetation Index (NDVI).
        Useful for environmental monitoring applications.
        """
        denominator = nir_band + red_band
        # Avoid division by zero
        denominator = np.where(denominator == 0, 1, denominator)
        return (nir_band - red_band) / denominator


class IntensityMapGenerator:
    """Generates 2D intensity maps from hyperspectral cubes."""
    
    @staticmethod
    def total_intensity(data_cube: np.ndarray) -> np.ndarray:
        """Sum across spectral dimension (total intensity per pixel)."""
        return np.sum(data_cube, axis=2) if len(data_cube.shape) == 3 else data_cube
    
    @staticmethod
    def mean_intensity(data_cube: np.ndarray) -> np.ndarray:
        """Mean across spectral dimension."""
        return np.mean(data_cube, axis=2) if len(data_cube.shape) == 3 else data_cube
    
    @staticmethod
    def band_intensity(data_cube: np.ndarray, band_index: int) -> np.ndarray:
        """Extract single spectral band as intensity map."""
        if len(data_cube.shape) == 3 and band_index < data_cube.shape[2]:
            return data_cube[:, :, band_index]
        return data_cube if len(data_cube.shape) == 2 else None
    
    @staticmethod
    def wavelength_range_intensity(data_cube: np.ndarray,
                                   start_band: int, end_band: int) -> np.ndarray:
        """Intensity from wavelength range (band range)."""
        if len(data_cube.shape) == 3:
            return np.sum(data_cube[:, :, start_band:end_band], axis=2)
        return data_cube
    
    @staticmethod
    def normalize_0_1(intensity_map: np.ndarray) -> np.ndarray:
        """Normalize intensity to [0, 1]."""
        vmin = intensity_map.min()
        vmax = intensity_map.max()
        if vmax > vmin:
            return (intensity_map - vmin) / (vmax - vmin)
        return intensity_map


class ROIAnalyzer:
    """Analyzes regions of interest within data cubes."""
    
    @staticmethod
    def rectangular_roi(data_cube: np.ndarray,
                       x1: int, y1: int, x2: int, y2: int) -> Dict:
        """Extract and analyze rectangular ROI."""
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)
        
        roi_data = data_cube[y_min:y_max+1, x_min:x_max+1, :]
        
        return {
            'bounds': {'x': (x_min, x_max), 'y': (y_min, y_max)},
            'mean_spectrum': np.mean(roi_data, axis=(0, 1)),
            'std_spectrum': np.std(roi_data, axis=(0, 1)),
            'max_spectrum': np.max(roi_data, axis=(0, 1)),
            'min_spectrum': np.min(roi_data, axis=(0, 1)),
            'pixel_count': roi_data.shape[0] * roi_data.shape[1]
        }
    
    @staticmethod
    def circular_roi(data_cube: np.ndarray,
                    center_x: int, center_y: int, radius: int) -> Dict:
        """Extract and analyze circular ROI."""
        h, w = data_cube.shape[:2]
        
        # Create mask
        y, x = np.ogrid[:h, :w]
        mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
        
        roi_data = data_cube[mask, :]
        
        return {
            'center': (center_x, center_y),
            'radius': radius,
            'mean_spectrum': np.mean(roi_data, axis=0),
            'std_spectrum': np.std(roi_data, axis=0),
            'pixel_count': np.sum(mask)
        }
    
    @staticmethod
    def spectral_clustering(data_cube: np.ndarray, n_clusters: int = 5) -> np.ndarray:
        """Simple K-means clustering on spectral signatures."""
        from sklearn.cluster import KMeans
        
        h, w, b = data_cube.shape
        reshaped = data_cube.reshape(-1, b)
        
        kmeans = KMeans(n_clusters=n_clusters, n_init=10)
        labels = kmeans.fit_predict(reshaped)
        
        return labels.reshape(h, w)


class StatisticalAnalyzer:
    """Statistical analysis on hyperspectral data."""
    
    @staticmethod
    def compute_statistics(data_cube: np.ndarray) -> Dict:
        """Compute comprehensive statistics."""
        return {
            'mean': np.mean(data_cube),
            'std': np.std(data_cube),
            'min': np.min(data_cube),
            'max': np.max(data_cube),
            'median': np.median(data_cube),
            'q25': np.percentile(data_cube, 25),
            'q75': np.percentile(data_cube, 75),
        }
    
    @staticmethod
    def detect_anomalies(intensity_map: np.ndarray, 
                        threshold_sigma: float = 3.0) -> np.ndarray:
        """Detect anomalies as pixels >N sigma from mean."""
        mean = np.mean(intensity_map)
        std = np.std(intensity_map)
        
        return np.abs(intensity_map - mean) > (threshold_sigma * std)
    
    @staticmethod
    def compute_correlation_map(data_cube: np.ndarray,
                               reference_spectrum: np.ndarray) -> np.ndarray:
        """Compute correlation of each pixel with reference spectrum."""
        h, w, b = data_cube.shape
        result = np.zeros((h, w))
        
        for i in range(h):
            for j in range(w):
                pixel_spectrum = data_cube[i, j, :]
                correlation = np.corrcoef(pixel_spectrum, reference_spectrum)[0, 1]
                result[i, j] = correlation if not np.isnan(correlation) else 0
        
        return result
