"""
Geometry and kinematics vector calculations for 4-cable planar robot.
Strict SI unit consistency (meters).
Origin at center of frame:
  X: horizontal, positive to the right
  Y: vertical, positive upward
  Z: normal to horizontal motion plane
"""
import numpy as np
from typing import Tuple, Dict
from backend.cdpr.config import RobotConfig


class Geometry:
    def __init__(self, config: RobotConfig):
        self.config = config
        # Anchors A_i: shape (4, 2) in meters
        # C1: (-0.25,  0.20)
        # C2: ( 0.25,  0.20)
        # C3: ( 0.25, -0.20)
        # C4: (-0.25, -0.20)
        self.anchors = config.frame.anchors_array()

        # Platform attachments b_i: shape (4, 2) in local platform coordinates in meters
        # C1: (-0.05,  0.04)
        # C2: ( 0.05,  0.04)
        # C3: ( 0.05, -0.04)
        # C4: (-0.05, -0.04)
        self.attachments = config.platform.attachments_array()

        # Dimensions
        self.frame_width = config.frame.width_m
        self.frame_height = config.frame.height_m
        self.platform_width = config.platform.width_m
        self.platform_height = config.platform.height_m

    def platform_attachments_world(self, q: np.ndarray) -> np.ndarray:
        """
        Calculates world coordinates P_i = q + b_i for all 4 cables.
        q: (2,) [x, y] in meters.
        Returns: (4, 2) array of P_i coordinates.
        """
        q = np.asarray(q, dtype=np.float64).reshape(2)
        return q + self.attachments

    def cable_vectors(self, q: np.ndarray) -> np.ndarray:
        """
        Calculates vector from platform attachment P_i to frame anchor A_i:
        v_i = A_i - P_i = A_i - (q + b_i)
        Shape: (4, 2)
        """
        P = self.platform_attachments_world(q)
        return self.anchors - P

    def cable_lengths(self, q: np.ndarray) -> np.ndarray:
        """
        Calculates Euclidean cable lengths L_i(q) = ||A_i - (q + b_i)||
        Returns: (4,) array of positive lengths in meters.
        """
        v = self.cable_vectors(q)
        lengths = np.linalg.norm(v, axis=1)
        # Numerical protection
        if np.any(lengths <= 1e-6):
            raise ValueError(f"Singular cable geometry: cable length too close to zero at q={q}")
        return lengths

    def unit_cable_vectors(self, q: np.ndarray) -> np.ndarray:
        """
        Unit vectors pointing from platform attachment P_i towards frame anchor A_i:
        u_i = (A_i - P_i) / L_i
        Cable tension exerts force on platform along u_i:
        F_cable_i = T_i * u_i
        Shape: (4, 2)
        """
        v = self.cable_vectors(q)
        L = np.linalg.norm(v, axis=1, keepdims=True)
        if np.any(L <= 1e-6):
            raise ValueError("Zero cable length encountered in unit vector calculation")
        return v / L
