"""
Real-time Flight Recorder & Diagnostics Logger for PROJECT W.A.L.L.
Captures continuous time-series telemetry at 30 Hz into a circular ring buffer,
computes runtime statistical metrics, and exports flight logs as CSV / JSON (Part 15).
"""

import time
import io
import csv
from typing import Dict, Any, List, Optional
from collections import deque
from dataclasses import dataclass, asdict


@dataclass
class TelemetryFrame:
    sim_time_s: float
    timestamp: float
    state: str
    ee_x_mm: float
    ee_y_mm: float
    est_x_mm: float
    est_y_mm: float
    tracking_err_mm: float
    kci_dexterity: float
    c1_tension_n: float
    c2_tension_n: float
    c3_tension_n: float
    c4_tension_n: float
    m1_rpm: float
    m2_rpm: float
    m3_rpm: float
    m4_rpm: float
    standoff_mm: float
    droplets_fired: int
    coverage_ratio: float


class TelemetryLogger:
    def __init__(self, max_buffer_size: int = 5000):
        self.max_buffer_size = max_buffer_size
        self.buffer: deque[TelemetryFrame] = deque(maxlen=max_buffer_size)
        self.is_logging_active: bool = True

    def record_frame(self, telemetry: Dict[str, Any]):
        if not self.is_logging_active or not telemetry:
            return

        ee = telemetry.get("end_effector", {})
        cables = telemetry.get("cables", {}).get("cables", {})
        motors = telemetry.get("motors", {})
        act = telemetry.get("actuator", {})
        dep = telemetry.get("deposition", {})
        sup = telemetry.get("supervisor", {})

        frame = TelemetryFrame(
            sim_time_s=float(telemetry.get("sim_time_s", 0.0)),
            timestamp=float(telemetry.get("timestamp", time.time())),
            state=str(sup.get("state", "UNKNOWN")),
            ee_x_mm=float(ee.get("x_mm", 0.0)),
            ee_y_mm=float(ee.get("y_mm", 0.0)),
            est_x_mm=float(ee.get("estimated_x_mm", 0.0)),
            est_y_mm=float(ee.get("estimated_y_mm", 0.0)),
            tracking_err_mm=float(ee.get("tracking_error_mm", 0.0)),
            kci_dexterity=float(ee.get("dexterity_index", 0.0)),
            c1_tension_n=float(cables.get("C1", {}).get("tension_n", 0.0)),
            c2_tension_n=float(cables.get("C2", {}).get("tension_n", 0.0)),
            c3_tension_n=float(cables.get("C3", {}).get("tension_n", 0.0)),
            c4_tension_n=float(cables.get("C4", {}).get("tension_n", 0.0)),
            m1_rpm=float(motors.get("M1", {}).get("rpm", 0.0)),
            m2_rpm=float(motors.get("M2", {}).get("rpm", 0.0)),
            m3_rpm=float(motors.get("M3", {}).get("rpm", 0.0)),
            m4_rpm=float(motors.get("M4", {}).get("rpm", 0.0)),
            standoff_mm=float(act.get("measured_standoff_mm", 2.0)),
            droplets_fired=int(dep.get("total_droplets", 0)),
            coverage_ratio=float(dep.get("coverage_ratio", 0.0))
        )
        self.buffer.append(frame)

    def get_statistics(self) -> Dict[str, Any]:
        if not self.buffer:
            return {"total_samples": 0}

        t1 = [f.c1_tension_n for f in self.buffer]
        t2 = [f.c2_tension_n for f in self.buffer]
        t3 = [f.c3_tension_n for f in self.buffer]
        t4 = [f.c4_tension_n for f in self.buffer]
        errs = [f.tracking_err_mm for f in self.buffer]

        return {
            "total_samples": len(self.buffer),
            "duration_s": round(self.buffer[-1].sim_time_s - self.buffer[0].sim_time_s, 2),
            "tracking_error_max_mm": round(max(errs), 3),
            "tracking_error_mean_mm": round(sum(errs) / len(errs), 3),
            "tension_c1_min_max_mean_n": [round(min(t1), 1), round(max(t1), 1), round(sum(t1)/len(t1), 1)],
            "tension_c2_min_max_mean_n": [round(min(t2), 1), round(max(t2), 1), round(sum(t2)/len(t2), 1)],
            "tension_c3_min_max_mean_n": [round(min(t3), 1), round(max(t3), 1), round(sum(t3)/len(t3), 1)],
            "tension_c4_min_max_mean_n": [round(min(t4), 1), round(max(t4), 1), round(sum(t4)/len(t4), 1)],
        }

    def export_csv(self) -> str:
        if not self.buffer:
            return ""

        output = io.StringIO()
        fieldnames = list(asdict(self.buffer[0]).keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for f in self.buffer:
            writer.writerow(asdict(f))
        return output.getvalue()

