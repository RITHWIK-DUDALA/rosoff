"""
Main FastAPI Server for Planar Cable-Driven Autonomous Surface Printing System (PROJECT W.A.L.L.)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.simulation.cdpr_orchestrator import CDPROrchestrator
from app.api.routes import create_cdpr_api_router
from app.api.websocket import CDPRTelemetryBroadcaster
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

orchestrator = CDPROrchestrator()
broadcaster = CDPRTelemetryBroadcaster(orchestrator)
sim_task = None


async def physics_loop():
    """Deterministic fixed-timestep simulation clock running at 30 Hz (dt = 0.033s)"""
    dt = 0.033
    while True:
        try:
            orchestrator.step(dt)
            await broadcaster.broadcast_telemetry()
        except Exception as e:
            print(f"[CDPR Sim Loop Error] {e}")
        await asyncio.sleep(dt)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sim_task
    print("[PROJECT W.A.L.L.] Starting Planar 4-Cable Surface Printing Simulation Engine...")
    sim_task = asyncio.create_task(physics_loop())
    yield
    print("[PROJECT W.A.L.L.] Stopping simulation engine...")
    if sim_task:
        sim_task.cancel()


app = FastAPI(
    title="PROJECT W.A.L.L. Planar Cable Robot Digital Twin",
    description="Universal Planar Cable-Driven Autonomous Surface Printing System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(create_cdpr_api_router(orchestrator))


@app.websocket("/ws")
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await broadcaster.handle_client(websocket)

# Mount CAD static directory for direct download/viewing of models
cad_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cad"))
if os.path.exists(cad_dir):
    app.mount("/cad", StaticFiles(directory=cad_dir), name="cad")

# Mount Frontend static files to serve the complete web UI directly on port 8000
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

