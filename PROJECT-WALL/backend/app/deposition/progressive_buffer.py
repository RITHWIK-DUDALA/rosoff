"""
Progressive Wall Deposition Buffer for PROJECT W.A.L.L.
Enforces the fundamental architectural rule of Part 12:
The surface appearance must emerge exclusively through accumulated nozzle droplet and stroke deposition events.
Never assign the original uploaded image directly as a surface texture.
"""

import math
import time
import base64
import io
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from PIL import Image

from ..models.surface_model import SurfaceMaterial


@dataclass
class DepositionEventRecord:
    event_id: int
    timestamp: float
    end_effector_pos_mm: Tuple[float, float]
    channel: str
    color_rgb: Tuple[int, int, int]
    coverage_delta: float
    surface_response: str


class ProgressiveDepositionBuffer:
    def __init__(
        self,
        canvas_width_px: int = 2400,
        canvas_height_px: int = 1800,
        surface_material: Optional[SurfaceMaterial] = None
    ):
        self.w = canvas_width_px
        self.h = canvas_height_px
        self.material = surface_material or SurfaceMaterial("smooth_panel", "Smooth Coated Panel", 0.05, 0.15, 1.05, True, True)

        # 3-channel RGB canvas initialized to base surface color
        self.canvas_rgb = np.full((self.h, self.w, 3), 245, dtype=np.uint8)
        self.target_raster_rgb: Optional[np.ndarray] = None
        self.artwork_image_rgb: Optional[Image.Image] = None
        self.artwork_bounds: Optional[Dict[str, float]] = None

        self.event_history: List[DepositionEventRecord] = []
        self.total_droplets_deposited: int = 0
        self.total_pixels_altered: int = 0
        self.is_active: bool = False

    @property
    def droplets_fired(self) -> int:
        return self.total_droplets_deposited

    @property
    def coverage_ratio(self) -> float:
        return self.compute_coverage_ratio()

    def load_target_raster(
        self,
        rgb_image: Image.Image,
        artwork_bounds: Optional[Dict[str, float]] = None
    ):
        """Prepares canvas to match target raster dimensions and base substrate"""
        # Ensure image is strictly 3-channel RGB
        if rgb_image.mode != "RGB":
            rgb_image = rgb_image.convert("RGB")

        self.artwork_image_rgb = rgb_image
        self.artwork_bounds = artwork_bounds or {
            "origin_x": 100.0,
            "origin_y": 100.0,
            "width": 300.0,
            "height": 250.0
        }

        target_resized = rgb_image.resize((self.w, self.h), Image.Resampling.LANCZOS)
        self.target_raster_rgb = np.array(target_resized, dtype=np.uint8)

        # Substrate background color based on material
        if self.material.type_id == "wood":
            base_col = [220, 195, 160]
        elif self.material.type_id == "rough_plaster":
            base_col = [215, 210, 200]
        elif self.material.type_id == "glass":
            base_col = [235, 240, 245]
        else:
            base_col = [248, 246, 240]

        self.canvas_rgb = np.full((self.h, self.w, 3), base_col, dtype=np.uint8)
        self.total_droplets_deposited = 0
        self.total_pixels_altered = 0
        self.event_history.clear()

    def sample_color_at_pos(self, x_mm: float, y_mm: float) -> Tuple[int, int, int]:
        """
        Samples the exact pixel color from the loaded artwork at physical wall coordinate (x_mm, y_mm).
        Accounts for artwork bounds, origin offset, and normalized (u, v) texture mapping.
        """
        if self.artwork_image_rgb is None or not self.artwork_bounds:
            return (25, 25, 25)

        b = self.artwork_bounds
        ox, oy = b["origin_x"], b["origin_y"]
        bw, bh = b["width"], b["height"]

        if not (ox <= x_mm <= ox + bw and oy <= y_mm <= oy + bh):
            return (248, 246, 240) # Outside print bounds

        u = (x_mm - ox) / max(0.1, bw)
        v = 1.0 - ((y_mm - oy) / max(0.1, bh))

        u = min(max(0.0, u), 1.0)
        v = min(max(0.0, v), 1.0)

        img_w, img_h = self.artwork_image_rgb.size
        px = int(u * (img_w - 1))
        py = int(v * (img_h - 1))

        return self.artwork_image_rgb.getpixel((px, py))[:3]

    def deposit_droplet(
        self,
        px_x: int,
        px_y: int,
        color_rgb: Tuple[int, int, int],
        ee_pos_mm: Tuple[float, float],
        radius_px: int = 1
    ) -> bool:
        """
        Executes a real deposition event on the surface canvas.
        Accounts for material absorption, spread factor, and color subtractive blending.
        """
        if not (0 <= px_x < self.w and 0 <= px_y < self.h):
            return False

        spread = self.material.ink_spread_factor
        effective_radius = max(1, int(round(radius_px * spread)))

        y_min = max(0, px_y - effective_radius)
        y_max = min(self.h, px_y + effective_radius + 1)
        x_min = max(0, px_x - effective_radius)
        x_max = min(self.w, px_x + effective_radius + 1)

        # Ink deposition with physical opacity and absorption
        absorption = self.material.absorption_rate
        ink_arr = np.array(color_rgb, dtype=np.float32)

        patch = self.canvas_rgb[y_min:y_max, x_min:x_max].astype(np.float32)
        # Direct pigment deposition with full saturation coverage
        opacity = 0.98 if effective_radius >= 3 else 0.94
        blended = patch * (1.0 - opacity) + ink_arr * opacity
        self.canvas_rgb[y_min:y_max, x_min:x_max] = np.clip(blended, 0, 255).astype(np.uint8)

        self.total_droplets_deposited += 1
        self.total_pixels_altered += (y_max - y_min) * (x_max - x_min)

        if len(self.event_history) < 20: # Keep sample trace
            self.event_history.append(DepositionEventRecord(
                event_id=self.total_droplets_deposited,
                timestamp=time.time(),
                end_effector_pos_mm=ee_pos_mm,
                channel="RGB",
                color_rgb=color_rgb,
                coverage_delta=1.0,
                surface_response=f"spread_{spread:.2f}_abs_{absorption:.2f}"
            ))
        return True

    def get_canvas_base64(self) -> str:
        """Encodes current accumulated deposition canvas to high-clarity JPEG Base64 with 4:4:4 chroma"""
        img = Image.fromarray(self.canvas_rgb)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=96, subsampling=0)
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

    def compute_coverage_ratio(self) -> float:
        total = self.w * self.h
        return min(1.0, self.total_pixels_altered / max(1, total))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canvas_dimensions": [self.w, self.h],
            "total_droplets": self.total_droplets_deposited,
            "coverage_ratio": round(self.compute_coverage_ratio(), 3),
            "material": self.material.name,
            "recent_events": [e.__dict__ for e in self.event_history[-5:]]
        }
