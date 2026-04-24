"""
Unit tests for MCP framework.

Tests the core MCP server framework functionality including:
- Tool registration
- Request/response handling
- Error handling
- Server lifecycle
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from mcp.framework import MCPServerBase, MCPToolError, create_mcp_app
from mcp.models import (
    MCPError,
    MCPMessageType,
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPToolType,
    MCPServerInfo,
)


class TestMCPServer(MCPServerBase):
    """Concrete implementation of MCPServerBase for testing."""
    
    async def initialize(self) -> None:
        self.initialized = True
    
    async def shutdown(self) -> None:
        self.shut_down = True


class TestMCPServerBase:
    """Test cases for MCPServerBase."""
    
    def test_server_initialization(self):
        """Test server can be initialized with correct attributes."""
        server = TestMCPServer(
            name="test-server",
            version="1.0.0",
            description="Test server",
            capabilities=["test", "mock"],
        )
        
        assert server.name == "test-server"
        assert server.version == "1.0.0"
        assert server.description == "Test server"
        assert server.capabilities == ["test", "mock"]
        assert len(server._tools) == 0
        assert len(server._tool_definitions) == 0
    
    def test_tool_registration(self):
        """Test tools can be registered correctly."""
        server = TestMCPServer(name="test")
        
        @server.register_tool(
            name="test_tool",
            description="A test tool",
            tool_type=MCPToolType.CUSTOM,
            parameters={"param1": {"type": "string"}},
            returns={"type": "object"},
        )
        def test_tool(param1: str) -> dict:
            return {"result": param1}
        
        # Check tool was registered
        assert "test_tool" in server._tools
        assert "test_tool" in server._tool_definitions
        
        # Check tool definition
        tool_def = server._tool_definitions["test_tool"]
        assert tool_def.name == "test_tool"
        assert tool_def.description == "A test tool"
        assert tool_def.tool_type == MCPToolType.CUSTOM
    
    @pytest.mark.asyncio
    async def test_tool_execution_success(self):
        """Test successful tool execution."""
        server = TestMCPServer(name="test")
        
        @server.register_tool(
            name="success_tool",
            description="Tool that succeeds",
            tool_type=MCPToolType.CUSTOM,
        )
        async def success_tool(value: str) -> dict:
            return {"echo": value}
        
        response = await server.execute_tool(
            tool_name="success_tool",
            params={"value": "hello"},
            request_id="test-123",
        )
        
        assert response.is_success
        assert response.id == "test-123"
        assert response.result == {"echo": "hello"}
        assert response.error is None
    
    @pytest.mark.asyncio
    async def test_tool_execution_not_found(self):
        """Test execution of non-existent tool."""
        server = TestMCPServer(name="test")
        
        response = await server.execute_tool(
            tool_name="nonexistent",
            params={},
            request_id="test-456",
        )
        
        assert not response.is_success
        assert response.error is not None
        assert response.error.code == -32601
        assert "not found" in response.error.message.lower()
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_error(self):
        """Test tool that raises MCPToolError."""
        server = TestMCPServer(name="test")
        
        @server.register_tool(
            name="error_tool",
            description="Tool that fails",
            tool_type=MCPToolType.CUSTOM,
        )
        async def error_tool() -> dict:
            raise MCPToolError(
                code=-32000,
                message="Custom error",
                data={"detail": "Something went wrong"}
            )
        
        response = await server.execute_tool(
            tool_name="error_tool",
            params={},
            request_id="test-789",
        )
        
        assert not response.is_success
        assert response.error is not None
        assert response.error.code == -32000
        assert response.error.message == "Custom error"
        assert response.error.data == {"detail": "Something went wrong"}
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_unexpected_error(self):
        """Test tool that raises unexpected exception."""
        server = TestMCPServer(name="test")
        
        @server.register_tool(
            name="crash_tool",
            description="Tool that crashes",
            tool_type=MCPToolType.CUSTOM,
        )
        async def crash_tool() -> dict:
            raise ValueError("Unexpected error")
        
        response = await server.execute_tool(
            tool_name="crash_tool",
            params={},
            request_id="test-abc",
        )
        
        assert not response.is_success
        assert response.error is not None
        assert response.error.code == -32603
        assert "Internal error" in response.error.message
    
    @pytest.mark.asyncio
    async def test_sync_tool_execution(self):
        """Test execution of synchronous tool."""
        server = TestMCPServer(name="test")
        
        @server.register_tool(
            name="sync_tool",
            description="Synchronous tool",
            tool_type=MCPToolType.CUSTOM,
        )
        def sync_tool(x: int, y: int) -> dict:
            return {"sum": x + y}
        
        response = await server.execute_tool(
            tool_name="sync_tool",
            params={"x": 5, "y": 7},
            request_id="test-sync",
        )
        
        assert response.is_success
        assert response.result == {"sum": 12}
    
    def test_get_server_info(self):
        """Test server info generation."""
        server = TestMCPServer(
            name="test-server",
            version="2.0.0",
            description="Test server info",
            capabilities=["test", "mock", "unit"],
        )
        
        @server.register_tool(
            name="info_tool",
            description="Tool for info test",
            tool_type=MCPToolType.CUSTOM,
        )
        def info_tool() -> str:
            return "info"
        
        info = server.get_server_info()
        
        assert isinstance(info, MCPServerInfo)
        assert info.name == "test-server"
        assert info.version == "2.0.0"
        assert info.description == "Test server info"
        assert info.capabilities == ["test", "mock", "unit"]
        assert len(info.tools) == 1
        assert info.tools[0].name == "info_tool"
    
    def test_get_tool_definitions(self):
        """Test getting tool definitions."""
        server = TestMCPServer(name="test")
        
        @server.register_tool(
            name="tool1",
            description="Tool 1",
            tool_type=MCPToolType.MEMORY,
        )
        def tool1() -> None:
            pass
        
        @server.register_tool(
            name="tool2",
            description="Tool 2",
            tool_type=MCPToolType.SEARCH,
        )
        def tool2() -> None:
            pass
        
        tools = server.get_tool_definitions()
        
        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert tool_names == {"tool1", "tool2"}
    
    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self):
        """Test server lifecycle methods."""
        server = TestMCPServer(name="test")
        
        # Before initialization
        assert not hasattr(server, 'initialized') or not server.initialized
        
        await server.initialize()
        assert server.initialized
        
        await server.shutdown()
        assert server.shut_down


class TestMCPToolError:
    """Test cases for MCPToolError."""
    
    def test_error_creation(self):
        """Test creating MCPToolError."""
        error = MCPToolError(
            code=-32600,
            message="Invalid request",
            data={"field": "tool"},
        )
        
        assert error.code == -32600
        assert error.message == "Invalid request"
        assert error.data == {"field": "tool"}
        assert str(error) == "Invalid request"
    
    def test_error_without_data(self):
        """Test creating MCPToolError without data."""
        error = MCPToolError(
            code=-32601,
            message="Tool not found",
        )
        
        assert error.code == -32601
        assert error.message == "Tool not found"
        assert error.data is None


class TestCreateMCPApp:
    """Test cases for create_mcp_app function."""
    
    def test_create_app(self):
        """Test creating FastAPI app from MCP server."""
        server = TestMCPServer(
            name="test-app",
            version="1.0.0",
            description="Test application",
        )
        
        @server.register_tool(
            name="hello",
            description="Say hello",
            tool_type=MCPToolType.CUSTOM,
        )
        def hello(name: str) -> dict:
            return {"message": f"Hello, {name}!"}
        
        app = create_mcp_app(server)
        
        assert app.title == "test-app MCP Server"
        assert app.version == "1.0.0"
        assert app.description == "Test application"
