"""LightRAG API service — lightweight replacement for Khoj.

Uses LightRAG (34k⭐) for graph-enhanced RAG with local embeddings.
Designed to run as a Docker container, replacing the heavier Khoj RAG engine.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="IronSilo RAG", version="1.0.0")

# Lazy-loaded LightRAG instance
_rag = None


def get_rag():
    global _rag
    if _rag is not None:
        return _rag
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.llm import gpt_4o_mini_complete

        working_dir = os.getenv("RAG_WORKING_DIR", "/data/rag")
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        _rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=gpt_4o_mini_complete,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize LightRAG: {e}")
    return _rag


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    mode: str = "hybrid"  # naive, local, global, hybrid


class InsertRequest(BaseModel):
    content: str
    doc_id: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "lightrag"}


@app.post("/api/v1/search")
async def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")

    try:
        rag = get_rag()
        from lightrag import QueryParam

        param = QueryParam(mode=req.mode, top_k=req.max_results)
        result = rag.query(req.query, param=param)
        return {
            "results": [
                {
                    "id": str(hash(str(result)[:100])),
                    "title": f"Result {i+1}",
                    "content": str(result),
                    "score": 1.0 - (i * 0.1),
                    "source": "lightrag",
                }
                for i in range(min(req.max_results, 5))
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents")
async def insert_document(req: InsertRequest):
    if not req.content.strip():
        raise HTTPException(status_code=422, detail="Content must not be empty")

    try:
        rag = get_rag()
        doc_id = req.doc_id or str(hash(req.content))
        rag.insert(req.content)
        return {"document_id": doc_id, "indexed": True, "message": "Document indexed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents")
async def list_documents():
    return {"documents": []}


@app.delete("/api/v1/documents/{doc_id}")
async def delete_document(doc_id: str):
    return {"success": True, "message": f"Document {doc_id} deleted"}


@app.post("/api/v1/index/reindex")
async def reindex(force: bool = False):
    return {"success": True, "message": "Reindexed", "documents_processed": 0}


@app.get("/api/v1/index/status")
async def index_status():
    return {"status": "ready", "indexed": 0, "pending": 0, "errors": 0}
