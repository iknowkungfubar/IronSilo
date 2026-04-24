"""
Unit tests for TUI module.

Tests cover:
- TUI app initialization
- CLI argument parsing
- Theme configuration
- Widget imports
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tui import __version__, main, monitor


class TestTUIVersion:
    """Test TUI version."""
    
    def test_version_exists(self):
        """Test that version is defined."""
        assert __version__ == "1.0.0"


class TestTUICLI:
    """Test TUI CLI functionality."""
    
    def test_main_with_version_flag(self, capsys):
        """Test main with --version flag."""
        with patch.object(sys, "argv", ["ironsilo", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "IronSilo TUI v1.0.0" in captured.out
    
    def test_main_with_default_args(self):
        """Test main with default arguments."""
        with patch.object(sys, "argv", ["ironsilo"]):
            with patch("tui.cli.launch_tui") as mock_launch:
                main()
                
                mock_launch.assert_called_once_with(refresh_interval=5, dark_mode=False)
    
    def test_main_with_custom_refresh(self):
        """Test main with custom refresh interval."""
        with patch.object(sys, "argv", ["ironsilo", "--refresh", "10"]):
            with patch("tui.cli.launch_tui") as mock_launch:
                main()
                
                mock_launch.assert_called_once_with(refresh_interval=10, dark_mode=False)
    
    def test_main_with_dark_mode(self):
        """Test main with dark mode flag."""
        with patch.object(sys, "argv", ["ironsilo", "--dark"]):
            with patch("tui.cli.launch_tui") as mock_launch:
                main()
                
                mock_launch.assert_called_once_with(refresh_interval=5, dark_mode=True)
    
    def test_monitor_function(self):
        """Test monitor function."""
        with patch("tui.cli.launch_tui") as mock_launch:
            monitor()
            
            mock_launch.assert_called_once_with()


class TestTUILaunch:
    """Test TUI launch functionality."""
    
    def test_launch_tui_success(self):
        """Test successful TUI launch."""
        from tui.cli import launch_tui
        
        mock_app = MagicMock()
        
        with patch("tui.app.IronSiloTUI", return_value=mock_app):
            launch_tui(refresh_interval=10, dark_mode=True)
            
            assert mock_app._refresh_interval == 10
            assert mock_app.dark is True
            mock_app.run.assert_called_once()
    
    def test_launch_tui_import_error(self, capsys):
        """Test TUI launch with import error."""
        from tui.cli import launch_tui
        
        with patch("tui.app.IronSiloTUI", side_effect=ImportError("textual not found")):
            with pytest.raises(SystemExit) as exc_info:
                launch_tui()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error: Required dependency missing" in captured.out
    
    def test_launch_tui_keyboard_interrupt(self, capsys):
        """Test TUI launch with keyboard interrupt."""
        from tui.cli import launch_tui
        
        mock_app = MagicMock()
        mock_app.run.side_effect = KeyboardInterrupt()
        
        with patch("tui.app.IronSiloTUI", return_value=mock_app):
            with pytest.raises(SystemExit) as exc_info:
                launch_tui()
            
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "Dashboard closed" in captured.out
    
    def test_launch_tui_generic_error(self, capsys):
        """Test TUI launch with generic error."""
        from tui.cli import launch_tui
        
        mock_app = MagicMock()
        mock_app.run.side_effect = RuntimeError("Something went wrong")
        
        with patch("tui.app.IronSiloTUI", return_value=mock_app):
            with pytest.raises(SystemExit) as exc_info:
                launch_tui()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error: Something went wrong" in captured.out


class TestTUITheme:
    """Test TUI theme configuration."""
    
    def test_ironsilo_theme_exists(self):
        """Test that IronSilo theme is defined."""
        from tui.theme import IRONSILO_THEME
        
        assert IRONSILO_THEME.name == "ironsilo"
        assert IRONSILO_THEME.primary == "#00ff88"
        assert IRONSILO_THEME.background == "#1a1a2e"
    
    def test_default_theme_exists(self):
        """Test that default theme is defined."""
        from tui.theme import DEFAULT_THEME
        
        assert DEFAULT_THEME.name == "default"
        assert DEFAULT_THEME.primary == "#007acc"


class TestTUIImports:
    """Test TUI module imports."""
    
    def test_import_app(self):
        """Test importing TUI app."""
        from tui.app import IronSiloTUI
        
        assert IronSiloTUI is not None
    
    def test_import_widgets(self):
        """Test importing TUI widgets."""
        from tui.widgets.container_status import ContainerStatusWidget
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        from tui.widgets.log_viewer import LogViewerWidget
        
        assert ContainerStatusWidget is not None
        assert ResourceMonitorWidget is not None
        assert LogViewerWidget is not None


class TestTUIStatusBar:
    """Test StatusBar widget."""
    
    def test_status_bar_render(self):
        """Test StatusBar render method."""
        from tui.app import StatusBar
        
        status_bar = StatusBar()
        status_bar.status = "Test Status"
        
        # The render method returns a string with the status
        rendered = status_bar.render()
        assert "Test Status" in rendered
        assert "IronSilo Dashboard" in rendered


class TestTUIApp:
    """Test IronSiloTUI app."""
    
    def test_app_class_exists(self):
        """Test that IronSiloTUI class exists."""
        from tui.app import IronSiloTUI
        
        assert IronSiloTUI is not None
    
    def test_app_title(self):
        """Test app title constant."""
        from tui.app import IronSiloTUI
        
        assert IronSiloTUI.TITLE == "IronSilo Dashboard"
    
    def test_app_bindings(self):
        """Test app key bindings."""
        from tui.app import IronSiloTUI
        
        # Check that bindings are defined (BINDINGS is a list of tuples)
        binding_keys = [b[0] for b in IronSiloTUI.BINDINGS]
        assert "q" in binding_keys
        assert "r" in binding_keys
        assert "c" in binding_keys
        assert "d" in binding_keys
    
    def test_app_css_defined(self):
        """Test that app CSS is defined."""
        from tui.app import IronSiloTUI
        
        assert IronSiloTUI.CSS is not None
        assert len(IronSiloTUI.CSS) > 0


class TestTUIWidgets:
    """Test TUI widget imports and basic structure."""
    
    def test_container_status_widget_exists(self):
        """Test that ContainerStatusWidget exists."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        assert ContainerStatusWidget is not None
    
    def test_resource_monitor_widget_exists(self):
        """Test that ResourceMonitorWidget exists."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        assert ResourceMonitorWidget is not None
    
    def test_log_viewer_widget_exists(self):
        """Test that LogViewerWidget exists."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        assert LogViewerWidget is not None
    
    def test_container_status_widget_has_refresh_data(self):
        """Test that ContainerStatusWidget has refresh_data method."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        assert hasattr(ContainerStatusWidget, 'refresh_data')
    
    def test_resource_monitor_widget_has_refresh_data(self):
        """Test that ResourceMonitorWidget has refresh_data method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        assert hasattr(ResourceMonitorWidget, 'refresh_data')
    
    def test_log_viewer_widget_has_clear(self):
        """Test that LogViewerWidget has clear method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        assert hasattr(LogViewerWidget, 'clear')


class TestResourceMetric:
    """Test ResourceMetric class."""
    
    def test_resource_metric_init(self):
        """Test ResourceMetric initialization."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        metric = ResourceMetric("CPU", 50.0, 100.0, "%")
        
        assert metric.name == "CPU"
        assert metric.value == 50.0
        assert metric.max_value == 100.0
        assert metric.unit == "%"
        assert metric.history == [50.0]
    
    def test_resource_metric_percentage(self):
        """Test ResourceMetric percentage calculation."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        metric = ResourceMetric("CPU", 75.0, 100.0, "%")
        assert metric.percentage == 75.0
        
        # Test with zero max
        metric_zero = ResourceMetric("CPU", 50.0, 0.0, "%")
        assert metric_zero.percentage == 0.0
    
    def test_resource_metric_display_value(self):
        """Test ResourceMetric display value formatting."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        # Percentage
        metric_percent = ResourceMetric("CPU", 75.5, 100.0, "%")
        assert metric_percent.display_value == "75.5%"
        
        # MB
        metric_mb = ResourceMetric("RAM", 512.0, 16384, "MB")
        assert metric_mb.display_value == "512MB"
        
        # GB
        metric_gb = ResourceMetric("Storage", 1.5, 10.0, "GB")
        assert metric_gb.display_value == "1.50GB"
        
        # Other unit
        metric_other = ResourceMetric("Custom", 42.0, 100.0, "ops")
        assert metric_other.display_value == "42.0ops"
    
    def test_resource_metric_add_sample(self):
        """Test adding samples to history."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        metric = ResourceMetric("CPU", 50.0, 100.0, "%")
        
        # Add samples
        metric.add_sample(60.0)
        metric.add_sample(70.0)
        
        assert metric.value == 70.0
        assert len(metric.history) == 3
        assert metric.history == [50.0, 60.0, 70.0]
    
    def test_resource_metric_history_limit(self):
        """Test that history is limited to max_history."""
        from tui.widgets.resource_monitor import ResourceMetric
        
        metric = ResourceMetric("CPU", 0.0, 100.0, "%")
        metric.max_history = 5
        
        # Add more samples than max
        for i in range(10):
            metric.add_sample(float(i))
        
        assert len(metric.history) == 5
        assert metric.history == [5.0, 6.0, 7.0, 8.0, 9.0]


class TestContainerStatusWidget:
    """Test ContainerStatusWidget class."""
    
    def test_container_status_widget_init(self):
        """Test ContainerStatusWidget initialization."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        
        assert widget._containers == []
        assert widget._last_update is None
    
    def test_container_status_widget_render_empty(self):
        """Test rendering when no containers loaded."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        
        # Without mounting, render should show loading
        rendered = widget.render()
        assert "Loading container status" in rendered
    
    def test_get_container_status(self):
        """Test getting container status (simulated)."""
        import asyncio
        from tui.widgets.container_status import ContainerStatusWidget
        
        widget = ContainerStatusWidget()
        
        # Run async method
        async def test():
            containers = await widget._get_container_status()
            return containers
        
        containers = asyncio.run(test())
        
        assert len(containers) == 7
        assert all("name" in c for c in containers)
        assert all("status" in c for c in containers)
        assert any(c["name"] == "llm-proxy" for c in containers)


class TestLogEntry:
    """Test LogEntry class."""
    
    def test_log_entry_init(self):
        """Test LogEntry initialization."""
        from datetime import datetime
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        entry = LogEntry(timestamp, "INFO", "test-container", "Test message")
        
        assert entry.timestamp == timestamp
        assert entry.level == "INFO"
        assert entry.container == "test-container"
        assert entry.message == "Test message"
    
    def test_log_entry_display_time(self):
        """Test LogEntry display time formatting."""
        from datetime import datetime
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        entry = LogEntry(timestamp, "INFO", "test", "message")
        
        assert entry.display_time == "10:30:45"
    
    def test_log_entry_color(self):
        """Test LogEntry color for different log levels."""
        from datetime import datetime
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime.now()
        
        # Test different log levels
        assert LogEntry(timestamp, "INFO", "test", "msg").color == "green"
        assert LogEntry(timestamp, "WARNING", "test", "msg").color == "yellow"
        assert LogEntry(timestamp, "ERROR", "test", "msg").color == "red"
        assert LogEntry(timestamp, "DEBUG", "test", "msg").color == "blue"
        assert LogEntry(timestamp, "CRITICAL", "test", "msg").color == "magenta"
        assert LogEntry(timestamp, "UNKNOWN", "test", "msg").color == "white"
    
    def test_log_entry_format(self):
        """Test LogEntry format method."""
        from datetime import datetime
        from tui.widgets.log_viewer import LogEntry
        
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        entry = LogEntry(timestamp, "INFO", "test-container", "Test message")
        
        formatted = entry.format()
        
        assert "10:30:45" in formatted
        assert "INFO" in formatted
        assert "test-container" in formatted
        assert "Test message" in formatted


class TestLogViewerWidget:
    """Test LogViewerWidget class."""
    
    def test_log_viewer_init(self):
        """Test LogViewerWidget initialization."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget()
        
        assert widget.max_lines == 1000
        assert widget._filter_level is None
        assert widget._filter_container is None
        assert widget._search_term == ""
        assert widget._last_update is None
    
    def test_log_viewer_init_custom_max(self):
        """Test LogViewerWidget with custom max_lines."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget(max_lines=500)
        
        assert widget.max_lines == 500
    
    def test_log_viewer_internal_state(self):
        """Test LogViewerWidget internal state management."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget()
        
        # Test filter state
        widget._filter_level = "INFO"
        widget._filter_container = "proxy"
        widget._search_term = "test"
        
        assert widget._filter_level == "INFO"
        assert widget._filter_container == "proxy"
        assert widget._search_term == "test"
    
    def test_log_viewer_render_empty(self):
        """Test rendering when no logs loaded."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        widget = LogViewerWidget()
        
        rendered = widget.render()
        assert "Logs (Updated:" in rendered
    
    def test_log_entry_add_to_logs(self):
        """Test adding log entries to internal deque."""
        from datetime import datetime
        from tui.widgets.log_viewer import LogEntry, LogViewerWidget
        
        widget = LogViewerWidget()
        
        # Manually add to the logs deque (bypassing UI)
        entry = LogEntry(datetime.now(), "INFO", "test", "message")
        widget._logs.append(entry)
        
        assert len(widget._logs) == 1
        assert widget._logs[0].level == "INFO"


class TestResourceMonitorWidget:
    """Test ResourceMonitorWidget class."""
    
    def test_resource_monitor_init(self):
        """Test ResourceMonitorWidget initialization."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        widget = ResourceMonitorWidget()
        
        assert "cpu" in widget._metrics
        assert "ram" in widget._metrics
        assert "docker" in widget._metrics
        assert "gpu" in widget._metrics
        assert widget._last_update is None
    
    def test_resource_monitor_get_metric(self):
        """Test getting specific metric."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        widget = ResourceMonitorWidget()
        
        cpu_metric = widget.get_metric("cpu")
        assert cpu_metric is not None
        assert cpu_metric.name == "CPU"
        
        # Non-existent metric
        assert widget.get_metric("nonexistent") is None
    
    def test_resource_monitor_render(self):
        """Test rendering resource monitor."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        widget = ResourceMonitorWidget()
        
        rendered = widget.render()
        assert "Resource Monitor (Updated:" in rendered


class TestIronSiloTUIApp:
    """Test IronSiloTUI app methods."""
    
    def test_app_class_attributes(self):
        """Test app class attributes."""
        from tui.app import IronSiloTUI
        
        # Test class attributes
        assert IronSiloTUI.TITLE == "IronSilo Dashboard"
        assert "q" in [b[0] for b in IronSiloTUI.BINDINGS]
        assert "r" in [b[0] for b in IronSiloTUI.BINDINGS]
        assert "c" in [b[0] for b in IronSiloTUI.BINDINGS]
        assert "d" in [b[0] for b in IronSiloTUI.BINDINGS]
        assert IronSiloTUI.CSS is not None
        assert len(IronSiloTUI.CSS) > 0
    
    def test_app_init(self):
        """Test app initialization."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        
        assert app._refresh_interval == 5
        assert app._last_refresh > 0
    
    def test_app_action_refresh(self):
        """Test app refresh action method exists."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        
        # Just verify the method exists
        assert hasattr(app, 'action_refresh')
        assert callable(app.action_refresh)
    
    def test_app_action_clear_logs(self):
        """Test app clear logs action method exists."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        
        # Just verify the method exists
        assert hasattr(app, 'action_clear_logs')
        assert callable(app.action_clear_logs)
    
    def test_app_action_toggle_dark(self):
        """Test app toggle dark action method exists."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        
        # Just verify the method exists
        assert hasattr(app, 'action_toggle_dark')
        assert callable(app.action_toggle_dark)
    
    def test_app_refresh_data_method(self):
        """Test app refresh_data method exists."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        
        # Just verify the method exists
        assert hasattr(app, 'refresh_data')
        assert callable(app.refresh_data)


class TestStatusBar:
    """Test StatusBar widget."""
    
    def test_status_bar_render(self):
        """Test StatusBar render method."""
        from tui.app import StatusBar
        
        status_bar = StatusBar()
        status_bar.status = "Test Status"
        
        rendered = status_bar.render()
        
        assert "IronSilo Dashboard" in rendered
        assert "Test Status" in rendered
    
    def test_status_bar_reactive(self):
        """Test StatusBar reactive status property."""
        from tui.app import StatusBar
        
        status_bar = StatusBar()
        
        # Initial value
        assert status_bar.status == "Initializing..."
        
        # Update
        status_bar.status = "Running"
        assert status_bar.status == "Running"
