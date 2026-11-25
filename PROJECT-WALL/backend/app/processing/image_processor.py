"""
Intelligent Artwork Processing & CAM Motion Classifier for PROJECT W.A.L.L.
Analyzes input artwork, quantizes color palettes, classifies actuator selection,
generates 4-cable CDPR toolpaths with tension verification, and computes paint/ink BOM recipes.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageFilter
from scipy.cluster.vq import kmeans2

from ..kinematics.cdpr_kinematics import CDPRKinematics
from ..dynamics.tension_solver import CableTensionSolver
from ..motion.trajectory_planner import MotionWaypoint, TrajectoryLimits
from ..models.surface_model import SurfaceModel, SurfaceMaterialCatalog


@dataclass
class ColorSegment:
    color_id: int
    hex_code: str
    rgb: Tuple[int, int, int]
    name: str
    coverage_percent: float
    pixel_count: int
    estimated_volume_ml: float


@dataclass
class MotionPlanSummary:
    mode: str  # "RASTER_SERPENTINE", "VECTOR_CONTOUR", "HYBRID"
    total_waypoints: int
    total_distance_m: float
    printing_distance_m: float
    rapid_traverse_distance_m: float
    estimated_time_s: float
    row_pitch_mm: float
    feedrate_mm_s: float
    kinematic_feasible: bool
    tension_range_n: Tuple[float, float]
    dexterity_min: float


@dataclass
class PaintRecipe:
    recommended_actuator: str  # "inkjet" or "paint_marker"
    actuator_display_name: str
    rationale: str
    ink_chemistry: str
    viscosity_cp: float
    total_volume_ml: float
    drying_time_per_pass_s: float
    recommended_passes: int
    color_breakdown: List[ColorSegment]
    substrate_compatibility: Dict[str, Any]


@dataclass
class ProcessedArtworkReport:
    job_id: str
    filename: str
    original_size_px: Tuple[int, int]
    target_size_mm: Tuple[float, float]
    aspect_ratio: float
    resolution_dpi: float
    surface_bounds_mm: Dict[str, float]
    paint_recipe: PaintRecipe
    motion_plan: MotionPlanSummary
    waypoints_preview: List[Dict[str, Any]]
    thumbnail_base64: Optional[str] = None
    segmented_preview_base64: Optional[str] = None


class ArtworkProcessor:
    def __init__(self, kinematics: CDPRKinematics, surface: SurfaceModel):
        self.kinematics = kinematics
        self.surface = surface
        self.limits = TrajectoryLimits()
        self.tension_solver = CableTensionSolver(kinematics)

    def analyze_image(
        self,
        img: Image.Image,
        filename: str = "artwork.png",
        target_width_mm: float = 300.0,
        target_height_mm: float = 250.0,
        row_pitch_mm: float = 3.0,
        force_actuator: Optional[str] = None
    ) -> ProcessedArtworkReport:
        """
        Executes full computer vision analysis, palette extraction, motion planning,
        actuator classification, and ink volume estimation.
        """
        orig_w, orig_h = img.size
        aspect_ratio = round(float(orig_w) / float(max(1, orig_h)), 3)

        # 1. Target physical scaling and DPI calculation
        bounds = self.surface.printable_bounds
        # Clamp to physical printable envelope
        max_w = bounds["width_mm"] - 20.0
        max_h = bounds["height_mm"] - 20.0
        target_w = min(max(50.0, target_width_mm), max_w)
        target_h = min(max(50.0, target_height_mm), max_h)

        # Centered print coordinates on surface
        origin_x = bounds["min_x_mm"] + (bounds["width_mm"] - target_w) / 2.0
        origin_y = bounds["min_y_mm"] + (bounds["height_mm"] - target_h) / 2.0

        # Equivalent DPI
        dpi_x = (orig_w / (target_w / 25.4))
        dpi_y = (orig_h / (target_h / 25.4))
        avg_dpi = round(float((dpi_x + dpi_y) / 2.0), 1)

        # Generate Base64 thumbnail for UI
        import base64
        import io
        thumb = img.copy()
        thumb.thumbnail((320, 320), Image.Resampling.LANCZOS)
        thumb_buf = io.BytesIO()
        thumb.save(thumb_buf, format="JPEG", quality=85)
        thumbnail_base64 = "data:image/jpeg;base64," + base64.b64encode(thumb_buf.getvalue()).decode("ascii")

        # 2. Downsample for fast robust clustering & edge analysis
        analysis_w = 200
        analysis_h = max(10, int(analysis_w * (orig_h / max(1, orig_w))))
        img_small = img.resize((analysis_w, analysis_h), Image.Resampling.BILINEAR)
        pixels = np.array(img_small, dtype=np.float32).reshape(-1, 3)

        # 3. Color Clustering & Quantization (Robust against any picture)
        n_colors = 4
        quant_pixels = (pixels // 8) * 8
        unique_colors, color_freqs = np.unique(quant_pixels, axis=0, return_counts=True)
        if len(unique_colors) <= n_colors:
            centroids = np.zeros((n_colors, 3), dtype=np.float32)
            for i in range(n_colors):
                idx = min(i, len(unique_colors) - 1)
                centroids[i] = unique_colors[idx]
            dists = np.linalg.norm(pixels[:, None, :] - centroids[None, :, :], axis=2)
            labels = np.argmin(dists, axis=1)
        else:
            try:
                centroids, labels = kmeans2(pixels, n_colors, minit='points', iter=10)
            except Exception:
                top_indices = np.argsort(color_freqs)[::-1][:n_colors]
                centroids = unique_colors[top_indices].astype(np.float32)
                dists = np.linalg.norm(pixels[:, None, :] - centroids[None, :, :], axis=2)
                labels = np.argmin(dists, axis=1)

        color_counts = np.bincount(labels, minlength=n_colors)
        total_pixels = len(labels)

        # Sort colors by dominance
        sorted_indices = np.argsort(color_counts)[::-1]
        color_segments: List[ColorSegment] = []

        # Color naming database
        def name_color(r: int, g: int, b: int) -> str:
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if brightness < 45:
                return "Carbon Obsidian Black"
            elif brightness > 220:
                return "Titanium Primer White"
            elif r > 180 and g < 100 and b < 100:
                return "Safety Oxide Red"
            elif r > 180 and g > 120 and b < 50:
                return "Signal Safety Amber"
            elif r < 100 and g > 140 and b < 100:
                return "Industrial Emerald"
            elif abs(r - g) < 25 and abs(g - b) < 25:
                return f"Slate Gray (Tone {int(brightness/2.55)}%)"
            return f"Custom Blend RGB({r},{g},{b})"

        # Total ink volume estimation baseline
        roughness = self.surface.material.roughness
        absorption = self.surface.material.absorption_rate

        for idx, c_idx in enumerate(sorted_indices):
            c_rgb = centroids[c_idx].astype(int)
            r, g, b = int(np.clip(c_rgb[0], 0, 255)), int(np.clip(c_rgb[1], 0, 255)), int(np.clip(c_rgb[2], 0, 255))
            hex_code = f"#{r:02x}{g:02x}{b:02x}"
            ratio = float(color_counts[c_idx] / max(1, total_pixels))

            # Volumetric calculation in mL
            area_m2 = (target_w / 1000.0) * (target_h / 1000.0)
            vol_ml = round(area_m2 * ratio * 2.5 * (1.0 + absorption * 0.5) * 10.0, 3)

            color_segments.append(ColorSegment(
                color_id=idx + 1,
                hex_code=hex_code,
                rgb=(r, g, b),
                name=name_color(r, g, b),
                coverage_percent=round(ratio * 100.0, 1),
                pixel_count=int(color_counts[c_idx]),
                estimated_volume_ml=vol_ml
            ))

        total_volume_ml = round(sum(cs.estimated_volume_ml for cs in color_segments), 2)

        # 4. Actuator Classification Engine
        # Analyze edge density, unique color bins, and color variance
        gray = img_small.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_data = np.array(edges)
        edge_density = float(np.mean(edge_data > 40))

        # Check unique discrete color bins (quantized to 16 levels/channel)
        unique_bins = len(np.unique((pixels // 16).astype(int), axis=0))
        std_colors = np.std(pixels, axis=0)
        gradient_score = float(np.mean(std_colors))

        if force_actuator:
            rec_module = force_actuator
            rec_display = "Module A: Piezo Drop-on-Demand Inkjet" if rec_module == "inkjet" else "Module B: Spring-Compliant Paint Marker"
            rationale = f"Manually configured by operator to {rec_display}."
        elif unique_bins <= 40 and edge_density > 0.05:
            rec_module = "paint"
            rec_display = "Module B: Spring-Compliant Paint Marker (1.2N Spring, 6mm Chisel Tip)"
            rationale = f"Discrete vector artwork detected ({unique_bins} distinct color clusters, edge density {edge_density*100:.1f}%). Module B provides continuous surface contact with a 1.2N compliance normal spring for high-density stroke saturation."
        else:
            rec_module = "inkjet"
            rec_display = "Module A: 48-Nozzle Drop-on-Demand Piezo Inkjet (14 pL micro-droplets)"
            rationale = f"Continuous photographic tones, soft gradients, or complex spatial variance detected ({unique_bins} color bins, tonal variance {gradient_score:.1f}). Module A fires 14 pL micro-droplets at 2.0 mm non-contact standoff to achieve photo-realistic gradient blending without surface scratching."

        # Paint formulation chemistry
        if rec_module == "inkjet":
            chemistry = "Low-viscosity UV-curable / Solvent Ink (Nanoparticle Pigment, Surface Tension: 28-32 mN/m)"
            viscosity = 10.2  # cP
            drying_time_s = 4.0
            passes = 1
        else:
            chemistry = "High-opacity Water-based Acrylic Emulsion (6mm Chisel Felt Delivery, Fast Dry)"
            viscosity = 22.5  # cP
            drying_time_s = 12.0
            passes = 2

        # 5. Motion Toolpath Generation & 4-Cable Kinematics Verification
        waypoints: List[Dict[str, Any]] = []
        rows = max(2, int(target_h / row_pitch_mm))
        total_distance = 0.0
        printing_dist = 0.0
        rapid_dist = 0.0

        current_x = origin_x
        current_y = origin_y

        min_tension = 999.0
        max_tension = -999.0
        min_dexterity = 1.0
        kinematic_feasible = True

        for r in range(rows):
            y = origin_y + (r * row_pitch_mm)
            x_start = origin_x
            x_end = origin_x + target_w

            if r % 2 == 1:
                x_start, x_end = x_end, x_start

            # Rapid traverse to row start
            rapid_dist += math.hypot(x_start - current_x, y - current_y)
            waypoints.append({
                "pass_idx": r,
                "x_mm": round(x_start, 2),
                "y_mm": round(y, 2),
                "is_printing": False,
                "speed_mm_s": 120.0,
                "dwell_s": 0.05
            })

            # Check kinematics at row start
            t_sol_start = self.tension_solver.solve_static_tensions(x_start, y)
            dex = self.kinematics.kinematic_conditioning_index(x_start, y)
            min_dexterity = min(min_dexterity, dex)
            if t_sol_start.is_feasible:
                min_tension = min(min_tension, min(t_sol_start.tensions_n))
                max_tension = max(max_tension, max(t_sol_start.tensions_n))
            else:
                kinematic_feasible = False

            # Printing scan across row
            print_stroke = abs(x_end - x_start)
            printing_dist += print_stroke
            waypoints.append({
                "pass_idx": r,
                "x_mm": round(x_end, 2),
                "y_mm": round(y, 2),
                "is_printing": True,
                "speed_mm_s": 65.0 if rec_module == "inkjet" else 45.0,
                "dwell_s": 0.0
            })

            # Check kinematics at row end
            t_sol_end = self.tension_solver.solve_static_tensions(x_end, y)
            dex = self.kinematics.kinematic_conditioning_index(x_end, y)
            min_dexterity = min(min_dexterity, dex)
            if t_sol_end.is_feasible:
                min_tension = min(min_tension, min(t_sol_end.tensions_n))
                max_tension = max(max_tension, max(t_sol_end.tensions_n))
            else:
                kinematic_feasible = False

            current_x = x_end
            current_y = y

        total_distance = rapid_dist + printing_dist
        print_speed = 65.0 if rec_module == "inkjet" else 45.0
        rapid_speed = 120.0
        est_time_s = (printing_dist / print_speed) + (rapid_dist / rapid_speed) + (rows * 0.1)

        motion_summary = MotionPlanSummary(
            mode="SERPENTINE_RASTER_SCAN",
            total_waypoints=len(waypoints),
            total_distance_m=round(total_distance / 1000.0, 2),
            printing_distance_m=round(printing_dist / 1000.0, 2),
            rapid_traverse_distance_m=round(rapid_dist / 1000.0, 2),
            estimated_time_s=round(est_time_s, 1),
            row_pitch_mm=row_pitch_mm,
            feedrate_mm_s=print_speed,
            kinematic_feasible=kinematic_feasible,
            tension_range_n=(round(float(min_tension), 1), round(float(max_tension), 1)) if min_tension < 900 else (2.0, 50.0),
            dexterity_min=round(float(min_dexterity), 3)
        )

        paint_recipe = PaintRecipe(
            recommended_actuator=rec_module,
            actuator_display_name=rec_display,
            rationale=rationale,
            ink_chemistry=chemistry,
            viscosity_cp=viscosity,
            total_volume_ml=total_volume_ml,
            drying_time_per_pass_s=drying_time_s,
            recommended_passes=passes,
            color_breakdown=color_segments,
            substrate_compatibility={
                "material_name": self.surface.material.name,
                "roughness": self.surface.material.roughness,
                "absorption_rate": self.surface.material.absorption_rate,
                "spread_factor": self.surface.material.ink_spread_factor,
                "status": "OPTIMAL_ADHESION" if roughness < 0.25 else "HIGH_ABSORPTION_WARNING"
            }
        )

        return ProcessedArtworkReport(
            job_id=f"JOB_{int(time.time())}",
            filename=filename,
            original_size_px=(orig_w, orig_h),
            target_size_mm=(target_w, target_h),
            aspect_ratio=aspect_ratio,
            resolution_dpi=avg_dpi,
            surface_bounds_mm={
                "origin_x": round(origin_x, 1),
                "origin_y": round(origin_y, 1),
                "width": round(target_w, 1),
                "height": round(target_h, 1)
            },
            paint_recipe=paint_recipe,
            motion_plan=motion_summary,
            waypoints_preview=waypoints[:20],
            thumbnail_base64=thumbnail_base64
        )
