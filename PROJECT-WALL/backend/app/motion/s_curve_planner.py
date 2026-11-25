"""
Jerk-Limited S-Curve Trajectory Generator & Path Optimization Module for PROJECT W.A.L.L.
Implements:
1. Jerk-Limited 7-Phase S-Curve Profile Generator (Section 9.3)
2. Ramer-Douglas-Peucker (RDP) Polyline Simplification (Section 9.2 & 15.2)
3. Nearest-Neighbor + 2-Opt TSP Contour Ordering (Section 15.1)
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import numpy as np


@dataclass
class SCurveParameters:
    v_max: float = 120.0       # mm/s (0.12 m/s)
    a_max: float = 400.0       # mm/s^2 (0.4 m/s^2)
    j_max: float = 2000.0      # mm/s^3 (2.0 m/s^3)


@dataclass
class TrajectorySample:
    t: float
    s: float
    v: float
    a: float
    j: float


class JerkLimitedSCurve:
    """
    Computes analytical 7-phase Jerk-Limited S-Curve profile for distance D:
    Phase 1: Jerk = +J_max, Accel ramps from 0 to a_limit
    Phase 2: Jerk = 0, Constant accel a_limit
    Phase 3: Jerk = -J_max, Accel ramps from a_limit to 0 (velocity reaches v_limit)
    Phase 4: Jerk = 0, Accel = 0, Constant velocity v_limit
    Phase 5: Jerk = -J_max, Accel ramps from 0 to -a_limit
    Phase 6: Jerk = 0, Constant decel -a_limit
    Phase 7: Jerk = +J_max, Accel ramps from -a_limit to 0 (velocity reaches 0 at target)
    """
    def __init__(self, params: Optional[SCurveParameters] = None):
        self.p = params or SCurveParameters()

    def plan_move(self, distance_mm: float) -> Tuple[float, List[float]]:
        """
        Plans move for distance_mm. Returns total_duration_s and list of phase durations [T1..T7].
        """
        D = abs(distance_mm)
        if D < 1e-6:
            return 0.0, [0.0] * 7

        v_max = self.p.v_max
        a_max = self.p.a_max
        j_max = self.p.j_max

        # Time to reach a_max from jerk: Tj = a_max / j_max
        Tj = a_max / j_max
        # Velocity reached during Tj accel ramp up and down: v_j = a_max * Tj = a_max^2 / j_max
        v_j = a_max * Tj

        # Check if v_max is reachable with a_max:
        if v_max <= v_j:
            # Acceleration phase does not reach a_max
            Tj = math.sqrt(v_max / j_max)
            Ta = 0.0
            v_reached = j_max * (Tj ** 2)
        else:
            # Reaches a_max
            Ta = (v_max - v_j) / a_max
            v_reached = v_max

        # Distance covered during acceleration phase (2 * Tj + Ta)
        # s_acc = v_reached * (Tj + Ta / 2.0)
        s_acc = v_reached * (Tj + 0.5 * Ta)
        s_dec = s_acc

        if D >= 2.0 * s_acc:
            # Profile has constant velocity phase (Trapezoidal in acceleration, reaches v_max)
            Tv = (D - 2.0 * s_acc) / v_reached
        else:
            # Distance is too short to reach v_max, solve for reachable peak velocity
            Tv = 0.0
            # Solve polynomial for reduced peak: D = 2 * v_peak * (Tj + 0.5 * Ta)
            # Simplified formulation:
            v_peak = D / (2.0 * Tj + 1e-6)
            if v_peak < v_j:
                Tj = (D / (2.0 * j_max)) ** (1.0 / 3.0)
                Ta = 0.0
            else:
                Ta = (D - 2.0 * (a_max ** 2 / j_max) * Tj) / (a_max * 2.0)
                Ta = max(0.0, Ta)

        T1 = Tj
        T2 = Ta
        T3 = Tj
        T4 = Tv
        T5 = Tj
        T6 = Ta
        T7 = Tj

        total_time = T1 + T2 + T3 + T4 + T5 + T6 + T7
        return total_time, [T1, T2, T3, T4, T5, T6, T7]

    def sample_at_time(self, t: float, total_time: float, phase_times: List[float], total_dist: float) -> TrajectorySample:
        """Evaluates position s, velocity v, accel a, and jerk j at time t [0..total_time]"""
        if t <= 0.0:
            return TrajectorySample(0.0, 0.0, 0.0, 0.0, 0.0)
        if t >= total_time:
            return TrajectorySample(total_time, total_dist, 0.0, 0.0, 0.0)

        # Numerical integration across the 7 phases
        dt = 0.001
        curr_t = 0.0
        curr_s = 0.0
        curr_v = 0.0
        curr_a = 0.0

        target_t = min(t, total_time)
        steps = int(target_t / dt)
        j_max = self.p.j_max

        # Cumulative phase boundaries
        cum_phases = np.cumsum(phase_times)

        for _ in range(steps):
            # Determine active phase
            if curr_t < cum_phases[0]: # Phase 1
                curr_j = j_max
            elif curr_t < cum_phases[1]: # Phase 2
                curr_j = 0.0
            elif curr_t < cum_phases[2]: # Phase 3
                curr_j = -j_max
            elif curr_t < cum_phases[3]: # Phase 4
                curr_j = 0.0
            elif curr_t < cum_phases[4]: # Phase 5
                curr_j = -j_max
            elif curr_t < cum_phases[5]: # Phase 6
                curr_j = 0.0
            else: # Phase 7
                curr_j = j_max

            curr_a += curr_j * dt
            curr_v = min(self.p.v_max, curr_v + curr_a * dt)
            curr_s += curr_v * dt
            curr_t += dt

        return TrajectorySample(t=t, s=min(curr_s, total_dist), v=max(0.0, curr_v), a=curr_a, j=curr_j)


def ramer_douglas_peucker(points: List[Tuple[float, float]], epsilon_mm: float) -> List[Tuple[float, float]]:
    """
    Ramer-Douglas-Peucker (RDP) Polyline Simplification (Section 9.2 & 15.2):
    Recursively reduces polyline vertices within perpendicular distance threshold epsilon_mm.
    """
    if len(points) <= 2:
        return points

    p_first = np.array(points[0], dtype=np.float64)
    p_last = np.array(points[-1], dtype=np.float64)
    line_vec = p_last - p_first
    line_len = np.linalg.norm(line_vec)

    dmax = 0.0
    index = 0

    for i in range(1, len(points) - 1):
        p = np.array(points[i], dtype=np.float64)
        if line_len < 1e-9:
            d = np.linalg.norm(p - p_first)
        else:
            # Perpendicular distance: |line_vec x (p_first - p)| / |line_vec|
            d = abs(line_vec[0] * (p_first[1] - p[1]) - line_vec[1] * (p_first[0] - p[0])) / line_len

        if d > dmax:
            dmax = d
            index = i

    if dmax > epsilon_mm:
        rec_results1 = ramer_douglas_peucker(points[:index + 1], epsilon_mm)
        rec_results2 = ramer_douglas_peucker(points[index:], epsilon_mm)
        return rec_results1[:-1] + rec_results2
    else:
        return [points[0], points[-1]]


def nearest_neighbor_2opt_tsp(contours: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
    """
    Nearest-Neighbor + 2-Opt TSP Contour Ordering (Section 15.1):
    Minimizes non-printing rapid air-traverse distance between independent print contours.
    """
    n = len(contours)
    if n <= 1:
        return contours

    # Compute entry/exit points for each contour (start at contour[0], exit at contour[-1])
    # 1. Greedy Nearest-Neighbor Tour
    visited = [False] * n
    tour = [0]
    visited[0] = True

    for _ in range(n - 1):
        last_idx = tour[-1]
        last_exit = np.array(contours[last_idx][-1])
        best_dist = float('inf')
        best_candidate = -1

        for cand in range(n):
            if not visited[cand]:
                cand_entry = np.array(contours[cand][0])
                d = float(np.linalg.norm(cand_entry - last_exit))
                if d < best_dist:
                    best_dist = d
                    best_candidate = cand

        tour.append(best_candidate)
        visited[best_candidate] = True

    # 2. 2-Opt Local Search Improvement
    def compute_tour_cost(order):
        cost = 0.0
        for i in range(len(order) - 1):
            c_curr = contours[order[i]][-1]
            c_next = contours[order[i + 1]][0]
            cost += math.hypot(c_next[0] - c_curr[0], c_next[1] - c_curr[1])
        return cost

    improved = True
    iteration = 0
    while improved and iteration < 50:
        improved = False
        iteration += 1
        best_cost = compute_tour_cost(tour)

        for i in range(1, n - 1):
            for j in range(i + 1, n):
                new_tour = tour[:i] + tour[i:j][::-1] + tour[j:]
                new_cost = compute_tour_cost(new_tour)
                if new_cost < best_cost - 1e-4:
                    tour = new_tour
                    best_cost = new_cost
                    improved = True
                    break
            if improved:
                break

    return [contours[idx] for idx in tour]
