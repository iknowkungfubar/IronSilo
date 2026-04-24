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
    
    def test_container_status_widget_has_refresh(self):
        """Test that ContainerStatusWidget has refresh method."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        assert hasattr(ContainerStatusWidget, 'refresh')
    
    def test_resource_monitor_widget_has_refresh(self):
        """Test that ResourceMonitorWidget has refresh method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        assert hasattr(ResourceMonitorWidget, 'refresh')
    
    def test_log_viewer_widget_has_clear(self):
        """Test that LogViewerWidget has clear method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        assert hasattr(LogViewerWidget, 'clear')
