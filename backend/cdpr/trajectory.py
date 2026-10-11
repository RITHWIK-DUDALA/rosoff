"""
Trajectory planning and path generation engine for 2-DOF planar CDPR.
Supports:
1. Point-to-point trapezoidal profile (bounded velocity and acceleration)
2. Straight-line interpolation
3. Circular paths
4. Rectangular perimeter paths
5. Arbitrary multi-waypoint sequences
6. Comprehensive pre-execution feasibility check:
   Samples along the candidate trajectory and evaluates:
   - Workspace boundaries & platform clearance
   - Cable lengths (positive, unentangled)
   - Cable-length rates and motor RPM limits (< 300 RPM)
   - Static/dynamic tension feasibility (T_min <= T <= T_max)
   - Actuator torque limits (< 0.4 Nm)
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable
import numpy as np
from backend.cdpr.config import RobotConfig
from backend.cdpr.geometry import Geometry
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.tension_solver import TensionSolver
from backend.cdpr.collision import CollisionChecker


@dataclass
class TrajectoryPoint:
    t: float                  # time from start in seconds
    q: np.ndarray             # [x, y] position in meters
    q_dot: np.ndarray         # [vx, vy] velocity in m/s
    q_ddot: np.ndarray        # [ax, ay] acceleration in m/s^2


@dataclass
class TrajectoryValidationResult:
    is_feasible: bool
    total_duration_s: float
    sampled_points_count: int
    max_speed_m_s: float
    max_accel_m_s2: float
    max_cable_rpm: float
    max_tension_N: float
    min_tension_N: float
    max_torque_Nm: float
    violation_code: str       # "OK", "WORKSPACE_LIMIT", "SPEED_LIMIT", "TENSION_INFEASIBLE", "TORQUE_LIMIT"
    violation_message: str


class TrajectoryPlanner:
    def __init__(
        self,
        config: RobotConfig,
        kinematics: Kinematics,
        tension_solver: TensionSolver,
        collision_checker: CollisionChecker
    ):
        self.config = config
        self.kin = kinematics
        self.tension_solver = tension_solver
        self.collision = collision_checker
        self.v_max_nominal = config.motion_limits.nominal_max_speed_m_s  # 0.1 m/s (100 mm/s)
        self.a_max = config.motion_limits.max_accel_m_s2                # 0.5 m/s^2
        self.drum_r = config.actuators.drum_radius_m
        self.max_rpm = config.actuators.max_speed_rpm                   # 300 RPM
        self.max_tau = config.actuators.max_torque_Nm                   # 0.4 Nm
        self.eff = config.actuators.efficiency

    def plan_point_to_point(
        self,
        q_start: np.ndarray,
        q_goal: np.ndarray,
        v_target: Optional[float] = None
    ) -> List[TrajectoryPoint]:
        """
        Generates trapezoidal velocity profile from q_start to q_goal.
        """
        q_0 = np.asarray(q_start, dtype=np.float64).reshape(2)
        q_1 = np.asarray(q_goal, dtype=np.float64).reshape(2)
        diff = q_1 - q_0
        dist = float(np.linalg.norm(diff))

        if dist < 1e-6:
            # Zero distance, return single point at t=0
            return [TrajectoryPoint(t=0.0, q=q_0, q_dot=np.zeros(2), q_ddot=np.zeros(2))]

        direction = diff / dist
        v_peak = min(self.v_max_nominal, v_target if v_target and v_target > 0 else self.v_max_nominal)
        a = self.a_max

        # Distance required to accelerate to v_peak and decelerate to 0
        d_accel = (v_peak ** 2) / (2.0 * a)

        if 2.0 * d_accel > dist:
            # Triangular profile (cannot reach v_peak)
            v_peak = np.sqrt(a * dist)
            t_acc = v_peak / a
            t_cruise = 0.0
            t_total = 2.0 * t_acc
        else:
            # Trapezoidal profile
            t_acc = v_peak / a
            d_cruise = dist - 2.0 * d_accel
            t_cruise = d_cruise / v_peak
            t_total = 2.0 * t_acc + t_cruise

        dt = self.config.simulation.timestep_s
        n_steps = max(2, int(np.ceil(t_total / dt)) + 1)
        time_grid = np.linspace(0.0, t_total, n_steps)

        points = []
        for t in time_grid:
            if t <= t_acc:
                # Accelerating phase
                s = 0.5 * a * (t ** 2)
                s_dot = a * t
                s_ddot = a
            elif t <= (t_acc + t_cruise):
                # Constant speed cruise phase
                t_c = t - t_acc
                s = d_accel + v_peak * t_c
                s_dot = v_peak
                s_ddot = 0.0
            else:
                # Decelerating phase
                t_d = t - (t_acc + t_cruise)
                s = dist - 0.5 * a * ((t_acc - t_d) ** 2)
                s_dot = v_peak - a * t_d
                s_ddot = -a

            # Clamp s to [0, dist]
            s = min(dist, max(0.0, s))
            s_dot = max(0.0, s_dot)

            q_curr = q_0 + s * direction
            v_curr = s_dot * direction
            a_curr = s_ddot * direction

            points.append(TrajectoryPoint(t=float(t), q=q_curr, q_dot=v_curr, q_ddot=a_curr))

        # Ensure final point is exact
        points[-1].q = q_1
        points[-1].q_dot = np.zeros(2)
        points[-1].q_ddot = np.zeros(2)
        return points

    def plan_circle(
        self,
        center: np.ndarray,
        radius_m: float,
        speed_m_s: float = 0.05,
        cycles: int = 1
    ) -> List[TrajectoryPoint]:
        """
        Generates circular trajectory centered at [cx, cy].
        """
        center = np.asarray(center, dtype=np.float64).reshape(2)
        circumference = 2.0 * np.pi * radius_m
        speed = min(self.v_max_nominal, max(0.01, speed_m_s))
        omega = speed / radius_m
        t_cycle = circumference / speed
        t_total = t_cycle * cycles

        dt = self.config.simulation.timestep_s
        n_steps = int(np.ceil(t_total / dt)) + 1
        time_grid = np.linspace(0.0, t_total, n_steps)

        points = []
        for t in time_grid:
            theta = omega * t
            # Position: [cx + r*cos(theta), cy + r*sin(theta)]
            q = center + np.array([radius_m * np.cos(theta), radius_m * np.sin(theta)])
            # Velocity: [-r*omega*sin(theta), r*omega*cos(theta)]
            q_dot = np.array([-radius_m * omega * np.sin(theta), radius_m * omega * np.cos(theta)])
            # Acceleration: [-r*omega^2*cos(theta), -r*omega^2*sin(theta)]
            q_ddot = np.array([-radius_m * (omega**2) * np.cos(theta), -radius_m * (omega**2) * np.sin(theta)])

            points.append(TrajectoryPoint(t=float(t), q=q, q_dot=q_dot, q_ddot=q_ddot))

        return points

    def plan_rectangle(
        self,
        center: np.ndarray,
        width_m: float,
        height_m: float,
        speed_m_s: float = 0.05
    ) -> List[TrajectoryPoint]:
        """
        Generates rectangular path around center.
        Corners: Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left -> Top-Left.
        """
        cx, cy = center[0], center[1]
        w2, h2 = width_m / 2.0, height_m / 2.0
        c1 = np.array([cx - w2, cy + h2])
        c2 = np.array([cx + w2, cy + h2])
        c3 = np.array([cx + w2, cy - h2])
        c4 = np.array([cx - w2, cy - h2])

        waypoints = [c1, c2, c3, c4, c1]
        return self.plan_waypoints(waypoints, speed_m_s=speed_m_s)

    def plan_waypoints(
        self,
        waypoints: List[np.ndarray],
        speed_m_s: float = 0.05
    ) -> List[TrajectoryPoint]:
        """
        Chains straight segments through waypoints.
        """
        if len(waypoints) < 2:
            raise ValueError("Must provide at least 2 waypoints")

        full_points = []
        current_time_offset = 0.0

        for i in range(len(waypoints) - 1):
            segment = self.plan_point_to_point(waypoints[i], waypoints[i+1], v_target=speed_m_s)
            for p in segment:
                p.t += current_time_offset
            if full_points:
                # Avoid duplicate point at segment boundary
                segment = segment[1:]
            full_points.extend(segment)
            if full_points:
                current_time_offset = full_points[-1].t

        return full_points

    def validate_trajectory(self, trajectory: List[TrajectoryPoint]) -> TrajectoryValidationResult:
        """
        Evaluates full feasibility across all trajectory points.
        Checks:
        1. Collision & boundary violations
        2. Actuator RPM limits (<= 300 RPM)
        3. Static & dynamic tension allocation feasibility
        4. Motor torque limits (<= 0.4 Nm)
        """
        if not trajectory:
            return TrajectoryValidationResult(
                is_feasible=False,
                total_duration_s=0.0,
                sampled_points_count=0,
                max_speed_m_s=0.0,
                max_accel_m_s2=0.0,
                max_cable_rpm=0.0,
                max_tension_N=0.0,
                min_tension_N=0.0,
                max_torque_Nm=0.0,
                violation_code="EMPTY_TRAJECTORY",
                violation_message="Trajectory has zero points"
            )

        max_v = 0.0
        max_a = 0.0
        max_rpm = 0.0
        max_t = 0.0
        min_t = float("inf")
        max_tau = 0.0

        m = self.config.platform.mass_kg

        for pt in trajectory:
            v_mag = float(np.linalg.norm(pt.q_dot))
            a_mag = float(np.linalg.norm(pt.q_ddot))
            max_v = max(max_v, v_mag)
            max_a = max(max_a, a_mag)

            # 1. Collision & Workspace check
            col = self.collision.check(pt.q)
            if not col.is_safe:
                return TrajectoryValidationResult(
                    is_feasible=False,
                    total_duration_s=trajectory[-1].t,
                    sampled_points_count=len(trajectory),
                    max_speed_m_s=max_v,
                    max_accel_m_s2=max_a,
                    max_cable_rpm=max_rpm,
                    max_tension_N=max_t,
                    min_tension_N=min_t if min_t != float("inf") else 0.0,
                    max_torque_Nm=max_tau,
                    violation_code="WORKSPACE_LIMIT",
                    violation_message=f"At t={pt.t:.2f}s, q={pt.q*1000}mm: {col.violation_message}"
                )

            # 2. Kinematics & Cable-length rates
            ik = self.kin.inverse_kinematics(pt.q, q_dot=pt.q_dot)
            if not ik.is_valid:
                return TrajectoryValidationResult(
                    is_feasible=False,
                    total_duration_s=trajectory[-1].t,
                    sampled_points_count=len(trajectory),
                    max_speed_m_s=max_v,
                    max_accel_m_s2=max_a,
                    max_cable_rpm=max_rpm,
                    max_tension_N=max_t,
                    min_tension_N=min_t if min_t != float("inf") else 0.0,
                    max_torque_Nm=max_tau,
                    violation_code="KINEMATIC_ERROR",
                    violation_message=f"At t={pt.t:.2f}s: {ik.message}"
                )

            # 3. Motor RPM check
            cable_rates = ik.lengths_dot
            # omega = L_dot / r
            rpms = np.abs(cable_rates / self.drum_r) * (60.0 / (2.0 * np.pi))
            current_max_rpm = float(np.max(rpms))
            max_rpm = max(max_rpm, current_max_rpm)
            if current_max_rpm > self.max_rpm + 1e-3:
                return TrajectoryValidationResult(
                    is_feasible=False,
                    total_duration_s=trajectory[-1].t,
                    sampled_points_count=len(trajectory),
                    max_speed_m_s=max_v,
                    max_accel_m_s2=max_a,
                    max_cable_rpm=max_rpm,
                    max_tension_N=max_t,
                    min_tension_N=min_t if min_t != float("inf") else 0.0,
                    max_torque_Nm=max_tau,
                    violation_code="SPEED_LIMIT",
                    violation_message=f"At t={pt.t:.2f}s: Motor speed {current_max_rpm:.1f} RPM exceeds limit {self.max_rpm:.1f} RPM"
                )

            # 4. Tension allocation check under dynamic wrench
            # F_dem = - M * q_ddot
            F_dem = - m * pt.q_ddot
            tension_res = self.tension_solver.solve(pt.q, F_ext=F_dem)
            if not tension_res.is_feasible:
                return TrajectoryValidationResult(
                    is_feasible=False,
                    total_duration_s=trajectory[-1].t,
                    sampled_points_count=len(trajectory),
                    max_speed_m_s=max_v,
                    max_accel_m_s2=max_a,
                    max_cable_rpm=max_rpm,
                    max_tension_N=max_t,
                    min_tension_N=min_t if min_t != float("inf") else 0.0,
                    max_torque_Nm=max_tau,
                    violation_code="TENSION_INFEASIBLE",
                    violation_message=f"At t={pt.t:.2f}s: {tension_res.message}"
                )

            tensions = tension_res.tensions
            max_t = max(max_t, float(np.max(tensions)))
            min_t = min(min_t, float(np.min(tensions)))

            # 5. Actuator torque check: tau = (T * r) / eff
            torques = (tensions * self.drum_r) / self.eff
            current_max_tau = float(np.max(torques))
            max_tau = max(max_tau, current_max_tau)
            if current_max_tau > self.max_tau + 1e-4:
                return TrajectoryValidationResult(
                    is_feasible=False,
                    total_duration_s=trajectory[-1].t,
                    sampled_points_count=len(trajectory),
                    max_speed_m_s=max_v,
                    max_accel_m_s2=max_a,
                    max_cable_rpm=max_rpm,
                    max_tension_N=max_t,
                    min_tension_N=min_t if min_t != float("inf") else 0.0,
                    max_torque_Nm=max_tau,
                    violation_code="TORQUE_LIMIT",
                    violation_message=f"At t={pt.t:.2f}s: Motor torque {current_max_tau:.3f} Nm exceeds limit {self.max_tau:.3f} Nm"
                )

        return TrajectoryValidationResult(
            is_feasible=True,
            total_duration_s=trajectory[-1].t,
            sampled_points_count=len(trajectory),
            max_speed_m_s=max_v,
            max_accel_m_s2=max_a,
            max_cable_rpm=max_rpm,
            max_tension_N=max_t,
            min_tension_N=min_t if min_t != float("inf") else 0.0,
            max_torque_Nm=max_tau,
            violation_code="OK",
            violation_message="Trajectory fully feasible within all physical constraints"
        )
