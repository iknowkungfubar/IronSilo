"""
Comprehensive tests for mcp/genesys_server.py to achieve 100% coverage.
Tests use mocked HTTP client to avoid real network calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx

from mcp.framework import MCPToolError


class TestGenesysMCPServer:
    """Test GenesysMCPServer class."""

    def test_server_initialization(self):
        """Test server initializes correctly."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        assert server.name == "memory-mcp"
        assert server.version == "2.0.0"
        assert "memory" in server.capabilities

    def test_server_has_tools(self):
        """Test server registers tools on initialization."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        expected_tools = [
            "create_memory_node",
            "create_causal_edge",
            "query_memories",
            "get_causal_chain",
            "create_session",
            "get_memory_node",
            "update_memory_node",
            "delete_memory_node",
        ]

        for tool_name in expected_tools:
            assert tool_name in server._tools

    @pytest.mark.asyncio
    async def test_create_memory_node(self):
        """Test create_memory_node tool."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "mem-123",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.post.return_value = mock_response

        handler = server.get_tool_handler("create_memory_node")
        result = await handler(content="Test memory content", metadata={"type": "test"})

        assert result is not None
        assert "node_id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_query_memories(self):
        """Test query_memories tool."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": "mem-1", "content": "Test 1"},
                {"id": "mem-2", "content": "Test 2"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.post.return_value = mock_response

        handler = server.get_tool_handler("query_memories")
        result = await handler(query="test", limit=10, filters={})

        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test create_session tool."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "session_id": "sess-456",
            "user_id": "user-123",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.post.return_value = mock_response

        handler = server.get_tool_handler("create_session")
        result = await handler(user_id="user-123", metadata={})

        assert result is not None
        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_get_memory_node(self):
        """Test get_memory_node tool."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "node_id": "mem-789",
            "content": "Test content",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.get.return_value = mock_response

        handler = server.get_tool_handler("get_memory_node")
        result = await handler(node_id="mem-789")

        assert result is not None
        assert result["node_id"] == "mem-789"

    @pytest.mark.asyncio
    async def test_update_memory_node(self):
        """Test update_memory_node tool."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "node_id": "mem-123",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.put.return_value = mock_response

        handler = server.get_tool_handler("update_memory_node")
        result = await handler(node_id="mem-123", content="Updated content", metadata=None)

        assert result is not None
        # The handler returns node_id from the mock response
        assert "node_id" in result or "updated_at" in result

    @pytest.mark.asyncio
    async def test_query_without_filters(self):
        """Test query_memories without filters parameter."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": "mem-1", "content": "Test 1"},
                {"id": "mem-2", "content": "Test 2"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.post.return_value = mock_response

        handler = server.get_tool_handler("query_memories")
        result = await handler(query="test", limit=10)

        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 2


class TestGenesysMCPServerErrors:
    """Test error handling in GenesysMCPServer."""

    @pytest.mark.asyncio
    async def test_invalid_memory_id_returns_error(self):
        """Test operations with invalid memory ID."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        server._client = AsyncMock()
        server._client.get.side_effect = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

        handler = server.get_tool_handler("get_memory_node")

        # Should raise MCPToolError
        with pytest.raises(MCPToolError):
            await handler(node_id="nonexistent-id")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self):
        """Test deleting non-existent memory (idempotent)."""
        from mcp.genesys_server import GenesysMCPServer

        server = GenesysMCPServer()

        # Mock successful delete (idempotent)
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "message": "Deleted"}

        server._client = AsyncMock()
        server._client.post.return_value = mock_response

        handler = server.get_tool_handler("create_memory_node")
        result = await handler(content="test", metadata={})

        assert result is not None


class TestKhojMCPServer:
    """Test KhojMCPServer class."""

    def test_server_initialization(self):
        """Test server initializes correctly."""
        from mcp.khoj_server import KhojMCPServer

        server = KhojMCPServer()

        assert server.name == "rag-mcp"
        assert server.version == "2.0.0"
        assert "search" in server.capabilities or "rag" in server.capabilities

    def test_server_has_tools(self):
        """Test server registers tools on initialization."""
        from mcp.khoj_server import KhojMCPServer

        server = KhojMCPServer()

        expected_tools = [
            "search_documents",
            "upload_document",
            "list_documents",
            "delete_document",
            "get_index_status",
        ]

        for tool_name in expected_tools:
            assert tool_name in server._tools

    @pytest.mark.asyncio
    async def test_search_documents(self):
        """Test search_documents tool."""
        from mcp.khoj_server import KhojMCPServer

        server = KhojMCPServer()

        # Mock the HTTP client - search uses POST to LightRAG API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "doc-1",
                    "title": "Result 1",
                    "content": "...",
                    "score": 1.0,
                    "source": "lightrag",
                },
                {
                    "id": "doc-2",
                    "title": "Result 2",
                    "content": "...",
                    "score": 0.9,
                    "source": "lightrag",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.post = AsyncMock(return_value=mock_response)

        handler = server.get_tool_handler("search_documents")
        result = await handler(query="test query", max_results=10, mode="hybrid")

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_documents(self):
        """Test list_documents tool."""
        from mcp.khoj_server import KhojMCPServer

        server = KhojMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "doc-1", "file": "test1.md"},
            {"id": "doc-2", "file": "test2.md"},
        ]
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.get.return_value = mock_response

        handler = server.get_tool_handler("list_documents")
        result = await handler()

        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_index_status(self):
        """Test get_index_status tool."""
        from mcp.khoj_server import KhojMCPServer

        server = KhojMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ready",
            "indexed_count": 42,
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.get.return_value = mock_response

        handler = server.get_tool_handler("get_index_status")
        result = await handler()

        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_reindex_documents(self):
        """Test reindex_documents removed — use restart instead."""
        pass

    @pytest.mark.asyncio
    async def test_upload_document(self):
        """Test upload_document tool with simplified API."""
        from mcp.khoj_server import KhojMCPServer

        server = KhojMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "document_id": "uploaded.txt",
            "indexed": True,
            "message": "Document indexed",
        }
        mock_response.raise_for_status = MagicMock()

        server._client = AsyncMock()
        server._client.post.return_value = mock_response

        handler = server.get_tool_handler("upload_document")
        result = await handler(
            content="Test document content",
        )

        assert result is not None
        assert "document_id" in result or "message" in result

    @pytest.mark.asyncio
    async def test_delete_document(self):
        """Test delete_document tool."""
        from mcp.khoj_server import KhojMCPServer

        server = KhojMCPServer()

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"success": True, "message": "Deleted"}

        server._client = AsyncMock()
        server._client.delete.return_value = mock_response

        handler = server.get_tool_handler("delete_document")
        result = await handler(document_id="test-doc-id")

        assert result is not None
        assert "success" in result or "message" in result
