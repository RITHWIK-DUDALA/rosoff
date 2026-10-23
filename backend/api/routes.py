"""
REST API routes for CDPR digital twin and hardware integration platform.
Endpoints:
- GET  /health
- GET  /config
- GET  /state
- GET  /workspace
- GET  /diagnostics
- GET  /hardware/profile
- GET  /hardware/status
- POST /command/move
- POST /command/jog
- POST /command/pause
- POST /command/resume
- POST /command/stop
- POST /command/reset
- POST /command/estop
- POST /command/trajectory
- POST /mode
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np

from backend.cdpr.hardware.driver_base import OperatingMode, MeasurementProvenance, HomingState
from backend.cdpr.hardware.simulator_driver import SimulatorDriver
from backend.cdpr.hardware.hardware_driver import HardwareDriver

router = APIRouter()


class MoveCommand(BaseModel):
    x_mm: float = Field(..., description="Target X coordinate in mm")
    y_mm: float = Field(..., description="Target Y coordinate in mm")
    speed_mm_s: Optional[float] = Field(None, description="Nominal trajectory speed in mm/s (<= 100 mm/s)")


class JogCommand(BaseModel):
    delta_x_mm: float = Field(..., description="Relative delta X in mm")
    delta_y_mm: float = Field(..., description="Relative delta Y in mm")
    speed_mm_s: Optional[float] = Field(None, description="Jog speed in mm/s")


class TrajectoryCommand(BaseModel):
    type: str = Field(..., description="Trajectory shape: 'circle', 'rectangle', 'waypoints'")
    params: Dict[str, Any] = Field(default_factory=dict, description="Shape parameters")


class ModeRequest(BaseModel):
    mode: str = Field(..., description="Operating mode: 'SIMULATION' or 'HARDWARE'")


# Global driver & simulation instances
_sim_instance = None
_simulator_driver: Optional[SimulatorDriver] = None
_hardware_driver: Optional[HardwareDriver] = None
_active_mode: OperatingMode = OperatingMode.SIMULATION


def set_sim_instance(sim):
    global _sim_instance, _simulator_driver, _hardware_driver, _active_mode
    _sim_instance = sim
    _simulator_driver = SimulatorDriver(sim)
    _hardware_driver = HardwareDriver(sim.config)
    _active_mode = OperatingMode.SIMULATION


def get_sim():
    if _sim_instance is None:
        raise HTTPException(status_code=500, detail="Simulation engine not initialized")
    return _sim_instance


def get_active_driver():
    global _active_mode, _simulator_driver, _hardware_driver
    if _active_mode == OperatingMode.SIMULATION or _simulator_driver is None:
        return _simulator_driver
    return _hardware_driver


@router.get("/health")
def health(sim=Depends(get_sim)):
    return {
        "status": "healthy",
        "sim_time_s": sim.sim_time,
        "mode": sim.controller.mode,
        "operating_mode": _active_mode.value,
        "controller_mode": sim.controller.mode,
        "faults": sim.controller.active_faults,
        "driver": get_active_driver().__class__.__name__ if get_active_driver() else "None",
    }


@router.get("/config")
def get_config(sim=Depends(get_sim)):
    return sim.config.raw_dict


@router.get("/state")
def get_state(sim=Depends(get_sim)):
    if sim.latest_telemetry is None:
        raise HTTPException(status_code=503, detail="Telemetry not yet computed")
    d = sim.latest_telemetry.to_dict()
    d["operating_mode"] = _active_mode.value
    return d


@router.get("/hardware/profile")
def get_hardware_profile(sim=Depends(get_sim)):
    if _hardware_driver is None:
        raise HTTPException(status_code=500, detail="Hardware driver not initialized")
    return _hardware_driver.get_status()


@router.get("/hardware/status")
def get_hardware_status(sim=Depends(get_sim)):
    if _hardware_driver is None:
        raise HTTPException(status_code=500, detail="Hardware driver not initialized")
    return _hardware_driver.get_status()


@router.post("/mode")
def set_operating_mode(req: ModeRequest, sim=Depends(get_sim)):
    global _active_mode, _hardware_driver, _simulator_driver
    target_mode = req.mode.upper().strip()

    if target_mode == "SIMULATION":
        _active_mode = OperatingMode.SIMULATION
        sim.operating_mode = OperatingMode.SIMULATION.value
        return {
            "status": "accepted",
            "operating_mode": _active_mode.value,
            "message": "Switched to safe offline simulation mode."
        }
    elif target_mode == "HARDWARE":
        # Check hardware verification prerequisites
        status = _hardware_driver.get_status()
        if not status["hardware_ready"]:
            missing = status.get("missing_prerequisites", [])
            _active_mode = OperatingMode.HARDWARE_DISABLED
            sim.operating_mode = OperatingMode.HARDWARE_DISABLED.value
            return {
                "status": "rejected_unverified",
                "operating_mode": OperatingMode.HARDWARE_DISABLED.value,
                "message": f"Hardware motion strictly blocked. Missing: {'; '.join(missing)}",
                "missing_prerequisites": missing
            }
        else:
            _active_mode = OperatingMode.HARDWARE
            sim.operating_mode = OperatingMode.HARDWARE.value
            return {
                "status": "accepted",
                "operating_mode": _active_mode.value,
                "message": "Switched to hardware commissioning mode. Motor torque remains SAFE DISABLED until explicit arming."
            }
    else:
        raise HTTPException(status_code=400, detail=f"Invalid mode '{req.mode}'. Expected 'SIMULATION' or 'HARDWARE'.")


@router.post("/command/move")
def command_move(cmd: MoveCommand, sim=Depends(get_sim)):
    driver = get_active_driver()
    target_q_m = np.array([cmd.x_mm / 1000.0, cmd.y_mm / 1000.0])
    speed_m_s = (cmd.speed_mm_s / 1000.0) if cmd.speed_mm_s is not None else None

    ok, message = driver.request_move(target_q_m, speed_m_s=speed_m_s)
    if not ok:
        raise HTTPException(status_code=400, detail={"error": "MoveRejected", "message": message})
    return {"status": "accepted", "message": message, "target": [cmd.x_mm, cmd.y_mm]}


@router.post("/command/jog")
def command_jog(cmd: JogCommand, sim=Depends(get_sim)):
    driver = get_active_driver()
    dx_m = cmd.delta_x_mm / 1000.0
    dy_m = cmd.delta_y_mm / 1000.0
    speed_m_s = (cmd.speed_mm_s / 1000.0) if cmd.speed_mm_s is not None else None

    ok, message = driver.request_jog(dx_m, dy_m, speed_m_s=speed_m_s)
    if not ok:
        raise HTTPException(status_code=400, detail={"error": "JogRejected", "message": message})
    return {"status": "accepted", "message": message}


@router.post("/command/pause")
def command_pause(sim=Depends(get_sim)):
    ok, msg = sim.controller.pause()
    if not ok:
        raise HTTPException(status_code=400, detail={"error": "PauseFailed", "message": msg})
    return {"status": "paused", "message": msg}


@router.post("/command/resume")
def command_resume(sim=Depends(get_sim)):
    ok, msg = sim.controller.resume()
    if not ok:
        raise HTTPException(status_code=400, detail={"error": "ResumeFailed", "message": msg})
    return {"status": "resumed", "message": msg}


@router.post("/command/stop")
def command_stop(sim=Depends(get_sim)):
    driver = get_active_driver()
    ok, msg = driver.request_stop()
    return {"status": "stopped", "message": msg}


@router.post("/command/estop")
def command_estop(sim=Depends(get_sim)):
    driver = get_active_driver()
    ok, msg = driver.request_estop()
    return {"status": "estop_activated", "message": msg}


@router.post("/command/reset")
def command_reset(sim=Depends(get_sim)):
    driver = get_active_driver()
    ok, msg = driver.reset_recoverable_fault()
    return {"status": "reset" if ok else "reset_failed", "message": msg}


@router.post("/command/trajectory")
def command_trajectory(cmd: TrajectoryCommand, sim=Depends(get_sim)):
    if _active_mode == OperatingMode.HARDWARE_DISABLED:
        raise HTTPException(status_code=400, detail={"error": "HardwareDisabled", "message": "Physical robot unverified. Switch to SIMULATION mode."})

    params_m = dict(cmd.params)
    if "speed_mm_s" in params_m:
        params_m["speed_m_s"] = params_m.pop("speed_mm_s") / 1000.0

    if cmd.type == "circle":
        if "radius_mm" in params_m:
            params_m["radius_m"] = params_m.pop("radius_mm") / 1000.0
        if "center_mm" in params_m:
            c = params_m.pop("center_mm")
            params_m["center"] = [c[0] / 1000.0, c[1] / 1000.0]

    elif cmd.type == "rectangle":
        if "width_mm" in params_m:
            params_m["width_m"] = params_m.pop("width_mm") / 1000.0
        if "height_mm" in params_m:
            params_m["height_m"] = params_m.pop("height_mm") / 1000.0
        if "center_mm" in params_m:
            c = params_m.pop("center_mm")
            params_m["center"] = [c[0] / 1000.0, c[1] / 1000.0]

    elif cmd.type == "waypoints":
        if "waypoints_mm" in params_m:
            wps = params_m.pop("waypoints_mm")
            params_m["waypoints"] = [[w[0] / 1000.0, w[1] / 1000.0] for w in wps]

    ok, msg = sim.controller.request_trajectory(cmd.type, params_m)
    if not ok:
        raise HTTPException(status_code=400, detail={"error": "TrajectoryRejected", "message": msg})
    return {"status": "accepted", "message": msg}


@router.get("/workspace")
def get_workspace(sim=Depends(get_sim)):
    ws = sim.config.workspace
    f = sim.config.frame
    p = sim.config.platform
    anchors = sim.geom.anchors
    return {
        "frame_width_mm": f.width_m * 1000.0,
        "frame_height_mm": f.height_m * 1000.0,
        "platform_width_mm": p.width_m * 1000.0,
        "platform_height_mm": p.height_m * 1000.0,
        "x_min_mm": ws.x_min_m * 1000.0,
        "x_max_mm": ws.x_max_m * 1000.0,
        "y_min_mm": ws.y_min_m * 1000.0,
        "y_max_mm": ws.y_max_m * 1000.0,
        "safety_margin_mm": ws.safety_margin_m * 1000.0,
        "anchors_mm": {
            "C1": [float(anchors[0, 0] * 1000.0), float(anchors[0, 1] * 1000.0)],
            "C2": [float(anchors[1, 0] * 1000.0), float(anchors[1, 1] * 1000.0)],
            "C3": [float(anchors[2, 0] * 1000.0), float(anchors[2, 1] * 1000.0)],
            "C4": [float(anchors[3, 0] * 1000.0), float(anchors[3, 1] * 1000.0)],
        }
    }


@router.get("/diagnostics")
def get_diagnostics(sim=Depends(get_sim)):
    telem = sim.latest_telemetry
    driver = get_active_driver()
    return {
        "sim_time_s": sim.sim_time,
        "operating_mode": _active_mode.value,
        "driver": driver.__class__.__name__ if driver else "None",
        "controller_mode": sim.controller.mode,
        "condition_number": telem.condition_number if telem else 1.0,
        "tracking_error_mm": telem.tracking_error_mm if telem else 0.0,
        "tracking_error_valid": telem.tracking_error_valid if telem else True,
        "tension_feasible": telem.tension_feasible if telem else True,
        "workspace_safe": telem.workspace_safe if telem else True,
        "active_faults": sim.controller.active_faults,
        "active_trajectory_length": len(sim.controller.active_trajectory),
        "trajectory_index": sim.controller.current_traj_index,
        "position_provenance": telem.position_provenance if telem else "simulated",
        "homing_state": telem.homing_state if telem else "HOMED",
    }
