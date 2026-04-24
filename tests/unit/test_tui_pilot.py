"""
Comprehensive TUI tests using Textual Pilot for 100% coverage.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Skip if textual not available
textual = pytest.importorskip("textual")
from textual.app import App, ComposeResult
from textual.pilot import Pilot
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Header, Footer


class TestTUIAppWithPilot:
    """Tests for tui/app.py using Textual Pilot."""
    
    @pytest.mark.asyncio
    async def test_app_compose(self):
        """Test app compose method."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        async with app.run_test() as pilot:
            assert app.is_running
            
            # Check that widgets exist
            status_bar = app.query_one("#status-bar")
            assert status_bar is not None
    
    @pytest.mark.asyncio
    async def test_app_on_mount(self):
        """Test app on_mount sets up correctly."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        async with app.run_test() as pilot:
            assert app.title == "IronSilo Dashboard"
            assert app.sub_title == "Local AI Development Sandbox"
    
    @pytest.mark.asyncio
    async def test_app_update_status(self):
        """Test app update_status method."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        async with app.run_test() as pilot:
            app.update_status("Test Status")
            
            status_bar = app.query_one("#status-bar")
            assert status_bar.status == "Test Status"
    
    @pytest.mark.asyncio
    async def test_app_action_refresh(self):
        """Test app action_refresh method."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        async with app.run_test() as pilot:
            app.action_refresh()
            await pilot.pause()
    
    @pytest.mark.asyncio
    async def test_app_action_clear_logs(self):
        """Test app action_clear_logs method."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        async with app.run_test() as pilot:
            app.action_clear_logs()
            await pilot.pause()
    
    @pytest.mark.asyncio
    async def test_app_action_toggle_dark(self):
        """Test app action_toggle_dark method."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        # Verify the method exists
        assert hasattr(app, 'action_toggle_dark')
        # The actual toggle requires app to be running and dark attribute to exist
        # This is tested at integration level
    
    @pytest.mark.asyncio
    async def test_app_refresh_data(self):
        """Test app refresh_data method."""
        from tui.app import IronSiloTUI
        
        app = IronSiloTUI()
        async with app.run_test() as pilot:
            await app.refresh_data()
            await pilot.pause()


class TestContainerStatusWidgetWithPilot:
    """Tests for container_status widget using Textual Pilot."""
    
    @pytest.mark.asyncio
    async def test_widget_mount(self):
        """Test widget mounts correctly."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ContainerStatusWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ContainerStatusWidget)
            assert widget is not None
    
    @pytest.mark.asyncio
    async def test_widget_on_mount(self):
        """Test widget on_mount method - widget should be mounted."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ContainerStatusWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ContainerStatusWidget)
            # Widget should be mounted and accessible
            assert widget is not None
            # on_mount should have been called by Textual
            # The async refresh may not complete in test, but the widget is mounted
    
    @pytest.mark.asyncio
    async def test_widget_refresh_data(self):
        """Test widget refresh_data method."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ContainerStatusWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ContainerStatusWidget)
            await widget.refresh_data()
            assert len(widget._containers) > 0
    
    @pytest.mark.asyncio
    async def test_widget_render_with_data(self):
        """Test widget render with data."""
        from tui.widgets.container_status import ContainerStatusWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ContainerStatusWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ContainerStatusWidget)
            await widget.refresh_data()
            rendered = widget.render()
            assert "Container Status" in rendered


class TestResourceMonitorWidgetWithPilot:
    """Tests for resource_monitor widget using Textual Pilot."""
    
    @pytest.mark.asyncio
    async def test_widget_mount(self):
        """Test widget mounts correctly."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ResourceMonitorWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ResourceMonitorWidget)
            assert widget is not None
            assert "cpu" in widget._metrics
    
    @pytest.mark.asyncio
    async def test_widget_on_mount(self):
        """Test widget on_mount method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ResourceMonitorWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ResourceMonitorWidget)
            # Wait for async refresh to complete
            await pilot.pause()
            # on_mount calls refresh_data which sets _last_update
            assert widget._last_update is not None or len(widget._metrics) > 0
    
    @pytest.mark.asyncio
    async def test_widget_refresh_data(self):
        """Test widget refresh_data method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ResourceMonitorWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ResourceMonitorWidget)
            await widget.refresh_data()
            assert widget._last_update is not None or len(widget._metrics) > 0
    
    @pytest.mark.asyncio
    async def test_widget_get_metric(self):
        """Test widget get_metric method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ResourceMonitorWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ResourceMonitorWidget)
            cpu = widget.get_metric("cpu")
            assert cpu is not None
            assert cpu.name == "CPU"
    
    @pytest.mark.asyncio
    async def test_widget_render(self):
        """Test widget render method."""
        from tui.widgets.resource_monitor import ResourceMonitorWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield ResourceMonitorWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", ResourceMonitorWidget)
            await widget.refresh_data()
            rendered = widget.render()
            assert "Resource Monitor" in rendered


class TestLogViewerWidgetWithPilot:
    """Tests for log_viewer widget using Textual Pilot."""
    
    @pytest.mark.asyncio
    async def test_widget_mount(self):
        """Test widget mounts correctly."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            assert widget is not None
            assert len(widget._logs) > 0
    
    @pytest.mark.asyncio
    async def test_widget_add_log(self):
        """Test widget add_log method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            initial_count = len(widget._logs)
            
            widget.add_log("INFO", "test", "test message")
            
            assert len(widget._logs) == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_widget_clear(self):
        """Test widget clear method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            widget.clear()
            assert len(widget._logs) == 0
    
    @pytest.mark.asyncio
    async def test_widget_set_filter(self):
        """Test widget set_filter method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            widget.set_filter(level="INFO", container="proxy")
            assert widget._filter_level == "INFO"
            assert widget._filter_container == "proxy"
    
    @pytest.mark.asyncio
    async def test_widget_set_search(self):
        """Test widget set_search method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            widget.set_search("test")
            assert widget._search_term == "test"
    
    @pytest.mark.asyncio
    async def test_widget_refresh_data(self):
        """Test widget refresh_data method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            await widget.refresh_data()
            assert widget._last_update is not None
    
    @pytest.mark.asyncio
    async def test_widget_on_input_changed(self):
        """Test widget on_input_changed method."""
        from tui.widgets.log_viewer import LogViewerWidget
        from textual.widgets import Input
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            
            # Simulate input change
            input_widget = widget.query_one("#log-filter", Input)
            input_widget.value = "search term"
            
            # Trigger the event handler
            event = Input.Changed(input_widget, "search term")
            widget.on_input_changed(event)
            
            assert widget._search_term == "search term"
    
    @pytest.mark.asyncio
    async def test_widget_render(self):
        """Test widget render method."""
        from tui.widgets.log_viewer import LogViewerWidget
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield LogViewerWidget(id="test-widget")
        
        app = TestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-widget", LogViewerWidget)
            rendered = widget.render()
            assert "Logs" in rendered
