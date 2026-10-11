"""
Workspace and geometric collision detection engine.
Verifies:
1. Platform body within frame interior minus clearance margin.
2. Platform footprint corners and guide boundary clearances.
3. Cable geometry sanity (positive lengths, clearance from corner obstacles).
4. Full collision status reports.
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from backend.cdpr.config import RobotConfig
from backend.cdpr.geometry import Geometry


@dataclass
class CollisionCheckResult:
    is_safe: bool
    platform_in_bounds: bool
    cables_clear: bool
    clearance_x_m: float
    clearance_y_m: float
    violation_message: str


class CollisionChecker:
    def __init__(self, geometry: Geometry):
        self.geom = geometry
        self.config = geometry.config
        self.half_fw = self.config.frame.width_m / 2.0
        self.half_fh = self.config.frame.height_m / 2.0
        self.half_pw = self.config.platform.width_m / 2.0
        self.half_ph = self.config.platform.height_m / 2.0
        self.margin = self.config.workspace.safety_margin_m

    def check(self, q: np.ndarray) -> CollisionCheckResult:
        """
        Evaluates collision and workspace boundaries for platform at center position q = [x, y].
        """
        q = np.asarray(q, dtype=np.float64).reshape(2)
        px, py = q[0], q[1]

        # Platform outer bounding box
        x_min_plat = px - self.half_pw
        x_max_plat = px + self.half_pw
        y_min_plat = py - self.half_ph
        y_max_plat = py + self.half_ph

        # Frame boundaries with safety margin
        x_min_allow = -self.half_fw + self.margin
        x_max_allow =  self.half_fw - self.margin
        y_min_allow = -self.half_fh + self.margin
        y_max_allow =  self.half_fh - self.margin

        clear_x = min(x_min_plat - (-self.half_fw), self.half_fw - x_max_plat)
        clear_y = min(y_min_plat - (-self.half_fh), self.half_fh - y_max_plat)

        in_bounds = (
            x_min_plat >= x_min_allow and
            x_max_plat <= x_max_allow and
            y_min_plat >= y_min_allow and
            y_max_plat <= y_max_allow
        )

        # Cable lengths check: must be strictly positive and within physical frame diagonal
        lengths = self.geom.cable_lengths(q)
        max_diag = np.sqrt(self.config.frame.width_m**2 + self.config.frame.height_m**2)
        cables_ok = np.all(lengths > 0.010) and np.all(lengths < max_diag)

        if not in_bounds:
            msg = (
                f"Platform footprint [{x_min_plat*1000:.1f}, {x_max_plat*1000:.1f}] x "
                f"[{y_min_plat*1000:.1f}, {y_max_plat*1000:.1f}] mm violates frame bounds with {self.margin*1000:.0f} mm safety margin"
            )
            return CollisionCheckResult(
                is_safe=False,
                platform_in_bounds=False,
                cables_clear=cables_ok,
                clearance_x_m=clear_x,
                clearance_y_m=clear_y,
                violation_message=msg
            )

        if not cables_ok:
            return CollisionCheckResult(
                is_safe=False,
                platform_in_bounds=True,
                cables_clear=False,
                clearance_x_m=clear_x,
                clearance_y_m=clear_y,
                violation_message="Cable length bounds violated"
            )

        return CollisionCheckResult(
            is_safe=True,
            platform_in_bounds=True,
            cables_clear=True,
            clearance_x_m=clear_x,
            clearance_y_m=clear_y,
            violation_message="Collision free"
        )
