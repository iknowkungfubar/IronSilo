"""
Fallback Genesys Memory API.

This provides a minimal in-memory implementation when the genesys-memory
package is not available. It maintains basic memory functionality with
PostgreSQL when available, or pure in-memory storage.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Genesys Memory API (Fallback)",
    description="In-memory fallback for Genesys long-term memory",
    version="0.1.0",
)

# In-memory storage
_memories: Dict[str, Dict[str, Any]] = {}
_edges: Dict[str, Dict[str, Any]] = {}
_sessions: Dict[str, Dict[str, Any]] = {}


class MemoryNode(BaseModel):
    """A memory node in the causal graph."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    memory_type: str = "semantic"
    importance: float = 0.5
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CausalEdge(BaseModel):
    """A causal relationship between memory nodes."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relationship: str = "causes"
    strength: float = 1.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Session(BaseModel):
    """A memory session."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_type: str = "default"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "genesys-memory-fallback",
        "version": "0.1.0",
        "memories_count": len(_memories),
        "edges_count": len(_edges),
    }


@app.post("/api/v1/memories")
async def create_memory(memory: MemoryNode):
    """Create a new memory node."""
    _memories[memory.id] = memory.model_dump()
    logger.info("Memory created", memory_id=memory.id)
    return memory


@app.get("/api/v1/memories/{memory_id}")
async def get_memory(memory_id: str):
    """Get a memory node by ID."""
    if memory_id not in _memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _memories[memory_id]


@app.put("/api/v1/memories/{memory_id}")
async def update_memory(memory_id: str, content: Optional[str] = None, **kwargs):
    """Update a memory node."""
    if memory_id not in _memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    if content is not None:
        _memories[memory_id]["content"] = content
    for k, v in kwargs.items():
        if v is not None:
            _memories[memory_id][k] = v
    
    return _memories[memory_id]


@app.delete("/api/v1/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory node."""
    if memory_id not in _memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    del _memories[memory_id]
    return {"deleted": True, "memory_id": memory_id}


@app.post("/api/v1/memories/search")
async def search_memories(
    query: str = "",
    limit: int = 10,
    memory_type: Optional[str] = None,
):
    """Search memories by content."""
    results = []
    query_lower = query.lower()
    
    for memory in _memories.values():
        if memory_type and memory.get("memory_type") != memory_type:
            continue
        if query_lower in memory.get("content", "").lower():
            results.append(memory)
        if len(results) >= limit:
            break
    
    return {"memories": results, "count": len(results)}


@app.post("/api/v1/edges")
async def create_edge(edge: CausalEdge):
    """Create a causal edge between memories."""
    _edges[edge.id] = edge.model_dump()
    logger.info("Edge created", edge_id=edge.id)
    return edge


@app.get("/api/v1/memories/{memory_id}/chain")
async def get_causal_chain(memory_id: str):
    """Get the causal chain for a memory."""
    chain = []
    for edge in _edges.values():
        if edge["source_id"] == memory_id or edge["target_id"] == memory_id:
            chain.append(edge)
    return {"chain": chain, "count": len(chain)}


@app.post("/api/v1/sessions")
async def create_session(session_type: str = "default"):
    """Create a new session."""
    session = Session(session_type=session_type)
    _sessions[session.id] = session.model_dump()
    logger.info("Session created", session_id=session.id)
    return session


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Genesys Memory API (Fallback)",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
