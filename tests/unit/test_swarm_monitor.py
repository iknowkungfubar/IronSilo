"""
Comprehensive unit tests for tui/widgets/swarm_monitor.py.

Tests cover:
- SwarmAction data class
- SwarmMonitorWidget initialization
- WebSocket connection handling
- Action display updates
- Connection status display
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if "textual" not in sys.modules:
    pytest.skip("textual not installed", allow_module_level=True)


class TestSwarmAction:
    """Test suite for SwarmAction data class."""

    def test_swarm_action_creation(self):
        """Test SwarmAction initializes correctly."""
        from tui.widgets.swarm_monitor import SwarmAction

        action = SwarmAction(
            action="Navigating to URL",
            agent="worker-1",
            timestamp=1234567890.0
        )

        assert action.action == "Navigating to URL"
        assert action.agent == "worker-1"
        assert action.timestamp == 1234567890.0

    def test_swarm_action_time_str(self):
        """Test SwarmAction formats timestamp correctly."""
        from tui.widgets.swarm_monitor import SwarmAction

        action = SwarmAction(
            action="Test",
            agent="test",
            timestamp=1234567890.0
        )

        dt = datetime.fromtimestamp(1234567890.0)
        expected = dt.strftime("%H:%M:%S")

        assert action.time_str == expected

    def test_swarm_action_time_str_format(self):
        """Test SwarmAction time_str is HH:MM:SS format."""
        from tui.widgets.swarm_monitor import SwarmAction

        action = SwarmAction(
            action="Test",
            agent="test",
            timestamp=1700000000.0
        )

        assert len(action.time_str) == 8
        assert ":" in action.time_str


class TestSwarmMonitorWidget:
    """Test suite for SwarmMonitorWidget."""

    @pytest.fixture
    def widget(self):
        """Create a SwarmMonitorWidget instance."""
        from tui.widgets.swarm_monitor import SwarmMonitorWidget
        return SwarmMonitorWidget()

    def test_widget_initialization(self, widget):
        """Test widget initializes with correct defaults."""
        assert widget._actions == []
        assert widget._ws_task is None
        assert widget._connected is False
        assert widget._ws_url == "ws://localhost:8095/ws/swarm"

    def test_widget_compose_yields_static(self, widget):
        """Test widget compose yields display static."""
        from textual.widgets import Static

        children = list(widget.compose())

        assert len(children) == 1
        assert isinstance(children[0], Static)
        assert children[0].id == "swarm-display"

    def test_widget_render_returns_title(self, widget):
        """Test widget render returns title."""
        assert widget.render() == "Swarm Monitor"

    def test_add_status_creates_action(self, widget):
        """Test _add_status adds action to history."""
        widget._add_status("Test status message")

        assert len(widget._actions) == 1
        assert widget._actions[0].action == "Test status message"
        assert widget._actions[0].agent == "system"

    def test_add_status_respects_limit(self, widget):
        """Test _add_status doesn't exceed 50 actions."""
        widget._actions = [
            type("Action", (), {"action": f"action_{i}", "agent": "test", "timestamp": i})()
            for i in range(50)
        ]

        widget._add_status("New status")

        assert len(widget._actions) == 50
        assert widget._actions[-1].action == "New status"

    def test_update_display_updates_children(self, widget):
        """Test _update_display calls update on display widget."""
        widget._connected = True
        widget._actions = [
            type("Action", (), {"action": "Test action", "agent": "test", "timestamp": time.time(), "time_str": lambda self: "12:00:00"})()
        ]

        mock_display = MagicMock()
        widget.query_one = MagicMock(return_value=mock_display)

        widget._update_display()

        mock_display.update.assert_called_once()


class TestSwarmMonitorWidgetWebSocket:
    """Test suite for SwarmMonitorWidget WebSocket handling."""

    @pytest.fixture
    def widget(self):
        """Create a SwarmMonitorWidget instance."""
        from tui.widgets.swarm_monitor import SwarmMonitorWidget
        return SwarmMonitorWidget()

    def test_start_websocket_sets_task(self, widget):
        """Test _start_websocket sets _ws_task."""
        with patch.object(widget, "watch_socket", new_callable=AsyncMock):
            widget._start_websocket()

            assert widget._ws_task is not None

    def test_stop_websocket_cancels_task(self, widget):
        """Test _stop_websocket cancels the task."""
        mock_task = MagicMock()
        widget._ws_task = mock_task

        widget._stop_websocket()

        mock_task.cancel.assert_called_once()
        assert widget._ws_task is None

    def test_stop_websocket_handles_none(self, widget):
        """Test _stop_websocket handles None task."""
        widget._ws_task = None

        widget._stop_websocket()

        assert widget._ws_task is None


class TestSwarmMonitorWidgetAsync:
    """Async tests for SwarmMonitorWidget."""

    @pytest.fixture
    def widget(self):
        """Create a SwarmMonitorWidget instance."""
        from tui.widgets.swarm_monitor import SwarmMonitorWidget
        return SwarmMonitorWidget()

    @pytest.mark.asyncio
    async def test_watch_socket_connection_success(self, widget):
        """Test watch_socket handles successful connection."""
        import websockets

        mock_ws = MagicMock()
        mock_ws.recv = AsyncMock(side_effect=[
            json.dumps({"type": "connected", "current_action": "idle", "timestamp": time.time()}),
            websockets.exceptions.ConnectionClosed(None, None)
        ])

        with patch("websockets.connect", AsyncMock(return_value=mock_ws)) as mock_connect:
            with patch.object(widget, "_update_display"):
                with patch.object(widget, "_add_status"):
                    try:
                        await widget.watch_socket()
                    except Exception:
                        pass

                    mock_connect.assert_called_once_with(widget._ws_url)

    @pytest.mark.asyncio
    async def test_watch_socket_processes_action_messages(self, widget):
        """Test watch_socket processes action messages."""
        import websockets

        action_msg = {
            "type": "action",
            "action": "DOM evaluated",
            "agent": "worker-1",
            "timestamp": time.time()
        }

        mock_ws = MagicMock()
        mock_ws.recv = AsyncMock(side_effect=[
            json.dumps({"type": "connected"}),
            json.dumps(action_msg),
            websockets.exceptions.ConnectionClosed(None, None)
        ])

        with patch("websockets.connect", AsyncMock(return_value=mock_ws)):
            with patch.object(widget, "_update_display"):
                try:
                    await widget.watch_socket()
                except Exception:
                    pass

                assert len(widget._actions) == 1
                assert widget._actions[0].action == "DOM evaluated"

    @pytest.mark.asyncio
    async def test_watch_socket_handles_connection_error(self, widget):
        """Test watch_socket handles connection errors gracefully."""
        with patch("websockets.connect", AsyncMock(side_effect=Exception("Connection failed"))):
            with patch.object(widget, "_add_status"):
                with patch.object(widget, "_update_display"):
                    try:
                        await widget.watch_socket()
                    except Exception:
                        pass

                    assert widget._connected is False


class TestSwarmMonitorWidgetDisplay:
    """Tests for SwarmMonitorWidget display formatting."""

    @pytest.fixture
    def widget(self):
        """Create a SwarmMonitorWidget instance."""
        from tui.widgets.swarm_monitor import SwarmMonitorWidget
        return SwarmMonitorWidget()

    def test_update_display_shows_connected(self, widget):
        """Test _update_display shows connected status."""
        widget._connected = True
        widget._actions = []

        display = MagicMock()
        widget.query_one = MagicMock(return_value=display)

        widget._update_display()

        content = display.update.call_args[0][0]
        assert "[green]● Connected[/green]" in content

    def test_update_display_shows_disconnected(self, widget):
        """Test _update_display shows disconnected status."""
        widget._connected = False
        widget._actions = []

        display = MagicMock()
        widget.query_one = MagicMock(return_value=display)

        widget._update_display()

        content = display.update.call_args[0][0]
        assert "[red]○ Disconnected[/red]" in content

    def test_update_display_shows_actions(self, widget):
        """Test _update_display shows action list."""
        widget._connected = True
        widget._actions = [
            type("Action", (), {"action": "Action 1", "agent": "agent1", "timestamp": 1000, "time_str": lambda s: "12:00:00"})(),
            type("Action", (), {"action": "Action 2", "agent": "agent2", "timestamp": 2000, "time_str": lambda s: "12:01:00"})(),
        ]

        display = MagicMock()
        widget.query_one = MagicMock(return_value=display)

        widget._update_display()

        content = display.update.call_args[0][0]
        assert "Action 1" in content
        assert "Action 2" in content
        assert "agent1" in content


class TestSwarmMonitorWidgetLifecycle:
    """Tests for SwarmMonitorWidget lifecycle methods."""

    @pytest.fixture
    def widget(self):
        """Create a SwarmMonitorWidget instance."""
        from tui.widgets.swarm_monitor import SwarmMonitorWidget
        return SwarmMonitorWidget()

    def test_on_mount_starts_websocket(self, widget):
        """Test on_mount starts WebSocket connection."""
        with patch.object(widget, "_start_websocket") as mock_start:
            widget.on_mount()

            mock_start.assert_called_once()

    def test_on_unmount_stops_websocket(self, widget):
        """Test on_unmount stops WebSocket connection."""
        mock_task = MagicMock()
        widget._ws_task = mock_task

        with patch.object(widget, "_stop_websocket") as mock_stop:
            widget.on_unmount()

            mock_stop.assert_called_once()


class TestSwarmMonitorWidgetImports:
    """Tests for module imports."""

    def test_swarm_monitor_imports_successfully(self):
        """Test swarm_monitor module imports without error."""
        from tui.widgets.swarm_monitor import SwarmMonitorWidget, SwarmAction

        assert SwarmMonitorWidget is not None
        assert SwarmAction is not None

    def test_swarm_monitor_has_correct_base_class(self):
        """Test SwarmMonitorWidget inherits from Static."""
        from textual.widgets import Static
        from tui.widgets.swarm_monitor import SwarmMonitorWidget

        assert issubclass(SwarmMonitorWidget, Static)

    def test_swarm_monitor_composes_result(self):
        """Test SwarmMonitorWidget.compose returns ComposeResult."""
        from tui.widgets.swarm_monitor import SwarmMonitorWidget
        from textual.app import ComposeResult

        widget = SwarmMonitorWidget()
        result = widget.compose()

        assert isinstance(result, ComposeResult)
