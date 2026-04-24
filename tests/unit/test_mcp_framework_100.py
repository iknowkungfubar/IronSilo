"""
Comprehensive tests for mcp/framework.py to achieve 100% coverage.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.models import (
    MCPError,
    MCPMessageType,
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPToolType,
    MCPServerInfo,
)


class TestMCPToolError:
    """Tests for MCPToolError class."""
    
    def test_mcp_tool_error_creation(self):
        """Test MCPToolError creation with all fields."""
        from mcp.framework import MCPToolError
        
        error = MCPToolError(
            code=400,
            message="Bad request",
            data={"field": "value"},
        )
        
        assert error.code == 400
        assert error.message == "Bad request"
        assert error.data == {"field": "value"}
        assert str(error) == "Bad request"
    
    def test_mcp_tool_error_without_data(self):
        """Test MCPToolError without optional data."""
        from mcp.framework import MCPToolError
        
        error = MCPToolError(code=500, message="Internal error")
        
        assert error.code == 500
        assert error.message == "Internal error"
        assert error.data is None


class TestMCPServerBase:
    """Tests for MCPServerBase abstract class."""
    
    def test_concrete_implementation(self):
        """Test concrete implementation of MCPServerBase."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(
            name="test-server",
            version="1.0.0",
            description="Test server",
            capabilities=["test"],
        )
        
        assert server.name == "test-server"
        assert server.version == "1.0.0"
        assert server.description == "Test server"
        assert server.capabilities == ["test"]
        assert server._tools == {}
        assert server._tool_definitions == {}
    
    def test_register_tool(self):
        """Test register_tool decorator."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        
        @server.register_tool(
            name="test_tool",
            description="A test tool",
            tool_type=MCPToolType.CUSTOM,
            parameters={"param1": {"type": "string"}},
            returns={"type": "object"},
        )
        async def test_handler(param1: str) -> Dict[str, Any]:
            return {"result": param1}
        
        assert "test_tool" in server._tools
        assert "test_tool" in server._tool_definitions
        assert server._tool_definitions["test_tool"].name == "test_tool"
        assert server._tool_definitions["test_tool"].description == "A test tool"
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        
        @server.register_tool(
            name="add",
            description="Add two numbers",
            tool_type=MCPToolType.CUSTOM,
        )
        async def add(a: int, b: int) -> int:
            return a + b
        
        response = await server.execute_tool(
            tool_name="add",
            params={"a": 5, "b": 3},
            request_id="test-123",
        )
        
        assert response.id == "test-123"
        assert response.type == MCPMessageType.RESPONSE
        assert response.result == 8
        assert response.error is None
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test tool execution with non-existent tool."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        
        response = await server.execute_tool(
            tool_name="nonexistent",
            params={},
            request_id="test-123",
        )
        
        assert response.id == "test-123"
        assert response.type == MCPMessageType.ERROR
        assert response.error is not None
        assert response.error.code == -32601
        assert "not found" in response.error.message
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self):
        """Test tool execution that raises MCPToolError."""
        from mcp.framework import MCPServerBase, MCPToolError
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        
        @server.register_tool(
            name="fail",
            description="Always fails",
            tool_type=MCPToolType.CUSTOM,
        )
        async def fail() -> str:
            raise MCPToolError(code=400, message="Intentional failure", data={"reason": "test"})
        
        response = await server.execute_tool(
            tool_name="fail",
            params={},
            request_id="test-123",
        )
        
        assert response.id == "test-123"
        assert response.type == MCPMessageType.ERROR
        assert response.error.code == 400
        assert "Intentional failure" in response.error.message
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_unexpected_error(self):
        """Test tool execution with unexpected error."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        
        @server.register_tool(
            name="crash",
            description="Crashes unexpectedly",
            tool_type=MCPToolType.CUSTOM,
        )
        async def crash() -> str:
            raise ValueError("Unexpected error")
        
        response = await server.execute_tool(
            tool_name="crash",
            params={},
            request_id="test-123",
        )
        
        assert response.id == "test-123"
        assert response.type == MCPMessageType.ERROR
        assert response.error.code == -32603
        assert "Internal error" in response.error.message
    
    @pytest.mark.asyncio
    async def test_execute_sync_tool(self):
        """Test execution of synchronous tool function."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        
        @server.register_tool(
            name="sync_add",
            description="Sync add",
            tool_type=MCPToolType.CUSTOM,
        )
        def sync_add(a: int, b: int) -> int:
            return a + b
        
        response = await server.execute_tool(
            tool_name="sync_add",
            params={"a": 10, "b": 20},
            request_id="test-123",
        )
        
        assert response.result == 30
    
    def test_get_server_info(self):
        """Test get_server_info method."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(
            name="test",
            version="1.0.0",
            description="Test server",
            capabilities=["memory", "search"],
        )
        
        @server.register_tool(
            name="tool1",
            description="Tool 1",
            tool_type=MCPToolType.MEMORY,
        )
        async def tool1() -> None:
            pass
        
        info = server.get_server_info()
        
        assert info.name == "test"
        assert info.version == "1.0.0"
        assert info.description == "Test server"
        assert len(info.tools) == 1
        assert info.capabilities == ["memory", "search"]
    
    def test_get_tool_definitions(self):
        """Test get_tool_definitions method."""
        from mcp.framework import MCPServerBase
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        
        @server.register_tool(
            name="tool1",
            description="Tool 1",
            tool_type=MCPToolType.MEMORY,
        )
        async def tool1() -> None:
            pass
        
        @server.register_tool(
            name="tool2",
            description="Tool 2",
            tool_type=MCPToolType.SEARCH,
        )
        async def tool2() -> None:
            pass
        
        tools = server.get_tool_definitions()
        
        assert len(tools) == 2
        assert all(isinstance(t, MCPTool) for t in tools)


class TestMCPFastAPIWrapper:
    """Tests for MCPFastAPIWrapper class."""
    
    def test_wrapper_initialization(self):
        """Test MCPFastAPIWrapper initialization."""
        from mcp.framework import MCPServerBase, MCPFastAPIWrapper
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        wrapper = MCPFastAPIWrapper(server)
        
        assert wrapper.mcp_server == server
        assert wrapper.app is not None
    
    def test_wrapper_creates_routes(self):
        """Test that wrapper creates all routes."""
        from mcp.framework import MCPServerBase, MCPFastAPIWrapper
        from fastapi.testclient import TestClient
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0", description="Test")
        wrapper = MCPFastAPIWrapper(server)
        
        client = TestClient(wrapper.app)
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Test tools endpoint
        response = client.get("/tools")
        assert response.status_code == 200
        assert "tools" in response.json()
    
    def test_wrapper_tool_endpoint(self):
        """Test wrapper tool endpoint."""
        from mcp.framework import MCPServerBase, MCPFastAPIWrapper
        from fastapi.testclient import TestClient
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
            
            def register_tools(self):
                @self.register_tool(
                    name="test",
                    description="Test tool",
                    tool_type=MCPToolType.CUSTOM,
                )
                async def test_tool(value: str) -> Dict[str, Any]:
                    return {"echo": value}
        
        server = TestServer(name="test", version="1.0.0")
        server.register_tools()
        
        wrapper = MCPFastAPIWrapper(server)
        client = TestClient(wrapper.app)
        
        response = client.post(
            "/tools/test",
            json={"value": "hello"},
        )
        
        assert response.status_code == 200
        assert response.json() == {"echo": "hello"}


class TestCreateMCPApp:
    """Tests for create_mcp_app function."""
    
    def test_create_mcp_app(self):
        """Test create_mcp_app function."""
        from mcp.framework import MCPServerBase, create_mcp_app
        
        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass
            
            async def shutdown(self) -> None:
                pass
        
        server = TestServer(name="test", version="1.0.0")
        app = create_mcp_app(server)
        
        assert app is not None
        assert hasattr(app, "routes")


class TestMCPModels:
    """Tests for MCP models."""
    
    def test_mcp_message_type_enum(self):
        """Test MCPMessageType enum values."""
        assert MCPMessageType.REQUEST.value == "request"
        assert MCPMessageType.RESPONSE.value == "response"
        assert MCPMessageType.NOTIFICATION.value == "notification"
        assert MCPMessageType.ERROR.value == "error"
    
    def test_mcp_tool_type_enum(self):
        """Test MCPToolType enum values."""
        assert MCPToolType.MEMORY.value == "memory"
        assert MCPToolType.SEARCH.value == "search"
        assert MCPToolType.FILE.value == "file"
        assert MCPToolType.EXECUTION.value == "execution"
        assert MCPToolType.CUSTOM.value == "custom"
    
    def test_mcp_error_model(self):
        """Test MCPError model."""
        error = MCPError(code=400, message="Bad request", data={"field": "value"})
        
        assert error.code == 400
        assert error.message == "Bad request"
        assert error.data == {"field": "value"}
    
    def test_mcp_request_model(self):
        """Test MCPRequest model."""
        request = MCPRequest(
            tool="test_tool",
            method="call",
            params={"param": "value"},
        )
        
        assert request.tool == "test_tool"
        assert request.method == "call"
        assert request.params == {"param": "value"}
        assert request.type == MCPMessageType.REQUEST
    
    def test_mcp_request_auto_id(self):
        """Test MCPRequest auto-generated ID."""
        request = MCPRequest(tool="test")
        
        assert request.id is not None
        assert len(request.id) > 0
    
    def test_mcp_response_model(self):
        """Test MCPResponse model."""
        response = MCPResponse(
            id="test-123",
            type=MCPMessageType.RESPONSE,
            result={"output": "success"},
        )
        
        assert response.id == "test-123"
        assert response.result == {"output": "success"}
        assert response.error is None
        assert response.is_success is True
    
    def test_mcp_response_with_error(self):
        """Test MCPResponse with error."""
        response = MCPResponse(
            id="test-123",
            type=MCPMessageType.ERROR,
            error=MCPError(code=500, message="Internal error"),
        )
        
        assert response.error is not None
        assert response.error.code == 500
        assert response.is_success is False
    
    def test_mcp_tool_model(self):
        """Test MCPTool model."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            tool_type=MCPToolType.CUSTOM,
            parameters={"param1": {"type": "string"}},
            returns={"type": "object"},
        )
        
        assert tool.name == "test_tool"
        assert tool.tool_type == MCPToolType.CUSTOM
    
    def test_mcp_server_info_model(self):
        """Test MCPServerInfo model."""
        info = MCPServerInfo(
            name="test-server",
            version="1.0.0",
            description="Test server",
            tools=[],
            capabilities=["memory"],
        )
        
        assert info.name == "test-server"
        assert info.capabilities == ["memory"]
