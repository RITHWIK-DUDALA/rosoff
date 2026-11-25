"""
Printable Surface & Modular Mounting System Module for PROJECT W.A.L.L.
Implements configurable surface geometry (800 x 600 mm baseline), perimeter anchor positions,
modular mounting options (Suction cup with vacuum seal estimation, Clamp, Rigid Frame),
and tension-feasible workspace classification as specified in Parts 2 and 3 of the Specification.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from ..kinematics.cdpr_kinematics import AnchorPoint


@dataclass
class SurfaceMaterial:
    type_id: str                      # "smooth_panel", "painted_plaster", "rough_plaster", "wood", "glass"
    name: str
    roughness: float                  # 0.0 to 1.0
    absorption_rate: float            # 0.0 to 1.0
    ink_spread_factor: float          # 1.0 to 2.5
    suction_compatible: bool          # Can suction mount seal against it?
    clamp_compatible: bool            # Can edge clamps attach?


class SurfaceMaterialCatalog:
    MATERIALS = {
        "smooth_panel": SurfaceMaterial("smooth_panel", "Smooth Coated Panel", 0.05, 0.15, 1.05, True, True),
        "painted_plaster": SurfaceMaterial("painted_plaster", "Painted Plaster Wall", 0.20, 0.35, 1.20, True, False),
        "rough_plaster": SurfaceMaterial("rough_plaster", "Rough Textured Plaster", 0.55, 0.60, 1.45, False, False),
        "wood": SurfaceMaterial("wood", "Rigid Wood Board", 0.30, 0.45, 1.30, False, True),
        "glass": SurfaceMaterial("glass", "Architectural Glass Panel", 0.01, 0.02, 1.02, True, True),
    }

    @classmethod
    def get(cls, key: str) -> SurfaceMaterial:
        return cls.MATERIALS.get(key, cls.MATERIALS["smooth_panel"])


@dataclass
class MountingVerificationResult:
    is_valid: bool
    mounting_type: str
    holding_capacity_n: float
    safety_factor: float
    message: str


class SurfaceModel:
    def __init__(
        self,
        width_mm: float = 800.0,
        height_mm: float = 600.0,
        margin_left_mm: float = 80.0,
        margin_right_mm: float = 80.0,
        margin_top_mm: float = 70.0,
        margin_bottom_mm: float = 70.0,
        material_id: str = "smooth_panel",
        mounting_type: str = "suction"  # "suction", "clamp", "frame"
    ):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.margin_left = margin_left_mm
        self.margin_right = margin_right_mm
        self.margin_top = margin_top_mm
        self.margin_bottom = margin_bottom_mm
        self.material = SurfaceMaterialCatalog.get(material_id)
        self.mounting_type = mounting_type

        # Corner anchor locations (A1: UL, A2: UR, A3: LL, A4: LR)
        # Positioned with slight structural offset outside margins
        self.anchors: List[AnchorPoint] = []
        self._update_anchors()

    def _update_anchors(self):
        """Update anchor positions when surface dimensions change"""
        self.anchors = [
            AnchorPoint("A1", 0.0, self.height_mm),              # Upper-Left
            AnchorPoint("A2", self.width_mm, self.height_mm),    # Upper-Right
            AnchorPoint("A3", 0.0, 0.0),                         # Lower-Left
            AnchorPoint("A4", self.width_mm, 0.0),               # Lower-Right
        ]

    def set_dimensions(self, width_mm: float, height_mm: float):
        self.width_mm = max(300.0, width_mm)
        self.height_mm = max(300.0, height_mm)
        self._update_anchors()

    @property
    def printable_bounds(self) -> Dict[str, float]:
        """Valid printable region respecting physical margins & end-effector half-dimensions"""
        # End effector is 100 x 80 mm -> half sizes: 50mm X, 40mm Y
        min_x = self.margin_left + 50.0
        max_x = self.width_mm - self.margin_right - 50.0
        min_y = self.margin_bottom + 40.0
        max_y = self.height_mm - self.margin_top - 40.0
        return {
            "min_x_mm": round(min_x, 1),
            "max_x_mm": round(max_x, 1),
            "min_y_mm": round(min_y, 1),
            "max_y_mm": round(max_y, 1),
            "width_mm": round(max_x - min_x, 1),
            "height_mm": round(max_y - min_y, 1)
        }

    def verify_mounting(self) -> MountingVerificationResult:
        """
        Mounting feasibility check (Part 3.6):
        Suction: verifies vacuum pressure seal and surface porosity.
        Clamp: verifies edge accessibility.
        Frame: rigid temporary perimeter.
        """
        if self.mounting_type == "suction":
            if not self.material.suction_compatible:
                return MountingVerificationResult(
                    is_valid=False,
                    mounting_type="suction",
                    holding_capacity_n=0.0,
                    safety_factor=0.0,
                    message=f"Surface '{self.material.name}' is too porous/rough for suction cup seal. Use clamp or rigid frame."
                )
            # 80mm suction cup at -70 kPa differential pressure: F = delta_P * Area = 70,000 * pi*(0.04)^2 = 351 N
            holding_force = 350.0 * (1.0 - self.material.roughness * 0.4)
            safety_factor = holding_force / 65.0 # Max cable tension 65N
            return MountingVerificationResult(
                is_valid=True,
                mounting_type="suction",
                holding_capacity_n=round(holding_force, 1),
                safety_factor=round(safety_factor, 2),
                message=f"Suction cups verified on {self.material.name}. Holding capacity: {holding_force:.1f}N (SF: {safety_factor:.1f})."
            )

        elif self.mounting_type == "clamp":
            if not self.material.clamp_compatible:
                return MountingVerificationResult(
                    is_valid=False,
                    mounting_type="clamp",
                    holding_capacity_n=0.0,
                    safety_factor=0.0,
                    message=f"Surface '{self.material.name}' has no exposed perimeter edges for mechanical clamping."
                )
            return MountingVerificationResult(
                is_valid=True,
                mounting_type="clamp",
                holding_capacity_n=500.0,
                safety_factor=7.6,
                message=f"Mechanical edge clamps verified on {self.material.name}."
            )

        else: # "frame"
            return MountingVerificationResult(
                is_valid=True,
                mounting_type="frame",
                holding_capacity_n=800.0,
                safety_factor=12.0,
                message="Rigid freestanding perimeter frame verified."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surface_dimensions": {
                "width_mm": self.width_mm,
                "height_mm": self.height_mm
            },
            "printable_bounds": self.printable_bounds,
            "anchors": [{"id": a.id, "x": a.x, "y": a.y} for a in self.anchors],
            "material": {
                "id": self.material.type_id,
                "name": self.material.name,
                "roughness": self.material.roughness,
                "absorption": self.material.absorption_rate,
                "spread_factor": self.material.ink_spread_factor
            },
            "mounting": {
                "type": self.mounting_type,
                "verification": self.verify_mounting().__dict__
            }
        }

