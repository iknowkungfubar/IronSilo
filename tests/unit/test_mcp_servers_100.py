"""
Comprehensive tests for mcp/genesys_server.py to achieve 100% coverage.
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.framework import MCPServerBase, MCPToolError
from mcp.models import MCPMessageType, MCPToolType


class TestGenesysMCPServer:
    """Test GenesysMCPServer class."""
    
    def test_server_initialization(self):
        """Test server initializes correctly."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        assert server.name == "genesys-mcp"
        assert server.version == "1.0.0"
        assert "memory" in server.capabilities
    
    def test_server_has_tools(self):
        """Test server registers tools on initialization."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        expected_tools = [
            "create_memory_node",
            "create_causal_edge",
            "query_memories",
            "get_causal_chain",
            "create_session",
            "get_memory_node",
            "update_memory_node",
            "delete_memory_node",
        ]
        
        for tool_name in expected_tools:
            assert tool_name in server._tools
    
    @pytest.mark.asyncio
    async def test_create_memory_node(self):
        """Test create_memory_node tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        result = await server._handle_create_memory_node(
            content="Test memory content",
            memory_type="semantic",
            importance=0.5,
            tags=["test"],
        )
        
        assert result is not None
        assert "id" in result
        assert result["content"] == "Test memory content"
    
    @pytest.mark.asyncio
    async def test_query_memories(self):
        """Test query_memories tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # First create a memory
        await server._handle_create_memory_node(
            content="Test query memory",
            memory_type="semantic",
        )
        
        # Query for it
        result = await server._handle_query_memories(
            query="test",
            limit=10,
        )
        
        assert result is not None
        assert "memories" in result
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test create_session tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        result = await server._handle_create_session(
            session_type="analysis",
        )
        
        assert result is not None
        assert "session_id" in result
    
    @pytest.mark.asyncio
    async def test_get_memory_node(self):
        """Test get_memory_node tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Create a memory
        create_result = await server._handle_create_memory_node(
            content="Test memory for retrieval",
            memory_type="semantic",
        )
        
        memory_id = create_result["id"]
        
        # Get the memory
        result = await server._handle_get_memory_node(
            memory_id=memory_id,
        )
        
        assert result is not None
        assert result["id"] == memory_id
    
    @pytest.mark.asyncio
    async def test_update_memory_node(self):
        """Test update_memory_node tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Create a memory
        create_result = await server._handle_create_memory_node(
            content="Original content",
            memory_type="semantic",
        )
        
        memory_id = create_result["id"]
        
        # Update it
        result = await server._handle_update_memory_node(
            memory_id=memory_id,
            content="Updated content",
        )
        
        assert result is not None
        assert result["content"] == "Updated content"
    
    @pytest.mark.asyncio
    async def test_delete_memory_node(self):
        """Test delete_memory_node tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Create a memory
        create_result = await server._handle_create_memory_node(
            content="To be deleted",
            memory_type="semantic",
        )
        
        memory_id = create_result["id"]
        
        # Delete it
        result = await server._handle_delete_memory_node(
            memory_id=memory_id,
        )
        
        assert result is not None
        assert result.get("deleted") is True or result.get("success") is True
    
    @pytest.mark.asyncio
    async def test_create_causal_edge(self):
        """Test create_causal_edge tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Create two memories
        mem1 = await server._handle_create_memory_node(
            content="Cause memory",
            memory_type="semantic",
        )
        mem2 = await server._handle_create_memory_node(
            content="Effect memory",
            memory_type="semantic",
        )
        
        # Create edge
        result = await server._handle_create_causal_edge(
            source_id=mem1["id"],
            target_id=mem2["id"],
            relationship="causes",
            strength=0.8,
        )
        
        assert result is not None
        assert "edge_id" in result or "id" in result
    
    @pytest.mark.asyncio
    async def test_get_causal_chain(self):
        """Test get_causal_chain tool."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Create a memory
        mem = await server._handle_create_memory_node(
            content="Chain memory",
            memory_type="semantic",
        )
        
        # Get causal chain
        result = await server._handle_get_causal_chain(
            memory_id=mem["id"],
        )
        
        assert result is not None
        assert "chain" in result or "edges" in result


class TestGenesysMCPServerErrors:
    """Test error handling in GenesysMCPServer."""
    
    @pytest.mark.asyncio
    async def test_invalid_memory_id_returns_error(self):
        """Test operations with invalid memory ID."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        # Try to get non-existent memory
        result = await server._handle_get_memory_node(
            memory_id="nonexistent-id",
        )
        
        # Should return error or None
        assert result is None or "error" in result
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self):
        """Test deleting non-existent memory."""
        from mcp.genesys_server import GenesysMCPServer
        
        server = GenesysMCPServer()
        
        result = await server._handle_delete_memory_node(
            memory_id="nonexistent-id",
        )
        
        # Should handle gracefully
        assert result is not None


class TestKhojMCPServer:
    """Test KhojMCPServer class."""
    
    def test_server_initialization(self):
        """Test server initializes correctly."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        assert server.name == "khoj-mcp"
        assert server.version == "1.0.0"
        assert "search" in server.capabilities or "file" in server.capabilities
    
    def test_server_has_tools(self):
        """Test server registers tools on initialization."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        expected_tools = [
            "search_documents",
            "upload_document",
            "list_documents",
            "delete_document",
            "reindex_documents",
            "get_index_status",
        ]
        
        for tool_name in expected_tools:
            assert tool_name in server._tools
    
    @pytest.mark.asyncio
    async def test_search_documents(self):
        """Test search_documents tool."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        result = await server._handle_search_documents(
            query="test query",
            limit=10,
        )
        
        assert result is not None
        assert "results" in result or "documents" in result
    
    @pytest.mark.asyncio
    async def test_list_documents(self):
        """Test list_documents tool."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        result = await server._handle_list_documents()
        
        assert result is not None
        assert "documents" in result or "files" in result
    
    @pytest.mark.asyncio
    async def test_get_index_status(self):
        """Test get_index_status tool."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        result = await server._handle_get_index_status()
        
        assert result is not None
        assert "status" in result or "indexed" in result
    
    @pytest.mark.asyncio
    async def test_reindex_documents(self):
        """Test reindex_documents tool."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        result = await server._handle_reindex_documents()
        
        assert result is not None
        assert "success" in result or "reindexed" in result
    
    @pytest.mark.asyncio
    async def test_upload_document(self):
        """Test upload_document tool."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test document content")
            temp_path = f.name
        
        try:
            result = await server._handle_upload_document(
                file_path=temp_path,
                document_type="text",
            )
            
            assert result is not None
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_delete_document(self):
        """Test delete_document tool."""
        from mcp.khoj_server import KhojMCPServer
        
        server = KhojMCPServer()
        
        result = await server._handle_delete_document(
            document_id="test-doc-id",
        )
        
        # Should handle gracefully
        assert result is not None
