"""
Container Status Widget for IronSilo TUI.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.widgets import DataTable, Static


class ContainerStatusWidget(Static):
    """
    Widget displaying Docker container status.
    
    Shows:
    - Container name
    - Status (running/stopped)
    - Health check status
    - CPU/Memory usage
    - Uptime
    """
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._containers: List[Dict[str, Any]] = []
        self._last_update: Optional[datetime] = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield DataTable(id="container-table")
    
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        table = self.query_one("#container-table", DataTable)
        table.add_columns("Container", "Status", "Health", "CPU", "Memory", "Uptime")
        self.refresh_data()
    
    async def refresh_data(self) -> None:
        """Refresh container status data."""
        try:
            self._containers = await self._get_container_status()
            self._last_update = datetime.now()
            self._update_table()
        except Exception as e:
            self._update_error(f"Error: {str(e)[:30]}")
    
    async def _get_container_status(self) -> List[Dict[str, Any]]:
        """
        Get Docker container status.
        
        In production, this would call Docker API.
        For now, returns simulated data.
        """
        # Simulated container data for demo
        return [
            {
                "name": "ironclaw-db",
                "status": "running",
                "health": "healthy",
                "cpu": "0.5%",
                "memory": "128MB",
                "uptime": "2h 30m",
            },
            {
                "name": "genesys-memory",
                "status": "running",
                "health": "healthy",
                "cpu": "1.2%",
                "memory": "256MB",
                "uptime": "2h 30m",
            },
            {
                "name": "khoj",
                "status": "running",
                "health": "healthy",
                "cpu": "5.3%",
                "memory": "512MB",
                "uptime": "2h 30m",
            },
            {
                "name": "llm-proxy",
                "status": "running",
                "health": "healthy",
                "cpu": "12.5%",
                "memory": "1.2GB",
                "uptime": "2h 30m",
            },
            {
                "name": "mcp-genesys",
                "status": "running",
                "health": "healthy",
                "cpu": "0.2%",
                "memory": "64MB",
                "uptime": "2h 30m",
            },
            {
                "name": "mcp-khoj",
                "status": "running",
                "health": "healthy",
                "cpu": "0.1%",
                "memory": "48MB",
                "uptime": "2h 30m",
            },
            {
                "name": "searxng",
                "status": "running",
                "health": "healthy",
                "cpu": "0.3%",
                "memory": "96MB",
                "uptime": "2h 30m",
            },
        ]
    
    def _update_table(self) -> None:
        """Update the data table with container status."""
        try:
            table = self.query_one("#container-table", DataTable)
            table.clear()
            
            for container in self._containers:
                # Add status indicator
                status_icon = "●" if container["status"] == "running" else "○"
                status_color = "green" if container["status"] == "running" else "red"
                
                # Add health indicator
                health_icon = "✓" if container["health"] == "healthy" else "✗"
                health_color = "green" if container["health"] == "healthy" else "yellow"
                
                table.add_row(
                    container["name"],
                    f"[{status_color}]{status_icon} {container['status']}[/{status_color}]",
                    f"[{health_color}]{health_icon} {container['health']}[/{health_color}]",
                    container["cpu"],
                    container["memory"],
                    container["uptime"],
                )
            
        except Exception as e:
            self._update_error(f"Table error: {str(e)[:20]}")
    
    def _update_error(self, message: str) -> None:
        """Display error message."""
        self.update(f"[red]Error: {message}[/red]")
    
    def render(self) -> str:
        """Render the widget."""
        if not self._containers:
            return "[yellow]Loading container status...[/yellow]"
        
        update_time = self._last_update.strftime("%H:%M:%S") if self._last_update else "N/A"
        return f"Container Status (Updated: {update_time})"
