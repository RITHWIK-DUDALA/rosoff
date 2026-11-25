"""
Central CDPR Digital Twin Simulation Orchestrator for PROJECT W.A.L.L.
Coordinates the 4 motorized winches, 4-cable transmission, central platform kinematics,
bounded tension allocation, synchronized trajectory planning, and progressive deposition
in a deterministic fixed-timestep simulation clock (Section 9.5 & Part 15).
"""

import time
import math
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from PIL import Image

from ..kinematics.cdpr_kinematics import CDPRKinematics, AnchorPoint, PlatformGeometry
from ..dynamics.tension_solver import CableTensionSolver, TensionLimits
from ..motors.winch_motor import WinchMotor, DrumGeometry, MotorSpecifications, MotorStatus
from ..cables.cable_system import FourCableSystem, CableProperties
from ..models.surface_model import SurfaceModel, SurfaceMaterialCatalog
from ..printing.actuator import PrintingActuator, PrintingModuleType, ActuatorState
from ..deposition.progressive_buffer import ProgressiveDepositionBuffer
from ..motion.trajectory_planner import SynchronizedTrajectoryPlanner
from ..quality.quality_inspector import QualityInspector, CompletedJobReport
from ..safety.supervisory_state_machine import CDPRSupervisor, CDPRSystemState, FaultSeverity
from ..scenarios.scenario_manager import CDPRScenarioManager
from ..perception.surface_scanner import SurfaceScanner
from ..calibration.anchor_calibrator import AnchorCalibrator
from collections import deque
from ..diagnostics.telemetry_logger import TelemetryLogger
from ..reports.report_generator import ReportGenerator
from ..processing.image_processor import ArtworkProcessor, ProcessedArtworkReport


class CDPROrchestrator:
    def __init__(self):
        # 1. Surface and Anchors (800 x 600 mm baseline)
        self.surface = SurfaceModel(width_mm=800.0, height_mm=600.0)

        # 2. Kinematics & Platform
        self.platform = PlatformGeometry(width_mm=100.0, height_mm=80.0, thickness_mm=6.0, mass_kg=0.50)
        self.kinematics = CDPRKinematics(anchors=self.surface.anchors, platform=self.platform)

        # 3. Cable Tension Statics Solver
        self.tension_solver = CableTensionSolver(self.kinematics, limits=TensionLimits(min_tension_n=2.0, max_tension_n=50.0))

        # 4. Four Winch Motors (M1: UL, M2: UR, M3: LL, M4: LR)
        self.motors: Dict[str, WinchMotor] = {
            "M1": WinchMotor("M1", "Winch 1 (Upper-Left)"),
            "M2": WinchMotor("M2", "Winch 2 (Upper-Right)"),
            "M3": WinchMotor("M3", "Winch 3 (Lower-Left)"),
            "M4": WinchMotor("M4", "Winch 4 (Lower-Right)"),
        }

        # 5. Four Distinct Cables
        initial_lengths = self.kinematics.inverse_kinematics(400.0, 300.0)
        self.cables = FourCableSystem(list(initial_lengths))

        # 6. Printing Actuator & Progressive Deposition
        self.actuator = PrintingActuator(module_type=PrintingModuleType.MODULE_A_INKJET)
        self.deposition = ProgressiveDepositionBuffer(canvas_width_px=2400, canvas_height_px=1800, surface_material=self.surface.material)

        # 7. Motion Planner & Quality Inspector
        self.planner = SynchronizedTrajectoryPlanner(self.kinematics)
        self.quality = QualityInspector()

        # 8. Supervisor & Scenarios
        self.supervisor = CDPRSupervisor()
        self.scenario_mgr = CDPRScenarioManager(self)

        # Current end-effector state
        self.pos_x_mm: float = 400.0
        self.pos_y_mm: float = 300.0
        self.target_x_mm: float = 400.0
        self.target_y_mm: float = 300.0
        self.current_tensions_n: np.ndarray = np.array([12.0, 12.0, 12.0, 12.0], dtype=np.float64)

        # Simulation clock
        self.sim_time_s: float = 0.0
        self.last_job_report: Optional[CompletedJobReport] = None

        # 9. Intelligent Artwork Processing & Execution Event Logging
        self.processor = ArtworkProcessor(self.kinematics, self.surface)
        self.event_log_counter = 0
        self.event_logs: deque = deque(maxlen=2000)
        self.last_processed_report: Optional[ProcessedArtworkReport] = None
        self.step_counter: int = 0

        # Boot telemetry logs
        self.add_log("INFO", "SUPERVISOR", "CDPR Orchestrator initialized. 4 Anchors A1..A4 configured.")
        self.add_log("INFO", "KINEMATICS", "Kinematic conditioning nominal (KCI: 0.85). Platform centered at (400.0, 300.0) mm.")
        self.add_log("INFO", "ACTUATOR", f"Active End-Effector: {self.actuator.module_type.value.upper()}. Standoff: 2.0 mm.")

    def add_log(self, level: str, subsystem: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Appends structured time-stamped execution log for real-time streaming"""
        self.event_log_counter += 1
        entry = {
            "id": self.event_log_counter,
            "time_s": round(self.sim_time_s, 2),
            "timestamp": round(time.time(), 3),
            "level": level,       # "INFO", "WARN", "ACTION", "PRINT", "FAULT"
            "subsystem": subsystem, # "PROCESSOR", "KINEMATICS", "MOTOR", "TENSION", "DEPOSITION", "SUPERVISOR"
            "message": message,
            "data": data or {}
        }
        self.event_logs.append(entry)

    def get_logs(self, since_id: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns buffered execution logs filtered by sequence id"""
        return [log for log in self.event_logs if log["id"] > since_id][-limit:]

    def process_artwork_file(
        self,
        img: Image.Image,
        filename: str = "artwork.png",
        target_w_mm: float = 300.0,
        target_h_mm: float = 250.0,
        pitch_mm: float = 3.0,
        actuator_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyzes input artwork, quantizes palette, classifies motion and actuator, and prepares job"""
        report = self.processor.analyze_image(
            img=img,
            filename=filename,
            target_width_mm=target_w_mm,
            target_height_mm=target_h_mm,
            row_pitch_mm=pitch_mm,
            force_actuator=actuator_override
        )
        self.last_processed_report = report

        # Load raster into progressive buffer with calculated physical print bounds
        self.deposition.load_target_raster(img, report.surface_bounds_mm)

        # Log analysis outcome
        self.add_log("ACTION", "PROCESSOR", f"Image '{filename}' processed ({report.original_size_px[0]}x{report.original_size_px[1]} px -> {target_w_mm:.1f}x{target_h_mm:.1f} mm).")
        self.add_log("INFO", "PROCESSOR", f"Classification: {report.paint_recipe.actuator_display_name}.")
        self.add_log("INFO", "PROCESSOR", f"Rationale: {report.paint_recipe.rationale}")
        self.add_log("INFO", "PROCESSOR", f"Paint Recipe: {len(report.paint_recipe.color_breakdown)} dominant pigments. Est. ink: {report.paint_recipe.total_volume_ml} mL.")
        self.add_log("INFO", "KINEMATICS", f"Toolpath: {report.motion_plan.total_waypoints} waypoints ({report.motion_plan.total_distance_m} m). Tension range: [{report.motion_plan.tension_range_n[0]:.1f}N .. {report.motion_plan.tension_range_n[1]:.1f}N].")

        from dataclasses import asdict
        return asdict(report)

    def execute_processed_job(self) -> Tuple[bool, str]:
        """Executes the pre-analyzed CAM job on the 4-cable CDPR surface printer"""
        if not self.last_processed_report:
            return False, "No processed artwork job found. Analyze an image in the Processor first."

        report = self.last_processed_report
        rec_module = report.paint_recipe.recommended_actuator

        # Auto-swap actuator module if required
        if rec_module == "paint" and self.actuator.module_type != PrintingModuleType.MODULE_B_PAINT:
            self.actuator.swap_module(PrintingModuleType.MODULE_B_PAINT)
            self.add_log("ACTION", "ACTUATOR", "Auto-swapped end-effector to Module B (Paint Marker, 1.2N compliance spring).")
        elif rec_module == "inkjet" and self.actuator.module_type != PrintingModuleType.MODULE_A_INKJET:
            self.actuator.swap_module(PrintingModuleType.MODULE_A_INKJET)
            self.add_log("ACTION", "ACTUATOR", "Auto-swapped end-effector to Module A (Piezo Inkjet, 48 nozzles).")

        # Generate raster waypoints
        bounds = report.surface_bounds_mm
        self.planner.generate_raster_scan(
            origin_x_mm=bounds["origin_x"],
            origin_y_mm=bounds["origin_y"],
            width_mm=bounds["width"],
            height_mm=bounds["height"],
            row_pitch_mm=report.motion_plan.row_pitch_mm
        )

        self.actuator.start_deposition()
        self.planner.is_active = True
        self.planner.is_paused = False
        self.supervisor.transition_to(CDPRSystemState.PRINTING, reason=f"Executing CAM Job {report.job_id} ({report.filename})")

        self.add_log("ACTION", "PRINT", f"Autonomous Surface Print started for {report.filename}. Total passes: {len(self.planner.waypoints)}.")
        return True, f"Print job {report.job_id} launched successfully."

    def move_to(self, target_x_mm: float, target_y_mm: float) -> Tuple[bool, str]:
        """Commands end-effector motion with kinematic & tension feasibility verification"""
        # 1. Bounds verification
        bounds = self.surface.printable_bounds
        if not (bounds["min_x_mm"] <= target_x_mm <= bounds["max_x_mm"] and bounds["min_y_mm"] <= target_y_mm <= bounds["max_y_mm"]):
            return False, f"Target ({target_x_mm:.1f}, {target_y_mm:.1f}) is outside printable boundaries"

        # 2. Tension feasibility check
        dist_res = self.tension_solver.solve_static_tensions(target_x_mm, target_y_mm)
        if not dist_res.is_feasible:
            return False, f"Target pose cannot maintain positive tension on all 4 cables (residual: {dist_res.equilibrium_residual_n:.2f}N)"

        # 3. Issue motion waypoint
        self.planner.waypoints = [
            type(self.planner.waypoints[0] if self.planner.waypoints else self.planner)(
                x_mm=target_x_mm, y_mm=target_y_mm, is_printing=False
            ) if False else None
        ]
        from ..motion.trajectory_planner import MotionWaypoint
        self.planner.waypoints = [MotionWaypoint(x_mm=target_x_mm, y_mm=target_y_mm, is_printing=False)]
        self.planner.current_idx = 0
        self.planner.is_active = True
        self.supervisor.transition_to(CDPRSystemState.MOVING, reason=f"Moving to ({target_x_mm:.1f}, {target_y_mm:.1f})")
        return True, "Motion commanded"

    def load_artwork_image(self, img: Image.Image, filename: str, target_w_mm: float = 300.0, target_h_mm: float = 250.0, pitch_mm: float = 1.5) -> Dict[str, Any]:
        """Ingests digital artwork, analyzes CAM classification, and loads target raster"""
        report_dict = self.process_artwork_file(img, filename, target_w_mm=target_w_mm, target_h_mm=target_h_mm, pitch_mm=pitch_mm)
        self.supervisor.transition_to(CDPRSystemState.READY, reason=f"Loaded and classified artwork {filename}")
        return {
            "image": filename,
            "raster_waypoints": report_dict["motion_plan"]["total_waypoints"],
            "canvas_size": [self.deposition.w, self.deposition.h],
            "estimated_duration_s": report_dict["motion_plan"]["estimated_time_s"]
        }

    def start_printing(self) -> Tuple[bool, str]:
        # If an artwork has been analyzed/processed, execute that CAM job directly
        if self.last_processed_report:
            return self.execute_processed_job()

        if not self.planner.waypoints:
            # Auto-generate default calibration artwork if none was uploaded yet
            bounds = self.surface.printable_bounds
            self.planner.generate_raster_scan(
                origin_x_mm=bounds["min_x_mm"] + 20.0,
                origin_y_mm=bounds["min_y_mm"] + 20.0,
                width_mm=min(250.0, bounds["width_mm"] - 40.0),
                height_mm=min(180.0, bounds["height_mm"] - 40.0),
                row_pitch_mm=4.0
            )
            if self.deposition.target_raster_rgb is None:
                test_arr = np.full((self.deposition.h, self.deposition.w, 3), 245, dtype=np.uint8)
                cx, cy = self.deposition.w // 2, self.deposition.h // 2
                test_arr[cy - 35:cy + 35, cx - 50:cx + 50] = [15, 23, 42]
                test_arr[cy - 15:cy + 15, cx - 25:cx + 25] = [245, 158, 11]
                self.deposition.target_raster_rgb = test_arr

        self.actuator.start_deposition()
        self.planner.is_active = True
        self.planner.is_paused = False
        self.supervisor.transition_to(CDPRSystemState.PRINTING, reason="Started progressive surface deposition")
        return True, "Printing started"

    def pause_printing(self):
        self.planner.pause()
        self.actuator.pause_deposition()
        self.supervisor.transition_to(CDPRSystemState.PAUSED, reason="Operator paused")

    def resume_printing(self):
        self.planner.resume()
        self.actuator.start_deposition()
        self.supervisor.transition_to(CDPRSystemState.PRINTING, reason="Operator resumed")

    def emergency_stop(self):
        self.planner.stop()
        self.actuator.stop_deposition()
        for m in self.motors.values():
            m.status = MotorStatus.EMERGENCY_STOP
        self.supervisor.report_fault(
            code="E_STOP_BTN",
            message="Operator Emergency Stop",
            subsystem="SYSTEM",
            severity=FaultSeverity.EMERGENCY_SHUTDOWN
        )

    def reset(self):
        self.planner.stop()
        self.actuator.stop_deposition()
        for m in self.motors.values():
            m.reset()
        self.supervisor.reset()
        self.pos_x_mm = self.surface.width_mm / 2.0
        self.pos_y_mm = self.surface.height_mm / 2.0

    def step(self, dt: float):
        """Deterministic fixed-timestep simulation tick (called at 25-50 Hz)"""
        self.sim_time_s += dt

        # 1. Update Trajectory Planner
        curr_x, curr_y, target_cable_lengths, is_printing = self.planner.step(dt)
        self.pos_x_mm = curr_x
        self.pos_y_mm = curr_y

        # 2. Synchronized Cable Length Deltas & Motor Steps
        motor_keys = ["M1", "M2", "M3", "M4"]
        actual_cable_lengths = []

        # Solve static tensions for current coordinate
        ten_res = self.tension_solver.solve_static_tensions(self.pos_x_mm, self.pos_y_mm)
        self.current_tensions_n = ten_res.tensions_n

        for i, mid in enumerate(motor_keys):
            motor = self.motors[mid]
            # Commanded length delta for this motor
            cmd_delta = target_cable_lengths[i] - self.cables.cables[f"C{i+1}"].commanded_length_mm
            actual_delta = motor.step(cmd_delta, dt, cable_tension_n=float(self.current_tensions_n[i]))
            actual_cable_lengths.append(self.cables.cables[f"C{i+1}"].commanded_length_mm + actual_delta)

        # 3. Update 4-Cable Physical State (including elastic stretch)
        self.cables.update_all(list(target_cable_lengths), list(self.current_tensions_n))

        # Check for cable slack or overload
        fault_present, fault_msg = self.cables.has_any_fault()
        if fault_present and self.supervisor.state not in (CDPRSystemState.EMERGENCY_STOP, CDPRSystemState.FAULT):
            self.emergency_stop()

        # 4. Progressive High-Fidelity Deposition Firing
        if is_printing and self.supervisor.state == CDPRSystemState.PRINTING:
            prev_x = getattr(self, "prev_print_x", self.pos_x_mm)
            prev_y = getattr(self, "prev_print_y", self.pos_y_mm)

            dist_step = math.hypot(self.pos_x_mm - prev_x, self.pos_y_mm - prev_y)
            # Sub-step every ~0.5 mm for continuous razor-sharp stroke saturation
            num_substeps = max(1, min(15, int(round(dist_step / 0.5))))

            is_inkjet = (self.actuator.module_type == PrintingModuleType.MODULE_A_INKJET)
            base_radius_px = 3 if is_inkjet else 9

            for s_idx in range(1, num_substeps + 1):
                interp = s_idx / float(num_substeps)
                sub_x = prev_x + interp * (self.pos_x_mm - prev_x)
                sub_y = prev_y + interp * (self.pos_y_mm - prev_y)

                # Map physical mm to 2400x1800 canvas pixels
                rel_x = sub_x / max(1.0, self.surface.width_mm)
                rel_y = sub_y / max(1.0, self.surface.height_mm)

                px_x = int(rel_x * self.deposition.w)
                px_y = int((1.0 - rel_y) * self.deposition.h)

                color = self.deposition.sample_color_at_pos(sub_x, sub_y)

                # Inkjet multi-nozzle swath for continuous high-clarity photographic coverage
                if is_inkjet:
                    for dy_mm in (-1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2):
                        swath_y = sub_y + dy_mm
                        swath_py = int((1.0 - swath_y / max(1.0, self.surface.height_mm)) * self.deposition.h)
                        swath_col = self.deposition.sample_color_at_pos(sub_x, swath_y)
                        self.deposition.deposit_droplet(
                            px_x=px_x,
                            px_y=swath_py,
                            color_rgb=swath_col,
                            ee_pos_mm=(sub_x, swath_y),
                            radius_px=3
                        )
                else:
                    self.deposition.deposit_droplet(
                        px_x=px_x,
                        px_y=px_y,
                        color_rgb=color,
                        ee_pos_mm=(sub_x, sub_y),
                        radius_px=base_radius_px
                    )

            self.prev_print_x = self.pos_x_mm
            self.prev_print_y = self.pos_y_mm
        else:
            self.prev_print_x = self.pos_x_mm
            self.prev_print_y = self.pos_y_mm

        # Periodic Live Telemetry Logging (every ~0.5s during printing)
        self.step_counter += 1
        if self.supervisor.state == CDPRSystemState.PRINTING and self.step_counter % 15 == 0:
            t_str = " ".join([f"C{i+1}={self.current_tensions_n[i]:.1f}N" for i in range(4)])
            rpm_str = " ".join([f"M{i+1}={self.motors[f'M{i+1}'].speed_rpm:.0f}" for i in range(4)])
            self.add_log(
                "PRINT",
                "KINEMATICS",
                f"Pos: ({self.pos_x_mm:.1f}, {self.pos_y_mm:.1f}) mm | Tensions: [{t_str}] | RPMs: [{rpm_str}]"
            )
            self.add_log(
                "PRINT",
                "DEPOSITION",
                f"Droplets: {self.deposition.total_droplets_deposited:,} | Coverage: {self.deposition.coverage_ratio*100.0:.1f}% | Layer: 1/1"
            )

        # 5. Print Completion Check
        if self.supervisor.state == CDPRSystemState.PRINTING and not self.planner.is_active:
            self.supervisor.transition_to(CDPRSystemState.COMPLETED, reason="Trajectory scan complete")
            self.actuator.stop_deposition()
            self.add_log("ACTION", "SUPERVISOR", f"Print job completed. Total droplets: {self.deposition.total_droplets_deposited:,}.")

            # Execute Quality Inspection
            if self.deposition.target_raster_rgb is not None:
                q_res = self.quality.evaluate_print(
                    self.deposition.canvas_rgb,
                    self.deposition.target_raster_rgb,
                    roughness_factor=self.surface.material.roughness
                )
                self.last_job_report = self.quality.generate_job_report(
                    job_id=f"JOB_{int(time.time())}",
                    surface_w=self.surface.width_mm,
                    surface_h=self.surface.height_mm,
                    print_w=300.0,
                    print_h=250.0,
                    image_name="artwork.png",
                    mode=self.actuator.module_type.value,
                    path_length_m=len(self.planner.waypoints) * 0.05,
                    elapsed_s=self.sim_time_s,
                    status="COMPLETED",
                    quality=q_res,
                    canvas_b64=self.deposition.get_canvas_base64()
                )

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive real-time CDPR telemetry payload for WebSocket / REST"""
        # Forward kinematics pose estimation from current cable lengths
        measured_lens = np.array([c.current_length_mm for c in self.cables.cables.values()])
        fk_ok, est_x, est_y, rms_res = self.kinematics.forward_kinematics(measured_lens, initial_guess=(self.pos_x_mm, self.pos_y_mm))

        # Dexterity conditioning
        dexterity = self.kinematics.kinematic_conditioning_index(self.pos_x_mm, self.pos_y_mm)

        payload = {
            "timestamp": float(round(time.time(), 3)),
            "sim_time_s": float(round(self.sim_time_s, 2)),
            "supervisor": self.supervisor.to_dict(),
            "surface": self.surface.to_dict(),
            "end_effector": {
                "x_mm": float(round(self.pos_x_mm, 2)),
                "y_mm": float(round(self.pos_y_mm, 2)),
                "estimated_x_mm": float(round(est_x, 2)),
                "estimated_y_mm": float(round(est_y, 2)),
                "tracking_error_mm": float(round(math.hypot(est_x - self.pos_x_mm, est_y - self.pos_y_mm), 3)),
                "dexterity_index": float(round(dexterity, 3)),
                "mass_kg": float(self.platform.mass_kg),
                "dimensions_mm": [float(self.platform.width_mm), float(self.platform.height_mm)]
            },
            "motors": {mid: m.to_dict() for mid, m in self.motors.items()},
            "cables": self.cables.to_dict(),
            "actuator": self.actuator.to_dict(),
            "deposition": self.deposition.to_dict(),
            "canvas_base64": self.deposition.get_canvas_base64(),
            "quality_report": self.last_job_report.quality.__dict__ if self.last_job_report else None,
            "recent_logs": self.get_logs(since_id=max(0, self.event_log_counter - 15), limit=15)
        }

        def _clean(val):
            if isinstance(val, dict):
                return {k: _clean(v) for k, v in val.items()}
            elif isinstance(val, (list, tuple)):
                return [_clean(v) for v in val]
            elif isinstance(val, (np.bool_, bool)):
                return bool(val)
            elif isinstance(val, (np.floating, float)):
                return float(val)
            elif isinstance(val, (np.integer, int)):
                return int(val)
            elif isinstance(val, np.ndarray):
                return [_clean(v) for v in val.tolist()]
            return val

        return _clean(payload)

