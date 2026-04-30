"""
Comprehensive unit tests for genesys/app.py module.

Tests cover:
- MemoryNode, CausalEdge, Session Pydantic models
- Health check endpoint
- Memory CRUD operations (create, read, update, delete)
- Memory search
- Edge creation
- Causal chain retrieval
- Session creation
- Both PostgreSQL and in-memory backend paths
"""

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMemoryNodeModel:
    """Test MemoryNode Pydantic model."""

    def test_memory_node_creation(self):
        """Test MemoryNode can be created with required fields."""
        from genesys.app import MemoryNode

        node = MemoryNode(content="Test content")

        assert node.content == "Test content"
        assert node.id is not None
        assert len(node.id) > 0

    def test_memory_node_default_values(self):
        """Test MemoryNode has correct defaults."""
        from genesys.app import MemoryNode

        node = MemoryNode(content="Test")

        assert node.memory_type == "semantic"
        assert node.importance == 0.5
        assert node.tags == []
        assert node.metadata == {}

    def test_memory_node_with_all_fields(self):
        """Test MemoryNode accepts all fields."""
        from genesys.app import MemoryNode

        node = MemoryNode(
            content="Full content",
            memory_type="research",
            importance=0.9,
            tags=["tag1", "tag2"],
            metadata={"key": "value"},
        )

        assert node.content == "Full content"
        assert node.memory_type == "research"
        assert node.importance == 0.9
        assert node.tags == ["tag1", "tag2"]
        assert node.metadata == {"key": "value"}


class TestCausalEdgeModel:
    """Test CausalEdge Pydantic model."""

    def test_causal_edge_creation(self):
        """Test CausalEdge can be created."""
        from genesys.app import CausalEdge

        edge = CausalEdge(source_id="src-1", target_id="tgt-1")

        assert edge.source_id == "src-1"
        assert edge.target_id == "tgt-1"
        assert edge.relationship == "causes"
        assert edge.strength == 1.0

    def test_causal_edge_custom_values(self):
        """Test CausalEdge accepts custom values."""
        from genesys.app import CausalEdge

        edge = CausalEdge(
            source_id="source",
            target_id="target",
            relationship="enables",
            strength=0.7,
        )

        assert edge.relationship == "enables"
        assert edge.strength == 0.7


class TestSessionModel:
    """Test Session Pydantic model."""

    def test_session_creation(self):
        """Test Session can be created."""
        from genesys.app import Session

        session = Session()

        assert session.id is not None
        assert session.session_type == "default"
        assert session.metadata == {}

    def test_session_custom_type(self):
        """Test Session accepts custom type."""
        from genesys.app import Session

        session = Session(session_type="research")

        assert session.session_type == "research"


class TestGenesysConfiguration:
    """Test module-level configuration."""

    def test_database_url_default_empty(self):
        """Test DATABASE_URL defaults to empty string when not set."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            from genesys.app import DATABASE_URL
            assert DATABASE_URL == ""

    def test_use_postgres_false_without_url(self):
        """Test USE_POSTGRES is False without DATABASE_URL."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            from genesys.app import USE_POSTGRES
            assert USE_POSTGRES is False


class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self):
        """Test root endpoint returns service information."""
        from genesys.app import root

        result = await root()

        assert result["service"] == "Genesys Memory API"
        assert result["version"] == "1.0.0"
        assert result["backend"] == "memory"
        assert "docs" in result
        assert "health" in result


class TestCreateMemory:
    """Test create memory endpoint."""

    @pytest.mark.asyncio
    async def test_create_memory_in_memory_mode(self):
        """Test create_memory stores in memory when no PostgreSQL."""
        import genesys.app
        genesys.app._pool = None

        from genesys.app import MemoryNode, create_memory, _memories

        memory = MemoryNode(content="Test memory")
        result = await create_memory(memory)

        assert result.content == "Test memory"
        assert memory.id in genesys.app._memories

    @pytest.mark.asyncio
    async def test_create_memory_with_postgres(self):
        """Test create_memory stores in PostgreSQL when available."""
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        import genesys.app
        genesys.app._pool = mock_pool

        from genesys.app import MemoryNode, create_memory

        memory = MemoryNode(content="PG memory")
        await create_memory(memory)

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT INTO memories" in call_args[0][0]

        genesys.app._pool = None


class TestGetMemory:
    """Test get memory endpoint."""

    @pytest.mark.asyncio
    async def test_get_memory_in_memory_mode_found(self):
        """Test get_memory returns memory when found in memory mode."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {"test-id": {"id": "test-id", "content": "Found"}}

        from genesys.app import get_memory

        result = await get_memory("test-id")

        assert result["content"] == "Found"

    @pytest.mark.asyncio
    async def test_get_memory_in_memory_mode_not_found(self):
        """Test get_memory raises 404 when not found in memory mode."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {}

        from genesys.app import get_memory

        with pytest.raises(Exception) as exc_info:
            await get_memory("nonexistent")

        assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_memory_with_postgres_found(self):
        """Test get_memory returns memory from PostgreSQL."""
        mock_row = {
            "id": "pg-id",
            "content": "PG content",
            "memory_type": "semantic",
            "importance": 0.5,
            "tags": '["tag1"]',
            "metadata": '{"key": "value"}',
        }

        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        import genesys.app
        genesys.app._pool = mock_pool

        from genesys.app import get_memory

        result = await get_memory("pg-id")

        assert result["id"] == "pg-id"
        assert result["content"] == "PG content"
        assert result["tags"] == ["tag1"]

        genesys.app._pool = None


class TestUpdateMemory:
    """Test update memory endpoint."""

    @pytest.mark.asyncio
    async def test_update_memory_in_memory_mode(self):
        """Test update_memory modifies memory in memory mode."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {"test-id": {"id": "test-id", "content": "Original"}}

        from genesys.app import update_memory

        result = await update_memory("test-id", content="Updated")

        assert result["content"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_memory_not_found(self):
        """Test update_memory raises 404 when memory doesn't exist."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {}

        from genesys.app import update_memory

        with pytest.raises(Exception):
            await update_memory("nonexistent", content="New")


class TestDeleteMemory:
    """Test delete memory endpoint."""

    @pytest.mark.asyncio
    async def test_delete_memory_in_memory_mode(self):
        """Test delete_memory removes from memory."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {"test-id": {"id": "test-id", "content": "To delete"}}

        from genesys.app import delete_memory

        result = await delete_memory("test-id")

        assert result["deleted"] is True
        assert "test-id" not in genesys.app._memories

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self):
        """Test delete_memory raises 404 when not found."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {}

        from genesys.app import delete_memory

        with pytest.raises(Exception):
            await delete_memory("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_memory_with_postgres(self):
        """Test delete_memory with PostgreSQL."""
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        import genesys.app
        genesys.app._pool = mock_pool

        from genesys.app import delete_memory

        result = await delete_memory("test-id")

        assert result["deleted"] is True
        mock_conn.execute.assert_called_once()

        genesys.app._pool = None


class TestSearchMemories:
    """Test search memories endpoint."""

    @pytest.mark.asyncio
    async def test_search_memories_in_memory_mode(self):
        """Test search_memories finds matching in memory."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {
            "1": {"id": "1", "content": "Python code", "memory_type": "semantic"},
            "2": {"id": "2", "content": "Rust code", "memory_type": "semantic"},
        }

        from genesys.app import search_memories

        result = await search_memories(query="Python")

        assert result["count"] == 1
        assert result["memories"][0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_search_memories_with_type_filter(self):
        """Test search_memories filters by memory_type."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {
            "1": {"id": "1", "content": "Research data", "memory_type": "research"},
            "2": {"id": "2", "content": "More research", "memory_type": "research"},
            "3": {"id": "3", "content": "Not research", "memory_type": "semantic"},
        }

        from genesys.app import search_memories

        result = await search_memories(query="research", memory_type="research")

        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_search_memories_limit(self):
        """Test search_memories respects limit."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._memories = {
            str(i): {"id": str(i), "content": "Content " + str(i), "memory_type": "semantic"}
            for i in range(20)
        }

        from genesys.app import search_memories

        result = await search_memories(query="Content", limit=5)

        assert result["count"] == 5


class TestCreateEdge:
    """Test create edge endpoint."""

    @pytest.mark.asyncio
    async def test_create_edge_in_memory_mode(self):
        """Test create_edge stores in memory when no PostgreSQL."""
        import genesys.app
        genesys.app._pool = None

        from genesys.app import CausalEdge, create_edge

        edge = CausalEdge(source_id="src-1", target_id="tgt-1")

        result = await create_edge(edge)

        assert result.source_id == "src-1"
        assert result.target_id == "tgt-1"
        assert edge.id in genesys.app._edges

    @pytest.mark.asyncio
    async def test_create_edge_with_postgres(self):
        """Test create_edge stores in PostgreSQL when available."""
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        import genesys.app
        genesys.app._pool = mock_pool

        from genesys.app import CausalEdge, create_edge

        edge = CausalEdge(source_id="src-2", target_id="tgt-2")

        await create_edge(edge)

        mock_conn.execute.assert_called_once()
        assert "INSERT INTO edges" in mock_conn.execute.call_args[0][0]

        genesys.app._pool = None


class TestGetCausalChain:
    """Test get causal chain endpoint."""

    @pytest.mark.asyncio
    async def test_get_causal_chain_in_memory_mode(self):
        """Test get_causal_chain finds edges in memory."""
        import genesys.app
        genesys.app._pool = None
        genesys.app._edges = {
            "edge-1": {"id": "edge-1", "source_id": "node-1", "target_id": "node-2"},
            "edge-2": {"id": "edge-2", "source_id": "node-2", "target_id": "node-3"},
        }

        from genesys.app import get_causal_chain

        result = await get_causal_chain("node-1")

        assert result["count"] == 1
        assert result["chain"][0]["id"] == "edge-1"

    @pytest.mark.asyncio
    async def test_get_causal_chain_with_postgres(self):
        """Test get_causal_chain with PostgreSQL."""
        mock_rows = [
            {"id": "edge-1", "source_id": "node-1", "target_id": "node-2"},
        ]

        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        import genesys.app
        genesys.app._pool = mock_pool

        from genesys.app import get_causal_chain

        result = await get_causal_chain("node-1")

        assert result["count"] == 1

        genesys.app._pool = None


class TestCreateSession:
    """Test create session endpoint."""

    @pytest.mark.asyncio
    async def test_create_session_in_memory_mode(self):
        """Test create_session stores in memory when no PostgreSQL."""
        import genesys.app
        genesys.app._pool = None

        from genesys.app import create_session

        result = await create_session(session_type="research")

        assert result.session_type == "research"
        assert result.id in genesys.app._sessions

    @pytest.mark.asyncio
    async def test_create_session_with_default_type(self):
        """Test create_session uses default type."""
        import genesys.app
        genesys.app._pool = None

        from genesys.app import create_session

        result = await create_session()

        assert result.session_type == "default"

    @pytest.mark.asyncio
    async def test_create_session_with_postgres(self):
        """Test create_session stores in PostgreSQL when available."""
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        import genesys.app
        genesys.app._pool = mock_pool

        from genesys.app import create_session

        result = await create_session(session_type="custom")

        assert result.session_type == "custom"
        mock_conn.execute.assert_called_once()

        genesys.app._pool = None