"""
MCP (Model Context Protocol) integration for IronSilo.

This package provides MCP servers for integrating IronClaw with various
services like Genesys memory and Khoj RAG engine.
"""

from .framework import MCPServerBase, MCPFastAPIWrapper, MCPToolError, create_mcp_app
from .genesys_server import GenesysMCPServer, create_genesys_mcp_app
from .khoj_server import KhojMCPServer, create_khoj_mcp_app
from .models import (
    DocumentInfo,
    MCPError,
    MCPMessageType,
    MCPRequest,
    MCPResponse,
    MCPServerInfo,
    MCPTool,
    MCPToolType,
    MemoryEdge,
    MemoryNode,
    MemoryQuery,
    MemorySearchResult,
    SearchQuery,
    SearchResult,
    Session,
)

__version__ = "1.0.0"

__all__ = [
    # Framework
    "MCPServerBase",
    "MCPFastAPIWrapper",
    "MCPToolError",
    "create_mcp_app",
    
    # Servers
    "GenesysMCPServer",
    "create_genesys_mcp_app",
    "KhojMCPServer",
    "create_khoj_mcp_app",
    
    # Models
    "DocumentInfo",
    "MCPError",
    "MCPMessageType",
    "MCPRequest",
    "MCPResponse",
    "MCPServerInfo",
    "MCPTool",
    "MCPToolType",
    "MemoryEdge",
    "MemoryNode",
    "MemoryQuery",
    "MemorySearchResult",
    "SearchQuery",
    "SearchResult",
    "Session",
]
