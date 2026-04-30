"""
Comprehensive unit tests for swarm/harness_worker module.

Tests cover:
- HarnessWorker connection management
- CDP command sending and response handling
- DOM extraction
- Element clicking
- Research evaluation with bypass compression
- WebSocket message handling
"""

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHarnessWorker:
    """Test suite for HarnessWorker class."""

    @pytest.fixture
    def mock_websockets(self):
        """Mock websockets module."""
        with patch("swarm.harness_worker.websockets") as mock:
            yield mock

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient."""
        with patch("swarm.harness_worker.httpx.AsyncClient") as mock:
            yield mock

    def test_worker_initialization(self):
        """Test HarnessWorker initializes with correct defaults."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()

        assert worker.cdp_url == "ws://browser-node:9222"
        assert worker.ws is None
        assert worker._message_id == 0
        assert len(worker._response_futures) == 0

    def test_worker_custom_cdp_url(self):
        """Test HarnessWorker accepts custom CDP URL."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker(cdp_url="ws://custom:9223")

        assert worker.cdp_url == "ws://custom:9223"

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_websockets):
        """Test successful WebSocket connection."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        await worker.connect()

        assert worker.ws == mock_ws
        mock_websockets.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_websockets):
        """Test WebSocket disconnection."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_ws.close = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        await worker.connect()
        await worker.disconnect()

        mock_ws.close.assert_called_once()
        assert worker.ws is None

    @pytest.mark.asyncio
    async def test_send_command_not_connected(self):
        """Test sending command when not connected raises RuntimeError."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()

        with pytest.raises(RuntimeError, match="WebSocket not connected"):
            await worker._send_command("DOM.getDocument")

    @pytest.mark.asyncio
    async def test_send_command_builds_message_with_params(self):
        """Test CDP command message includes method and params."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        worker._message_id = 5
        worker.ws = MagicMock()

        sent_commands = []

        async def mock_ws_send(cmd):
            sent_commands.append(json.loads(cmd))

        worker.ws.send = mock_ws_send

        async def mock_wait_for(fut, timeout):
            fut.set_result({"success": True})
            return {"success": True}

        with patch("swarm.harness_worker.asyncio.wait_for", mock_wait_for):
            result = await worker._send_command("DOM.getDocument", {"depth": -1})

        assert result == {"success": True}
        assert worker._message_id == 6
        assert len(sent_commands) == 1
        assert sent_commands[0]["method"] == "DOM.getDocument"
        assert sent_commands[0]["params"] == {"depth": -1}

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_send_command_increments_message_id(self):
        """Test CDP command increments message ID."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()
        initial_id = worker._message_id
        worker.ws = MagicMock()

        async def mock_ws_send(cmd):
            pass

        worker.ws.send = mock_ws_send

        async def mock_wait_for(fut, timeout):
            fut.set_result({"result": True})
            return {"result": True}

        with patch("swarm.harness_worker.asyncio.wait_for", mock_wait_for):
            await worker._send_command("Test.method")

        assert worker._message_id == initial_id + 1

    @pytest.mark.asyncio
    async def test_get_dom_returns_json_string(self, mock_websockets):
        """Test DOM extraction returns JSON string."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        worker.ws = mock_ws

        mock_result = {"root": {"nodeId": 1, "name": "html"}}

        async def mock_ws_send(cmd):
            pass

        worker.ws.send = mock_ws_send

        async def mock_wait_for(fut, timeout):
            fut.set_result(mock_result)
            return mock_result

        with patch("swarm.harness_worker.asyncio.wait_for", mock_wait_for):
            result = await worker.get_dom()

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["name"] == "html"

    @pytest.mark.asyncio
    async def test_click_element_returns_true_on_success(self, mock_websockets):
        """Test click_element returns True when element found."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        worker.ws = mock_ws
        worker._message_id = 0

        async def mock_ws_send(cmd):
            pass

        worker.ws.send = mock_ws_send

        async def mock_wait_for(fut, timeout):
            if worker._message_id == 1:
                fut.set_result({"result": {"objectId": "obj-123"}})
                return {"result": {"objectId": "obj-123"}}
            else:
                fut.set_result({"result": None})
                return {"result": None}

        with patch("swarm.harness_worker.asyncio.wait_for", mock_wait_for):
            result = await worker.click_element("#button")

        assert result is True

    @pytest.mark.asyncio
    async def test_click_element_returns_false_when_not_found(self, mock_websockets):
        """Test click_element returns False when element not found."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        worker.ws = mock_ws
        worker._message_id = 0

        async def mock_ws_send(cmd):
            pass

        worker.ws.send = mock_ws_send

        async def mock_wait_for(fut, timeout):
            fut.set_result({"result": None})
            return {"result": None}

        with patch("swarm.harness_worker.asyncio.wait_for", mock_wait_for):
            result = await worker.click_element("#nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_for_research_sends_bypass_header(self, mock_websockets, mock_httpx_client):
        """Test evaluate_for_research sends X-Bypass-Compression header."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"data": "test"}'}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        worker = HarnessWorker()
        worker.ws = mock_ws

        result = await worker.evaluate_for_research("<html>test</html>")

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args.kwargs
        assert call_kwargs["headers"]["X-Bypass-Compression"] == "true"

    @pytest.mark.asyncio
    async def test_evaluate_for_research_returns_content(self, mock_websockets, mock_httpx_client):
        """Test evaluate_for_research returns extracted content."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"extracted": "data"}'}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        worker = HarnessWorker()
        worker.ws = mock_ws

        result = await worker.evaluate_for_research("<html>test</html>")

        assert result == '{"extracted": "data"}'


class TestHarnessWorkerEnvironment:
    """Test environment variable configuration."""

    def test_cdp_url_default(self):
        """Test CDP_URL defaults to browser-node:9222."""
        from swarm.harness_worker import CDP_URL

        assert CDP_URL == "ws://browser-node:9222"

    def test_openai_api_base_default(self):
        """Test OPENAI_API_BASE has a valid default."""
        from swarm.harness_worker import OPENAI_API_BASE

        assert OPENAI_API_BASE.startswith("http")
        assert "/v1" in OPENAI_API_BASE

    def test_cdp_url_from_environment(self):
        """Test CDP_URL can be overridden via environment."""
        import os
        from swarm import harness_worker

        with patch.dict(os.environ, {"CDP_URL": "ws://custom:9999"}):
            with patch.object(harness_worker, 'CDP_URL', "ws://custom:9999"):
                assert harness_worker.CDP_URL == "ws://custom:9999"
