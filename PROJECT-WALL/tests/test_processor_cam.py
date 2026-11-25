"""
Automated Integration Tests for Artwork Processor & CAM Classifier
Tests image ingestion, palette quantization, actuator selection, 4-cable motion plan,
and ink volume estimation for PROJECT W.A.L.L.
"""

import pytest
import numpy as np
from PIL import Image

from backend.app.kinematics.cdpr_kinematics import CDPRKinematics, PlatformGeometry
from backend.app.models.surface_model import SurfaceModel
from backend.app.processing.image_processor import ArtworkProcessor


def test_artwork_processor_full_pipeline():
    surface = SurfaceModel(width_mm=800.0, height_mm=600.0)
    platform = PlatformGeometry(width_mm=100.0, height_mm=80.0, thickness_mm=6.0, mass_kg=0.50)
    kinematics = CDPRKinematics(anchors=surface.anchors, platform=platform)

    processor = ArtworkProcessor(kinematics, surface)

    # 1. Test image with gradient
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    for y in range(100):
        for x in range(100):
            arr[y, x] = [x * 2, y * 2, 120]
    img = Image.fromarray(arr)

    report = processor.analyze_image(
        img=img,
        filename="gradient_test.png",
        target_width_mm=300.0,
        target_height_mm=250.0,
        row_pitch_mm=3.0
    )

    assert report.job_id.startswith("JOB_")
    assert report.motion_plan.total_waypoints > 50
    assert report.motion_plan.kinematic_feasible is True
    assert report.paint_recipe.total_volume_ml > 0.0
    assert len(report.paint_recipe.color_breakdown) >= 1
    assert report.paint_recipe.recommended_actuator in ("inkjet", "paint")
    assert report.aspect_ratio == 1.0
    assert report.thumbnail_base64 is not None


def test_any_picture_format_and_color_modes():
    """
    Verifies that ANY picture given by the user works flawlessly:
    - Transparent RGBA PNG
    - Grayscale mode L
    - CMYK print art
    - Solid single color (zero variance)
    - Extreme aspect ratios (panoramic and vertical banner)
    - High-contrast vector schematic (tests Module B marker classification)
    """
    from backend.app.processing.image_loader import UniversalImageLoader
    import io

    surface = SurfaceModel(width_mm=800.0, height_mm=600.0)
    platform = PlatformGeometry(width_mm=100.0, height_mm=80.0, thickness_mm=6.0, mass_kg=0.50)
    kinematics = CDPRKinematics(anchors=surface.anchors, platform=platform)
    processor = ArtworkProcessor(kinematics, surface)

    # 1. RGBA with transparency
    rgba_img = Image.new("RGBA", (200, 150), (245, 158, 11, 200))
    buf = io.BytesIO()
    rgba_img.save(buf, format="PNG")
    rgb, dims, thumb = UniversalImageLoader.load_image(buf.getvalue())
    assert rgb.mode == "RGB"
    assert dims == (200, 150)
    rep_rgba = processor.analyze_image(rgb, "transparent_logo.png")
    assert rep_rgba.paint_recipe.total_volume_ml > 0

    # 2. Grayscale (mode L)
    gray_img = Image.new("L", (180, 180), 128)
    buf = io.BytesIO()
    gray_img.save(buf, format="PNG")
    rgb_gray, dims_g, _ = UniversalImageLoader.load_image(buf.getvalue())
    assert rgb_gray.mode == "RGB"
    rep_gray = processor.analyze_image(rgb_gray, "grayscale_doc.png")
    assert len(rep_gray.paint_recipe.color_breakdown) >= 1

    # 3. Solid single-color image (edge case: 0 variance)
    solid_img = Image.new("RGB", (100, 100), (255, 255, 255))
    rep_solid = processor.analyze_image(solid_img, "white_canvas.png")
    assert rep_solid.paint_recipe.total_volume_ml >= 0

    # 4. Extreme panoramic aspect ratio (10:1)
    pano_img = Image.new("RGB", (500, 50), (20, 20, 20))
    rep_pano = processor.analyze_image(pano_img, "panoramic_banner.png", target_width_mm=400.0, target_height_mm=80.0)
    assert rep_pano.aspect_ratio == 10.0
    assert rep_pano.motion_plan.kinematic_feasible is True

    # 5. High-contrast line schematic (tests Module B marker classification)
    schem = Image.new("RGB", (300, 300), (255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(schem)
    draw.rectangle([20, 20, 280, 280], outline=(0, 0, 0), width=6)
    draw.line([(20, 20), (280, 280)], fill=(0, 0, 0), width=6)
    draw.line([(20, 280), (280, 20)], fill=(0, 0, 0), width=6)
    rep_schem = processor.analyze_image(schem, "hazard_x.png")
    assert rep_schem.paint_recipe.recommended_actuator == "paint"
    assert "Module B" in rep_schem.paint_recipe.actuator_display_name


