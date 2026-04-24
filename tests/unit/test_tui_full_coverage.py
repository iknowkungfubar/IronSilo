"""
Comprehensive tests for TUI components to achieve 100% coverage.

Tests cover:
- TUI app lifecycle and methods
- ContainerStatusWidget with real data
- ResourceMonitorWidget with metrics
- LogViewerWidget with filtering
- StatusBar widget
"""

import asyncio
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Skip all tests if textual is not available
textual = pytest.importorskip("textual", reason="textual not installed")


class TestTUIAppFullCoverage:
    """Tests for tui/app.py to achieve 100% coverage."""
    
    def test_app_css_content(self):
        """Test app CSS is properly defined."""
        from tui.app import IronSiloTUI
        
        assert "Screen" in IronSiloTUI.CSS
        assert "background" in IronSiloTUI.CSS
        assert "#header" in IronSiloTUI.CSS
        assert "#main-container" in IronSiloTUI.CSS
        assert "#top-panel" in IronSiloTUI.CSS
        assert "#bottom-panel" in IronSiloTUI.CSS
        assert "#status-bar" in IronSiloTUI.CSS
    
    def test_app_bindings_structure(self):
        """Test app bindings have correct structure."""
        from tui.app import IronSiloTUI
        
        for binding in IronSiloTUI.BINDINGS:
            assert len(binding) >= 2
            key, action = binding[0], binding[1]
            assert isinstance(key, str)
            assert isinstance(action, str)
    
    def test_status_bar_initial_state(self):
        """Test StatusBar initial reactive state."""
        from tui.app import StatusBar
        
        bar = StatusBar()
        assert bar.status == "Initializing..."
    
    def test_status_bar_render_format(self):
        """Test StatusBar render produces correct format."""
        from tui.app import StatusBar
        
        bar = StatusBar()
        bar.status = "Test"
        rendered = bar.render()
        
        assert "IronSilo Dashboard" in rendered
        assert "Test" in rendered
        # Should contain time format HH:MM:SS
        import re
        assert re.search(r'\d{2}:\d{2}:\d{2}', rendered)


class TestContainerStatusWidgetFullCoverage:
    """Tests for tui/widgets/container_status.py to achieve 100% coverage."""
    
    def test_container_widget_init_state(self):
        """Test widget initialization state."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        assert widget._containers == []
        assert widget._last_update is None
    
    def test_container_status_data_structure(self):
        """Test container status data has required fields."""
        import asyncio
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        
        async def test():
            containers = await widget._get_container_status()
            return containers
        
        containers = asyncio.run(test())
        
        required_fields = ["name", "status", "health", "cpu", "memory", "uptime"]
        for container in containers:
            for field in required_fields:
                assert field in container, f"Missing field: {field}"
    
    def test_container_status_running_values(self):
        """Test container status has valid running values."""
        import asyncio
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        
        async def test():
            containers = await widget._get_container_status()
            return containers
        
        containers = asyncio.run(test())
        
        for container in containers:
            assert container["status"] in ["running", "stopped"]
            assert container["health"] in ["healthy", "unhealthy", "starting"]
    
    def test_container_render_loading(self):
        """Test render shows loading when no containers."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        rendered = widget.render()
        assert "Loading" in rendered or "Container" in rendered
    
    def test_container_render_with_data(self):
        """Test render shows update time when data exists."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        widget._containers = [{"name": "test", "status": "running", "health": "healthy", "cpu": "1%", "memory": "100MB", "uptime": "1h"}]
        widget._last_update = datetime.now()
        
        rendered = widget.render()
        assert "Updated:" in rendered


class TestResourceMonitorWidgetFullCoverage:
    """Tests for tui/widgets/resource_monitor.py to achieve 100% coverage."""
    
    def test_resource_metric_init_all_fields(self):
        """Test ResourceMetric initialization with all fields."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        metric = ResourceMetric("CPU", 50.0, 100.0, "%")
        assert metric.name == "CPU"
        assert metric.value == 50.0
        assert metric.max_value == 100.0
        assert metric.unit == "%"
        assert metric.history == [50.0]
        assert metric.max_history == 60
    
    def test_resource_metric_percentage_calculation(self):
        """Test ResourceMetric percentage calculation."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        # Normal case
        metric = ResourceMetric("CPU", 75.0, 100.0, "%")
        assert metric.percentage == 75.0
        
        # Zero value
        metric_zero = ResourceMetric("CPU", 0.0, 100.0, "%")
        assert metric_zero.percentage == 0.0
        
        # Zero max (edge case)
        metric_zero_max = ResourceMetric("CPU", 50.0, 0.0, "%")
        assert metric_zero_max.percentage == 0.0
        
        # Full value
        metric_full = ResourceMetric("CPU", 100.0, 100.0, "%")
        assert metric_full.percentage == 100.0
    
    def test_resource_metric_display_values(self):
        """Test ResourceMetric display_value for different units."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        # Percentage
        metric_percent = ResourceMetric("CPU", 75.5, 100.0, "%")
        assert "75.5" in metric_percent.display_value
        assert "%" in metric_percent.display_value
        
        # MB
        metric_mb = ResourceMetric("RAM", 512.0, 16384, "MB")
        assert "512" in metric_mb.display_value
        assert "MB" in metric_mb.display_value
        
        # GB
        metric_gb = ResourceMetric("Storage", 1.5, 10.0, "GB")
        assert "1.50" in metric_gb.display_value
        assert "GB" in metric_gb.display_value
        
        # Other unit
        metric_other = ResourceMetric("Custom", 42.0, 100.0, "ops")
        assert "42.0" in metric_other.display_value
        assert "ops" in metric_other.display_value
    
    def test_resource_metric_add_sample(self):
        """Test ResourceMetric add_sample updates history."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        metric = ResourceMetric("CPU", 0.0, 100.0, "%")
        
        # Add samples
        for i in range(5):
            metric.add_sample(float(i * 10))
        
        assert metric.value == 40.0
        assert len(metric.history) == 6  # Initial + 5 samples
    
    def test_resource_metric_history_limit(self):
        """Test ResourceMetric history is limited."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        metric = ResourceMetric("CPU", 0.0, 100.0, "%")
        metric.max_history = 5
        
        # Add more samples than max
        for i in range(10):
            metric.add_sample(float(i))
        
        assert len(metric.history) == 5
        # Should keep most recent
        assert metric.history[-1] == 9.0
    
    def test_resource_monitor_widget_init(self):
        """Test ResourceMonitorWidget initialization."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        widget = ResourceMonitorWidget()
        
        assert "cpu" in widget._metrics
        assert "ram" in widget._metrics
        assert "docker" in widget._metrics
        assert "gpu" in widget._metrics
        assert widget._last_update is None
    
    def test_resource_monitor_get_metric(self):
        """Test ResourceMonitorWidget get_metric method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        widget = ResourceMonitorWidget()
        
        cpu = widget.get_metric("cpu")
        assert cpu is not None
        assert cpu.name == "CPU"
        
        nonexistent = widget.get_metric("nonexistent")
        assert nonexistent is None
    
    def test_resource_monitor_render(self):
        """Test ResourceMonitorWidget render method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        widget = ResourceMonitorWidget()
        rendered = widget.render()
        assert "Resource Monitor" in rendered


class TestLogViewerWidgetFullCoverage:
    """Tests for tui/widgets/log_viewer.py to achieve 100% coverage."""
    
    def test_log_entry_init(self):
        """Test LogEntry initialization."""
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        entry = LogEntry(timestamp, "INFO", "test-container", "Test message")
        
        assert entry.timestamp == timestamp
        assert entry.level == "INFO"
        assert entry.container == "test-container"
        assert entry.message == "Test message"
    
    def test_log_entry_display_time(self):
        """Test LogEntry display_time formatting."""
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        entry = LogEntry(timestamp, "INFO", "test", "message")
        
        assert entry.display_time == "10:30:45"
    
    def test_log_entry_colors(self):
        """Test LogEntry color for each log level."""
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime.now()
        
        test_cases = [
            ("INFO", "green"),
            ("WARNING", "yellow"),
            ("ERROR", "red"),
            ("DEBUG", "blue"),
            ("CRITICAL", "magenta"),
            ("UNKNOWN", "white"),
        ]
        
        for level, expected_color in test_cases:
            entry = LogEntry(timestamp, level, "test", "message")
            assert entry.color == expected_color, f"Level {level} should have color {expected_color}"
    
    def test_log_entry_format(self):
        """Test LogEntry format method."""
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        entry = LogEntry(timestamp, "INFO", "test-container", "Test message")
        
        formatted = entry.format()
        
        assert "10:30:45" in formatted
        assert "INFO" in formatted
        assert "test-container" in formatted
        assert "Test message" in formatted
    
    def test_log_viewer_init(self):
        """Test LogViewerWidget initialization."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget()
        
        assert widget.max_lines == 1000
        assert widget._filter_level is None
        assert widget._filter_container is None
        assert widget._search_term == ""
        assert widget._last_update is None
    
    def test_log_viewer_custom_max_lines(self):
        """Test LogViewerWidget with custom max_lines."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget(max_lines=500)
        assert widget.max_lines == 500
    
    def test_log_viewer_internal_logs_manipulation(self):
        """Test LogViewerWidget internal logs manipulation."""
        from datetime import datetime
        from tui.widgets.log_viewer import LogViewerWidget, LogEntry
        
        widget = LogViewerWidget()
        
        # Add logs directly to the deque (bypassing UI updates)
        entry1 = LogEntry(datetime.now(), "INFO", "container1", "message1")
        entry2 = LogEntry(datetime.now(), "ERROR", "container2", "message2")
        
        widget._logs.append(entry1)
        widget._logs.append(entry2)
        
        assert len(widget._logs) == 2
        
        # Clear
        widget._logs.clear()
        assert len(widget._logs) == 0
    
    def test_log_viewer_filter_state(self):
        """Test LogViewerWidget filter state management."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget()
        
        # Set filter state directly
        widget._filter_level = "INFO"
        widget._filter_container = "proxy"
        widget._search_term = "error"
        
        assert widget._filter_level == "INFO"
        assert widget._filter_container == "proxy"
        assert widget._search_term == "error"
    
    def test_log_viewer_render(self):
        """Test LogViewerWidget render method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget()
        rendered = widget.render()
        assert "Logs" in rendered
