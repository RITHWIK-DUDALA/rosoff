"""
REST API routes for CDPR simulator.
Endpoints:
- GET  /health
- GET  /config
- GET  /state
- POST /command/move
- POST /command/jog
- POST /command/pause
- POST /command/resume
- POST /command/stop
- POST /command/reset
- POST /command/estop
- POST /command/trajectory
- GET  /workspace
- GET  /diagnostics
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np

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


# Dependency injection placeholder for global simulation instance
_sim_instance = None


def set_sim_instance(sim):
    global _sim_instance
    _sim_instance = sim


def get_sim():
    if _sim_instance is None:
        raise HTTPException(status_code=500, detail="Simulation engine not initialized")
    return _sim_instance


@router.get("/health")
def health(sim=Depends(get_sim)):
    return {
        "status": "healthy",
        "sim_time_s": sim.sim_time,
        "mode": sim.controller.mode,
        "faults": sim.controller.active_faults
    }


@router.get("/config")
def get_config(sim=Depends(get_sim)):
    return sim.config.raw_dict


@router.get("/state")
def get_state(sim=Depends(get_sim)):
    if sim.latest_telemetry is None:
        raise HTTPException(status_code=503, detail="Telemetry not yet computed")
    return sim.latest_telemetry.to_dict()


@router.post("/command/move")
def command_move(cmd: MoveCommand, sim=Depends(get_sim)):
    target_q_m = np.array([cmd.x_mm / 1000.0, cmd.y_mm / 1000.0])
    speed_m_s = (cmd.speed_mm_s / 1000.0) if cmd.speed_mm_s is not None else None

    ok, message = sim.controller.request_move(target_q_m, speed_m_s=speed_m_s)
    if not ok:
        raise HTTPException(status_code=400, detail={"error": "MoveRejected", "message": message})
    return {"status": "accepted", "message": message, "target": [cmd.x_mm, cmd.y_mm]}


@router.post("/command/jog")
def command_jog(cmd: JogCommand, sim=Depends(get_sim)):
    dx_m = cmd.delta_x_mm / 1000.0
    dy_m = cmd.delta_y_mm / 1000.0
    speed_m_s = (cmd.speed_mm_s / 1000.0) if cmd.speed_mm_s is not None else None

    ok, message = sim.controller.request_jog(dx_m, dy_m, speed_m_s=speed_m_s)
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
    ok, msg = sim.controller.stop()
    return {"status": "stopped", "message": msg}


@router.post("/command/estop")
def command_estop(sim=Depends(get_sim)):
    ok, msg = sim.controller.estop()
    return {"status": "estop_activated", "message": msg}


@router.post("/command/reset")
def command_reset(sim=Depends(get_sim)):
    sim.reset()
    return {"status": "reset", "message": "Simulation homed and state reset"}


@router.post("/command/trajectory")
def command_trajectory(cmd: TrajectoryCommand, sim=Depends(get_sim)):
    # Convert mm params to meters where relevant
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
            "C1": [-f.width_m * 500.0,  f.height_m * 500.0],
            "C2": [ f.width_m * 500.0,  f.height_m * 500.0],
            "C3": [ f.width_m * 500.0, -f.height_m * 500.0],
            "C4": [-f.width_m * 500.0, -f.height_m * 500.0]
        }
    }


@router.get("/diagnostics")
def get_diagnostics(sim=Depends(get_sim)):
    telem = sim.latest_telemetry
    return {
        "sim_time_s": sim.sim_time,
        "mode": sim.controller.mode,
        "condition_number": telem.condition_number if telem else 1.0,
        "tracking_error_mm": telem.tracking_error_mm if telem else 0.0,
        "tension_feasible": telem.tension_feasible if telem else True,
        "workspace_safe": telem.workspace_safe if telem else True,
        "active_faults": sim.controller.active_faults,
        "active_trajectory_length": len(sim.controller.active_trajectory),
        "trajectory_index": sim.controller.current_traj_index
    }
