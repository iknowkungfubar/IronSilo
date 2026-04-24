"""
MCP (Model Context Protocol) models for IronSilo.

This module defines the data models for MCP communication between
IronClaw and various services (Genesys, Khoj, etc.).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class MCPError(BaseModel):
    """MCP error model."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": -32601,
                "message": "Method not found",
                "data": {"method": "unknown_method"}
            }
        }
    )
    
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPRequest(BaseModel):
    """MCP request model."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "request",
                "tool": "genesys",
                "method": "create_memory_node",
                "params": {
                    "content": "User prefers Python for backend development",
                    "metadata": {"category": "preference", "confidence": 0.9}
                }
            }
        }
    )
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MCPMessageType = MCPMessageType.REQUEST
    tool: str
    method: str = "call"
    params: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MCPResponse(BaseModel):
    """MCP response model."""
    
    id: str
    type: MCPMessageType = MCPMessageType.RESPONSE
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_success(self) -> bool:
        return self.error is None


class MCPTool(BaseModel):
    """MCP tool definition."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "create_memory_node",
                "description": "Create a new memory node in the causal graph",
                "tool_type": "memory",
                "parameters": {
                    "content": {"type": "string", "description": "Memory content"},
                    "metadata": {"type": "object", "description": "Additional metadata"}
                },
                "returns": {
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string"}
                    }
                }
            }
        }
    )
    
    name: str
    description: str
    tool_type: MCPToolType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)


class MCPServerInfo(BaseModel):
    """MCP server information."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "genesys-mcp",
                "version": "1.0.0",
                "description": "MCP server for Genesys memory system",
                "tools": [],
                "capabilities": ["memory", "causal-graph", "session"]
            }
        }
    )
    
    name: str
    version: str = "1.0.0"
    description: str
    tools: List[MCPTool] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)


# Memory-specific MCP models
class MemoryNode(BaseModel):
    """Memory node for Genesys causal graph."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Content must not be empty')
        return v.strip()


class MemoryEdge(BaseModel):
    """Causal edge between memory nodes."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_node_id: str
    to_node_id: str
    relationship: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('relationship')
    @classmethod
    def relationship_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Relationship must not be empty')
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
    """Search query for Khoj RAG."""
    
    query: str
    max_results: int = Field(default=10, ge=1, le=50)
    filters: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Search result from Khoj."""
    
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
