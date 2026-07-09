"""
MCP (Model Context Protocol) framework for IronSilo.

Updated for MCP 2026-07-28 RC stateless protocol:
- _meta injection on every response (protocol version, server identity, trace context)
- server/discover endpoint with capability discovery
- MCP protocol headers (Mcp-Protocol-Version, Mcp-Method, Mcp-Name)
- ttlMs/cacheScope on list responses
- W3C Trace Context via traceparent header
- Tool annotations (readOnlyHint, idempotentHint, destructiveHint)
- Stateless — no session store dependency
- JSON Schema 2020-12 (via Pydantic V2)
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .models import (
    MCPError,
    MCPMessageType,
    MCPResponse,
    MCP_PROTOCOL_VERSION,
    MCPTool,
    MCPServerInfo,
    MCPToolType,
    ServerCard,
    ServerMeta,
    ToolAnnotation,
)

logger = structlog.get_logger(__name__)


def _parse_traceparent(header: str) -> str:
    """Extract trace_id from W3C Trace Context header, or generate one."""
    if header and "-" in header:
        parts = header.split("-")
        if len(parts) >= 1:
            return f"00-{parts[0]}-{uuid.uuid4().hex[:16]}-01"
    return f"00-{uuid.uuid4().hex[:32]}-{uuid.uuid4().hex[:16]}-01"


def _build_meta(server_name: str, server_version: str, traceparent: str = "") -> ServerMeta:
    """Build _meta payload for MCP response."""
    return ServerMeta(
        protocol_version=MCP_PROTOCOL_VERSION,
        server_name=server_name,
        server_version=server_version,
        traceparent=traceparent or _parse_traceparent(""),
    )


class MCPToolError(Exception):
    """Exception raised when MCP tool execution fails."""

    def __init__(self, code: int, message: str, data: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class MCPServerBase(ABC):
    """
    Abstract base class for MCP servers.

    Provides the foundation for creating MCP-compatible servers
    that expose tools via the Model Context Protocol.
    Stateless — no session storage.
    """

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        capabilities: Optional[List[str]] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.capabilities = capabilities or []
        self._tools: Dict[str, Callable] = {}
        self._tool_definitions: Dict[str, MCPTool] = {}

        self.logger = logger.bind(server=name, version=version)

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the server. Override in subclasses."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the server. Override in subclasses."""
        pass

    def register_tool(
        self,
        name: str,
        description: str,
        tool_type: MCPToolType,
        parameters: Optional[Dict[str, Any]] = None,
        returns: Optional[Dict[str, Any]] = None,
        annotations: Optional[ToolAnnotation] = None,
        ttl_ms: Optional[int] = None,
        cache_scope: Optional[str] = None,
    ) -> Callable:
        """
        Decorator to register an MCP tool with the 2026-07-28 protocol.

        Args:
            name: Tool name (must be unique)
            description: Tool description
            tool_type: Type of tool
            parameters: JSON Schema for input arguments
            returns: JSON Schema for output
            annotations: Tool behaviour hints
            ttl_ms: Cache TTL in milliseconds for tool list
            cache_scope: Cache scope identifier

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            self._tools[name] = func

            # Build inputSchema from parameters dict
            input_schema = parameters or {}
            if "type" not in input_schema:
                input_schema = {
                    "type": "object",
                    "properties": input_schema,
                }

            tool_def = MCPTool(
                name=name,
                description=description,
                tool_type=tool_type,
                inputSchema=input_schema,
                outputSchema=returns or {},
                annotations=annotations,
                ttlMs=ttl_ms,
                cacheScope=cache_scope,
            )
            self._tool_definitions[name] = tool_def

            self.logger.info(
                "Registered MCP tool",
                tool=name,
                type=tool_type.value,
            )

            return func

        return decorator

    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        request_id: str,
        traceparent: str = "",
    ) -> MCPResponse:
        """
        Execute an MCP tool with _meta injection.

        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            request_id: Request ID for tracking
            traceparent: W3C Trace Context header value

        Returns:
            MCP response with _meta, result or error
        """
        start_time = time.time()
        meta = _build_meta(self.name, self.version, traceparent)

        try:
            if tool_name not in self._tools:
                raise MCPToolError(
                    code=-32601,
                    message=f"Tool not found: {tool_name}",
                    data={"available_tools": list(self._tools.keys())},
                )

            tool_func = self._tools[tool_name]

            self.logger.info(
                "Executing MCP tool",
                tool=tool_name,
                request_id=request_id,
                params_keys=list(params.keys()),
            )

            result = await self._call_tool(tool_func, params)

            duration = time.time() - start_time
            self.logger.info(
                "MCP tool executed successfully",
                tool=tool_name,
                request_id=request_id,
                duration_ms=round(duration * 1000, 2),
            )

            return MCPResponse(
                id=request_id,
                type=MCPMessageType.RESPONSE,
                result=result,
                error=None,
                _meta=meta,
            )

        except MCPToolError as e:
            duration = time.time() - start_time
            self.logger.error(
                "MCP tool execution failed",
                tool=tool_name,
                request_id=request_id,
                error_code=e.code,
                error_message=e.message,
                duration_ms=round(duration * 1000, 2),
            )

            return MCPResponse(
                id=request_id,
                type=MCPMessageType.ERROR,
                error=MCPError(code=e.code, message=e.message, data=e.data),
                _meta=meta,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.exception(
                "Unexpected error during MCP tool execution",
                tool=tool_name,
                request_id=request_id,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )

            return MCPResponse(
                id=request_id,
                type=MCPMessageType.ERROR,
                error=MCPError(
                    code=-32603,
                    message=f"Internal error: {str(e)}",
                    data={"exception_type": type(e).__name__},
                ),
                _meta=meta,
            )

    async def _call_tool(self, func: Callable, params: Dict[str, Any]) -> Any:
        """Call a tool function, handling both sync and async functions."""
        import inspect

        if inspect.iscoroutinefunction(func):
            return await func(**params)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(**params))

    def get_server_info(self) -> MCPServerInfo:
        """Get server information including available tools."""
        return MCPServerInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            tools=list(self._tool_definitions.values()),
            capabilities=self.capabilities,
        )

    def get_server_card(self) -> ServerCard:
        """Get server card for /.well-known/mcp/server-card.json discovery."""
        return ServerCard(
            name=self.name,
            version=self.version,
            description=self.description,
            capabilities=self.capabilities,
        )

    def get_tool_handler(self, tool_name: str) -> Optional[Callable]:
        """Get a tool handler by name for testing."""
        return self._tools.get(tool_name)

    def get_tool_definitions(self) -> List[MCPTool]:
        """Get list of all registered tool definitions."""
        return list(self._tool_definitions.values())

    def get_discover_response(self) -> Dict[str, Any]:
        """Build the /mcp/discover response with server card + tools + ttl/cache hints."""
        card = self.get_server_card()
        tools = self.get_tool_definitions()

        return {
            "server": card.model_dump(),
            "tools": [t.model_dump(exclude_none=True) for t in tools],
            "tool_count": len(tools),
            "ttlMs": 30_000,
            "cacheScope": f"mcp:{self.name}",
        }


class MCPFastAPIWrapper:
    """
    FastAPI wrapper for MCP servers with 2026-07-28 protocol compliance.

    Adds _meta injection, server/discover endpoint, protocol headers,
    W3C Trace Context, and ttlMs/cacheScope to responses.
    """

    def __init__(self, mcp_server: MCPServerBase):
        self.mcp_server = mcp_server
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            self.mcp_server.logger.info("Starting MCP server")
            await self.mcp_server.initialize()
            yield
            self.mcp_server.logger.info("Shutting down MCP server")
            await self.mcp_server.shutdown()

        app = FastAPI(
            title=f"{self.mcp_server.name} MCP Server",
            description=self.mcp_server.description,
            version=self.mcp_server.version,
            lifespan=lifespan,
        )

        # CORS middleware
        _cors_origins = os.getenv("MCP_CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=[
                "Mcp-Protocol-Version",
                "Mcp-Method",
                "Mcp-Name",
                "Traceparent",
            ],
        )

        # Middleware for MCP protocol headers
        @app.middleware("http")
        async def add_mcp_headers(request: Request, call_next):
            response = await call_next(request)

            # Extract trace context from request
            traceparent = request.headers.get("traceparent", "")
            tp = _parse_traceparent(traceparent)

            # Add MCP protocol headers to every response
            response.headers["Mcp-Protocol-Version"] = MCP_PROTOCOL_VERSION
            response.headers["Mcp-Name"] = self.mcp_server.name
            response.headers["Mcp-Method"] = request.method
            if tp:
                response.headers["Traceparent"] = tp
            return response

        self._add_routes(app)
        return app

    def _add_routes(self, app: FastAPI) -> None:

        @app.get("/", response_model=MCPServerInfo)
        async def server_info():
            """Get MCP server information."""
            return self.mcp_server.get_server_info()

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "server": self.mcp_server.name,
                "protocol_version": MCP_PROTOCOL_VERSION,
            }

        @app.get("/mcp/discover")
        async def discover(request: Request):
            """MCP capability discovery endpoint.

            Returns server card, tools with annotations, and caching hints.
            """
            return self.mcp_server.get_discover_response()

        @app.get("/tools")
        async def list_tools(request: Request):
            """List all available MCP tools with ttlMs/cacheScope hints."""
            tools = self.mcp_server.get_tool_definitions()
            return {
                "tools": [t.model_dump(exclude_none=True) for t in tools],
                "count": len(tools),
                "ttlMs": 30_000,
                "cacheScope": f"mcp:{self.mcp_server.name}",
            }

        @app.post("/mcp")
        async def mcp_endpoint(request: Request):
            """Main MCP endpoint — JSON-RPC over HTTP.

            Accepts standard MCP request format with method like 'tools/call'.
            """
            traceparent = request.headers.get("traceparent", "")

            try:
                body = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON body")

            if isinstance(body, dict) and "method" in body:
                # JSON-RPC format: {"method": "tools/call", "params": {"name": "...", "arguments": {...}}}
                method = body.get("method", "")
                params = body.get("params", {})
                req_id = body.get("id", str(uuid.uuid4()))

                if method == "tools/call":
                    tool_name = params.get("name", "")
                    arguments = params.get("arguments", {})
                    if not tool_name:
                        raise HTTPException(status_code=400, detail="Missing tool name in params")
                    response = await self.mcp_server.execute_tool(
                        tool_name=tool_name,
                        params=arguments,
                        request_id=str(req_id),
                        traceparent=traceparent,
                    )
                    return _response_to_json_rpc(response)

                elif method in ("tools/list", "discover"):
                    return self.mcp_server.get_discover_response()

                elif method == "server/info":
                    return self.mcp_server.get_server_info().model_dump()

                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown method: {method}",
                    )
            else:
                # Legacy format: {"tool": "...", "params": {...}}
                tool_name = body.get("tool", "")
                params = body.get("params", {})
                req_id = body.get("id", str(uuid.uuid4()))

                if not tool_name:
                    raise HTTPException(status_code=400, detail="Missing tool name")

                response = await self.mcp_server.execute_tool(
                    tool_name=tool_name,
                    params=params,
                    request_id=str(req_id),
                    traceparent=traceparent,
                )
                return _response_to_json_rpc(response)

        @app.post("/tools/{tool_name}")
        async def tool_endpoint(tool_name: str, request: Request):
            """Direct tool invocation endpoint (legacy compatibility)."""
            traceparent = request.headers.get("traceparent", "")

            try:
                params = await request.json()
            except Exception:
                params = {}

            request_id = str(uuid.uuid4())
            response = await self.mcp_server.execute_tool(
                tool_name=tool_name,
                params=params,
                request_id=request_id,
                traceparent=traceparent,
            )

            if response.error:
                raise HTTPException(
                    status_code=400,
                    detail=response.error.model_dump(),
                )

            return response.result

        @app.exception_handler(MCPToolError)
        async def mcp_tool_error_handler(request: Request, exc: MCPToolError):
            """Handle MCP tool errors."""
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "data": exc.data,
                    }
                },
            )


def _response_to_json_rpc(response: MCPResponse) -> Dict[str, Any]:
    """Convert internal MCPResponse to JSON-RPC response format."""
    result = {
        "id": response.id,
        "jsonrpc": "2.0",
    }
    if response.error:
        result["error"] = {
            "code": response.error.code,
            "message": response.error.message,
        }
        if response.error.data:
            result["error"]["data"] = response.error.data
    else:
        result["result"] = response.result

    # Include _meta if present
    if response._meta:
        result["_meta"] = {
            "protocol_version": response._meta.protocol_version,
            "server_name": response._meta.server_name,
            "server_version": response._meta.server_version,
            "traceparent": response._meta.traceparent,
        }

    return result


def create_mcp_app(server: MCPServerBase) -> FastAPI:
    """
    Create a FastAPI application from an MCP server.

    Args:
        server: MCP server instance

    Returns:
        FastAPI application
    """
    wrapper = MCPFastAPIWrapper(server)
    return wrapper.app
