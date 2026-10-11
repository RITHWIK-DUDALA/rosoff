"""
WebSocket broadcaster for high-frequency telemetry streaming to frontend clients.
"""
import asyncio
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("websocket")
ws_router = APIRouter()

active_connections: Set[WebSocket] = set()


@ws_router.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Keep-alive receive or client command listener
            data = await websocket.receive_text()
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
    finally:
        active_connections.discard(websocket)


async def broadcast_telemetry(telemetry_dict: dict):
    """Broadcasts telemetry payload to all connected frontend clients."""
    if not active_connections:
        return
    message = json.dumps(telemetry_dict)
    dead_clients = []
    for client in list(active_connections):
        try:
            await client.send_text(message)
        except Exception:
            dead_clients.append(client)

    for dead in dead_clients:
        active_connections.discard(dead)
