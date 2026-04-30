"""
Contract tests for MCP servers.

Tests cover:
- OpenAPI schema validation
- Tool endpoint contracts
- Request/response format compliance
- Error handling consistency

Run with: pytest tests/contract/test_mcp_contracts.py -v
"""

import pytest
from fastapi.testclient import TestClient


class TestMCPFrameworkContracts:
    """Contract tests for MCP framework."""

    def test_mcp_server_base_has_required_methods(self):
        """Test MCPServerBase has required abstract methods."""
        from mcp.framework import MCPServerBase

        assert hasattr(MCPServerBase, 'initialize')
        assert hasattr(MCPServerBase, 'shutdown')
        assert hasattr(MCPServerBase, 'register_tool')
        assert hasattr(MCPServerBase, 'execute_tool')
        assert hasattr(MCPServerBase, 'get_server_info')

    def test_mcp_fastapi_wrapper_creates_valid_app(self):
        """Test MCPFastAPIWrapper creates a valid FastAPI app."""
        from mcp.framework import MCPServerBase, create_mcp_app

        class MockMCPServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        server = MockMCPServer(name="test", version="1.0.0")
        app = create_mcp_app(server)

        assert app is not None
        assert app.title == "test MCP Server"


class TestMCPModelsContracts:
    """Contract tests for MCP models."""

    def test_mcp_request_model(self):
        """Test MCPRequest model validation."""
        from mcp.models import MCPRequest

        request = MCPRequest(
            id="test-123",
            tool="test_tool",
            params={"key": "value"},
        )

        assert request.id == "test-123"
        assert request.tool == "test_tool"
        assert request.params == {"key": "value"}

    def test_mcp_response_model(self):
        """Test MCPResponse model with result."""
        from mcp.models import MCPRequest, MCPResponse, MCPMessageType

        response = MCPResponse(
            id="test-123",
            type=MCPMessageType.RESPONSE,
            result={"output": "test output"},
        )

        assert response.id == "test-123"
        assert response.type == MCPMessageType.RESPONSE
        assert response.result == {"output": "test output"}
        assert response.error is None

    def test_mcp_error_model(self):
        """Test MCPResponse model with error."""
        from mcp.models import MCPRequest, MCPResponse, MCPMessageType, MCPError

        response = MCPResponse(
            id="test-123",
            type=MCPMessageType.ERROR,
            error=MCPError(code=-32601, message="Tool not found"),
        )

        assert response.id == "test-123"
        assert response.type == MCPMessageType.ERROR
        assert response.result is None
        assert response.error is not None
        assert response.error.code == -32601

    def test_mcp_tool_model(self):
        """Test MCPTool model."""
        from mcp.models import MCPTool, MCPToolType

        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            tool_type=MCPToolType.MEMORY,
            parameters={"type": "object"},
        )

        assert tool.name == "test_tool"
        assert tool.tool_type == MCPToolType.MEMORY

    def test_mcp_server_info_model(self):
        """Test MCPServerInfo model."""
        from mcp.models import MCPServerInfo, MCPTool, MCPToolType

        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            tool_type=MCPToolType.MEMORY,
        )

        server_info = MCPServerInfo(
            name="test-server",
            version="1.0.0",
            description="Test MCP server",
            tools=[tool],
            capabilities=["memory"],
        )

        assert server_info.name == "test-server"
        assert len(server_info.tools) == 1
        assert "memory" in server_info.capabilities


class TestMCPToolRegistration:
    """Contract tests for MCP tool registration."""

    def test_tool_registration_via_method(self):
        """Test tool registration via register_tool method."""
        from mcp.framework import MCPServerBase
        from mcp.models import MCPToolType

        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

            async def test_tool_impl(self, param1: str):
                return {"result": param1}

        server = TestServer(name="test", version="1.0.0")
        server.register_tool(
            name="test_tool",
            description="Test tool",
            tool_type=MCPToolType.MEMORY,
        )(server.test_tool_impl)

        tool_defs = server.get_tool_definitions()
        assert len(tool_defs) == 1
        assert tool_defs[0].name == "test_tool"

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test tool execution through MCP server."""
        from mcp.framework import MCPServerBase
        from mcp.models import MCPToolType, MCPMessageType

        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

            async def add_impl(self, a: int, b: int):
                return {"sum": a + b}

        server = TestServer(name="test", version="1.0.0")
        server.register_tool(
            name="add",
            description="Add two numbers",
            tool_type=MCPToolType.MEMORY,
        )(server.add_impl)

        response = await server.execute_tool(
            tool_name="add",
            params={"a": 5, "b": 3},
            request_id="req-123",
        )

        assert response.type == MCPMessageType.RESPONSE
        assert response.result == {"sum": 8}


class TestMCPErrorHandling:
    """Contract tests for MCP error handling."""

    @pytest.mark.asyncio
    async def test_tool_not_found_error(self):
        """Test error when tool not found."""
        from mcp.framework import MCPServerBase
        from mcp.models import MCPMessageType

        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        server = TestServer(name="test", version="1.0.0")

        response = await server.execute_tool(
            tool_name="nonexistent",
            params={},
            request_id="req-123",
        )

        assert response.type == MCPMessageType.ERROR
        assert response.error is not None
        assert response.error.code == -32601

    @pytest.mark.asyncio
    async def test_internal_error_handling(self):
        """Test internal error handling."""
        from mcp.framework import MCPServerBase
        from mcp.models import MCPToolType, MCPMessageType

        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

            async def failing_impl(self):
                raise ValueError("Test error")

        server = TestServer(name="test", version="1.0.0")
        server.register_tool(
            name="failing_tool",
            description="A tool that fails",
            tool_type=MCPToolType.MEMORY,
        )(server.failing_impl)

        response = await server.execute_tool(
            tool_name="failing_tool",
            params={},
            request_id="req-123",
        )

        assert response.type == MCPMessageType.ERROR
        assert response.error is not None
        assert response.error.code == -32603


class TestMCPEndpoints:
    """Contract tests for MCP HTTP endpoints."""

    def test_server_info_endpoint(self):
        """Test server info endpoint returns valid structure."""
        from mcp.framework import MCPServerBase, create_mcp_app

        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        server = TestServer(name="test-server", version="1.0.0")
        app = create_mcp_app(server)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-server"
        assert data["version"] == "1.0.0"

    def test_health_endpoint(self):
        """Test health endpoint."""
        from mcp.framework import MCPServerBase, create_mcp_app

        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        server = TestServer(name="test-server")
        app = create_mcp_app(server)
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_tools_list_endpoint(self):
        """Test tools list endpoint."""
        from mcp.framework import MCPServerBase, create_mcp_app
        from mcp.models import MCPToolType

        class TestServer(MCPServerBase):
            async def initialize(self) -> None:
                pass

            async def shutdown(self) -> None:
                pass

            async def test_impl(self):
                return {"result": "test"}

        server = TestServer(name="test-server")
        server.register_tool(
            name="test_tool",
            description="Test tool",
            tool_type=MCPToolType.MEMORY,
        )(server.test_impl)

        app = create_mcp_app(server)
        client = TestClient(app)

        response = client.get("/tools")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["tools"]) == 1
