"""
MCP (Model Context Protocol) integration for IronSilo.

Provides MCP servers for:
- rag_memory: Memory operations (replaces Genesys)
- rag_search: RAG search (replaces Khoj)

Backward-compatible aliases are maintained so existing tests
and imports continue to work.
"""

from .framework import MCPServerBase, MCPFastAPIWrapper, MCPToolError, create_mcp_app
from .genesys_server import MemoryMCPServer, create_memory_mcp_app
from .khoj_server import RAGMCPServer, create_rag_mcp_app
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

__version__ = "2.0.0"

__all__ = [
    # Framework
    "MCPServerBase",
    "MCPFastAPIWrapper",
    "MCPToolError",
    "create_mcp_app",
    # New names
    "MemoryMCPServer",
    "create_memory_mcp_app",
    "RAGMCPServer",
    "create_rag_mcp_app",
    # Backward-compatible aliases
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
