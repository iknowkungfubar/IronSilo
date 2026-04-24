"""
Unit tests for TUI module.

Tests cover:
- CLI interface
- App structure
- Widget components
- Theme configuration

Note: TUI tests are skipped if textual is not installed since it's an optional dependency.
"""

import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Check if textual is available
try:
    import textual
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False


pytestmark = pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")


class TestTUIApp:
    """Test TUI app module."""
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_app_imports(self):
        """Test app module imports correctly."""
        from tui import app
        assert app is not None
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_iron_silo_tui_exists(self):
        """Test IronSiloTUI class exists in app module."""
        from tui.app import IronSiloTUI
        assert IronSiloTUI is not None
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_status_bar_exists(self):
        """Test StatusBar class exists."""
        from tui.app import StatusBar
        assert StatusBar is not None


class TestTUICli:
    """Test TUI CLI module."""
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_cli_main_exists(self):
        """Test main function exists."""
        from tui.cli import main
        assert callable(main)
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_cli_monitor_exists(self):
        """Test monitor function exists."""
        from tui.cli import monitor
        assert callable(monitor)
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_cli_launch_tui_exists(self):
        """Test launch_tui function exists."""
        from tui.cli import launch_tui
        assert callable(launch_tui)


class TestTUITheme:
    """Test TUI theme module."""
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_theme_exists(self):
        """Test theme is defined."""
        from tui.theme import IRONSILO_THEME
        assert IRONSILO_THEME is not None


class TestTUIWidgets:
    """Test TUI widgets."""
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_container_status_widget_exists(self):
        """Test ContainerStatusWidget exists."""
        from tui.widgets.container_status import ContainerStatusWidget
        assert ContainerStatusWidget is not None
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_log_viewer_widget_exists(self):
        """Test LogViewerWidget exists."""
        from tui.widgets.log_viewer import LogViewerWidget
        assert LogViewerWidget is not None
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_resource_monitor_widget_exists(self):
        """Test ResourceMonitorWidget exists."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        assert ResourceMonitorWidget is not None


class TestTUIAppBindings:
    """Test app key bindings."""
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_app_has_bindings(self):
        """Test app defines key bindings."""
        from tui.app import IronSiloTUI
        assert hasattr(IronSiloTUI, 'BINDINGS')
        assert IronSiloTUI.BINDINGS is not None
        assert len(IronSiloTUI.BINDINGS) > 0


class TestTUIAppCSS:
    """Test app CSS."""
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_app_has_css(self):
        """Test app defines CSS."""
        from tui.app import IronSiloTUI
        assert hasattr(IronSiloTUI, 'CSS')
        assert IronSiloTUI.CSS is not None
        assert "Screen" in IronSiloTUI.CSS


class TestTUIAppTitle:
    """Test app title."""
    
    @pytest.mark.skipif(not HAS_TEXTUAL, reason="textual not installed")
    def test_app_has_title(self):
        """Test app has title defined."""
        from tui.app import IronSiloTUI
        assert hasattr(IronSiloTUI, 'TITLE')
        assert IronSiloTUI.TITLE == "IronSilo Dashboard"


class TestTUIModuleStructure:
    """Test TUI module structure without importing textual."""
    
    def test_tui_init_exists(self):
        """Test tui/__init__.py exists."""
        from pathlib import Path
        init_path = Path(__file__).parent.parent.parent / "tui" / "__init__.py"
        assert init_path.exists()
    
    def test_tui_app_exists(self):
        """Test tui/app.py exists."""
        from pathlib import Path
        app_path = Path(__file__).parent.parent.parent / "tui" / "app.py"
        assert app_path.exists()
    
    def test_tui_cli_exists(self):
        """Test tui/cli.py exists."""
        from pathlib import Path
        cli_path = Path(__file__).parent.parent.parent / "tui" / "cli.py"
        assert cli_path.exists()
    
    def test_tui_theme_exists(self):
        """Test tui/theme.py exists."""
        from pathlib import Path
        theme_path = Path(__file__).parent.parent.parent / "tui" / "theme.py"
        assert theme_path.exists()
    
    def test_tui_widgets_exist(self):
        """Test tui/widgets directory exists."""
        from pathlib import Path
        widgets_dir = Path(__file__).parent.parent.parent / "tui" / "widgets"
        assert widgets_dir.exists()
        assert widgets_dir.is_dir()
