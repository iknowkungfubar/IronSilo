from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Optional

from textual.app import ComposeResult
from textual.widgets import Static


class SwarmAction:
    """Represents a single swarm action."""

    def __init__(self, action: str, agent: str, timestamp: float) -> None:
        self.action = action
        self.agent = agent
        self.timestamp = timestamp

    @property
    def time_str(self) -> str:
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%H:%M:%S")


class SwarmMonitorWidget(Static):
    """
    Widget displaying live swarm actions.

    Connects to swarm-service WebSocket and displays
    a live feed of agent actions.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._actions: list[SwarmAction] = []
        self._ws_task: Optional[asyncio.Task] = None
        self._connected = False
        self._ws_url = "ws://localhost:8095/ws/swarm"

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="swarm-display")

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self._start_websocket()

    def on_unmount(self) -> None:
        """Called when widget is unmounted."""
        self._stop_websocket()

    def _start_websocket(self) -> None:
        """Start WebSocket connection to swarm service."""
        self._ws_task = asyncio.create_task(self.watch_socket())

    async def watch_socket(self) -> None:
        """Watch swarm-service WebSocket for actions."""
        import websockets

        try:
            async with websockets.connect(self._ws_url) as ws:
                self._connected = True
                self._update_display()
                self._add_status("Connected to swarm-service")

                while True:
                    try:
                        data = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        message = json.loads(data)

                        if message.get("type") == "action":
                            action = SwarmAction(
                                action=message.get("action", "unknown"),
                                agent=message.get("agent", "unknown"),
                                timestamp=message.get("timestamp", time.time()),
                            )
                            self._actions.append(action)
                            if len(self._actions) > 50:
                                self._actions.pop(0)
                            self._update_display()

                    except asyncio.TimeoutError:
                        continue

        except Exception as e:
            self._connected = False
            self._add_status(f"Disconnected: {str(e)[:40]}")
            self._update_display()

    def _stop_websocket(self) -> None:
        """Stop WebSocket connection."""
        if self._ws_task:
            self._ws_task.cancel()
            self._ws_task = None

    def _update_display(self) -> None:
        """Update the display with current actions."""
        display = self.query_one("#swarm-display", Static)

        lines = []
        lines.append("[bold cyan]Swarm Monitor[/bold cyan]")
        lines.append("")

        if self._connected:
            lines.append("[green]● Connected[/green]")
        else:
            lines.append("[red]○ Disconnected[/red]")

        lines.append("")

        for action in reversed(self._actions[-20:]):
            lines.append(f"[dim]{action.time_str}[/dim] {action.agent}: {action.action}")

        display.update("\n".join(lines))

    def _add_status(self, status: str) -> None:
        """Add a status message."""
        self._actions.append(SwarmAction(
            action=status,
            agent="system",
            timestamp=datetime.now().timestamp(),
        ))
        if len(self._actions) > 50:
            self._actions.pop(0)

    def render(self) -> str:
        """Render the widget."""
        return "Swarm Monitor"
