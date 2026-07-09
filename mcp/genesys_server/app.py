"""
Application factory for the Memory MCP server.

Provides the FastAPI application factory and module-level app
for uvicorn, plus backward-compatible aliases.
"""

from __future__ import annotations

from typing import Any

from ..framework import create_mcp_app
from .server import MemoryMCPServer


def create_memory_mcp_app(
    memory_api_url: str = "http://memory:8020",
) -> Any:
    """Create FastAPI app for Memory MCP server."""
    server = MemoryMCPServer(memory_api_url=memory_api_url)
    return create_mcp_app(server)


# For uvicorn
app = create_memory_mcp_app()


# Backward-compatible aliases
GenesysMCPServer = MemoryMCPServer
create_genesys_mcp_app = create_memory_mcp_app
