"""
Environmental Surface Perception & Planarity Scanner for PROJECT W.A.L.L.
Simulates a pre-print optical triangulation / TOF raster scan across the mounted wall surface
to assess flatness, identify printable boundaries, and detect surface anomalies.
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import numpy as np

from ..models.surface_model import SurfaceModel, SurfaceMaterial


@dataclass
class SurfaceScanReport:
    total_points_scanned: int
    mean_elevation_mm: float
    max_peak_deviation_mm: float
    rms_planarity_error_mm: float
    is_printable: bool
    printable_area_w_mm: float
    printable_area_h_mm: float
    detected_anomalies: List[Dict[str, Any]]
    substrate_material: str


class SurfaceScanner:
    def __init__(self, surface: SurfaceModel):
        self.surface = surface

    def execute_pre_print_scan(self, grid_rows: int = 8, grid_cols: int = 10) -> SurfaceScanReport:
        """
        Scans a grid of points across the physical surface dimensions,
        simulating laser depth profiling.
        """
        w = self.surface.width_mm
        h = self.surface.height_mm
        roughness = self.surface.material.roughness

        x_coords = np.linspace(50.0, w - 50.0, grid_cols)
        y_coords = np.linspace(50.0, h - 50.0, grid_rows)

        depth_readings = []
        anomalies = []

        for r_idx, y in enumerate(y_coords):
            for c_idx, x in enumerate(x_coords):
                # Simulated micro-deviation from nominal wall plane (Z=0)
                # Derived from substrate roughness
                noise = np.random.normal(0.0, roughness * 1.5)
                # Introduce slight wall bow / curvature
                curvature = 0.5 * np.sin(np.pi * x / w) * np.sin(np.pi * y / h)
                z_dev = curvature + noise
                depth_readings.append(z_dev)

                # Anomaly detection: protrusion > 3.0 mm
                if abs(z_dev) > 3.0:
                    anomalies.append({
                        "coord_mm": [round(float(x), 1), round(float(y), 1)],
                        "deviation_mm": round(float(z_dev), 2),
                        "type": "PROTRUSION" if z_dev > 0 else "DEPRESSION"
                    })

        depths = np.array(depth_readings)
        rms = float(np.sqrt(np.mean(depths ** 2)))
        max_dev = float(np.max(np.abs(depths)))
        mean_elev = float(np.mean(depths))

        # Acceptable planarity tolerance: RMS <= 2.5 mm
        is_ok = (rms <= 2.5) and (len(anomalies) < 3)

        bounds = self.surface.printable_bounds

        return SurfaceScanReport(
            total_points_scanned=grid_rows * grid_cols,
            mean_elevation_mm=round(mean_elev, 3),
            max_peak_deviation_mm=round(max_dev, 3),
            rms_planarity_error_mm=round(rms, 3),
            is_printable=is_ok,
            printable_area_w_mm=bounds["width_mm"],
            printable_area_h_mm=bounds["height_mm"],
            detected_anomalies=anomalies,
            substrate_material=self.surface.material.name
        )

