"""
Comprehensive unit tests for swarm/main.py FastAPI server.

Tests cover:
- SwarmState class behavior
- /status endpoint
- /ws/swarm WebSocket handling
- /history endpoint
- Broadcast functionality
"""

import asyncio
import json
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestSwarmState:
    """Test suite for SwarmState class."""

    def test_swarm_state_defaults(self):
        """Test SwarmState initializes with correct defaults."""
        from swarm.main import SwarmState

        state = SwarmState()

        assert state.current_action == "idle"
        assert state.action_history == []
        assert len(state.connected_clients) == 0
        assert isinstance(state.lock, asyncio.Lock)

    def test_swarm_state_mutable(self):
        """Test SwarmState can track changes."""
        from swarm.main import SwarmState

        state = SwarmState()

        state.current_action = "Navigating to URL"
        state.action_history.append({"action": "test", "timestamp": time.time(), "agent": "test"})

        assert state.current_action == "Navigating to URL"
        assert len(state.action_history) == 1


class TestStatusEndpoint:
    """Test suite for /status endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from swarm.main import app
        return TestClient(app)

    def test_status_returns_running(self, client):
        """Test status endpoint returns running state."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_status_returns_current_action(self, client):
        """Test status includes current action."""
        from swarm.main import state

        state.current_action = "Test Action"

        response = client.get("/status")

        data = response.json()
        assert data["current_action"] == "Test Action"

    def test_status_returns_timestamp(self, client):
        """Test status includes timestamp."""
        response = client.get("/status")

        data = response.json()
        assert "timestamp" in data
        assert isinstance(data["timestamp"], (int, float))

    def test_status_returns_connected_agents_count(self, client):
        """Test status includes connected agents count."""
        response = client.get("/status")

        data = response.json()
        assert "connected_agents" in data
        assert isinstance(data["connected_agents"], int)


class TestHistoryEndpoint:
    """Test suite for /history endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from swarm.main import app
        return TestClient(app)

    def test_history_returns_list(self, client):
        """Test history endpoint returns a list."""
        response = client.get("/history")

        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "count" in data

    def test_history_returns_recent_actions(self, client):
        """Test history returns most recent actions."""
        from swarm.main import state

        state.action_history = [
            {"action": "first", "timestamp": 1000, "agent": "a"},
            {"action": "second", "timestamp": 2000, "agent": "b"},
        ]

        response = client.get("/history")

        data = response.json()
        assert data["count"] == 2

    def test_history_returns_last_50(self, client):
        """Test history endpoint returns only last 50 items."""
        from swarm.main import state

        state.action_history = []
        state.action_history.extend([
            {"action": f"action_{i}", "timestamp": i * 1000, "agent": "test"}
            for i in range(60)
        ])

        response = client.get("/history")

        data = response.json()
        assert data["count"] == 60
        assert len(data["history"]) == 50
        assert data["history"][0]["action"] == "action_10"


class TestWebSocketEndpoint:
    """Test suite for /ws/swarm WebSocket endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from swarm.main import app
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_websocket_accepts_connection(self, client):
        """Test WebSocket endpoint accepts connections."""
        with client.websocket_connect("/ws/swarm") as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert "current_action" in data

    @pytest.mark.asyncio
    async def test_websocket_sends_action_updates_state(self, client):
        """Test WebSocket action message updates shared state."""
        from swarm.main import state

        state.action_history = []
        state.current_action = "idle"

        with client.websocket_connect("/ws/swarm") as ws:
            ws.send_json({
                "type": "action",
                "action": "Navigating to URL",
                "agent": "test-agent"
            })

            await asyncio.sleep(0.2)

            assert state.current_action == "Navigating to URL"

    @pytest.mark.asyncio
    async def test_websocket_receives_confirmation(self, client):
        """Test WebSocket sends back confirmation."""
        with client.websocket_connect("/ws/swarm") as ws:
            ws.send_json({
                "type": "action",
                "action": "Test action",
                "agent": "test"
            })

            data = ws.receive_json(timeout=2.0)
            assert data["type"] == "action"
            assert "timestamp" in data


class TestSwarmMainIntegration:
    """Integration tests for swarm main module."""

    def test_all_endpoints_exist(self):
        """Test all expected endpoints are registered."""
        from swarm.main import app

        routes = [route.path for route in app.routes]

        assert "/status" in routes
        assert "/ws/swarm" in routes
        assert "/history" in routes

    def test_app_title(self):
        """Test FastAPI app has correct title."""
        from swarm.main import app

        assert app.title == "Swarm Service API"
        assert app.version == "1.0.0"


class TestMainExecution:
    """Test main module execution."""

    def test_main_imports_without_error(self):
        """Test main.py can be imported."""
        from swarm import main

        assert hasattr(main, "app")
        assert hasattr(main, "state")

    def test_structlog_configured(self):
        """Test structlog is properly configured."""
        from swarm.main import logger

        assert logger is not None

    def test_swarm_state_exported(self):
        """Test SwarmState is accessible."""
        from swarm.main import SwarmState, state

        assert isinstance(state, SwarmState)
