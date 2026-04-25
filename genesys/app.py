"""
Genesys Memory API with PostgreSQL persistence.

This provides memory functionality with PostgreSQL when available,
falling back to in-memory storage when the database is unavailable.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL and os.getenv("GENESYS_BACKEND") == "postgres")

# Try to import asyncpg for PostgreSQL
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    logger.warning("asyncpg not installed, using in-memory storage")

# In-memory storage (fallback)
_memories: Dict[str, Dict[str, Any]] = {}
_edges: Dict[str, Dict[str, Any]] = {}
_sessions: Dict[str, Dict[str, Any]] = {}

# PostgreSQL connection pool
_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize database if available."""
    global _pool
    
    if USE_POSTGRES and HAS_ASYNCPG:
        try:
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=30,
            )
            
            # Create tables if they don't exist
            async with _pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        memory_type TEXT DEFAULT 'semantic',
                        importance REAL DEFAULT 0.5,
                        tags JSONB DEFAULT '[]',
                        created_at TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}'
                    );
                    
                    CREATE TABLE IF NOT EXISTS edges (
                        id TEXT PRIMARY KEY,
                        source_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        relationship TEXT DEFAULT 'causes',
                        strength REAL DEFAULT 1.0,
                        created_at TEXT NOT NULL
                    );
                    
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        session_type TEXT DEFAULT 'default',
                        created_at TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}'
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                    CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
                    CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
                """)
            
            logger.info("PostgreSQL connected", database_url=DATABASE_URL.split("@")[-1])
            
        except Exception as e:
            logger.error("PostgreSQL connection failed, using in-memory", error=str(e))
            _pool = None
    
    logger.info("Genesys Memory API started", backend="postgres" if _pool else "memory")
    yield
    
    # Cleanup
    if _pool:
        await _pool.close()
        logger.info("PostgreSQL connection closed")


app = FastAPI(
    title="Genesys Memory API",
    description="Long-term memory with PostgreSQL persistence",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    db_status = "connected" if _pool else "disconnected"
    
    # Get counts
    if _pool:
        async with _pool.acquire() as conn:
            mem_count = await conn.fetchval("SELECT COUNT(*) FROM memories")
            edge_count = await conn.fetchval("SELECT COUNT(*) FROM edges")
    else:
        mem_count = len(_memories)
        edge_count = len(_edges)
    
    return {
        "status": "healthy",
        "service": "genesys-memory",
        "version": "1.0.0",
        "backend": "postgres" if _pool else "memory",
        "database_status": db_status,
        "memories_count": mem_count,
        "edges_count": edge_count,
    }


@app.post("/api/v1/memories")
async def create_memory(memory: MemoryNode):
    """Create a new memory node."""
    if _pool:
        async with _pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO memories (id, content, memory_type, importance, tags, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, memory.id, memory.content, memory.memory_type, memory.importance,
                 json.dumps(memory.tags), memory.created_at, json.dumps(memory.metadata))
    else:
        _memories[memory.id] = memory.model_dump()
    
    logger.info("Memory created", memory_id=memory.id)
    return memory


@app.get("/api/v1/memories/{memory_id}")
async def get_memory(memory_id: str):
    """Get a memory node by ID."""
    if _pool:
        async with _pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", memory_id)
            if not row:
                raise HTTPException(status_code=404, detail="Memory not found")
            
            # Convert row to dict, parse JSON fields
            result = dict(row)
            result['tags'] = json.loads(result['tags']) if result.get('tags') else []
            result['metadata'] = json.loads(result['metadata']) if result.get('metadata') else {}
            return result
    else:
        if memory_id not in _memories:
            raise HTTPException(status_code=404, detail="Memory not found")
        return _memories[memory_id]


@app.put("/api/v1/memories/{memory_id}")
async def update_memory(memory_id: str, content: Optional[str] = None, **kwargs):
    """Update a memory node."""
    if _pool:
        async with _pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", memory_id)
            if not row:
                raise HTTPException(status_code=404, detail="Memory not found")
            
            updates = []
            params = [memory_id]
            param_idx = 2
            
            if content is not None:
                updates.append(f"content = ${param_idx}")
                params.append(content)
                param_idx += 1
            
            for k, v in kwargs.items():
                if v is not None and k in ['memory_type', 'importance']:
                    updates.append(f"{k} = ${param_idx}")
                    params.append(v)
                    param_idx += 1
            
            if updates:
                query = f"UPDATE memories SET {', '.join(updates)} WHERE id = $1"
                await conn.execute(query, *params)
            
            # Return updated row
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", memory_id)
            result = dict(row)
            result['tags'] = json.loads(result['tags']) if result.get('tags') else []
            result['metadata'] = json.loads(result['metadata']) if result.get('metadata') else {}
            return result
    else:
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
    if _pool:
        async with _pool.acquire() as conn:
            result = await conn.execute("DELETE FROM memories WHERE id = $1", memory_id)
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Memory not found")
    else:
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
    if _pool:
        async with _pool.acquire() as conn:
            if memory_type:
                rows = await conn.fetch("""
                    SELECT * FROM memories 
                    WHERE memory_type = $1 AND content ILIKE $2
                    ORDER BY importance DESC
                    LIMIT $3
                """, memory_type, f"%{query}%", limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM memories 
                    WHERE content ILIKE $1
                    ORDER BY importance DESC
                    LIMIT $2
                """, f"%{query}%", limit)
            
            results = []
            for row in rows:
                result = dict(row)
                result['tags'] = json.loads(result['tags']) if result.get('tags') else []
                result['metadata'] = json.loads(result['metadata']) if result.get('metadata') else {}
                results.append(result)
            
            return {"memories": results, "count": len(results)}
    else:
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
    if _pool:
        async with _pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO edges (id, source_id, target_id, relationship, strength, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, edge.id, edge.source_id, edge.target_id, edge.relationship, edge.strength, edge.created_at)
    else:
        _edges[edge.id] = edge.model_dump()
    
    logger.info("Edge created", edge_id=edge.id)
    return edge


@app.get("/api/v1/memories/{memory_id}/chain")
async def get_causal_chain(memory_id: str):
    """Get the causal chain for a memory."""
    if _pool:
        async with _pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM edges 
                WHERE source_id = $1 OR target_id = $1
            """, memory_id)
            chain = [dict(row) for row in rows]
            return {"chain": chain, "count": len(chain)}
    else:
        chain = []
        for edge in _edges.values():
            if edge["source_id"] == memory_id or edge["target_id"] == memory_id:
                chain.append(edge)
        return {"chain": chain, "count": len(chain)}


@app.post("/api/v1/sessions")
async def create_session(session_type: str = "default"):
    """Create a new session."""
    session = Session(session_type=session_type)
    
    if _pool:
        async with _pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (id, session_type, created_at, metadata)
                VALUES ($1, $2, $3, $4)
            """, session.id, session.session_type, session.created_at, json.dumps(session.metadata))
    else:
        _sessions[session.id] = session.model_dump()
    
    logger.info("Session created", session_id=session.id)
    return session


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Genesys Memory API",
        "version": "1.0.0",
        "backend": "postgres" if _pool else "memory",
        "docs": "/docs",
        "health": "/health",
    }
