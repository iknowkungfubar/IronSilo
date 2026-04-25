"""
MCP (Model Context Protocol) framework for IronSilo.

This module provides a reusable MCP server framework that wraps FastAPI
endpoints as MCP tools for IronClaw integration.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Type, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .models import (
    MCPError,
    MCPMessageType,
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPToolType,
    MCPServerInfo,
)

logger = structlog.get_logger(__name__)


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
    
    This class provides the foundation for creating MCP-compatible servers
    that can be used by IronClaw for tool integration.
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
        
        # Initialize logging
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
    ) -> Callable:
        """
        Decorator to register an MCP tool.
        
        Args:
            name: Tool name (must be unique)
            description: Tool description
            tool_type: Type of tool
            parameters: Parameter schema
            returns: Return value schema
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            # Store the function
            self._tools[name] = func
            
            # Create tool definition
            tool_def = MCPTool(
                name=name,
                description=description,
                tool_type=tool_type,
                parameters=parameters or {},
                returns=returns or {},
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
    ) -> MCPResponse:
        """
        Execute an MCP tool.
        
        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            request_id: Request ID for tracking
            
        Returns:
            MCP response with result or error
        """
        start_time = time.time()
        
        try:
            # Check if tool exists
            if tool_name not in self._tools:
                raise MCPToolError(
                    code=-32601,
                    message=f"Tool not found: {tool_name}",
                    data={"available_tools": list(self._tools.keys())}
                )
            
            # Get tool function
            tool_func = self._tools[tool_name]
            
            # Log tool execution
            self.logger.info(
                "Executing MCP tool",
                tool=tool_name,
                request_id=request_id,
                params_keys=list(params.keys()),
            )
            
            # Execute tool
            result = await self._call_tool(tool_func, params)
            
            # Log success
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
            )
            
        except MCPToolError as e:
            # Tool-specific error
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
                error=MCPError(
                    code=e.code,
                    message=e.message,
                    data=e.data,
                ),
            )
            
        except Exception as e:
            # Unexpected error
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
                    data={"exception_type": type(e).__name__}
                ),
            )
    
    async def _call_tool(self, func: Callable, params: Dict[str, Any]) -> Any:
        """Call a tool function, handling both sync and async functions."""
        import inspect
        if inspect.iscoroutinefunction(func):
            return await func(**params)
        else:
            # Run sync function in executor to avoid blocking
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
    
    def get_tool_handler(self, tool_name: str) -> Optional[Callable]:
        """
        Get a tool handler by name for testing purposes.
        
        This method allows tests to directly call tool handlers without
        going through the full MCP protocol.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            The tool handler function, or None if not found
        """
        return self._tools.get(tool_name)
    
    def get_tool_definitions(self) -> List[MCPTool]:
        """Get list of all registered tool definitions."""
        return list(self._tool_definitions.values())


class MCPFastAPIWrapper:
    """
    FastAPI wrapper for MCP servers.
    
    This class creates a FastAPI application that wraps an MCP server,
    exposing it via HTTP endpoints compatible with IronClaw.
    """
    
    def __init__(self, mcp_server: MCPServerBase):
        self.mcp_server = mcp_server
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            self.mcp_server.logger.info("Starting MCP server")
            await self.mcp_server.initialize()
            yield
            # Shutdown
            self.mcp_server.logger.info("Shutting down MCP server")
            await self.mcp_server.shutdown()
        
        app = FastAPI(
            title=f"{self.mcp_server.name} MCP Server",
            description=self.mcp_server.description,
            version=self.mcp_server.version,
            lifespan=lifespan,
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add routes
        self._add_routes(app)
        
        return app
    
    def _add_routes(self, app: FastAPI) -> None:
        """Add MCP routes to FastAPI app."""
        
        @app.get("/", response_model=MCPServerInfo)
        async def server_info():
            """Get MCP server information."""
            return self.mcp_server.get_server_info()
        
        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "server": self.mcp_server.name}
        
        @app.get("/tools")
        async def list_tools():
            """List all available MCP tools."""
            tools = self.mcp_server.get_tool_definitions()
            return {
                "tools": [tool.model_dump() for tool in tools],
                "count": len(tools),
            }
        
        @app.post("/mcp")
        async def mcp_endpoint(request: MCPRequest):
            """Main MCP endpoint for tool execution."""
            return await self.mcp_server.execute_tool(
                tool_name=request.tool,
                params=request.params,
                request_id=request.id,
            )
        
        @app.post("/tools/{tool_name}")
        async def tool_endpoint(tool_name: str, request: Request):
            """Direct tool invocation endpoint."""
            try:
                params = await request.json()
            except Exception:
                params = {}
            
            # Generate request ID if not provided
            import uuid
            request_id = str(uuid.uuid4())
            
            response = await self.mcp_server.execute_tool(
                tool_name=tool_name,
                params=params,
                request_id=request_id,
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
                }
            )


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
