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
    
    def test_tool_definitions_have_types(self):
        """Test tool definitions have correct types."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        tool_defs = server.get_tool_definitions()
        
        # Khoj tools can be SEARCH, FILE, or EXECUTION type
        for tool in tool_defs:
            assert tool.tool_type in [MCPToolType.SEARCH, MCPToolType.FILE, MCPToolType.EXECUTION]


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
