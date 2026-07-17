"""
Memory MCP server for IronSilo.

Replaces Genesys with IronSilo Memory Service (sqlite-vec backed).
Provides memory operations, session management, and vector search
with zero Docker infrastructure requirements.

Integration path: Stash (single Go binary, MCP-native) can replace this
when 8-stage consolidation pipeline is needed.
"""

from __future__ import annotations

from .server import MemoryMCPServer
from .app import (
    GenesysMCPServer,
    app,
    create_genesys_mcp_app,
    create_memory_mcp_app,
)

__all__ = [
    "MemoryMCPServer",
    "GenesysMCPServer",
    "create_memory_mcp_app",
    "create_genesys_mcp_app",
    "app",
]
