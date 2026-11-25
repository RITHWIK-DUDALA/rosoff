"""
Interchangeable Printing Actuator Module for PROJECT W.A.L.L.
Implements Module A (Photographic Inkjet) and Module B (Artistic Paint/Marker),
wall distance compliance, and deposition actuation states as specified in Part 7 of the Specification.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional


class ActuatorState(str, Enum):
    DISABLED = "DISABLED"
    READY = "READY"
    PRIMING = "PRIMING"
    PRINTING = "PRINTING"
    PAUSED = "PAUSED"
    CLEANING = "CLEANING"
    LOW_SUPPLY = "LOW_SUPPLY"
    NOZZLE_FAULT = "NOZZLE_FAULT"
    CONTACT_FAULT = "CONTACT_FAULT"
    COMPLETED = "COMPLETED"


class PrintingModuleType(str, Enum):
    MODULE_A_INKJET = "inkjet"
    MODULE_B_PAINT = "paint"
    MODULE_B_MARKER = "paint"
    PIEZO_INKJET = "inkjet"
    PAINT_MARKER = "paint"


@dataclass
class InkjetSpecifications:
    nozzle_count: int = 48
    nozzle_pitch_mm: float = 0.50       # 0.5 mm spacing
    droplet_volume_pl: float = 14.0     # 14 pico-liters
    target_standoff_mm: float = 2.0     # 2mm non-contact standoff
    max_firing_frequency_hz: int = 15000
    ink_level_percent: float = 94.0


@dataclass
class PaintSpecifications:
    tip_diameter_mm: float = 6.0        # Replaceable felt / roller tip
    contact_force_n: float = 1.2        # Light spring compliance contact
    stroke_width_range_mm: tuple = (2.0, 10.0)
    paint_viscosity_factor: float = 1.25
    is_tip_engaged: bool = False
    paint_level_percent: float = 88.0


class PrintingActuator:
    def __init__(self, module_type: PrintingModuleType = PrintingModuleType.MODULE_A_INKJET):
        self.module_type = module_type
        self.state: ActuatorState = ActuatorState.READY
        self.inkjet_specs = InkjetSpecifications()
        self.paint_specs = PaintSpecifications()

        # Wall standoff compliance
        self.measured_standoff_mm: float = 2.0
        self.is_primed: bool = True
        self.total_ejected_droplets: int = 0
        self.total_stroke_length_mm: float = 0.0

    def swap_module(self, new_module_type: PrintingModuleType):
        self.stop_deposition()
        self.module_type = new_module_type
        if new_module_type == PrintingModuleType.MODULE_B_PAINT:
            self.measured_standoff_mm = 0.0
        else:
            self.measured_standoff_mm = 2.0

    def prime(self):
        self.state = ActuatorState.PRIMING
        self.is_primed = True
        self.state = ActuatorState.READY

    def start_deposition(self):
        if self.is_primed:
            self.state = ActuatorState.PRINTING
            if self.module_type == PrintingModuleType.MODULE_B_PAINT:
                self.paint_specs.is_tip_engaged = True

    def pause_deposition(self):
        self.state = ActuatorState.PAUSED
        if self.module_type == PrintingModuleType.MODULE_B_PAINT:
            self.paint_specs.is_tip_engaged = False

    def stop_deposition(self):
        self.state = ActuatorState.READY
        if self.module_type == PrintingModuleType.MODULE_B_PAINT:
            self.paint_specs.is_tip_engaged = False

    def update_standoff(self, measured_mm: float) -> bool:
        """
        Passive compliance verification (Section 7.4):
        Checks whether end-effector is within safe working distance.
        """
        self.measured_standoff_mm = measured_mm
        if self.module_type == PrintingModuleType.MODULE_A_INKJET:
            # Safe inkjet range: 1.0mm to 3.5mm
            if not (1.0 <= measured_mm <= 3.5):
                self.state = ActuatorState.CONTACT_FAULT
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_type": self.module_type.value,
            "state": self.state.value,
            "measured_standoff_mm": round(self.measured_standoff_mm, 2),
            "is_primed": self.is_primed,
            "inkjet": {
                "nozzle_count": self.inkjet_specs.nozzle_count,
                "droplet_volume_pl": self.inkjet_specs.droplet_volume_pl,
                "ink_level_percent": round(self.inkjet_specs.ink_level_percent, 1),
                "ejected_droplets": self.total_ejected_droplets
            } if self.module_type == PrintingModuleType.MODULE_A_INKJET else None,
            "paint": {
                "tip_diameter_mm": self.paint_specs.tip_diameter_mm,
                "is_engaged": self.paint_specs.is_tip_engaged,
                "contact_force_n": self.paint_specs.contact_force_n,
                "paint_level_percent": round(self.paint_specs.paint_level_percent, 1)
            } if self.module_type == PrintingModuleType.MODULE_B_PAINT else None
        }
