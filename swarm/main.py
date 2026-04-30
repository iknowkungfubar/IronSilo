from __future__ import annotations

import asyncio
import json
import signal
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for graceful shutdown."""
    logger.info("swarm_service_starting")

    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("swarm_received_shutdown_signal")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    yield

    logger.info("swarm_service_stopping", clients=len(state.connected_clients))

    async with state.lock:
        for client in state.connected_clients:
            try:
                await client.close(code=1001, reason="Server shutting down")
            except Exception as e:
                logger.warning("swarm_client_close_error", error=str(e))
        state.connected_clients.clear()

    logger.info("swarm_service_stopped")


app = FastAPI(
    title="Swarm Service API",
    version="1.0.0",
    lifespan=lifespan,
)


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


@app.get("/metrics")
async def get_metrics() -> JSONResponse:
    """Return Prometheus-compatible metrics."""
    return JSONResponse({
        "metrics": {
            "state": {
                "current_action": state.current_action,
                "action_history_count": len(state.action_history),
                "connected_clients": len(state.connected_clients),
            },
            "uptime_seconds": time.time() - state.start_time,
            "timestamp": time.time(),
        }
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8095)
