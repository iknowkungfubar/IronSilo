"""
RAG MCP server for IronSilo — LightRAG backed.

Replaces Khoj with LightRAG (34k⭐, MIT) — a lightweight graph-enhanced
RAG engine that runs locally without GPU. This MCP server provides
the same interface as the old Khoj server but routes to LightRAG.

Integration path: Onyx can replace this when more connectors are needed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
import structlog

from .framework import MCPServerBase, MCPToolError, create_mcp_app
from .models import (
    MCPToolType,
)

logger = structlog.get_logger(__name__)


class RAGMCPServer(MCPServerBase):
    """MCP server for LightRAG backend integration."""

    def __init__(
        self,
        rag_api_url: str = "http://rag:8010",
        timeout: float = 60.0,
    ):
        super().__init__(
            name="rag-mcp",
            version="2.0.0",
            description="MCP server for LightRAG engine (replaces Khoj)",
            capabilities=["search", "documents", "rag"],
        )

        self.rag_api_url = rag_api_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        self._register_tools()

    async def initialize(self) -> None:
        """Initialize HTTP client and verify LightRAG connection."""
        self._client = httpx.AsyncClient(
            base_url=self.rag_api_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )

        try:
            response = await self._client.get("/health")
            response.raise_for_status()
            self.logger.info("Connected to LightRAG API")
        except Exception as e:
            self.logger.warning(
                "Could not connect to LightRAG API, will retry on first request",
                error=str(e),
            )

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()

    def _register_tools(self) -> None:
        @self.register_tool(
            name="search_documents",
            description="Search documents via LightRAG semantic search",
            tool_type=MCPToolType.SEARCH,
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results (1-50)",
                    "default": 10,
                },
                "mode": {
                    "type": "string",
                    "description": "Search mode: naive, local, global, hybrid",
                    "default": "hybrid",
                },
            },
            returns={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "score": {"type": "number"},
                        "source": {"type": "string"},
                    },
                },
            },
        )
        async def search_documents(
            query: str,
            max_results: int = 10,
            mode: str = "hybrid",
        ) -> List[Dict[str, Any]]:
            if not query.strip():
                raise MCPToolError(-32602, "Query must not be empty")
            if not 1 <= max_results <= 50:
                raise MCPToolError(-32602, "max_results must be between 1 and 50")

            try:
                response = await self._client.post(
                    "/api/v1/search",
                    json={"query": query.strip(), "max_results": max_results, "mode": mode},
                )
                response.raise_for_status()
                results = response.json()
                return results.get("results", [])

            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Search failed: {e.response.status_code}",
                    {"response": e.response.text},
                )

        @self.register_tool(
            name="upload_document",
            description="Upload a document to LightRAG for indexing",
            tool_type=MCPToolType.FILE,
            parameters={
                "content": {"type": "string", "description": "Document content"},
                "doc_id": {"type": "string", "description": "Optional document ID"},
            },
            returns={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "indexed": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            },
        )
        async def upload_document(
            content: Optional[str] = None,
            doc_id: Optional[str] = None,
        ) -> Dict[str, Any]:
            if not content:
                raise MCPToolError(-32602, "content must be provided")

            try:
                response = await self._client.post(
                    "/api/v1/documents",
                    json={"content": content, "doc_id": doc_id},
                )
                response.raise_for_status()
                result = response.json()
                return result

            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to index document: {e.response.status_code}",
                    {"response": e.response.text},
                )

        @self.register_tool(
            name="list_documents",
            description="List indexed documents",
            tool_type=MCPToolType.FILE,
            parameters={},
            returns={"type": "object"},
        )
        async def list_documents() -> Dict[str, Any]:
            try:
                response = await self._client.get("/api/v1/documents")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to list documents: {e.response.status_code}",
                )

        @self.register_tool(
            name="delete_document",
            description="Delete a document from the index",
            tool_type=MCPToolType.FILE,
            parameters={
                "document_id": {"type": "string", "description": "Document ID to delete"},
            },
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            },
        )
        async def delete_document(document_id: str) -> Dict[str, Any]:
            if not document_id:
                raise MCPToolError(-32602, "Document ID is required")
            try:
                response = await self._client.delete(f"/api/v1/documents/{document_id}")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise MCPToolError(-32602, f"Document not found: {document_id}")
                raise MCPToolError(-32000, f"Failed to delete document: {e.response.status_code}")

        @self.register_tool(
            name="get_index_status",
            description="Get the indexing status",
            tool_type=MCPToolType.EXECUTION,
            parameters={},
            returns={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "indexed": {"type": "integer"},
                },
            },
        )
        async def get_index_status() -> Dict[str, Any]:
            try:
                response = await self._client.get("/api/v1/index/status")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise MCPToolError(-32000, f"Failed to get index status: {e.response.status_code}")


# Factory function
def create_rag_mcp_app(
    rag_api_url: str = "http://rag:8010",
) -> Any:
    """Create FastAPI app for RAG MCP server."""
    server = RAGMCPServer(rag_api_url=rag_api_url)
    return create_mcp_app(server)


# For uvicorn
app = create_rag_mcp_app()


# Backward-compatible alias
KhojMCPServer = RAGMCPServer
create_khoj_mcp_app = create_rag_mcp_app
