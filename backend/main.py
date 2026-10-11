"""
Main FastAPI server for CDPR Simulator.
Serves:
- REST API under /api
- WebSocket live telemetry under /ws/telemetry
- Static frontend files under /
- Background deterministic simulation loop running at fixed timestep dt = 10 ms (100 Hz).
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.cdpr.simulation import CDPRSimulation
from backend.api.routes import router as api_router, set_sim_instance
from backend.api.websocket import ws_router, broadcast_telemetry

# Initialize global simulation engine
sim = CDPRSimulation("robot_config.yaml")
set_sim_instance(sim)

# Simulation background task flag
_sim_loop_task = None


async def run_simulation_loop():
    """Runs simulation at fixed timestep (100 Hz), broadcasts telemetry at 30 Hz."""
    dt = sim.dt  # 0.010 s (100 Hz)
    telemetry_interval = 1.0 / sim.config.simulation.telemetry_rate_hz
    last_telemetry_time = 0.0

    while True:
        t0 = asyncio.get_event_loop().time()
        sim.step()

        now = asyncio.get_event_loop().time()
        if (now - last_telemetry_time) >= telemetry_interval:
            if sim.latest_telemetry is not None:
                await broadcast_telemetry(sim.latest_telemetry.to_dict())
            last_telemetry_time = now

        elapsed = asyncio.get_event_loop().time() - t0
        sleep_time = max(0.001, dt - elapsed)
        await asyncio.sleep(sleep_time)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sim_loop_task
    # Start deterministic physics simulation loop in background
    _sim_loop_task = asyncio.create_task(run_simulation_loop())
    yield
    if _sim_loop_task:
        _sim_loop_task.cancel()
        try:
            await _sim_loop_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Planar Cable Robot Simulator API",
    description="Engineering-grade 2-DOF CDPR Simulation Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.include_router(api_router, prefix="/api")
app.include_router(ws_router)

# Mount frontend static directory
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
