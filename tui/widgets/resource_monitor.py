"""
Resource Monitor Widget for IronSilo TUI.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.widgets import Static, Sparkline


class ResourceMetric:
    """Represents a single resource metric."""
    
    def __init__(self, name: str, value: float, max_value: float, unit: str = "%") -> None:
        self.name = name
        self.value = value
        self.max_value = max_value
        self.unit = unit
        self.history: List[float] = [value]
        self.max_history = 60  # Keep 60 data points
    
    @property
    def percentage(self) -> float:
        """Get value as percentage of max."""
        if self.max_value == 0:
            return 0.0
        return (self.value / self.max_value) * 100
    
    @property
    def display_value(self) -> str:
        """Get formatted display value."""
        if self.unit == "%":
            return f"{self.value:.1f}{self.unit}"
        elif self.unit == "MB":
            return f"{self.value:.0f}{self.unit}"
        elif self.unit == "GB":
            return f"{self.value:.2f}{self.unit}"
        else:
            return f"{self.value:.1f}{self.unit}"
    
    def add_sample(self, value: float) -> None:
        """Add a new sample to history."""
        self.value = value
        self.history.append(value)
        if len(self.history) > self.max_history:
            self.history.pop(0)


class ResourceMonitorWidget(Static):
    """
    Widget displaying resource usage metrics.
    
    Shows:
    - CPU usage
    - RAM usage
    - Docker memory
    - GPU usage (if available)
    """
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._metrics: Dict[str, ResourceMetric] = {}
        self._last_update: Optional[datetime] = None
        self._initialize_metrics()
    
    def _initialize_metrics(self) -> None:
        """Initialize resource metrics."""
        self._metrics = {
            "cpu": ResourceMetric("CPU", 0.0, 100.0, "%"),
            "ram": ResourceMetric("RAM", 0.0, 16384, "MB"),  # 16GB assumed
            "docker": ResourceMetric("Docker", 0.0, 4096, "MB"),  # 4GB limit
            "gpu": ResourceMetric("GPU", 0.0, 100.0, "%"),
        }
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="metrics-display")
    
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.refresh()
    
    async def refresh(self) -> None:
        """Refresh resource metrics."""
        try:
            # In production, this would read actual system metrics
            # For now, simulate with random values
            import random
            
            for metric in self._metrics.values():
                # Simulate some variation
                base_value = metric.value if metric.value > 0 else 50
                variation = random.uniform(-5, 5)
                new_value = max(0, min(metric.max_value, base_value + variation))
                metric.add_sample(new_value)
            
            self._last_update = datetime.now()
            self._update_display()
            
        except Exception as e:
            self._update_error(f"Error: {str(e)[:30]}")
    
    def _update_display(self) -> None:
        """Update the display with current metrics."""
        display = self.query_one("#metrics-display", Static)
        
        lines = []
        lines.append("[bold cyan]Resource Usage[/bold cyan]")
        lines.append("")
        
        for name, metric in self._metrics.items():
            # Calculate bar length (20 chars max)
            bar_length = int(metric.percentage / 5)  # Scale to 20
            bar_length = min(20, max(0, bar_length))
            
            # Color based on usage
            if metric.percentage > 90:
                color = "red"
            elif metric.percentage > 70:
                color = "yellow"
            else:
                color = "green"
            
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            lines.append(f"[bold]{name.upper():6}[/bold]: [{color}]{bar}[/{color}] {metric.display_value}")
        
        lines.append("")
        
        # Add sparkline history for CPU
        cpu_metric = self._metrics["cpu"]
        if len(cpu_metric.history) > 1:
            lines.append(f"[dim]CPU History: {'▁▂▃▄▅▆▇█'[:min(8, len(cpu_metric.history))]}[/dim]")
        
        display.update("\n".join(lines))
    
    def _update_error(self, message: str) -> None:
        """Display error message."""
        display = self.query_one("#metrics-display", Static)
        display.update(f"[red]{message}[/red]")
    
    def render(self) -> str:
        """Render the widget."""
        update_time = self._last_update.strftime("%H:%M:%S") if self._last_update else "N/A"
        return f"Resource Monitor (Updated: {update_time})"
    
    def get_metric(self, name: str) -> Optional[ResourceMetric]:
        """Get a specific metric by name."""
        return self._metrics.get(name)
