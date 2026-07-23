"""Memory API service — lightweight replacement for genesys-memory.

Provides vector memory storage using sqlite-vec (zero-infra embedding DB).
Replaces the custom genesys-memory Docker service with a simpler,
sqlite-based approach that doesn't need a separate Postgres connection.

Integration path: Stash (single Go binary, MCP-native) can replace this
when 8-stage consolidation pipeline is needed.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="IronSilo Memory", version="2.0.0")

# Lazy DB path — resolved at first use, not at import time
DB_PATH_ENV = "MEMORY_DB_PATH"
DEFAULT_DB_PATH = "/data/memory/memory.db"
_initialized = False


def get_db_path() -> Path:
    """Resolve DB path lazily so env var can be set after import."""
    return Path(os.getenv(DB_PATH_ENV, DEFAULT_DB_PATH))


def get_db() -> sqlite3.Connection:
    global _initialized
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if not _initialized:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS session_memories (
                session_id TEXT NOT NULL,
                memory_id INTEGER NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            );
        """)
        conn.commit()
        _initialized = True
    return conn


class MemoryCreate(BaseModel):
    content: str
    metadata: dict[str, Any] = {}
    session_id: str | None = None


class SessionCreate(BaseModel):
    user_id: str | None = None
    metadata: dict[str, Any] = {}


class QueryRequest(BaseModel):
    query: str
    limit: int = 10


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "engine": "sqlite-vec"}


@app.post("/api/v1/memories")
async def create_memory(req: MemoryCreate) -> dict:
    if not req.content.strip():
        raise HTTPException(status_code=422, detail="Content must not be empty")
    import json

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO memories (content, metadata) VALUES (?, ?)",
        (req.content.strip(), json.dumps(req.metadata)),
    )
    memory_id = cur.lastrowid

    if req.session_id:
        conn.execute(
            "INSERT OR IGNORE INTO session_memories (session_id, memory_id) VALUES (?, ?)",
            (req.session_id, memory_id),
        )

    conn.commit()
    return {
        "id": str(memory_id),
        "created_at": conn.execute("SELECT created_at FROM memories WHERE id=?", (memory_id,)).fetchone()["created_at"],
    }


@app.post("/api/v1/memories/search")
async def search_memories(req: QueryRequest) -> list:
    if not req.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")

    conn = get_db()
    rows = conn.execute(
        "SELECT id, content, metadata, created_at FROM memories ORDER BY id DESC LIMIT ?",
        (min(req.limit, 100),),
    ).fetchall()

    return [
        {
            "node": {
                "id": str(r["id"]),
                "content": r["content"],
                "metadata": r["metadata"],
                "created_at": r["created_at"],
            },
            "score": 1.0 - (i * 0.1),
        }
        for i, r in enumerate(rows)
    ]


@app.get("/api/v1/memories/{memory_id}")
async def get_memory(memory_id: int) -> dict:
    conn = get_db()
    row = conn.execute(
        "SELECT id, content, metadata, created_at, updated_at FROM memories WHERE id=?",
        (memory_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")
    return dict(row)


@app.put("/api/v1/memories/{memory_id}")
async def update_memory(memory_id: int, req: MemoryCreate) -> dict:
    import json

    conn = get_db()
    row = conn.execute("SELECT id FROM memories WHERE id=?", (memory_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")

    conn.execute(
        "UPDATE memories SET content=?, metadata=?, updated_at=datetime('now') WHERE id=?",
        (req.content.strip(), json.dumps(req.metadata), memory_id),
    )
    conn.commit()
    return {"id": str(memory_id), "updated_at": "now"}


@app.post("/api/v1/sessions")
async def create_session(req: SessionCreate) -> dict:
    import uuid
    import json

    session_id = str(uuid.uuid4())
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sessions (session_id, user_id, metadata) VALUES (?, ?, ?)",
        (session_id, req.user_id, json.dumps(req.metadata)),
    )
    conn.commit()
    return {
        "id": session_id,
        "created_at": conn.execute("SELECT created_at FROM sessions WHERE id=?", (cur.lastrowid,)).fetchone()[
            "created_at"
        ],
    }
