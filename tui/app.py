"""
IronSilo Terminal User Interface (TUI) - Main Application.

A Textual-based terminal dashboard for monitoring IronSilo services.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    DataTable,
    Static,
)

from .widgets.container_status import ContainerStatusWidget
from .widgets.resource_monitor import ResourceMonitorWidget
from .widgets.log_viewer import LogViewerWidget
from .theme import IRONSILO_THEME


class StatusBar(Static):
    """Status bar showing overall system status."""
    
    status = reactive("Initializing...")
    
    def render(self) -> str:
        return f"IronSilo Dashboard | {self.status} | {datetime.now().strftime('%H:%M:%S')}"


class IronSiloTUI(App):
    """
    IronSilo Terminal User Interface.
    
    A Textual-based terminal dashboard for monitoring:
    - Docker container status
    - Resource usage (CPU, Memory)
    - Service logs
    - System health
    """
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
    }
    
    #main-container {
        height: 100%;
    }
    
    #top-panel {
        height: 50%;
        border: solid $primary;
        margin: 1;
    }
    
    #bottom-panel {
        height: 50%;
        border: solid $primary;
        margin: 1;
    }
    
    #status-bar {
        dock: bottom;
        height: 1;
        background: $primary-background;
        color: $text;
        padding: 0 1;
    }
    
    ContainerStatusWidget {
        height: 100%;
    }
    
    ResourceMonitorWidget {
        height: 100%;
    }
    
    LogViewerWidget {
        height: 100%;
    }
    
    DataTable {
        height: 100%;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("c", "clear_logs", "Clear Logs"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]
    
    TITLE = "IronSilo Dashboard"
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._refresh_interval = 5  # seconds
        self._last_refresh = time.time()
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield StatusBar(id="status-bar")
        
        with Container(id="main-container"):
            with Horizontal(id="top-panel"):
                yield ContainerStatusWidget(id="container-status")
                yield ResourceMonitorWidget(id="resource-monitor")
            
            with Vertical(id="bottom-panel"):
                yield LogViewerWidget(id="log-viewer")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.title = "IronSilo Dashboard"
        self.sub_title = "Local AI Development Sandbox"
        self.update_status("Ready")
        
        # Start background refresh task
        self.set_interval(self._refresh_interval, self.refresh_data)
    
    def update_status(self, status: str) -> None:
        """Update the status bar."""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.status = status
    
    async def refresh_data(self) -> None:
        """Refresh all dashboard data."""
        try:
            self._last_refresh = time.time()
            self.update_status(f"Refreshing... ({datetime.now().strftime('%H:%M:%S')})")
            
            # Refresh components
            container_status = self.query_one("#container-status", ContainerStatusWidget)
            resource_monitor = self.query_one("#resource-monitor", ResourceMonitorWidget)
            log_viewer = self.query_one("#log-viewer", LogViewerWidget)
            
            await asyncio.gather(
                container_status.refresh_data(),
                resource_monitor.refresh_data(),
                log_viewer.refresh_data(),
                return_exceptions=True,
            )
            
            self.update_status(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)[:50]}")
    
    def action_refresh(self) -> None:
        """Manually refresh data."""
        self.call_later(self.refresh_data)
    
    def action_clear_logs(self) -> None:
        """Clear log viewer."""
        log_viewer = self.query_one("#log-viewer", LogViewerWidget)
        log_viewer.clear()
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = IronSiloTUI()
    app.run()
