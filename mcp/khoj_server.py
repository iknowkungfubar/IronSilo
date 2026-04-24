"""
Khoj MCP server for IronSilo.

This module provides MCP tools for integrating IronClaw with the Khoj
RAG engine, enabling document search and management operations.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union

import httpx
import structlog

from .framework import MCPServerBase, MCPToolError, create_mcp_app
from .models import (
    DocumentInfo,
    MCPToolType,
    SearchQuery,
    SearchResult,
)

logger = structlog.get_logger(__name__)


class KhojMCPServer(MCPServerBase):
    """MCP server for Khoj RAG engine integration."""
    
    def __init__(
        self,
        khoj_api_url: str = "http://khoj:42110",
        timeout: float = 60.0,
    ):
        super().__init__(
            name="khoj-mcp",
            version="1.0.0",
            description="MCP server for Khoj RAG engine",
            capabilities=["search", "documents", "rag"],
        )
        
        self.khoj_api_url = khoj_api_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        # Register tools
        self._register_tools()
    
    async def initialize(self) -> None:
        """Initialize HTTP client and verify Khoj connection."""
        self._client = httpx.AsyncClient(
            base_url=self.khoj_api_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        
        # Verify connection
        try:
            response = await self._client.get("/api/health")
            response.raise_for_status()
            self.logger.info("Connected to Khoj API")
        except Exception as e:
            self.logger.warning(
                "Could not connect to Khoj API, will retry on first request",
                error=str(e),
            )
    
    async def shutdown(self) -> None:
        """Shutdown HTTP client."""
        if self._client:
            await self._client.aclose()
    
    def _register_tools(self) -> None:
        """Register all MCP tools."""
        
        @self.register_tool(
            name="search_documents",
            description="Search documents using semantic similarity via Khoj RAG",
            tool_type=MCPToolType.SEARCH,
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Maximum results (1-50)", "default": 10},
                "filters": {"type": "object", "description": "Search filters", "default": {}},
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
                    }
                }
            },
        )
        async def search_documents(
            query: str,
            max_results: int = 10,
            filters: Optional[Dict[str, Any]] = None,
        ) -> List[Dict[str, Any]]:
            """Search documents using Khoj RAG."""
            if not query.strip():
                raise MCPToolError(-32602, "Query must not be empty")
            
            if not 1 <= max_results <= 50:
                raise MCPToolError(-32602, "max_results must be between 1 and 50")
            
            search_query = SearchQuery(
                query=query.strip(),
                max_results=max_results,
                filters=filters or {},
            )
            
            try:
                # Khoj uses a different API format
                response = await self._client.get(
                    "/api/search",
                    params={
                        "q": search_query.query,
                        "n": search_query.max_results,
                        "type": "all",
                    },
                )
                response.raise_for_status()
                results = response.json()
                
                # Transform Khoj results to our format
                transformed_results = []
                for result in results.get("search", []):
                    transformed_results.append({
                        "id": result.get("id", ""),
                        "title": result.get("title", "Untitled"),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0),
                        "source": result.get("source", ""),
                        "metadata": {
                            "type": result.get("type", "unknown"),
                            "file": result.get("file", ""),
                            "updated": result.get("updated", ""),
                        }
                    })
                
                self.logger.info(
                    "Document search executed",
                    query_length=len(query),
                    results_count=len(transformed_results),
                )
                
                return transformed_results
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to search documents: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="upload_document",
            description="Upload a document to Khoj for indexing",
            tool_type=MCPToolType.FILE,
            parameters={
                "file_path": {"type": "string", "description": "Path to file to upload"},
                "content": {"type": "string", "description": "Document content (if no file)"},
                "content_type": {"type": "string", "description": "MIME type", "default": "text/plain"},
                "filename": {"type": "string", "description": "Filename", "default": None},
            },
            returns={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "indexed": {"type": "boolean"},
                    "message": {"type": "string"},
                }
            },
        )
        async def upload_document(
            file_path: Optional[str] = None,
            content: Optional[str] = None,
            content_type: str = "text/plain",
            filename: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Upload a document to Khoj."""
            if not file_path and not content:
                raise MCPToolError(-32602, "Either file_path or content must be provided")
            
            if file_path and content:
                raise MCPToolError(-32602, "Provide either file_path or content, not both")
            
            try:
                if file_path:
                    # Upload file
                    import os
                    if not os.path.exists(file_path):
                        raise MCPToolError(-32602, f"File not found: {file_path}")
                    
                    with open(file_path, "rb") as f:
                        files = {"file": (os.path.basename(file_path), f, content_type)}
                        response = await self._client.post(
                            "/api/upload",
                            files=files,
                        )
                else:
                    # Upload content
                    if not filename:
                        filename = "document.txt"
                    
                    files = {"file": (filename, content.encode(), content_type)}
                    response = await self._client.post(
                        "/api/upload",
                        files=files,
                    )
                
                response.raise_for_status()
                result = response.json()
                
                doc_id = result.get("id", filename or "unknown")
                
                self.logger.info(
                    "Document uploaded to Khoj",
                    document_id=doc_id,
                    content_type=content_type,
                    has_file=bool(file_path),
                )
                
                return {
                    "document_id": doc_id,
                    "indexed": True,
                    "message": f"Document '{filename}' uploaded and indexed successfully",
                }
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to upload document: {e.response.status_code}",
                    {"response": e.response.text}
                )
            except Exception as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to upload document: {str(e)}",
                )
        
        @self.register_tool(
            name="list_documents",
            description="List all indexed documents in Khoj",
            tool_type=MCPToolType.FILE,
            parameters={},
            returns={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "content_type": {"type": "string"},
                        "size": {"type": "integer"},
                    }
                }
            },
        )
        async def list_documents() -> List[Dict[str, Any]]:
            """List all indexed documents."""
            try:
                response = await self._client.get("/api/documents")
                response.raise_for_status()
                documents = response.json()
                
                # Transform to our format
                result = []
                for doc in documents:
                    result.append({
                        "id": doc.get("id", ""),
                        "title": doc.get("name", doc.get("title", "Untitled")),
                        "content_type": doc.get("type", "unknown"),
                        "size": doc.get("size", 0),
                        "indexed": doc.get("indexed", True),
                        "updated": doc.get("updated", ""),
                    })
                
                self.logger.info(
                    "Listed Khoj documents",
                    documents_count=len(result),
                )
                
                return result
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to list documents: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="delete_document",
            description="Delete a document from Khoj index",
            tool_type=MCPToolType.FILE,
            parameters={
                "document_id": {"type": "string", "description": "Document ID to delete"},
            },
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                }
            },
        )
        async def delete_document(document_id: str) -> Dict[str, Any]:
            """Delete a document from Khoj."""
            if not document_id:
                raise MCPToolError(-32602, "Document ID is required")
            
            try:
                response = await self._client.delete(f"/api/documents/{document_id}")
                response.raise_for_status()
                
                self.logger.info(
                    "Deleted document from Khoj",
                    document_id=document_id,
                )
                
                return {
                    "success": True,
                    "message": f"Document '{document_id}' deleted successfully",
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise MCPToolError(-32602, f"Document not found: {document_id}")
                raise MCPToolError(
                    -32000,
                    f"Failed to delete document: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="reindex_documents",
            description="Trigger reindexing of all documents in Khoj",
            tool_type=MCPToolType.EXECUTION,
            parameters={
                "force": {"type": "boolean", "description": "Force reindexing even if already indexed", "default": False},
            },
            returns={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "documents_processed": {"type": "integer"},
                }
            },
        )
        async def reindex_documents(force: bool = False) -> Dict[str, Any]:
            """Reindex all documents."""
            try:
                response = await self._client.post(
                    "/api/index/reindex",
                    params={"force": force},
                )
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(
                    "Triggered document reindexing",
                    force=force,
                    documents_processed=result.get("documents_processed", 0),
                )
                
                return {
                    "success": True,
                    "message": "Reindexing started successfully",
                    "documents_processed": result.get("documents_processed", 0),
                }
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to reindex documents: {e.response.status_code}",
                    {"response": e.response.text}
                )
        
        @self.register_tool(
            name="get_index_status",
            description="Get the indexing status of Khoj",
            tool_type=MCPToolType.EXECUTION,
            parameters={},
            returns={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "indexed": {"type": "integer"},
                    "pending": {"type": "integer"},
                    "errors": {"type": "integer"},
                }
            },
        )
        async def get_index_status() -> Dict[str, Any]:
            """Get Khoj indexing status."""
            try:
                response = await self._client.get("/api/index/status")
                response.raise_for_status()
                status = response.json()
                
                return {
                    "status": status.get("status", "unknown"),
                    "indexed": status.get("indexed", 0),
                    "pending": status.get("pending", 0),
                    "errors": status.get("errors", 0),
                }
                
            except httpx.HTTPStatusError as e:
                raise MCPToolError(
                    -32000,
                    f"Failed to get index status: {e.response.status_code}",
                    {"response": e.response.text}
                )


# Create FastAPI app
def create_khoj_mcp_app(
    khoj_api_url: str = "http://khoj:42110",
) -> Any:
    """Create FastAPI app for Khoj MCP server."""
    server = KhojMCPServer(khoj_api_url=khoj_api_url)
    return create_mcp_app(server)


# For uvicorn
app = create_khoj_mcp_app()
