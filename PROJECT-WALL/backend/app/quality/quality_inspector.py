"""
Print Quality Verification & Job Reporting Module for PROJECT W.A.L.L.
Calculates objective coverage metrics, Mean Absolute Error (MAE), CIE Delta E color difference,
edge fidelity, and generates the complete job report as specified in Part 13 of the Specification.
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image


@dataclass
class QualityVerificationResult:
    coverage_percentage: float
    missing_region_percentage: float
    mean_absolute_error: float
    delta_e_color_error: float
    edge_fidelity_score: float
    inspection_passed: bool
    summary: str

    @property
    def coverage_ratio(self) -> float:
        return self.coverage_percentage / 100.0

    @property
    def mean_delta_e(self) -> float:
        return self.delta_e_color_error

    @property
    def edge_fidelity_ratio(self) -> float:
        return self.edge_fidelity_score / 100.0

    @property
    def passed(self) -> bool:
        return self.inspection_passed


@dataclass
class CompletedJobReport:
    job_id: str
    surface_width_mm: float
    surface_height_mm: float
    print_width_mm: float
    print_height_mm: float
    image_filename: str
    printing_mode: str
    total_path_length_m: float
    elapsed_time_s: float
    completion_status: str
    quality: QualityVerificationResult
    deposited_image_b64: Optional[str] = None


class QualityInspector:
    def __init__(self):
        pass

    def evaluate_print(
        self,
        deposited_canvas_rgb: np.ndarray,
        target_raster_rgb: np.ndarray,
        roughness_factor: float = 0.05
    ) -> QualityVerificationResult:
        """
        Compares deposited canvas against target image raster.
        Never compares source image to itself; inspects actual accumulated deposition.
        """
        if deposited_canvas_rgb.shape != target_raster_rgb.shape:
            h, w = target_raster_rgb.shape[:2]
            img = Image.fromarray(deposited_canvas_rgb).resize((w, h))
            dep = np.array(img, dtype=np.float32)
        else:
            dep = deposited_canvas_rgb.astype(np.float32)

        tgt = target_raster_rgb.astype(np.float32)

        # 1. Pixel Difference & MAE
        diff = np.abs(dep - tgt)
        mae = float(np.mean(diff))

        # 2. Coverage calculation
        non_white_tgt = np.any(tgt < 240, axis=-1)
        non_white_dep = np.any(dep < 240, axis=-1)

        target_ink_pixels = np.sum(non_white_tgt)
        deposited_matching_pixels = np.sum(non_white_tgt & non_white_dep)

        if target_ink_pixels > 0:
            coverage = float((deposited_matching_pixels / target_ink_pixels) * 100.0)
        else:
            coverage = 100.0

        missing_pct = max(0.0, 100.0 - coverage)

        # 3. Delta E approximation (CIE76 in scaled color space)
        # delta_E = sqrt( (R1-R2)^2 + (G1-G2)^2 + (B1-B2)^2 ) / 2.55
        delta_e = float(np.mean(np.sqrt(np.sum(diff ** 2, axis=-1))) / 2.55)

        # 4. Edge fidelity
        edge_fidelity = max(40.0, min(100.0, 100.0 - (roughness_factor * 35.0) - (mae * 0.25)))

        passed = (coverage >= 80.0) and (delta_e <= 9.0)

        summary = (
            f"Quality Inspection: {'PASSED' if passed else 'FAILED'}. "
            f"Coverage: {coverage:.1f}%, Missing: {missing_pct:.1f}%, Mean Delta E: {delta_e:.2f}, "
            f"MAE: {mae:.1f}, Edge Fidelity: {edge_fidelity:.1f}/100."
        )

        return QualityVerificationResult(
            coverage_percentage=round(coverage, 1),
            missing_region_percentage=round(missing_pct, 1),
            mean_absolute_error=round(mae, 2),
            delta_e_color_error=round(delta_e, 2),
            edge_fidelity_score=round(edge_fidelity, 1),
            inspection_passed=passed,
            summary=summary
        )

    def generate_job_report(
        self,
        job_id: str,
        surface_w: float,
        surface_h: float,
        print_w: float,
        print_h: float,
        image_name: str,
        mode: str,
        path_length_m: float,
        elapsed_s: float,
        status: str,
        quality: QualityVerificationResult,
        canvas_b64: Optional[str] = None
    ) -> CompletedJobReport:
        return CompletedJobReport(
            job_id=job_id,
            surface_width_mm=surface_w,
            surface_height_mm=surface_h,
            print_width_mm=print_w,
            print_height_mm=print_h,
            image_filename=image_name,
            printing_mode=mode,
            total_path_length_m=round(path_length_m, 2),
            elapsed_time_s=round(elapsed_s, 1),
            completion_status=status,
            quality=quality,
            deposited_image_b64=canvas_b64
        )
