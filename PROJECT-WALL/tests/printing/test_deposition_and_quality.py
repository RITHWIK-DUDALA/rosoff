import pytest
import numpy as np
from PIL import Image

from app.deposition.progressive_buffer import ProgressiveDepositionBuffer
from app.models.surface_model import SurfaceMaterialCatalog
from app.quality.quality_inspector import QualityInspector


def test_progressive_deposition_droplet_accumulation():
    mat = SurfaceMaterialCatalog.get("smooth_panel")
    buf = ProgressiveDepositionBuffer(canvas_width_px=100, canvas_height_px=100, surface_material=mat)

    # Initial state
    assert buf.droplets_fired == 0
    assert buf.coverage_ratio == 0.0

    # Deposit a droplet at (50, 50)
    buf.deposit_droplet(50, 50, color_rgb=(20, 20, 20), ee_pos_mm=(400.0, 300.0), radius_px=2)
    assert buf.droplets_fired == 1
    assert buf.coverage_ratio > 0.0

    # Deposited pixel should be dark
    pixel = buf.canvas_rgb[50, 50]
    assert pixel[0] < 200 and pixel[1] < 200 and pixel[2] < 200


def test_quality_inspection_metrics():
    inspector = QualityInspector()

    # Create dummy reference and rendered canvas
    ref = np.ones((50, 50, 3), dtype=np.uint8) * 255
    ref[10:40, 10:40] = [0, 0, 0] # black square

    rendered = np.ones((50, 50, 3), dtype=np.uint8) * 255
    rendered[10:40, 10:40] = [10, 10, 10] # near black square

    res = inspector.evaluate_print(rendered, ref, roughness_factor=0.05)
    assert res.coverage_ratio > 0.0
    assert res.mean_absolute_error < 15.0
    assert res.mean_delta_e < 10.0

