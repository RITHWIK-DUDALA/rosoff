"""
Offline engineering validation script for CDPR.
Uses the actual simulation and physics engine to generate 5 validation plots:
1. docs/workspace_feasibility.png: Heatmap of static tension condition number across XY plane.
2. docs/cable_lengths_vs_position.png: Cable lengths L1..L4 along a diagonal cross-section.
3. docs/motor_rpm_trajectory.png: Actuator RPM profile during a 100 mm/s representative move.
4. docs/cable_tensions_time.png: Dynamic tensions T1..T4 during trajectory execution.
5. docs/tracking_error_trajectory.png: Platform position tracking error vs time.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from backend.cdpr.config import load_robot_config
from backend.cdpr.geometry import Geometry
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.tension_solver import TensionSolver
from backend.cdpr.collision import CollisionChecker
from backend.cdpr.trajectory import TrajectoryPlanner
from backend.cdpr.simulation import CDPRSimulation


def generate_all_validation_plots():
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    config = load_robot_config("robot_config.yaml")
    geom = Geometry(config)
    kin = Kinematics(geom)
    ts = TensionSolver(kin)
    col = CollisionChecker(geom)

    # ----------------------------------------------------
    # 1. Workspace Feasibility & Jacobian Condition Number Map
    # ----------------------------------------------------
    print("Generating Plot 1: Workspace Feasibility...")
    xs = np.linspace(-0.18, 0.18, 80)
    ys = np.linspace(-0.14, 0.14, 60)
    X, Y = np.meshgrid(xs, ys)
    cond_grid = np.zeros_like(X)
    feas_grid = np.zeros_like(X)

    for i in range(len(ys)):
        for j in range(len(xs)):
            q = np.array([xs[j], ys[i]])
            ik = kin.inverse_kinematics(q)
            if ik.is_valid:
                cond_grid[i, j] = ik.condition_number
                t_res = ts.solve(q)
                feas_grid[i, j] = 1.0 if t_res.is_feasible else 0.0
            else:
                cond_grid[i, j] = np.nan
                feas_grid[i, j] = 0.0

    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    c = ax.contourf(X * 1000, Y * 1000, cond_grid, levels=30, cmap="viridis")
    cbar = fig.colorbar(c, ax=ax)
    cbar.set_label("Jacobian Condition Number $\\kappa(J_L)$")

    # Overlay frame boundary (500x400 mm)
    fw_mm, fh_mm = config.frame.width_m * 1000, config.frame.height_m * 1000
    ax.plot([-fw_mm/2, fw_mm/2, fw_mm/2, -fw_mm/2, -fw_mm/2],
            [-fh_mm/2, -fh_mm/2, fh_mm/2, fh_mm/2, -fh_mm/2],
            'r--', label="Physical Frame Outer Limit (500x400 mm)")

    # Overlay safe workspace
    ax.plot([-180, 180, 180, -180, -180], [-140, -140, 140, 140, -140],
            'c-', lw=2, label="Safe Platform Workspace Limit")

    ax.set_title("CDPR Workspace Kinematic Condition Number Map")
    ax.set_xlabel("X Position (mm)")
    ax.set_ylabel("Y Position (mm)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(docs_dir / "workspace_feasibility.png")
    plt.close(fig)

    # ----------------------------------------------------
    # 2. Cable Lengths vs Position across Diagonal
    # ----------------------------------------------------
    print("Generating Plot 2: Cable Lengths vs Position...")
    diag_s = np.linspace(-0.15, 0.15, 100)
    lengths_c1, lengths_c2, lengths_c3, lengths_c4 = [], [], [], []

    for s in diag_s:
        q = np.array([s, s * (140.0 / 180.0)]) # Diagonal trajectory
        L = geom.cable_lengths(q)
        lengths_c1.append(L[0] * 1000)
        lengths_c2.append(L[1] * 1000)
        lengths_c3.append(L[2] * 1000)
        lengths_c4.append(L[3] * 1000)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ax.plot(diag_s * 1000, lengths_c1, label="Cable 1 (Top-Left)", color="#d95f02", lw=1.8)
    ax.plot(diag_s * 1000, lengths_c2, label="Cable 2 (Top-Right)", color="#1b9e77", lw=1.8)
    ax.plot(diag_s * 1000, lengths_c3, label="Cable 3 (Bottom-Right)", color="#7570b3", lw=1.8)
    ax.plot(diag_s * 1000, lengths_c4, label="Cable 4 (Bottom-Left)", color="#e7298a", lw=1.8)

    ax.set_title("Analytic Cable Length Variation Across Workspace Diagonal")
    ax.set_xlabel("Position along X Diagonal Axis (mm)")
    ax.set_ylabel("Cable Length (mm)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(docs_dir / "cable_lengths_vs_position.png")
    plt.close(fig)

    # ----------------------------------------------------
    # 3, 4, 5. Trajectory Simulation Data: RPM, Tension, Tracking Error
    # ----------------------------------------------------
    print("Generating Plots 3-5: Trajectory Simulation Telemetry...")
    sim = CDPRSimulation("robot_config.yaml")
    # Command smooth circle trajectory
    sim.controller.request_trajectory("circle", {"radius_m": 0.05, "speed_m_s": 0.08, "center": [0, 0], "cycles": 1})

    t_arr, rpms_arr, tensions_arr, err_arr = [], [], [], []

    for _ in range(500):
        sim.step()
        telem = sim.latest_telemetry
        t_arr.append(telem.sim_time_s)
        rpms_arr.append(telem.motor_speeds_rpm)
        tensions_arr.append(telem.cable_tensions_N)
        err_arr.append(telem.tracking_error_mm)
        if sim.controller.mode == "IDLE":
            break

    rpms_arr = np.array(rpms_arr)
    tensions_arr = np.array(tensions_arr)

    # Plot 3: Motor RPMs
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    for k in range(4):
        ax.plot(t_arr, rpms_arr[:, k], label=f"Motor {k+1} RPM", lw=1.5)
    ax.axhline(300.0, color='r', linestyle='--', label="Provisional Limit (+300 RPM)")
    ax.axhline(-300.0, color='r', linestyle='--', label="Provisional Limit (-300 RPM)")
    ax.set_title("Motor Speed (RPM) During Circular Trajectory (R=50 mm, V=80 mm/s)")
    ax.set_xlabel("Simulation Time (s)")
    ax.set_ylabel("Motor Speed (RPM)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(docs_dir / "motor_rpm_trajectory.png")
    plt.close(fig)

    # Plot 4: Dynamic Cable Tensions
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    for k in range(4):
        ax.plot(t_arr, tensions_arr[:, k], label=f"Cable {k+1} Tension", lw=1.5)
    ax.axhline(2.0, color='orange', linestyle=':', label="Min Operating Tension (2 N)")
    ax.axhline(36.0, color='red', linestyle='--', label="Actuator Torque Cap (36 N)")
    ax.set_title("Dynamic Cable Tensions During Trajectory Execution")
    ax.set_xlabel("Simulation Time (s)")
    ax.set_ylabel("Cable Tension (N)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(docs_dir / "cable_tensions_time.png")
    plt.close(fig)

    # Plot 5: Tracking Error
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.plot(t_arr, err_arr, color="#e6550d", lw=1.8, label="Tracking Error ||q - q_ref||")
    ax.set_title("Kinematic Tracking Error Over Time")
    ax.set_xlabel("Simulation Time (s)")
    ax.set_ylabel("Position Tracking Error (mm)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(docs_dir / "tracking_error_trajectory.png")
    plt.close(fig)

    print("All 5 validation plots generated successfully into docs/")


if __name__ == "__main__":
    generate_all_validation_plots()
