"""
Log Viewer Widget for IronSilo TUI.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional
from collections import deque

from textual.app import ComposeResult
from textual.widgets import Static, Input
from textual.containers import Vertical


class LogEntry:
    """Represents a single log entry."""
    
    def __init__(
        self,
        timestamp: datetime,
        level: str,
        container: str,
        message: str,
    ) -> None:
        self.timestamp = timestamp
        self.level = level.upper()
        self.container = container
        self.message = message
    
    @property
    def display_time(self) -> str:
        """Get formatted timestamp."""
        return self.timestamp.strftime("%H:%M:%S")
    
    @property
    def color(self) -> str:
        """Get color for log level."""
        colors = {
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "DEBUG": "blue",
            "CRITICAL": "magenta",
        }
        return colors.get(self.level, "white")
    
    def format(self) -> str:
        """Format log entry for display."""
        return f"[dim]{self.display_time}[/dim] [{self.color}]{self.level:8}[/{self.color}] [cyan]{self.container:15}[/cyan] {self.message}"


class LogViewerWidget(Static):
    """
    Widget for viewing and filtering container logs.
    
    Features:
    - Real-time log streaming
    - Log level filtering
    - Container filtering
    - Search functionality
    """
    
    def __init__(self, max_lines: int = 1000, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_lines = max_lines
        self._logs: Deque[LogEntry] = deque(maxlen=max_lines)
        self._filter_level: Optional[str] = None
        self._filter_container: Optional[str] = None
        self._search_term: str = ""
        self._last_update: Optional[datetime] = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Vertical():
            yield Input(placeholder="Filter logs...", id="log-filter")
            yield Static(id="log-display")
    
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        # Generate some sample logs
        self._generate_sample_logs()
        self._update_display()
    
    def _generate_sample_logs(self) -> None:
        """Generate sample log entries for demo."""
        sample_logs = [
            ("INFO", "llm-proxy", "Request received: /api/v1/chat/completions"),
            ("INFO", "genesys-memory", "Connected to PostgreSQL"),
            ("INFO", "khoj", "Index loaded: 156 documents"),
            ("WARNING", "llm-proxy", "High latency detected: 2.5s"),
            ("INFO", "mcp-genesys", "MCP tool registered: create_memory_node"),
            ("DEBUG", "ironclaw-db", "Query executed: SELECT * FROM memories"),
            ("INFO", "llm-proxy", "Cache hit ratio: 78.5%"),
            ("ERROR", "searxng", "Search engine timeout: google"),
            ("INFO", "llm-proxy", "Compression ratio: 42.3%"),
            ("INFO", "mcp-khoj", "Document uploaded: report.pdf"),
        ]
        
        base_time = datetime.now()
        for i, (level, container, message) in enumerate(sample_logs):
            timestamp = base_time.replace(microsecond=i * 100000)
            self._logs.append(LogEntry(timestamp, level, container, message))
    
    async def refresh(self) -> None:
        """Refresh log data."""
        try:
            # In production, this would fetch new logs from containers
            # For now, just update timestamp
            self._last_update = datetime.now()
            self._update_display()
        except Exception as e:
            self._update_error(f"Error: {str(e)[:30]}")
    
    def _update_display(self) -> None:
        """Update the log display."""
        display = self.query_one("#log-display", Static)
        
        # Filter logs
        filtered_logs = list(self._logs)
        
        if self._filter_level:
            filtered_logs = [
                log for log in filtered_logs
                if log.level == self._filter_level.upper()
            ]
        
        if self._filter_container:
            filtered_logs = [
                log for log in filtered_logs
                if self._filter_container.lower() in log.container.lower()
            ]
        
        if self._search_term:
            filtered_logs = [
                log for log in filtered_logs
                if self._search_term.lower() in log.message.lower()
            ]
        
        # Format logs
        if not filtered_logs:
            content = "[dim]No logs to display[/dim]"
        else:
            # Show last 50 logs
            recent_logs = list(filtered_logs)[-50:]
            content = "\n".join(log.format() for log in recent_logs)
        
        # Add header
        header = f"[bold cyan]Recent Logs ({len(filtered_logs)} entries)[/bold cyan]"
        if self._filter_level or self._search_term:
            filters = []
            if self._filter_level:
                filters.append(f"level={self._filter_level}")
            if self._search_term:
                filters.append(f"search={self._search_term}")
            header += f" [dim]({', '.join(filters)})[/dim]"
        
        display.update(f"{header}\n{content}")
    
    def _update_error(self, message: str) -> None:
        """Display error message."""
        display = self.query_one("#log-display", Static)
        display.update(f"[red]{message}[/red]")
    
    def add_log(self, level: str, container: str, message: str) -> None:
        """Add a new log entry."""
        entry = LogEntry(datetime.now(), level, container, message)
        self._logs.append(entry)
        self._update_display()
    
    def clear(self) -> None:
        """Clear all logs."""
        self._logs.clear()
        self._update_display()
    
    def set_filter(self, level: Optional[str] = None, container: Optional[str] = None) -> None:
        """Set log filters."""
        self._filter_level = level
        self._filter_container = container
        self._update_display()
    
    def set_search(self, term: str) -> None:
        """Set search term."""
        self._search_term = term
        self._update_display()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        if event.input.id == "log-filter":
            self.set_search(event.value)
    
    def render(self) -> str:
        """Render the widget."""
        update_time = self._last_update.strftime("%H:%M:%S") if self._last_update else "N/A"
        return f"Logs (Updated: {update_time})"
