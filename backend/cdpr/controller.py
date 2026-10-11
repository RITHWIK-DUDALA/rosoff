"""
Motion supervisor and controller state machine for CDPR.
Manages:
- Operating modes: IDLE, MOVING, PAUSED, STOPPED, FAULT, ESTOP
- Waypoint execution queue
- Jogging step interpolation
- Stop (cancels queued points and smoothly brings platform to rest)
- Pause and Resume
- Reset (returns state to origin [0, 0])
"""
from typing import List, Optional, Tuple
import numpy as np
from backend.cdpr.config import RobotConfig
from backend.cdpr.trajectory import TrajectoryPoint, TrajectoryPlanner, TrajectoryValidationResult


class Controller:
    def __init__(self, config: RobotConfig, planner: TrajectoryPlanner):
        self.config = config
        self.planner = planner
        self.mode = "IDLE"  # "IDLE", "MOVING", "PAUSED", "STOPPED", "FAULT", "ESTOP"
        self.active_trajectory: List[TrajectoryPoint] = []
        self.current_traj_index: int = 0
        self.current_q = np.zeros(2, dtype=np.float64)
        self.target_q = np.zeros(2, dtype=np.float64)
        self.target_q_dot = np.zeros(2, dtype=np.float64)
        self.target_q_ddot = np.zeros(2, dtype=np.float64)
        self.active_faults: List[str] = []

    def set_position(self, q: np.ndarray):
        """Initializes platform position."""
        self.current_q = np.asarray(q, dtype=np.float64).reshape(2).copy()
        self.target_q = self.current_q.copy()
        self.target_q_dot = np.zeros(2)
        self.target_q_ddot = np.zeros(2)

    def request_move(self, q_goal: np.ndarray, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        """Requests straight-line movement to goal coordinates."""
        if self.mode == "ESTOP":
            return False, "Cannot execute move: E-STOP is active. Reset required."

        pts = self.planner.plan_point_to_point(self.current_q, q_goal, v_target=speed_m_s)
        val = self.planner.validate_trajectory(pts)
        if not val.is_feasible:
            return False, f"Move rejected: {val.violation_message} ({val.violation_code})"

        self.active_trajectory = pts
        self.current_traj_index = 0
        self.mode = "MOVING"
        self.active_faults.clear()
        return True, "Move trajectory accepted and queued"

    def request_trajectory(self, trajectory_type: str, params: dict) -> Tuple[bool, str]:
        """Plans and queues geometric trajectory (circle, rectangle, waypoints)."""
        if self.mode == "ESTOP":
            return False, "E-STOP active. Reset required."

        speed = float(params.get("speed_m_s", 0.05))

        if trajectory_type == "circle":
            center = np.array(params.get("center", [0.0, 0.0]), dtype=np.float64)
            radius = float(params.get("radius_m", 0.05))
            cycles = int(params.get("cycles", 1))

            # Connect current pose to circle start smoothly
            theta0 = 0.0
            start_pt = center + np.array([radius * np.cos(theta0), radius * np.sin(theta0)])
            pts_lead = self.planner.plan_point_to_point(self.current_q, start_pt, v_target=speed)
            pts_circ = self.planner.plan_circle(center, radius, speed_m_s=speed, cycles=cycles)

            # Offset time
            lead_duration = pts_lead[-1].t if pts_lead else 0.0
            for p in pts_circ:
                p.t += lead_duration

            full_pts = pts_lead + pts_circ[1:]

        elif trajectory_type == "rectangle":
            center = np.array(params.get("center", [0.0, 0.0]), dtype=np.float64)
            width = float(params.get("width_m", 0.12))
            height = float(params.get("height_m", 0.08))

            c_start = center + np.array([-width/2.0, height/2.0])
            pts_lead = self.planner.plan_point_to_point(self.current_q, c_start, v_target=speed)
            pts_rect = self.planner.plan_rectangle(center, width, height, speed_m_s=speed)

            lead_duration = pts_lead[-1].t if pts_lead else 0.0
            for p in pts_rect:
                p.t += lead_duration
            full_pts = pts_lead + pts_rect[1:]

        elif trajectory_type == "waypoints":
            raw_wps = params.get("waypoints", [])
            if len(raw_wps) < 2:
                return False, "At least two waypoints required"
            wps = [np.array(w, dtype=np.float64) for w in raw_wps]
            full_pts = self.planner.plan_waypoints(wps, speed_m_s=speed)
        else:
            return False, f"Unknown trajectory type: {trajectory_type}"

        val = self.planner.validate_trajectory(full_pts)
        if not val.is_feasible:
            return False, f"Trajectory rejected: {val.violation_message} ({val.violation_code})"

        self.active_trajectory = full_pts
        self.current_traj_index = 0
        self.mode = "MOVING"
        self.active_faults.clear()
        return True, f"{trajectory_type.capitalize()} trajectory accepted ({len(full_pts)} steps, {val.total_duration_s:.1f}s)"

    def request_jog(self, delta_x_m: float, delta_y_m: float, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        """Relative step move in meters."""
        goal = self.current_q + np.array([delta_x_m, delta_y_m])
        return self.request_move(goal, speed_m_s=speed_m_s)

    def pause(self) -> Tuple[bool, str]:
        if self.mode == "MOVING":
            self.mode = "PAUSED"
            self.target_q_dot = np.zeros(2)
            self.target_q_ddot = np.zeros(2)
            return True, "Simulation paused"
        return False, f"Cannot pause in mode {self.mode}"

    def resume(self) -> Tuple[bool, str]:
        if self.mode == "PAUSED":
            self.mode = "MOVING"
            return True, "Simulation resumed"
        return False, f"Cannot resume in mode {self.mode}"

    def stop(self) -> Tuple[bool, str]:
        """Smoothly stops motion and cancels remaining path."""
        self.active_trajectory.clear()
        self.current_traj_index = 0
        self.target_q = self.current_q.copy()
        self.target_q_dot = np.zeros(2)
        self.target_q_ddot = np.zeros(2)
        self.mode = "STOPPED"
        return True, "Motion stopped, queue cleared"

    def estop(self) -> Tuple[bool, str]:
        """Emergency stop: locks simulator into ESTOP state."""
        self.active_trajectory.clear()
        self.current_traj_index = 0
        self.target_q_dot = np.zeros(2)
        self.target_q_ddot = np.zeros(2)
        self.mode = "ESTOP"
        self.active_faults.append("EMERGENCY_STOP_ACTIVE")
        return True, "EMERGENCY STOP TRIGGERED"

    def reset(self) -> Tuple[bool, str]:
        """Resets faults and homes the platform to center [0, 0]."""
        self.active_trajectory.clear()
        self.current_traj_index = 0
        self.active_faults.clear()
        self.current_q = np.zeros(2, dtype=np.float64)
        self.target_q = np.zeros(2, dtype=np.float64)
        self.target_q_dot = np.zeros(2)
        self.target_q_ddot = np.zeros(2)
        self.mode = "IDLE"
        return True, "System reset to home position (0, 0)"

    def update_step(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """
        Advances one step along active trajectory.
        Returns: (target_q, target_q_dot, target_q_ddot, progress_pct)
        """
        if self.mode == "MOVING" and self.active_trajectory:
            if self.current_traj_index < len(self.active_trajectory):
                pt = self.active_trajectory[self.current_traj_index]
                self.target_q = pt.q.copy()
                self.target_q_dot = pt.q_dot.copy()
                self.target_q_ddot = pt.q_ddot.copy()
                self.current_traj_index += 1
                progress = (self.current_traj_index / len(self.active_trajectory)) * 100.0
                return self.target_q, self.target_q_dot, self.target_q_ddot, progress
            else:
                # Finished trajectory
                self.mode = "IDLE"
                self.target_q_dot = np.zeros(2)
                self.target_q_ddot = np.zeros(2)
                self.active_trajectory.clear()
                return self.target_q, self.target_q_dot, self.target_q_ddot, 100.0

        # When IDLE, PAUSED, STOPPED or ESTOP
        return self.target_q, np.zeros(2), np.zeros(2), 0.0
