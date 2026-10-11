"""
Configuration loader and validator for the Cable-Driven Parallel Robot (CDPR).
Strictly validates robot_config.yaml ensuring physical feasibility and completeness.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple
import yaml
import numpy as np


class ConfigValidationError(ValueError):
    """Raised when robot configuration parameters fail validation."""
    pass


@dataclass
class AnchorConfig:
    c1: np.ndarray
    c2: np.ndarray
    c3: np.ndarray
    c4: np.ndarray

    def as_array(self) -> np.ndarray:
        """Returns 4x2 matrix of [x, y] coordinates in meters."""
        return np.vstack([self.c1[:2], self.c2[:2], self.c3[:2], self.c4[:2]])


@dataclass
class PlatformConfig:
    width_m: float
    height_m: float
    thickness_m: float
    mass_kg: float
    inertia_z_kg_m2: float
    attachments: AnchorConfig

    def attachments_array(self) -> np.ndarray:
        """Returns 4x2 matrix of local attachment [x, y] coordinates in meters."""
        return self.attachments.as_array()


@dataclass
class FrameConfig:
    width_m: float
    height_m: float
    depth_m: float
    anchors: AnchorConfig

    def anchors_array(self) -> np.ndarray:
        """Returns 4x2 matrix of anchor [x, y] coordinates in meters."""
        return self.anchors.as_array()


@dataclass
class CableConfig:
    count: int
    model: str
    min_tension_N: float
    max_tension_N: float
    elastic_modulus_Pa: float
    diameter_m: float


@dataclass
class ActuatorConfig:
    count: int
    drum_radius_m: float
    drum_inertia_kg_m2: float
    max_speed_rpm: float
    max_torque_Nm: float
    efficiency: float
    control_bandwidth_hz: float

    @property
    def max_speed_rad_s(self) -> float:
        return self.max_speed_rpm * (2.0 * np.pi / 60.0)

    @property
    def max_cable_speed_m_s(self) -> float:
        """Ideal maximum linear cable velocity: v = omega * r"""
        return self.max_speed_rad_s * self.drum_radius_m

    @property
    def max_cable_force_from_motor_N(self) -> float:
        """Maximum tension motor can sustain: T = (tau * efficiency) / r"""
        return (self.max_torque_Nm * self.efficiency) / self.drum_radius_m


@dataclass
class MotionLimits:
    nominal_max_speed_m_s: float
    max_accel_m_s2: float
    max_jerk_m_s3: float


@dataclass
class WorkspaceConfig:
    safety_margin_m: float
    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float


@dataclass
class SolverTolerances:
    fk_tol: float
    fk_max_iter: int
    tension_tol: float
    tension_max_iter: int
    equilibrium_residual_tol: float


@dataclass
class SimulationConfig:
    timestep_s: float
    telemetry_rate_hz: int
    solver_tolerances: SolverTolerances


@dataclass
class RobotConfig:
    raw_dict: dict
    frame: FrameConfig
    platform: PlatformConfig
    cables: CableConfig
    actuators: ActuatorConfig
    motion_limits: MotionLimits
    workspace: WorkspaceConfig
    simulation: SimulationConfig
    operating_plane: str = "horizontal"


def load_robot_config(config_path: str | Path) -> RobotConfig:
    """
    Loads and validates the YAML robot configuration file.
    Rejects missing, malformed, or physically invalid values.
    """
    path = Path(config_path)
    if not path.is_file():
        raise ConfigValidationError(f"Configuration file not found: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Malformed YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigValidationError("Configuration root must be a YAML mapping.")

    # Validate coordinate system
    coord = data.get("coordinate_system", {})
    if coord.get("origin") != "center_of_frame":
        raise ConfigValidationError("coordinate_system.origin must be 'center_of_frame'")
    if coord.get("plane") != "horizontal":
        raise ConfigValidationError("coordinate_system.plane must be 'horizontal'")

    # Validate frame
    frame_dict = data.get("frame")
    if not frame_dict:
        raise ConfigValidationError("Missing 'frame' section in config")

    fw = float(frame_dict.get("width_m", 0.0))
    fh = float(frame_dict.get("height_m", 0.0))
    fd = float(frame_dict.get("depth_m", 0.0))
    if fw <= 0.0 or fh <= 0.0 or fd <= 0.0:
        raise ConfigValidationError(f"Frame dimensions must be strictly positive: {fw}, {fh}, {fd}")

    anchors_dict = frame_dict.get("anchors")
    if not anchors_dict or len(anchors_dict) != 4:
        raise ConfigValidationError("Frame must have exactly 4 anchors (C1..C4)")

    c_keys = ["C1", "C2", "C3", "C4"]
    parsed_anchors = {}
    for k in c_keys:
        val = anchors_dict.get(k)
        if not val or len(val) < 2:
            raise ConfigValidationError(f"Anchor {k} must have [x, y, z] coordinates")
        arr = np.array(val, dtype=np.float64)
        parsed_anchors[k] = arr

    frame_config = FrameConfig(
        width_m=fw,
        height_m=fh,
        depth_m=fd,
        anchors=AnchorConfig(
            c1=parsed_anchors["C1"],
            c2=parsed_anchors["C2"],
            c3=parsed_anchors["C3"],
            c4=parsed_anchors["C4"],
        ),
    )

    # Validate platform
    plat_dict = data.get("platform")
    if not plat_dict:
        raise ConfigValidationError("Missing 'platform' section in config")

    pw = float(plat_dict.get("width_m", 0.0))
    ph = float(plat_dict.get("height_m", 0.0))
    pt = float(plat_dict.get("thickness_m", 0.0))
    pmass = float(plat_dict.get("mass_kg", 0.0))
    pinertia = float(plat_dict.get("inertia_z_kg_m2", 0.0))

    if pw <= 0.0 or ph <= 0.0 or pt <= 0.0 or pmass <= 0.0:
        raise ConfigValidationError(f"Platform physical properties must be strictly positive: {pw}, {ph}, {pmass}")

    if pw >= fw or ph >= fh:
        raise ConfigValidationError("Platform dimensions cannot exceed frame dimensions")

    plat_att_dict = plat_dict.get("attachments")
    if not plat_att_dict or len(plat_att_dict) != 4:
        raise ConfigValidationError("Platform must have exactly 4 attachments (C1..C4)")

    parsed_attachments = {}
    for k in c_keys:
        val = plat_att_dict.get(k)
        if not val or len(val) < 2:
            raise ConfigValidationError(f"Platform attachment {k} must have [x, y, z]")
        parsed_attachments[k] = np.array(val, dtype=np.float64)

    platform_config = PlatformConfig(
        width_m=pw,
        height_m=ph,
        thickness_m=pt,
        mass_kg=pmass,
        inertia_z_kg_m2=pinertia,
        attachments=AnchorConfig(
            c1=parsed_attachments["C1"],
            c2=parsed_attachments["C2"],
            c3=parsed_attachments["C3"],
            c4=parsed_attachments["C4"],
        ),
    )

    # Validate cables
    cables_dict = data.get("cables")
    if not cables_dict:
        raise ConfigValidationError("Missing 'cables' section in config")
    cable_count = int(cables_dict.get("count", 0))
    if cable_count != 4:
        raise ConfigValidationError("Cable count must be exactly 4 for 4-cable planar robot")

    t_min = float(cables_dict.get("min_tension_N", -1.0))
    t_max = float(cables_dict.get("max_tension_N", -1.0))
    if t_min < 0.0:
        raise ConfigValidationError("min_tension_N cannot be negative (unilateral constraint)")
    if t_max <= t_min:
        raise ConfigValidationError(f"max_tension_N ({t_max}) must be strictly greater than min_tension_N ({t_min})")

    cable_config = CableConfig(
        count=cable_count,
        model=str(cables_dict.get("model", "rigid_massless_unilateral")),
        min_tension_N=t_min,
        max_tension_N=t_max,
        elastic_modulus_Pa=float(cables_dict.get("elastic_modulus_Pa", 1.0e11)),
        diameter_m=float(cables_dict.get("diameter_m", 0.001)),
    )

    # Validate actuators
    act_dict = data.get("actuators")
    if not act_dict:
        raise ConfigValidationError("Missing 'actuators' section in config")

    r_drum = float(act_dict.get("drum_radius_m", 0.0))
    rpm_max = float(act_dict.get("max_speed_rpm", 0.0))
    tau_max = float(act_dict.get("max_torque_Nm", 0.0))
    eff = float(act_dict.get("efficiency", 0.0))

    if r_drum <= 0.0:
        raise ConfigValidationError(f"Actuator drum radius must be positive: {r_drum}")
    if rpm_max <= 0.0:
        raise ConfigValidationError(f"Actuator max RPM must be positive: {rpm_max}")
    if tau_max <= 0.0:
        raise ConfigValidationError(f"Actuator max torque must be positive: {tau_max}")
    if not (0.0 < eff <= 1.0):
        raise ConfigValidationError(f"Actuator efficiency must be in (0.0, 1.0]: {eff}")

    actuator_config = ActuatorConfig(
        count=int(act_dict.get("count", 4)),
        drum_radius_m=r_drum,
        drum_inertia_kg_m2=float(act_dict.get("drum_inertia_kg_m2", 1e-5)),
        max_speed_rpm=rpm_max,
        max_torque_Nm=tau_max,
        efficiency=eff,
        control_bandwidth_hz=float(act_dict.get("control_bandwidth_hz", 50.0)),
    )

    # Motion limits
    mot_dict = data.get("motion_limits", {})
    nom_v = float(mot_dict.get("nominal_max_speed_m_s", 0.0))
    max_a = float(mot_dict.get("max_accel_m_s2", 0.0))
    max_j = float(mot_dict.get("max_jerk_m_s3", 0.0))
    if nom_v <= 0.0 or max_a <= 0.0 or max_j <= 0.0:
        raise ConfigValidationError("Motion limits (speed, accel, jerk) must be strictly positive")

    motion_limits = MotionLimits(
        nominal_max_speed_m_s=nom_v,
        max_accel_m_s2=max_a,
        max_jerk_m_s3=max_j,
    )

    # Workspace
    ws_dict = data.get("workspace", {})
    margin = float(ws_dict.get("safety_margin_m", 0.0))
    xmin = float(ws_dict.get("x_min_m", 0.0))
    xmax = float(ws_dict.get("x_max_m", 0.0))
    ymin = float(ws_dict.get("y_min_m", 0.0))
    ymax = float(ws_dict.get("y_max_m", 0.0))

    if xmin >= xmax or ymin >= ymax:
        raise ConfigValidationError(f"Invalid workspace min/max bounds: x[{xmin}, {xmax}], y[{ymin}, {ymax}]")

    # Platform outer footprint check at boundary
    if (xmax + pw / 2.0) > (fw / 2.0) or (abs(xmin) + pw / 2.0) > (fw / 2.0):
        raise ConfigValidationError("Workspace bounds allow platform footprint to collide with frame X boundaries")
    if (ymax + ph / 2.0) > (fh / 2.0) or (abs(ymin) + ph / 2.0) > (fh / 2.0):
        raise ConfigValidationError("Workspace bounds allow platform footprint to collide with frame Y boundaries")

    workspace_config = WorkspaceConfig(
        safety_margin_m=margin,
        x_min_m=xmin,
        x_max_m=xmax,
        y_min_m=ymin,
        y_max_m=ymax,
    )

    # Simulation settings
    sim_dict = data.get("simulation", {})
    dt = float(sim_dict.get("timestep_s", 0.0))
    if dt <= 0.0 or dt > 0.1:
        raise ConfigValidationError(f"Timestep must be between 0.0 and 0.1s, got {dt}")
    telem_hz = int(sim_dict.get("telemetry_rate_hz", 30))

    tols_dict = sim_dict.get("solver_tolerances", {})
    solver_tols = SolverTolerances(
        fk_tol=float(tols_dict.get("fk_tol", 1e-7)),
        fk_max_iter=int(tols_dict.get("fk_max_iter", 50)),
        tension_tol=float(tols_dict.get("tension_tol", 1e-5)),
        tension_max_iter=int(tols_dict.get("tension_max_iter", 100)),
        equilibrium_residual_tol=float(tols_dict.get("equilibrium_residual_tol", 0.01)),
    )

    simulation_config = SimulationConfig(
        timestep_s=dt,
        telemetry_rate_hz=telem_hz,
        solver_tolerances=solver_tols,
    )

    return RobotConfig(
        raw_dict=data,
        frame=frame_config,
        platform=platform_config,
        cables=cable_config,
        actuators=actuator_config,
        motion_limits=motion_limits,
        workspace=workspace_config,
        simulation=simulation_config,
        operating_plane="horizontal",
    )
