# =============================================================================
# HSI-Core — Advanced Scan Patterns
# =============================================================================
# Supports multiple scanning modes:
# - Raster (standard row-by-row)
# - Serpentine (bidirectional, efficient)
# - Spiral
# - Custom ROI patterns
# =============================================================================

from __future__ import annotations

from enum import Enum
from typing import List, Tuple

import numpy as np


class ScanPattern(str, Enum):
    RASTER = "raster"
    SERPENTINE = "serpentine"
    SPIRAL = "spiral"


class ScanPathGenerator:
    """Generates optimized 2D scanning paths."""
    
    @staticmethod
    def raster(x_start: float, x_end: float, x_step: float,
               y_start: float, y_end: float, y_step: float) -> List[Tuple[float, float]]:
        """
        Standard raster scan: row by row, always going left-to-right.
        Good for stability but potentially slow due to stage reversals.
        """
        path = []
        y = y_start
        while y <= y_end + y_step / 2:
            x = x_start
            while x <= x_end + x_step / 2:
                path.append((round(x, 6), round(y, 6)))
                x += x_step
            y += y_step
        return path
    
    @staticmethod
    def serpentine(x_start: float, x_end: float, x_step: float,
                   y_start: float, y_end: float, y_step: float) -> List[Tuple[float, float]]:
        """
        Serpentine (boustrophedon) scan: alternates direction per row.
        More efficient—avoids stage reversals, reducing settling time.
        """
        path = []
        y = y_start
        direction = 1  # 1 = left-to-right, -1 = right-to-left
        
        while y <= y_end + y_step / 2:
            if direction == 1:
                x = x_start
                while x <= x_end + x_step / 2:
                    path.append((round(x, 6), round(y, 6)))
                    x += x_step
            else:
                x = x_end
                while x >= x_start - x_step / 2:
                    path.append((round(x, 6), round(y, 6)))
                    x -= x_step
            
            y += y_step
            direction *= -1  # Flip direction
        
        return path
    
    @staticmethod
    def spiral(x_start: float, x_end: float, x_step: float,
               y_start: float, y_end: float, y_step: float) -> List[Tuple[float, float]]:
        """
        Spiral scan: good for detecting gradients from center outward.
        """
        # Calculate center and dimensions
        x_center = (x_start + x_end) / 2
        y_center = (y_start + y_end) / 2
        x_range = (x_end - x_start) / 2
        y_range = (y_end - y_start) / 2
        
        path = []
        angle = 0
        radius = 0
        
        # Generate spiral points
        while radius <= max(x_range, y_range):
            x = x_center + radius * np.cos(angle)
            y = y_center + radius * np.sin(angle)
            
            # Clamp to bounds
            x = np.clip(x, x_start, x_end)
            y = np.clip(y, y_start, y_end)
            
            path.append((round(x, 6), round(y, 6)))
            
            angle += 0.1  # Increment angle
            if angle > 2 * np.pi:
                angle = 0
                radius += min(x_step, y_step)
        
        return path
    
    @staticmethod
    def roi_box(x1: float, y1: float, x2: float, y2: float, 
                x_step: float, y_step: float) -> List[Tuple[float, float]]:
        """Scan rectangular region of interest."""
        x_start, x_end = min(x1, x2), max(x1, x2)
        y_start, y_end = min(y1, y2), max(y1, y2)
        
        return ScanPathGenerator.serpentine(x_start, x_end, x_step,
                                           y_start, y_end, y_step)
    
    @staticmethod
    def roi_circle(center_x: float, center_y: float, radius: float,
                   step: float) -> List[Tuple[float, float]]:
        """Scan circular region of interest."""
        path = []
        
        for angle in np.linspace(0, 2 * np.pi, int(2 * np.pi * radius / step)):
            for r in np.arange(0, radius, step):
                x = center_x + r * np.cos(angle)
                y = center_y + r * np.sin(angle)
                path.append((round(x, 6), round(y, 6)))
        
        return path
    
    @staticmethod
    def roi_polygon(vertices: List[Tuple[float, float]], 
                    step: float) -> List[Tuple[float, float]]:
        """Scan polygonal region of interest (not yet fully implemented)."""
        # Placeholder for polygon rasterization
        # Would use Bresenham or similar algorithm
        return []
    
    @staticmethod
    def optimized_line(x1: float, y1: float, x2: float, y2: float,
                       step: float) -> List[Tuple[float, float]]:
        """Scan along a line with given step size (for spectral line scans)."""
        path = []
        distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        num_steps = int(distance / step) + 1
        
        for i in range(num_steps):
            t = i / max(1, num_steps - 1)
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            path.append((round(x, 6), round(y, 6)))
        
        return path


def estimate_scan_time(path: List[Tuple[float, float]], 
                       stage_velocity_mm_s: float = 10.0,
                       settling_time_s: float = 0.1,
                       capture_time_s: float = 0.1) -> float:
    """Estimate total scan duration."""
    
    travel_distance = 0
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        travel_distance += distance
    
    travel_time = travel_distance / stage_velocity_mm_s
    frame_time = len(path) * (settling_time_s + capture_time_s)
    
    return travel_time + frame_time
