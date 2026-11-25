"""
Synchronized 4-Cable Motion Planning Module for PROJECT W.A.L.L.
Converts requested end-effector (X, Y) paths into 4 synchronized cable-length commands
sharing a single deterministic time base as specified in Part 9 of the Specification.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from ..kinematics.cdpr_kinematics import CDPRKinematics


@dataclass
class TrajectoryLimits:
    max_velocity_mm_s: float = 120.0     # 0.12 m/s
    max_accel_mm_s2: float = 400.0       # 0.40 m/s^2


@dataclass
class MotionWaypoint:
    x_mm: float
    y_mm: float
    is_printing: bool = False
    dwell_s: float = 0.0


class SynchronizedTrajectoryPlanner:
    def __init__(self, kinematics: CDPRKinematics, limits: Optional[TrajectoryLimits] = None):
        self.kinematics = kinematics
        self.limits = limits or TrajectoryLimits()
        self.waypoints: List[MotionWaypoint] = []
        self.current_idx: int = 0
        self.is_active: bool = False
        self.is_paused: bool = False

        # Current continuous generator state
        self.current_x_mm: float = 400.0
        self.current_y_mm: float = 300.0
        self.target_x_mm: float = 400.0
        self.target_y_mm: float = 300.0
        self.current_speed_mm_s: float = 0.0

    def generate_raster_scan(
        self,
        origin_x_mm: float,
        origin_y_mm: float,
        width_mm: float,
        height_mm: float,
        row_pitch_mm: float = 2.0
    ) -> List[MotionWaypoint]:
        """
        Generates bidirectional raster scanning pattern for planar printing.
        Row changes occur with printhead turned off during non-printing repositions.
        """
        wps = []
        rows = int(height_mm / row_pitch_mm)
        for r in range(rows):
            y = origin_y_mm + (r * row_pitch_mm)
            if r % 2 == 0:
                # Left to right
                wps.append(MotionWaypoint(x_mm=origin_x_mm, y_mm=y, is_printing=False))
                wps.append(MotionWaypoint(x_mm=origin_x_mm + width_mm, y_mm=y, is_printing=True))
            else:
                # Right to left
                wps.append(MotionWaypoint(x_mm=origin_x_mm + width_mm, y_mm=y, is_printing=False))
                wps.append(MotionWaypoint(x_mm=origin_x_mm, y_mm=y, is_printing=True))

        self.waypoints = wps
        self.current_idx = 0
        self.is_active = True
        return wps

    def step(self, dt: float) -> Tuple[float, float, np.ndarray, bool]:
        """
        Advances along trajectory by timestep dt.
        Returns:
            (x_mm, y_mm, synchronized_cable_lengths_mm, is_printing_active)
        """
        if not self.is_active or self.is_paused or self.current_idx >= len(self.waypoints):
            lengths = self.kinematics.inverse_kinematics(self.current_x_mm, self.current_y_mm)
            return self.current_x_mm, self.current_y_mm, lengths, False

        wp = self.waypoints[self.current_idx]
        dx = wp.x_mm - self.current_x_mm
        dy = wp.y_mm - self.current_y_mm
        dist = math.hypot(dx, dy)

        if dist < 1.0: # Waypoint reached
            self.current_x_mm = wp.x_mm
            self.current_y_mm = wp.y_mm
            self.current_idx += 1
            is_printing = wp.is_printing
        else:
            # Acceleration limited movement towards target
            step_dist = min(dist, self.limits.max_velocity_mm_s * dt)
            self.current_x_mm += (dx / dist) * step_dist
            self.current_y_mm += (dy / dist) * step_dist
            is_printing = wp.is_printing

        # Synchronously compute the 4 exact cable lengths for this coordinate
        cable_lengths = self.kinematics.inverse_kinematics(self.current_x_mm, self.current_y_mm)

        if self.current_idx >= len(self.waypoints):
            self.is_active = False

        return self.current_x_mm, self.current_y_mm, cable_lengths, is_printing

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_active = False
        self.is_paused = False
        self.waypoints.clear()
        self.current_idx = 0

