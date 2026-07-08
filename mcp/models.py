"""
MCP (Model Context Protocol) models for IronSilo.

Updated for MCP 2026-07-28 RC stateless protocol:
- _meta injection for every request/response
- Tool annotations (readOnlyHint, idempotentHint, etc.)
- ttlMs/cacheScope for list responses
- MCP protocol version headers
- W3C Trace Context support
- JSON Schema 2020-12 (via Pydantic V2)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# MCP Protocol Version
MCP_PROTOCOL_VERSION = "2026-07-28"


class MCPMessageType(str, Enum):
    """MCP message types."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPToolType(str, Enum):
    """Types of MCP tools available."""

    MEMORY = "memory"
    SEARCH = "search"
    FILE = "file"
    EXECUTION = "execution"
    CUSTOM = "custom"


class ToolAnnotation(BaseModel):
    """MCP tool annotation hints (2025-06-18+).

    Declares behaviour so clients can decide what to call
    without prompting the user.
    """

    readOnlyHint: bool = False
    idempotentHint: bool = False
    destructiveHint: bool = False
    openWorldHint: bool = True


class ServerMeta(BaseModel):
    """_meta payload injected into every MCP response.

    Carries protocol version, server identity, and W3C Trace Context.
    """

    protocol_version: str = MCP_PROTOCOL_VERSION
    server_name: str = ""
    server_version: str = ""
    traceparent: str = ""


class MCPError(BaseModel):
    """MCP error model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": -32601,
                "message": "Method not found",
                "data": {"method": "unknown_method"},
            }
        }
    )

    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPRequest(BaseModel):
    """MCP request model with _meta support."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "request",
                "method": "tools/call",
                "params": {
                    "name": "create_memory_node",
                    "arguments": {"content": "test"},
                },
            }
        }
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MCPMessageType = MCPMessageType.REQUEST
    method: str = "tools/call"
    params: Dict[str, Any] = Field(default_factory=dict)
    _meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MCPResponse(BaseModel):
    """MCP response model with _meta support."""

    id: str
    type: MCPMessageType = MCPMessageType.RESPONSE
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    _meta: Optional[ServerMeta] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_success(self) -> bool:
        return self.error is None


class MCPTool(BaseModel):
    """MCP tool definition with annotations and output schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "create_memory_node",
                "description": "Create a new memory node",
                "tool_type": "memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Memory content"},
                    },
                },
                "outputSchema": {
                    "type": "object",
                    "properties": {"node_id": {"type": "string"}},
                },
                "annotations": {
                    "readOnlyHint": False,
                    "idempotentHint": False,
                    "destructiveHint": False,
                },
            }
        }
    )

    name: str
    description: str
    tool_type: MCPToolType
    inputSchema: Dict[str, Any] = Field(default_factory=dict)
    outputSchema: Dict[str, Any] = Field(default_factory=dict)
    annotations: Optional[ToolAnnotation] = None
    ttlMs: Optional[int] = None
    cacheScope: Optional[str] = None


class MCPServerInfo(BaseModel):
    """MCP server information for discovery endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "memory-mcp",
                "version": "2.0.0",
                "description": "MCP server for memory system",
                "tools": [],
                "capabilities": ["memory", "search"],
                "protocol_version": "2026-07-28",
            }
        }
    )

    name: str
    version: str = "1.0.0"
    description: str
    tools: List[MCPTool] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    protocol_version: str = MCP_PROTOCOL_VERSION


class ServerCard(BaseModel):
    """MCP server card for /.well-known/mcp/server-card.json discovery."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    transport: str = "http+sse"
    endpoint_url: str = "/mcp"
    capabilities: List[str] = Field(default_factory=list)
    protocol_version: str = MCP_PROTOCOL_VERSION


# Memory-specific MCP models
class MemoryNode(BaseModel):
    """Memory node model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content must not be empty")
        return v.strip()


class MemoryEdge(BaseModel):
    """Edge between memory nodes."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_node_id: str
    to_node_id: str
    relationship: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("relationship")
    @classmethod
    def relationship_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Relationship must not be empty")
        return v.strip()


class MemoryQuery(BaseModel):
    """Query for memory search."""

    query: str
    limit: int = Field(default=10, ge=1, le=100)
    filters: Dict[str, Any] = Field(default_factory=dict)
    include_edges: bool = False


class MemorySearchResult(BaseModel):
    """Result from memory search."""

    node: MemoryNode
    score: float = Field(ge=0.0, le=1.0)
    edges: List[MemoryEdge] = Field(default_factory=list)


# Session management models
class Session(BaseModel):
    """Session for memory tracking."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


# Search-specific MCP models
class SearchQuery(BaseModel):
    """Search query."""

    query: str
    max_results: int = Field(default=10, ge=1, le=50)
    filters: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Search result."""

    id: str
    title: str
    content: str
    score: float = Field(ge=0.0, le=1.0)
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentInfo(BaseModel):
    """Document information."""

    id: str
    title: str
    content_type: str
    size: int
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Export all models
__all__ = [
    # Constants
    "MCP_PROTOCOL_VERSION",
    # Models
    "ServerMeta",
    "ServerCard",
    "ToolAnnotation",
    # Enums
    "MCPMessageType",
    "MCPToolType",
    # Base models
    "MCPRequest",
    "MCPResponse",
    "MCPError",
    "MCPTool",
    "MCPServerInfo",
    # Memory models
    "MemoryNode",
    "MemoryEdge",
    "MemoryQuery",
    "MemorySearchResult",
    "Session",
    # Search models
    "SearchQuery",
    "SearchResult",
    "DocumentInfo",
]
