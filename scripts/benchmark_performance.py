"""
Benchmark script to measure actual execution timing for CDPR algorithms.
Measures:
- Inverse kinematics and Jacobian calculation time
- Forward kinematics solver convergence time
- Tension solver optimization time
- Trajectory planning time
- Deterministic simulation loop step execution time
"""
import time
import sys
from pathlib import Path
import numpy as np

# Add workspace root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.cdpr.simulation import CDPRSimulation


def run_benchmark():
    sim = CDPRSimulation("config/robot_config.yaml")

    print("=== CDPR Performance & Timing Benchmark ===")

    # 1. Inverse Kinematics & Analytical Jacobian
    N = 10000
    q_test = np.array([0.05, 0.03])
    t0 = time.perf_counter()
    for _ in range(N):
        sim.kin.inverse_kinematics(q_test)
    t1 = time.perf_counter()
    ik_time_us = ((t1 - t0) / N) * 1e6
    print(f"Inverse Kinematics + Jacobian: {ik_time_us:.2f} microseconds per eval ({N} runs)")

    # 2. Forward Kinematics Solver (Levenberg-Marquardt)
    lengths_test = sim.geom.cable_lengths(q_test)
    N_fk = 1000
    t0 = time.perf_counter()
    for _ in range(N_fk):
        sim.kin.forward_kinematics(lengths_test, q_initial=np.zeros(2))
    t1 = time.perf_counter()
    fk_time_us = ((t1 - t0) / N_fk) * 1e6
    print(f"Forward Kinematics Solver:     {fk_time_us:.2f} microseconds per solve ({N_fk} runs)")

    # 3. Tension Allocation Solver (lsq_linear)
    N_ts = 1000
    t0 = time.perf_counter()
    for _ in range(N_ts):
        sim.tension_solver.solve(q_test)
    t1 = time.perf_counter()
    ts_time_us = ((t1 - t0) / N_ts) * 1e6
    print(f"Tension Allocation Solver:    {ts_time_us:.2f} microseconds per solve ({N_ts} runs)")

    # 4. Trajectory Generation (Point-to-Point)
    N_tr = 500
    q_start = np.array([0.0, 0.0])
    q_goal = np.array([0.10, 0.08])
    t0 = time.perf_counter()
    for _ in range(N_tr):
        pts = sim.planner.plan_point_to_point(q_start, q_goal, v_target=0.08)
        sim.planner.validate_trajectory(pts)
    t1 = time.perf_counter()
    tr_time_us = ((t1 - t0) / N_tr) * 1e6
    print(f"Trajectory Plan + Validation:  {tr_time_us:.2f} microseconds per plan ({N_tr} runs)")

    # 5. Full Simulation Step
    N_step = 2000
    sim.controller.request_move(q_goal, speed_m_s=0.08)
    t0 = time.perf_counter()
    for _ in range(N_step):
        sim.step()
    t1 = time.perf_counter()
    step_time_us = ((t1 - t0) / N_step) * 1e6
    max_achievable_hz = 1e6 / step_time_us if step_time_us > 0 else 0
    print(f"Full Simulation Step (Physics):{step_time_us:.2f} microseconds per step ({max_achievable_hz:.0f} Hz max)")


if __name__ == "__main__":
    run_benchmark()
