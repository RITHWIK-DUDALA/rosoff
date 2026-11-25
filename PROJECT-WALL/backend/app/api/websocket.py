"""
WebSocket Telemetry Streaming for Planar Cable Robot PROJECT W.A.L.L.
Streams live 4-motor states, cable lengths, tensions, platform coordinates,
and progressive deposition canvas at up to 30 Hz.
"""

import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
from ..simulation.cdpr_orchestrator import CDPROrchestrator


class CDPRTelemetryBroadcaster:
    def __init__(self, orchestrator: CDPROrchestrator):
        self.orchestrator = orchestrator
        self.active_sockets: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_sockets.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active_sockets.discard(ws)

    async def broadcast_telemetry(self):
        if not self.active_sockets:
            return

        payload = self.orchestrator.get_telemetry()
        dead = []
        for ws in list(self.active_sockets):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def handle_client(self, ws: WebSocket):
        await self.connect(ws)
        try:
            while True:
                msg = await ws.receive_text()
                try:
                    data = json.loads(msg)
                    cmd = data.get("command")
                    if cmd == "MOVE":
                        self.orchestrator.move_to(data.get("x", 400.0), data.get("y", 300.0))
                    elif cmd == "START_PRINT":
                        self.orchestrator.start_printing()
                    elif cmd == "PAUSE_PRINT":
                        self.orchestrator.pause_printing()
                    elif cmd == "RESUME_PRINT":
                        self.orchestrator.resume_printing()
                    elif cmd == "ESTOP":
                        self.orchestrator.emergency_stop()
                    elif cmd == "RESET":
                        self.orchestrator.reset()
                except Exception as e:
                    await ws.send_json({"error": str(e)})
        except WebSocketDisconnect:
            self.disconnect(ws)

