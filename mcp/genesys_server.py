"""
Genesys MCP server for IronSilo.

This module provides MCP tools for integrating IronClaw with the Genesys
memory system, enabling causal graph memory operations.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union

import httpx
import structlog

from .framework import MCPServerBase, MCPToolError, create_mcp_app
from .models import (
    MCPToolType,
    MemoryEdge,
    MemoryNode,
    MemoryQuery,
    MemorySearchResult,
    Session,
)

logger = structlog.get_logger(__name__)


class GenesysMCPServer(MCPServerBase):
    """MCP server for Genesys memory system integration."""
    
    def __init__(
        self,
        genesys_api_url: str = "http://genesys-memory:8000",
        timeout: float = 30.0,
    ):
        super().__init__(
            name="genesys-mcp",
            version="1.0.0",
            description="MCP server for Genesys causal graph memory system",
            capabilities=["memory", "causal-graph", "session"],
        )
        
        self.genesys_api_url = genesys_api_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        # Register tools
        self._register_tools()
    
    async def initialize(self) -> None:
        """Initialize HTTP client and verify Genesys connection."""
        self._client = httpx.AsyncClient(
            base_url=self.genesys_api_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        
        # Verify connection
        try:
            response = await self._client.get("/health")
            response.raise_for_status()
            self.logger.info("Connected to Genesys API")
        except Exception as e:
            self.logger.error("Failed to connect to Genesys API", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown HTTP client."""
        if self._client:
            await self._client.aclose()
    
    def _register_tools(self) -> None:
        """Register all MCP tools."""
        
        @self.register_tool(
            name="create_memory_node",
            description="Create a new memory node in the causal graph",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "content": {"type": "string", "description": "Memory content"},
                "metadata": {"type": "object", "description": "Additional metadata", "default": {}},
            },
            returns={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                }
            },
        )
        async def create_memory_node(
            content: str,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """Create a new memory node."""
            if not content.strip():
                raise MCPToolError(-32602, "Content must not be empty")
            
            node = MemoryNode(
                content=content.strip(),
                metadata=metadata or {},
            )
            
            try:
                response = await self._client.post(
                    "/api/v1/memories",
                    json=node.model_dump(),
                )
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(
                    "Created memory node",
                    node_id=result.get("id"),
                    content_length=len(content),
                )
                
                return {
                    "node_id": result.get("id"),
                    "created_at": result.get("created_at"),
                }
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to create memory node: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="create_causal_edge",
            description="Create a causal edge between two memory nodes",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "from_node_id": {"type": "string", "description": "Source node ID"},
                "to_node_id": {"type": "string", "description": "Target node ID"},
                "relationship": {"type": "string", "description": "Relationship type"},
                "weight": {"type": "number", "description": "Edge weight (0.0-1.0)", "default": 1.0},
            },
            returns={
                "type": "object",
                "properties": {
                    "edge_id": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                }
            },
        )
        async def create_causal_edge(
            from_node_id: str,
            to_node_id: str,
            relationship: str,
            weight: float = 1.0,
        ) -> Dict[str, Any]:
            """Create a causal edge between memory nodes."""
            if not from_node_id or not to_node_id:
                raise MCPToolError(-32602, "Both node IDs are required")
            
            if not relationship.strip():
                raise MCPToolError(-32602, "Relationship must not be empty")
            
            if not 0.0 <= weight <= 1.0:
                raise MCPToolError(-32602, "Weight must be between 0.0 and 1.0")
            
            edge = MemoryEdge(
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                relationship=relationship.strip(),
                weight=weight,
            )
            
            try:
                response = await self._client.post(
                    "/api/v1/edges",
                    json=edge.model_dump(),
                )
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(
                    "Created causal edge",
                    edge_id=result.get("id"),
                    from_node=from_node_id,
                    to_node=to_node_id,
                    relationship=relationship,
                )
                
                return {
                    "edge_id": result.get("id"),
                    "created_at": result.get("created_at"),
                }
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to create causal edge: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="query_memories",
            description="Search memories using semantic similarity",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Maximum results (1-100)", "default": 10},
                "filters": {"type": "object", "description": "Additional filters", "default": {}},
                "include_edges": {"type": "boolean", "description": "Include causal edges", "default": False},
            },
            returns={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "node": {"type": "object"},
                        "score": {"type": "number"},
                        "edges": {"type": "array"},
                    }
                }
            },
        )
        async def query_memories(
            query: str,
            limit: int = 10,
            filters: Optional[Dict[str, Any]] = None,
            include_edges: bool = False,
        ) -> List[Dict[str, Any]]:
            """Search memories using semantic similarity."""
            if not query.strip():
                raise MCPToolError(-32602, "Query must not be empty")
            
            if not 1 <= limit <= 100:
                raise MCPToolError(-32602, "Limit must be between 1 and 100")
            
            memory_query = MemoryQuery(
                query=query.strip(),
                limit=limit,
                filters=filters or {},
                include_edges=include_edges,
            )
            
            try:
                response = await self._client.post(
                    "/api/v1/memories/search",
                    json=memory_query.model_dump(),
                )
                response.raise_for_status()
                results = response.json()
                
                self.logger.info(
                    "Memory query executed",
                    query_length=len(query),
                    results_count=len(results),
                    include_edges=include_edges,
                )
                
                return results
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to query memories: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="get_causal_chain",
            description="Get causal chain starting from a memory node",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "node_id": {"type": "string", "description": "Starting node ID"},
                "max_depth": {"type": "integer", "description": "Maximum chain depth", "default": 5},
                "direction": {"type": "string", "description": "Direction: forward, backward, both", "default": "both"},
            },
            returns={
                "type": "object",
                "properties": {
                    "nodes": {"type": "array"},
                    "edges": {"type": "array"},
                }
            },
        )
        async def get_causal_chain(
            node_id: str,
            max_depth: int = 5,
            direction: str = "both",
        ) -> Dict[str, Any]:
            """Get causal chain from a memory node."""
            if not node_id:
                raise MCPToolError(-32602, "Node ID is required")
            
            if direction not in ["forward", "backward", "both"]:
                raise MCPToolError(-32602, "Direction must be forward, backward, or both")
            
            try:
                response = await self._client.get(
                    f"/api/v1/memories/{node_id}/chain",
                    params={
                        "max_depth": max_depth,
                        "direction": direction,
                    },
                )
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(
                    "Retrieved causal chain",
                    node_id=node_id,
                    max_depth=max_depth,
                    direction=direction,
                    nodes_count=len(result.get("nodes", [])),
                    edges_count=len(result.get("edges", [])),
                )
                
                return result
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to get causal chain: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="create_session",
            description="Create a new memory session for tracking context",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "user_id": {"type": "string", "description": "User ID for session", "default": None},
                "metadata": {"type": "object", "description": "Session metadata", "default": {}},
            },
            returns={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                }
            },
        )
        async def create_session(
            user_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """Create a new memory session."""
            session = Session(
                user_id=user_id,
                metadata=metadata or {},
            )
            
            try:
                response = await self._client.post(
                    "/api/v1/sessions",
                    json=session.model_dump(),
                )
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(
                    "Created memory session",
                    session_id=result.get("id"),
                    user_id=user_id,
                )
                
                return {
                    "session_id": result.get("id"),
                    "created_at": result.get("created_at"),
                }
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to create session: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="get_memory_node",
            description="Get a specific memory node by ID",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "node_id": {"type": "string", "description": "Node ID to retrieve"},
                "include_edges": {"type": "boolean", "description": "Include edges", "default": False},
            },
            returns={
                "type": "object",
                "properties": {
                    "node": {"type": "object"},
                    "edges": {"type": "array"},
                }
            },
        )
        async def get_memory_node(
            node_id: str,
            include_edges: bool = False,
        ) -> Dict[str, Any]:
            """Get a memory node by ID."""
            if not node_id:
                raise MCPToolError(-32602, "Node ID is required")
            
            try:
                response = await self._client.get(
                    f"/api/v1/memories/{node_id}",
                    params={"include_edges": include_edges},
                )
                response.raise_for_status()
                result = response.json()
                
                return result
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise MCPToolError(-32602, f"Memory node not found: {node_id}")
                raise MCPToolError(
                    -32000,
                    f"Failed to get memory node: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="update_memory_node",
            description="Update an existing memory node",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "node_id": {"type": "string", "description": "Node ID to update"},
                "content": {"type": "string", "description": "Updated content"},
                "metadata": {"type": "object", "description": "Updated metadata", "default": None},
            },
            returns={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "updated_at": {"type": "string", "format": "date-time"},
                }
            },
        )
        async def update_memory_node(
            node_id: str,
            content: str,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """Update a memory node."""
            if not node_id:
                raise MCPToolError(-32602, "Node ID is required")
            
            if not content.strip():
                raise MCPToolError(-32602, "Content must not be empty")
            
            update_data = {"content": content.strip()}
            if metadata is not None:
                update_data["metadata"] = metadata
            
            try:
                response = await self._client.put(
                    f"/api/v1/memories/{node_id}",
                    json=update_data,
                )
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(
                    "Updated memory node",
                    node_id=node_id,
                    content_length=len(content),
                )
                
                return {
                    "node_id": result.get("id"),
                    "updated_at": result.get("updated_at"),
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise MCPToolError(-32602, f"Memory node not found: {node_id}")
                raise MCPToolError(
                    -32000,
                    f"Failed to update memory node: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="delete_memory_node",
            description="Delete a memory node and its edges",
            tool_type=MCPToolType.MEMORY,
            parameters={
                "node_id": {"type": "string", "description": "Node ID to delete"},
            },
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "deleted_edges": {"type": "integer"},
                }
            },
        )
        async def delete_memory_node(node_id: str) -> Dict[str, Any]:
            """Delete a memory node."""
            if not node_id:
                raise MCPToolError(-32602, "Node ID is required")
            
            try:
                response = await self._client.delete(f"/api/v1/memories/{node_id}")
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(
                    "Deleted memory node",
                    node_id=node_id,
                    deleted_edges=result.get("deleted_edges", 0),
                )
                
                return result
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise MCPToolError(-32602, f"Memory node not found: {node_id}")
                raise MCPToolError(
                    -32000,
                    f"Failed to delete memory node: {e.response.status_code}",
                    {"response": e.response.text}
                )


# Create FastAPI app
def create_genesys_mcp_app(
    genesys_api_url: str = "http://genesys-memory:8000",
) -> Any:
    """Create FastAPI app for Genesys MCP server."""
    server = GenesysMCPServer(genesys_api_url=genesys_api_url)
    return create_mcp_app(server)


# For uvicorn
app = create_genesys_mcp_app()
