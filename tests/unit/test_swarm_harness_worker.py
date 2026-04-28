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
    async def test_send_command_success(self, mock_websockets):
        """Test sending CDP command and receiving response."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(return_value=json.dumps({"id": 1, "result": {"success": True}}))
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        await worker.connect()

        result = await worker._send_command("DOM.getDocument", {"depth": -1})

        assert result == {"success": True}
        mock_ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_command_not_connected(self):
        """Test sending command when not connected raises RuntimeError."""
        from swarm.harness_worker import HarnessWorker

        worker = HarnessWorker()

        with pytest.raises(RuntimeError, match="WebSocket not connected"):
            await worker._send_command("DOM.getDocument")

    @pytest.mark.asyncio
    async def test_send_command_timeout(self, mock_websockets):
        """Test CDP command timeout raises TimeoutError."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        await worker.connect()

        worker._message_id = 0
        future = asyncio.get_event_loop().create_future()
        worker._response_futures[1] = future

        with pytest.raises(TimeoutError):
            await worker._send_command("DOM.getDocument", {"depth": -1})

    @pytest.mark.asyncio
    async def test_get_dom(self, mock_websockets):
        """Test DOM extraction."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        mock_response = {
            "id": 1,
            "result": {
                "root": {
                    "nodeId": 1,
                    "name": "html",
                    "value": "<html></html>"
                }
            }
        }
        mock_ws.recv = AsyncMock(return_value=json.dumps(mock_response))
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        await worker.connect()

        result = await worker.get_dom()
        result_parsed = json.loads(result)

        assert result_parsed["name"] == "html"
        assert result_parsed["value"] == "<html></html>"

    @pytest.mark.asyncio
    async def test_click_element_success(self, mock_websockets):
        """Test successful element click."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()

        query_response = {
            "id": 1,
            "result": {
                "result": {
                    "objectId": "obj-123"
                }
            }
        }

        click_response = {
            "id": 2,
            "result": {"success": True}
        }

        mock_ws.recv = AsyncMock(side_effect=[
            json.dumps(query_response),
            json.dumps(click_response)
        ])
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        await worker.connect()

        result = await worker.click_element("#my-button")

        assert result is True

    @pytest.mark.asyncio
    async def test_click_element_not_found(self, mock_websockets):
        """Test clicking element that doesn't exist."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()

        query_response = {
            "id": 1,
            "result": {
                "result": None
            }
        }

        mock_ws.recv = AsyncMock(return_value=json.dumps(query_response))
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        await worker.connect()

        result = await worker.click_element("#nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_for_research(self, mock_websockets, mock_httpx_client):
        """Test research evaluation sends correct headers."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"key": "value"}'
                }
            }]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        worker = HarnessWorker()
        await worker.connect()

        result = await worker.evaluate_for_research('<html><body><div>Test</div></body></html>')

        assert result == '{"key": "value"}'
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args.kwargs
        assert call_kwargs["headers"]["X-Bypass-Compression"] == "true"

    @pytest.mark.asyncio
    async def test_receive_loop_processes_messages(self, mock_websockets):
        """Test receive loop processes incoming messages."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        response_message = {"id": 1, "result": {"success": True}}
        mock_ws.recv = AsyncMock(return_value=json.dumps(response_message))
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        worker.ws = mock_ws

        future = asyncio.get_event_loop().create_future()
        worker._response_futures[1] = future

        await worker._receive_loop()

        assert future.done()
        assert future.result() == {"success": True}

    @pytest.mark.asyncio
    async def test_receive_loop_handles_console_events(self, mock_websockets):
        """Test receive loop handles Runtime.consoleAPICalled events."""
        from swarm.harness_worker import HarnessWorker

        mock_ws = MagicMock()
        console_message = {
            "method": "Runtime.consoleAPICalled",
            "params": {"type": "log", "args": [{"value": "test"}]}
        }
        mock_ws.recv = AsyncMock(side_effect=[
            json.dumps(console_message),
            Exception("stop")
        ])
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        worker = HarnessWorker()
        worker.ws = mock_ws

        with pytest.raises(Exception, match="stop"):
            await worker._receive_loop()


class TestHarnessWorkerEnvironment:
    """Test environment variable configuration."""

    def test_cdp_url_default(self):
        """Test CDP_URL defaults to browser-node:9222."""
        import os

        with patch.dict(os.environ, {}, clear=True):
            from swarm.harness_worker import CDP_URL

            assert CDP_URL == "ws://browser-node:9222"

    def test_openai_api_base_default(self):
        """Test OPENAI_API_BASE defaults to llm-proxy."""
        import os

        with patch.dict(os.environ, {}, clear=True):
            from swarm.harness_worker import OPENAI_API_BASE

            assert OPENAI_API_BASE == "http://llm-proxy:8001/api/v1"

    def test_cdp_url_from_environment(self):
        """Test CDP_URL can be overridden via environment."""
        import os

        with patch.dict(os.environ, {"CDP_URL": "ws://custom:9999"}):
            from swarm.harness_worker import CDP_URL

            assert CDP_URL == "ws://custom:9999"
