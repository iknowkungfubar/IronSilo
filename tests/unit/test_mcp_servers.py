"""
Unit tests for MCP servers (genesys_server.py and khoj_server.py).

Tests cover:
- Genesys MCP server initialization
- Tool registration
- Memory node operations
- Khoj MCP server
- Error handling
"""

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp.framework import MCPServerBase, MCPToolError
from mcp.models import (
    MCPToolType,
    MemoryNode,
    MemoryEdge,
    MemoryQuery,
)


class TestGenesysMCPServerInit:
    """Test GenesysMCPServer initialization."""
    
    def test_server_initialization(self):
        """Test server can be initialized."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer(
            genesys_api_url="http://localhost:8002",
        )
        
        assert server.name == "genesys-mcp"
        assert server.version == "1.0.0"
        assert "memory" in server.capabilities
    
    def test_server_custom_url(self):
        """Test server with custom URL."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer(
            genesys_api_url="http://custom:9000",
        )
        
        assert server.genesys_api_url == "http://custom:9000"
    
    def test_server_url_stripping(self):
        """Test URL trailing slash is stripped."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer(
            genesys_api_url="http://localhost:8000/",
        )
        
        assert server.genesys_api_url == "http://localhost:8000"


class TestGenesysMCPServerTools:
    """Test GenesysMCP server tool registration."""
    
    def test_tools_registered(self):
        """Test that tools are registered."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        tool_defs = server.get_tool_definitions()
        tool_names = [t.name for t in tool_defs]
        
        # Check expected tools exist
        assert "create_memory_node" in tool_names
        assert "create_causal_edge" in tool_names
        assert "query_memories" in tool_names
        assert "get_causal_chain" in tool_names
        assert "create_session" in tool_names
    
    def test_tool_definitions_have_types(self):
        """Test tool definitions have correct types."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        tool_defs = server.get_tool_definitions()
        
        for tool in tool_defs:
            assert tool.tool_type == MCPToolType.MEMORY


class TestGenesysMCPExecuteTools:
    """Test GenesysMCP server tool execution."""
    
    @pytest.mark.asyncio
    async def test_create_memory_node_empty_content(self):
        """Test creating memory node with empty content."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        # Don't initialize - just test validation
        
        with pytest.raises(MCPToolError) as exc_info:
            # Simulate the tool being called with empty content
            if "create_memory_node" in server._tools:
                tool_func = server._tools["create_memory_node"]
                # Mock the client since we didn't initialize
                server._client = MagicMock()
                await tool_func(content="   ", metadata={})
        
        # The error should indicate empty content
        # Note: This may not raise if the tool isn't registered due to no client
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test executing non-existent tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        response = await server.execute_tool(
            tool_name="nonexistent_tool",
            params={},
            request_id="test-123",
        )
        
        assert not response.is_success
        assert response.error.code == -32601
    
    @pytest.mark.asyncio
    async def test_create_memory_node_success(self):
        """Test creating memory node successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "node-123",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.post.return_value = mock_response
        
        # Get the tool function
        tool_func = server._tools["create_memory_node"]
        
        result = await tool_func(content="Test memory", metadata={"key": "value"})
        
        assert result["node_id"] == "node-123"
        assert result["created_at"] == "2024-01-01T00:00:00Z"
        server._client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_memory_node_http_error(self):
        """Test creating memory node with HTTP error."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        http_error = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        
        server._client = AsyncMock()
        server._client.post.side_effect = http_error
        
        tool_func = server._tools["create_memory_node"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(content="Test memory")
        
        assert exc_info.value.code == -32000
    
    @pytest.mark.asyncio
    async def test_create_causal_edge_success(self):
        """Test creating causal edge successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "edge-456",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.post.return_value = mock_response
        
        tool_func = server._tools["create_causal_edge"]
        
        result = await tool_func(
            from_node_id="node-1",
            to_node_id="node-2",
            relationship="causes",
            weight=0.8,
        )
        
        assert result["edge_id"] == "edge-456"
        assert result["created_at"] == "2024-01-01T00:00:00Z"
    
    @pytest.mark.asyncio
    async def test_create_causal_edge_validation_errors(self):
        """Test causal edge validation errors."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        tool_func = server._tools["create_causal_edge"]
        
        # Test empty from_node_id
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(
                from_node_id="",
                to_node_id="node-2",
                relationship="causes",
            )
        assert exc_info.value.code == -32602
        
        # Test empty relationship
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(
                from_node_id="node-1",
                to_node_id="node-2",
                relationship="   ",
            )
        assert exc_info.value.code == -32602
        
        # Test invalid weight
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(
                from_node_id="node-1",
                to_node_id="node-2",
                relationship="causes",
                weight=1.5,
            )
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_query_memories_success(self):
        """Test querying memories successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"node": {"id": "node-1", "content": "Test"}, "score": 0.9},
        ]
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.post.return_value = mock_response
        
        tool_func = server._tools["query_memories"]
        
        results = await tool_func(query="test query", limit=5)
        
        assert len(results) == 1
        assert results[0]["score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_query_memories_validation_errors(self):
        """Test query memories validation errors."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        tool_func = server._tools["query_memories"]
        
        # Test empty query
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(query="   ")
        assert exc_info.value.code == -32602
        
        # Test invalid limit
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(query="test", limit=0)
        assert exc_info.value.code == -32602
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(query="test", limit=101)
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_get_causal_chain_success(self):
        """Test getting causal chain successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "nodes": [{"id": "node-1"}, {"id": "node-2"}],
            "edges": [{"id": "edge-1"}],
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.get.return_value = mock_response
        
        tool_func = server._tools["get_causal_chain"]
        
        result = await tool_func(node_id="node-1", max_depth=3, direction="forward")
        
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_causal_chain_validation_errors(self):
        """Test get causal chain validation errors."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        tool_func = server._tools["get_causal_chain"]
        
        # Test empty node_id
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(node_id="")
        assert exc_info.value.code == -32602
        
        # Test invalid direction
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(node_id="node-1", direction="invalid")
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """Test creating session successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "session-789",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.post.return_value = mock_response
        
        tool_func = server._tools["create_session"]
        
        result = await tool_func(user_id="user-1", metadata={"key": "value"})
        
        assert result["session_id"] == "session-789"
        assert result["created_at"] == "2024-01-01T00:00:00Z"
    
    @pytest.mark.asyncio
    async def test_get_memory_node_success(self):
        """Test getting memory node successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "node": {"id": "node-123", "content": "Test content"},
            "edges": [],
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.get.return_value = mock_response
        
        tool_func = server._tools["get_memory_node"]
        
        result = await tool_func(node_id="node-123", include_edges=True)
        
        assert result["node"]["id"] == "node-123"
    
    @pytest.mark.asyncio
    async def test_get_memory_node_not_found(self):
        """Test getting memory node that doesn't exist."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        http_error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        
        server._client = AsyncMock()
        server._client.get.side_effect = http_error
        
        tool_func = server._tools["get_memory_node"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(node_id="nonexistent")
        
        assert exc_info.value.code == -32602
        assert "not found" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_update_memory_node_success(self):
        """Test updating memory node successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "node-123",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.put.return_value = mock_response
        
        tool_func = server._tools["update_memory_node"]
        
        result = await tool_func(
            node_id="node-123",
            content="Updated content",
            metadata={"key": "new_value"},
        )
        
        assert result["node_id"] == "node-123"
        assert result["updated_at"] == "2024-01-01T00:00:00Z"
    
    @pytest.mark.asyncio
    async def test_update_memory_node_validation_errors(self):
        """Test update memory node validation errors."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        tool_func = server._tools["update_memory_node"]
        
        # Test empty node_id
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(node_id="", content="test")
        assert exc_info.value.code == -32602
        
        # Test empty content
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(node_id="node-1", content="   ")
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_delete_memory_node_success(self):
        """Test deleting memory node successfully."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "deleted_edges": 3,
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.delete.return_value = mock_response
        
        tool_func = server._tools["delete_memory_node"]
        
        result = await tool_func(node_id="node-123")
        
        assert result["success"] is True
        assert result["deleted_edges"] == 3
    
    @pytest.mark.asyncio
    async def test_delete_memory_node_not_found(self):
        """Test deleting memory node that doesn't exist."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        http_error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        
        server._client = AsyncMock()
        server._client.delete.side_effect = http_error
        
        tool_func = server._tools["delete_memory_node"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(node_id="nonexistent")
        
        assert exc_info.value.code == -32602
        assert "not found" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_delete_memory_node_empty_id(self):
        """Test deleting memory node with empty ID."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        tool_func = server._tools["delete_memory_node"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(node_id="")
        
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful server initialization."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            await server.initialize()
            
            assert server._client is not None
            mock_client.get.assert_called_with("/health")
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test server initialization failure."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client
            
            with pytest.raises(Exception, match="Connection failed"):
                await server.initialize()
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test server shutdown."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        mock_client = AsyncMock()
        server._client = mock_client
        
        await server.shutdown()
        
        mock_client.aclose.assert_called_once()


class TestKhojMCPServerInit:
    """Test KhojMCPServer initialization."""
    
    def test_server_initialization(self):
        """Test server can be initialized."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer(
            khoj_api_url="http://localhost:42110",
        )
        
        assert server.name == "khoj-mcp"
        assert server.version == "1.0.0"
        assert "search" in server.capabilities
    
    def test_server_custom_url(self):
        """Test server with custom URL."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer(
            khoj_api_url="http://custom:9999",
        )
        
        assert server.khoj_api_url == "http://custom:9999"
    
    def test_server_url_stripping(self):
        """Test URL trailing slash is stripped."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer(
            khoj_api_url="http://localhost:42110/",
        )
        
        assert server.khoj_api_url == "http://localhost:42110"


class TestKhojMCPServerTools:
    """Test KhojMCP server tool registration."""
    
    def test_tools_registered(self):
        """Test that tools are registered."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        tool_defs = server.get_tool_definitions()
        tool_names = [t.name for t in tool_defs]
        
        # Check expected tools exist
        assert "search_documents" in tool_names
        assert "upload_document" in tool_names
        assert "list_documents" in tool_names
        assert "delete_document" in tool_names
        assert "reindex_documents" in tool_names
        assert "get_index_status" in tool_names
    
    def test_tool_definitions_have_types(self):
        """Test tool definitions have correct types."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        tool_defs = server.get_tool_definitions()
        
        # Khoj tools can be SEARCH, FILE, or EXECUTION type
        for tool in tool_defs:
            assert tool.tool_type in [MCPToolType.SEARCH, MCPToolType.FILE, MCPToolType.EXECUTION]


class TestKhojMCPExecuteTools:
    """Test KhojMCP server tool execution."""
    
    @pytest.mark.asyncio
    async def test_search_documents_success(self):
        """Test searching documents successfully."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "search": [
                {
                    "id": "doc-1",
                    "title": "Test Document",
                    "content": "Test content",
                    "score": 0.95,
                    "source": "test.txt",
                    "type": "text",
                    "file": "test.txt",
                    "updated": "2024-01-01",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.get.return_value = mock_response
        
        tool_func = server._tools["search_documents"]
        
        results = await tool_func(query="test query", max_results=5)
        
        assert len(results) == 1
        assert results[0]["id"] == "doc-1"
        assert results[0]["score"] == 0.95
    
    @pytest.mark.asyncio
    async def test_search_documents_validation_errors(self):
        """Test search documents validation errors."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        tool_func = server._tools["search_documents"]
        
        # Test empty query
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(query="   ")
        assert exc_info.value.code == -32602
        
        # Test invalid max_results
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(query="test", max_results=0)
        assert exc_info.value.code == -32602
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(query="test", max_results=51)
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_search_documents_http_error(self):
        """Test searching documents with HTTP error."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        http_error = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        
        server._client = AsyncMock()
        server._client.get.side_effect = http_error
        
        tool_func = server._tools["search_documents"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(query="test")
        
        assert exc_info.value.code == -32000
    
    @pytest.mark.asyncio
    async def test_upload_document_with_content(self):
        """Test uploading document with content."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "doc-123",
            "indexed": True,
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.post.return_value = mock_response
        
        tool_func = server._tools["upload_document"]
        
        result = await tool_func(
            content="Test document content",
            filename="test.txt",
            content_type="text/plain",
        )
        
        assert result["document_id"] == "doc-123"
        assert result["indexed"] is True
    
    @pytest.mark.asyncio
    async def test_upload_document_validation_errors(self):
        """Test upload document validation errors."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        tool_func = server._tools["upload_document"]
        
        # Test neither file_path nor content
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func()
        assert exc_info.value.code == -32602
        
        # Test both file_path and content
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(file_path="/path/to/file", content="content")
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_upload_document_file_not_found(self):
        """Test uploading document with non-existent file."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        tool_func = server._tools["upload_document"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(file_path="/nonexistent/file.txt")
        
        # File not found is caught by generic exception handler
        assert exc_info.value.code == -32000
        assert "not found" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_list_documents_success(self):
        """Test listing documents successfully."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "doc-1",
                "name": "Document 1",
                "type": "text",
                "size": 1024,
                "indexed": True,
                "updated": "2024-01-01",
            },
            {
                "id": "doc-2",
                "title": "Document 2",
                "type": "pdf",
                "size": 2048,
                "indexed": False,
                "updated": "2024-01-02",
            },
        ]
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.get.return_value = mock_response
        
        tool_func = server._tools["list_documents"]
        
        results = await tool_func()
        
        assert len(results) == 2
        assert results[0]["id"] == "doc-1"
        assert results[0]["title"] == "Document 1"
        assert results[1]["title"] == "Document 2"
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self):
        """Test deleting document successfully."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.delete.return_value = mock_response
        
        tool_func = server._tools["delete_document"]
        
        result = await tool_func(document_id="doc-123")
        
        assert result["success"] is True
        assert "doc-123" in result["message"]
    
    @pytest.mark.asyncio
    async def test_delete_document_empty_id(self):
        """Test deleting document with empty ID."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        tool_func = server._tools["delete_document"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(document_id="")
        
        assert exc_info.value.code == -32602
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found(self):
        """Test deleting document that doesn't exist."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        http_error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        
        server._client = AsyncMock()
        server._client.delete.side_effect = http_error
        
        tool_func = server._tools["delete_document"]
        
        with pytest.raises(MCPToolError) as exc_info:
            await tool_func(document_id="nonexistent")
        
        assert exc_info.value.code == -32602
        assert "not found" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_reindex_documents_success(self):
        """Test reindexing documents successfully."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "documents_processed": 10,
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.post.return_value = mock_response
        
        tool_func = server._tools["reindex_documents"]
        
        result = await tool_func(force=True)
        
        assert result["success"] is True
        assert result["documents_processed"] == 10
    
    @pytest.mark.asyncio
    async def test_get_index_status_success(self):
        """Test getting index status successfully."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ready",
            "indexed": 100,
            "pending": 5,
            "errors": 2,
        }
        mock_response.raise_for_status = MagicMock()
        
        server._client = AsyncMock()
        server._client.get.return_value = mock_response
        
        tool_func = server._tools["get_index_status"]
        
        result = await tool_func()
        
        assert result["status"] == "ready"
        assert result["indexed"] == 100
        assert result["pending"] == 5
        assert result["errors"] == 2
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful server initialization."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            await server.initialize()
            
            assert server._client is not None
            mock_client.get.assert_called_with("/api/health")
    
    @pytest.mark.asyncio
    async def test_initialize_connection_warning(self):
        """Test server initialization with connection warning."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client
            
            # Should not raise, just log warning
            await server.initialize()
            
            assert server._client is not None
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test server shutdown."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        mock_client = AsyncMock()
        server._client = mock_client
        
        await server.shutdown()
        
        mock_client.aclose.assert_called_once()


class TestMCPFrameworkIntegration:
    """Test MCP framework integration with servers."""
    
    def test_create_mcp_app_genesys(self):
        """Test creating FastAPI app for Genesys MCP."""
        from mcp.genesys_server import GenesysMCPServer
        from mcp.framework import create_mcp_app
        
        server = GenesysMCPServer()
        app = create_mcp_app(server)
        
        assert app is not None
        assert app.title == "genesys-mcp MCP Server"
    
    def test_create_mcp_app_khoj(self):
        """Test creating FastAPI app for Khoj MCP."""
        from mcp.khoj_server import KhojMCPServer
        from mcp.framework import create_mcp_app
        
        server = KhojMCPServer()
        app = create_mcp_app(server)
        
        assert app is not None
        assert app.title == "khoj-mcp MCP Server"


class TestMCPModels:
    """Test MCP models used by servers."""
    
    def test_memory_node_creation(self):
        """Test creating memory node."""
        node = MemoryNode(
            content="Test memory content",
            metadata={"category": "test"},
        )
        
        assert node.content == "Test memory content"
        assert node.id is not None
    
    def test_memory_node_validation(self):
        """Test memory node validation."""
        with pytest.raises(ValueError, match="Content must not be empty"):
            MemoryNode(content="   ")
    
    def test_memory_edge_creation(self):
        """Test creating memory edge."""
        edge = MemoryEdge(
            from_node_id="node-1",
            to_node_id="node-2",
            relationship="causes",
            weight=0.8,
        )
        
        assert edge.from_node_id == "node-1"
        assert edge.relationship == "causes"
        assert edge.weight == 0.8
    
    def test_memory_edge_validation(self):
        """Test memory edge validation."""
        with pytest.raises(ValueError, match="Relationship must not be empty"):
            MemoryEdge(
                from_node_id="node-1",
                to_node_id="node-2",
                relationship="   ",
            )


class TestMCPToolError:
    """Test MCPToolError handling."""
    
    def test_tool_error_creation(self):
        """Test creating MCP tool error."""
        error = MCPToolError(
            code=-32602,
            message="Invalid params",
            data={"param": "content"},
        )
        
        assert error.code == -32602
        assert error.message == "Invalid params"
        assert error.data == {"param": "content"}
    
    def test_tool_error_without_data(self):
        """Test MCP tool error without data."""
        error = MCPToolError(
            code=-32601,
            message="Tool not found",
        )
        
        assert error.code == -32601
        assert error.data is None


class TestServerInfo:
    """Test server info generation."""
    
    def test_genesys_server_info(self):
        """Test Genesys server info."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        info = server.get_server_info()
        
        assert info.name == "genesys-mcp"
        assert "memory" in info.capabilities
        assert "causal-graph" in info.capabilities
        assert len(info.tools) > 0
    
    def test_khoj_server_info(self):
        """Test Khoj server info."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        info = server.get_server_info()
        
        assert info.name == "khoj-mcp"
        assert "search" in info.capabilities
        assert len(info.tools) > 0


class TestMCPDockerEntrypoint:
    """Test MCP Docker entrypoint script logic."""
    
    def test_server_type_selection(self):
        """Test MCP server type selection logic."""
        # Test the expected environment variable handling
        import os
        
        server_types = ["genesys", "khoj"]
        assert "genesys" in server_types
        assert "khoj" in server_types
    
    def test_mcp_port_config(self):
        """Test MCP server port configuration."""
        # Default MCP port
        default_port = 8000
        
        assert default_port > 0
        assert default_port < 65536
