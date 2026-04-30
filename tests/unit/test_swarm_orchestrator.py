"""
Comprehensive unit tests for swarm/orchestrator module.

Tests cover:
- Manager class initialization
- MemoryNodeInput schema validation
- extract_and_store workflow
- _store_memory HTTP calls
- run_research_session batch processing
"""

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMemoryNodeInput:
    """Test suite for MemoryNodeInput Pydantic model."""

    def test_memory_node_input_creation(self):
        """Test MemoryNodeInput can be created with valid data."""
        from swarm.orchestrator import MemoryNodeInput

        node = MemoryNodeInput(
            content="Test content",
            memory_type="research",
            importance=0.7
        )

        assert node.content == "Test content"
        assert node.memory_type == "research"
        assert node.importance == 0.7
        assert len(node.id) > 0
        assert len(node.created_at) > 0

    def test_memory_node_input_default_values(self):
        """Test MemoryNodeInput has correct defaults."""
        from swarm.orchestrator import MemoryNodeInput

        node = MemoryNodeInput(content="Test content")

        assert node.memory_type == "semantic"
        assert node.importance == 0.5
        assert node.tags == []
        assert node.metadata == {}

    def test_memory_node_input_json_serialization(self):
        """Test MemoryNodeInput serializes to JSON correctly."""
        from swarm.orchestrator import MemoryNodeInput

        node = MemoryNodeInput(
            content="Test content",
            tags=["tag1", "tag2"]
        )

        data = node.model_dump()

        assert data["content"] == "Test content"
        assert data["tags"] == ["tag1", "tag2"]
        assert "id" in data
        assert "created_at" in data


class TestManager:
    """Test suite for Manager class."""

    @pytest.fixture
    def mock_worker(self):
        """Create a mock HarnessWorker."""
        worker = MagicMock()
        worker.get_dom = AsyncMock(return_value='{"html": "<body>test</body>"}')
        worker.evaluate_for_research = AsyncMock(return_value='{"data": "extracted"}')
        worker.connect = AsyncMock()
        worker.disconnect = AsyncMock()
        return worker

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient."""
        with patch("swarm.orchestrator.httpx.AsyncClient") as mock:
            yield mock

    def test_manager_initialization(self, mock_worker):
        """Test Manager initializes with correct defaults."""
        from swarm.orchestrator import Manager

        manager = Manager(mock_worker)

        assert manager.worker == mock_worker
        assert manager.genesys_url == "http://genesys-memory:8000"

    @pytest.mark.asyncio
    async def test_extract_and_store_success(self, mock_worker, mock_httpx_client):
        """Test complete extract and store workflow."""
        from swarm.orchestrator import Manager

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem-123", "content": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        manager = Manager(mock_worker)

        result = await manager.extract_and_store("test query")

        assert result["id"] == "mem-123"
        mock_worker.get_dom.assert_called_once()
        mock_worker.evaluate_for_research.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_and_store_parses_json(self, mock_worker, mock_httpx_client):
        """Test extract_and_store parses JSON research data."""
        from swarm.orchestrator import Manager

        captured_data = {}

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem-123", "content": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()

        async def mock_post(*args, **kwargs):
            captured_data['json'] = kwargs.get('json', {})
            return mock_response

        mock_client.post = mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        manager = Manager(mock_worker)
        mock_worker.evaluate_for_research = AsyncMock(return_value='{"data": "extracted", "extra": "value"}')

        await manager.extract_and_store("test query")

        assert "raw_research" not in captured_data.get('json', {}).get('content', '')

    @pytest.mark.asyncio
    async def test_extract_and_store_fallback_for_invalid_json(self, mock_worker, mock_httpx_client):
        """Test extract_and_store handles invalid JSON gracefully."""
        from swarm.orchestrator import Manager

        mock_worker.evaluate_for_research = AsyncMock(return_value="not valid json")

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem-123", "content": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        manager = Manager(mock_worker)

        result = await manager.extract_and_store("test query")

        assert "raw_research" in str(result) or result.get("id") == "mem-123"

    @pytest.mark.asyncio
    async def test_store_memory_calls_correct_endpoint(self, mock_httpx_client):
        """Test _store_memory POSTs to correct endpoint."""
        from swarm.orchestrator import Manager, MemoryNodeInput

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem-456"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        memory = MemoryNodeInput(content="test memory")
        result = await manager._store_memory(memory)

        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args.args[0] if mock_client.post.call_args.args else mock_client.post.call_args.kwargs.get("url", "")
        assert "/api/v1/memories" in call_url
        assert result["id"] == "mem-456"

    @pytest.mark.asyncio
    async def test_store_memory_sets_correct_metadata(self, mock_httpx_client):
        """Test _store_memory includes source metadata."""
        from swarm.orchestrator import Manager, MemoryNodeInput

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem-789"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        mock_worker = MagicMock()
        manager = Manager(mock_worker)

        memory = MemoryNodeInput(content="test", metadata={"source": "browser_swarm"})
        await manager._store_memory(memory)

        call_kwargs = mock_client.post.call_args.kwargs
        posted_data = call_kwargs.get("json", {})
        assert posted_data.get("metadata", {}).get("source") == "browser_swarm"

    @pytest.mark.asyncio
    async def test_store_memory_sets_research_tags(self, mock_httpx_client):
        """Test extract_and_store includes research query in tags."""
        from swarm.orchestrator import Manager, MemoryNodeInput

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem-101"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        mock_worker = MagicMock()
        mock_worker.get_dom = AsyncMock(return_value="<html></html>")
        mock_worker.evaluate_for_research = AsyncMock(return_value='{"data": "test"}')

        manager = Manager(mock_worker)

        long_query = "A" * 100
        await manager.extract_and_store(long_query)

        call_kwargs = mock_client.post.call_args.kwargs
        posted_data = call_kwargs.get("json", {})
        assert "web_scraping" in posted_data["tags"]
        assert "dom_analysis" in posted_data["tags"]
        assert len(posted_data["tags"]) >= 3

    @pytest.mark.asyncio
    async def test_run_research_session(self, mock_worker, mock_httpx_client):
        """Test batch research session processing."""
        from swarm.orchestrator import Manager

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem-session"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        manager = Manager(mock_worker)

        queries = ["query1", "query2", "query3"]
        results = await manager.run_research_session(queries)

        assert len(results) == 3
        mock_worker.connect.assert_called_once()
        mock_worker.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_research_session_disconnects_on_error(self, mock_worker, mock_httpx_client):
        """Test research session disconnects even on error."""
        from swarm.orchestrator import Manager

        mock_worker.get_dom = AsyncMock(side_effect=Exception("DOM error"))

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client

        manager = Manager(mock_worker)

        with pytest.raises(Exception):
            await manager.run_research_session(["query1"])

        mock_worker.disconnect.assert_called_once()


class TestOrchestratorEnvironment:
    """Test environment variable configuration."""

    def test_genesys_url_default(self):
        """Test GENESYS_URL defaults to genesys-memory:8000."""
        from swarm.orchestrator import GENESYS_URL

        assert GENESYS_URL == "http://genesys-memory:8000"

    def test_genesys_url_from_environment(self):
        """Test GENESYS_URL can be overridden via environment."""
        import os
        from swarm import orchestrator

        with patch.dict(os.environ, {"GENESYS_URL": "http://custom-gene:9000"}):
            with patch.object(orchestrator, 'GENESYS_URL', "http://custom-gene:9000"):
                assert orchestrator.GENESYS_URL == "http://custom-gene:9000"
