"""
Four-Cable Transmission System Module for PROJECT W.A.L.L.
Implements 4 distinct cable instances (C1, C2, C3, C4), linear elastic stretch
(delta_L = F*L / E*A), positive tension monitoring, slack detection, and overload interlocks
as specified in Part 5 of the Specification.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import math


@dataclass
class CableProperties:
    diameter_mm: float = 1.0           # 1.0 mm Dyneema SK75 / UHMWPE
    elastic_modulus_mpa: float = 100000.0 # 100 GPa
    damping_coefficient_ns_per_mm: float = 0.05 # Viscous damping c
    max_permitted_load_n: float = 65.0 # Tensile limit before emergency halt
    min_permitted_tension_n: float = 2.0 # Minimum to prevent cable sag/slack
    nominal_tension_n: float = 18.0

    @property
    def cross_section_area_mm2(self) -> float:
        return (math.pi * (self.diameter_mm ** 2)) / 4.0


class Cable:
    def __init__(
        self,
        cable_id: str,
        motor_id: str,
        attachment_id: str,
        initial_length_mm: float = 600.0,
        properties: Optional[CableProperties] = None
    ):
        self.cable_id = cable_id
        self.motor_id = motor_id
        self.attachment_id = attachment_id
        self.props = properties or CableProperties()

        self.current_length_mm: float = initial_length_mm
        self.commanded_length_mm: float = initial_length_mm
        self.previous_length_mm: float = initial_length_mm
        self.tension_n: float = self.props.nominal_tension_n

        self.is_slack: bool = False
        self.is_overloaded: bool = False
        self.elastic_stretch_mm: float = 0.0

    def compute_axial_stiffness_n_per_mm(self) -> float:
        """Axial stiffness k = (E * A) / L"""
        ea = self.props.elastic_modulus_mpa * self.props.cross_section_area_mm2
        return ea / max(10.0, self.commanded_length_mm)

    def compute_kelvin_voigt_tension(self, delta_mm: float, delta_rate_mm_s: float = 0.0) -> float:
        """
        Unilateral Kelvin-Voigt Constitutive Law (Section 7.5):
        T = max(0, k * delta + c * delta_dot)
        Enforces unilateral tensile behavior (slack cables have zero tension).
        """
        if delta_mm <= 0.0:
            return 0.0 # Cable is completely slack
        k = self.compute_axial_stiffness_n_per_mm()
        c = self.props.damping_coefficient_ns_per_mm
        viscous_term = c * delta_rate_mm_s
        raw_tension = k * delta_mm + viscous_term
        return float(max(0.0, raw_tension))

    def compute_elastic_stretch_mm(self, tension_n: float) -> float:
        """
        Linear elasticity (Section 5.5):
        delta_L = (F * L) / (E * A)
        """
        ea = self.props.elastic_modulus_mpa * self.props.cross_section_area_mm2
        stretch = (tension_n * self.current_length_mm) / max(1.0, ea)
        return stretch

    def update_state(self, geometric_length_mm: float, tension_n: float, dt: float = 0.033):
        """Updates cable physical state and checks slack/overload thresholds"""
        self.commanded_length_mm = float(geometric_length_mm)
        self.tension_n = float(tension_n)

        # Calculate elastic elongation
        self.elastic_stretch_mm = float(self.compute_elastic_stretch_mm(self.tension_n))
        self.previous_length_mm = self.current_length_mm
        self.current_length_mm = float(self.commanded_length_mm + self.elastic_stretch_mm)

        # Check safety boundaries - explicitly cast to native bool
        self.is_slack = bool(self.tension_n < self.props.min_permitted_tension_n)
        self.is_overloaded = bool(self.tension_n > self.props.max_permitted_load_n)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cable_id": str(self.cable_id),
            "motor_id": str(self.motor_id),
            "attachment_id": str(self.attachment_id),
            "length_mm": float(round(self.current_length_mm, 2)),
            "commanded_length_mm": float(round(self.commanded_length_mm, 2)),
            "stretch_mm": float(round(self.elastic_stretch_mm, 3)),
            "tension_n": float(round(self.tension_n, 2)),
            "is_slack": bool(self.is_slack),
            "is_overloaded": bool(self.is_overloaded),
            "status": "SLACK" if self.is_slack else ("OVERLOAD" if self.is_overloaded else "NORMAL")
        }


class FourCableSystem:
    def __init__(self, initial_lengths: Optional[List[float]] = None):
        lens = initial_lengths or [600.0, 600.0, 600.0, 600.0]
        self.cables: Dict[str, Cable] = {
            "C1": Cable("C1", "M1", "B1", lens[0]),
            "C2": Cable("C2", "M2", "B2", lens[1]),
            "C3": Cable("C3", "M3", "B3", lens[2]),
            "C4": Cable("C4", "M4", "B4", lens[3]),
        }

    def update_all(self, geometric_lengths_mm: List[float], tensions_n: List[float]):
        keys = ["C1", "C2", "C3", "C4"]
        for i, k in enumerate(keys):
            self.cables[k].update_state(geometric_lengths_mm[i], tensions_n[i])

    def has_any_fault(self) -> Tuple[bool, Optional[str]]:
        for cid, c in self.cables.items():
            if c.is_overloaded:
                return True, f"Cable {cid} overloaded: {c.tension_n:.1f}N > {c.props.max_permitted_load_n}N"
            if c.is_slack:
                return True, f"Cable {cid} slack: {c.tension_n:.1f}N < {c.props.min_permitted_tension_n}N"
        return False, None

    def to_dict(self) -> Dict[str, Any]:
        return {cid: c.to_dict() for cid, c in self.cables.items()}
