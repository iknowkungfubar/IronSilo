from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)


class SwarmState:
    """Shared state for swarm service."""
    current_action: str = "idle"
    action_history: list[dict[str, Any]] = []
    connected_clients: list[WebSocket] = []
    lock: asyncio.Lock = asyncio.Lock()
    start_time: float = time.time()


state = SwarmState()

app = FastAPI(title="Swarm Service API", version="1.0.0")


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "service": "swarm-service",
        "version": "1.0.0",
        "uptime_seconds": time.time() - state.start_time,
        "current_action": state.current_action,
        "connected_agents": len(state.connected_clients),
    })


@app.get("/status")
async def get_status() -> JSONResponse:
    """Return current swarm status."""
    return JSONResponse({
        "status": "running",
        "current_action": state.current_action,
        "timestamp": time.time(),
        "connected_agents": len(state.connected_clients),
    })


@app.websocket("/ws/swarm")
async def websocket_swarm(websocket: WebSocket) -> None:
    """WebSocket endpoint for broadcasting swarm actions."""
    await websocket.accept()
    logger.info("swarm_ws_client_connected")

    async with state.lock:
        state.connected_clients.append(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "current_action": state.current_action,
            "timestamp": time.time(),
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "action":
                async with state.lock:
                    state.current_action = message.get("action", "unknown")
                    state.action_history.append({
                        "action": state.current_action,
                        "timestamp": time.time(),
                        "agent": message.get("agent", "unknown"),
                    })
                    if len(state.action_history) > 100:
                        state.action_history.pop(0)

                    broadcast_message = {
                        "type": "action",
                        "action": state.current_action,
                        "timestamp": time.time(),
                        "agent": message.get("agent", "unknown"),
                    }

                for client in state.connected_clients:
                    if client != websocket:
                        try:
                            await client.send_json(broadcast_message)
                        except Exception:
                            pass

    except WebSocketDisconnect:
        logger.info("swarm_ws_client_disconnected")
    finally:
        async with state.lock:
            if websocket in state.connected_clients:
                state.connected_clients.remove(websocket)


@app.get("/history")
async def get_history() -> JSONResponse:
    """Return action history."""
    async with state.lock:
        return JSONResponse({
            "history": state.action_history[-50:],
            "count": len(state.action_history),
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8095)
