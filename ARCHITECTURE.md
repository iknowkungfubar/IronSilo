# IronSilo Architecture

## Overview

IronSilo is a local-first, cross-platform AI development sandbox that provides a secure, resource-capped environment for AI-assisted coding. It combines specialized tools into a cohesive workspace running entirely on your local machine.

## System Architecture (July 2026)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          HOST MACHINE                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │  OpenCode / Aider │  │  Hermes Agent   │  │  LM Studio / Ollama   │  │
│  │  (Coding Engine)  │  │  (Orchestrator) │  │  (Local LLM, :8000)  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────────┬────────────┘  │
│           │                     │                         │               │
│           │                     │                         │               │
│           ▼                     ▼                         ▼               │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    CADDY API GATEWAY (:8080)                          │ │
│  │  ┌──────────┐ ┌──────┐ ┌────────┐ ┌──────────┐ ┌──────┐ ┌────────┐  │ │
│  │  │ Headroom │ │ RAG │ │ Memory │ │ SearxNG │ │ Swarm│ │ MCP   │  │ │
│  │  │ Proxy    │ │RAG  │ │ Srv    │ │ (Search)│ │(Brws)│ │Srvrs  │  │ │
│  │  │ :8001    │ │:8010│ │ :8020  │ │ :8080   │ │:8095 │ │:8000+ │  │ │
│  │  └──────────┘ └──────┘ └────────┘ └──────────┘ └──────┘ └────────┘  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  Resource Limits: ~4GB RAM total | CPU per service capped                 │
└───────────────────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. API Gateway: Caddy (`Caddyfile`)

- **Port**: 8080
- **Memory**: ~20MB (vs Traefik's ~50MB)
- **Config**: Single `Caddyfile` with route + reverse_proxy directives
- **Routing**: Prefix-based with automatic stripping (`/rag/*`, `/memory/*`, `/search/*`, etc.)
- **Replaces**: Traefik (docker labels + 186-line traefik.yml + 28-line dynamic.yml)

### 2. Headroom Proxy (`proxy/`)

- **Port**: 8001
- **Purpose**: Context compression — intercepts prompts, compresses them, forwards to LLM
- **Technology**: FastAPI + Headroom (CPU/ONNX, 57.7k⭐)
- **Key features**: CacheAligner, cross-agent memory, output reduction
- **Compression ratio**: 47-92% with ±0.001 GSM8K accuracy delta
- **Replaces**: LLMLingua + torch (2GB dependency, GPU-required)

### 3. LightRAG RAG Engine (`rag/`)

- **Port**: 8010
- **Purpose**: Graph-enhanced RAG with CPU-only inference
- **Technology**: FastAPI + LightRAG (34k⭐, MIT, pip-installable)
- **Features**: Semantic search, hybrid retrieval, document indexing
- **Replaces**: Khoj (Docker container, ~1GB, questionable maintenance)

### 4. Memory Service (`memory/`)

- **Port**: 8020
- **Purpose**: Persistent agent memory with vector search
- **Technology**: FastAPI + sqlite-vec (zero-infra embedding DB)
- **Features**: Memory CRUD, session tracking, semantic search
- **Replaces**: Genesys (custom Docker build, 471-line app.py, causal graph)

### 5. MCP Servers (`mcp/`)

- **Protocol**: MCP 2026-07-28 RC (stateless, JSON-RPC 2.0)
- **Features**:
  - `_meta` injection on all responses (protocol version, server identity, trace context)
  - `server/discover` endpoint with capability discovery
  - W3C Trace Context via `traceparent` header
  - Tool annotations (readOnlyHint, idempotentHint, destructiveHint)
  - `ttlMs`/`cacheScope` on list responses
- **Memory MCP** (`mcp/genesys_server.py`): MemoryMCPServer — CRUD + search
- **RAG MCP** (`mcp/khoj_server.py`): RAGMCPServer — document search + indexing

### 6. SearxNG

- **Port**: 8080 (internal)
- **Purpose**: Private, privacy-respecting meta-search engine
- **Replaces**: Direct Google/Bing API access

### 7. Browser Swarm (`swarm/`)

- **Port**: 8095
- **Purpose**: Autonomous web browsing via headless Chrome
- **Technology**: FastAPI + CDP (Chrome DevTools Protocol)
- **Components**: HarnessWorker (CDP client), Manager (research orchestrator)

## Data Flow

```
User Request
    │
    ▼
Caddy Gateway (:8080)
    │
    ├── /api/v1/*    → Headroom Proxy (:8001) → Local LLM (:8000)
    ├── /rag/*       → LightRAG (:8010)
    ├── /memory/*    → Memory Service (:8020)
    ├── /mcp/*       → MCP Servers (:8000+)
    ├── /search/*    → SearxNG (:8080)
    ├── /swarm/*     → Swarm Service (:8095)
    └── /*           → Default response (health check)
```

### Agent Research Flow

```
Agent → MCP/tools/call → RAG MCP → LightRAG → Search results
     └→ Memory MCP → Memory Service → Historical context
     └→ Swarm → Browser automation → Web data
```

## Key Design Decisions

| Decision | Before | After | Rationale |
|----------|--------|-------|-----------|
| Compression | LLMLingua+torch (2GB) | Headroom (200MB) | CPU/ONNX, no GPU needed |
| Cache | Redis (Docker) | diskcache (in-process) | One fewer container |
| RAG | Khoj (Docker, 1GB) | LightRAG (Python, ~300MB) | Graph-enhanced, active dev |
| Memory | Genesys (causal graph) | sqlite-vec (embedded) | Zero infra, simpler |
| MCP | Session-based | Stateless (2026-07-28) | Protocol compliance |
| Gateway | Traefik (50MB) | Caddy (20MB) | Simpler config, lower memory |
| Tracing | Custom tracing.py | W3C Trace Context | Standard compliance |

## Testing

- **874 tests** (870 passing, 4 skipped)
- **Coverage**: ~82%
- **Test types**: Unit, integration, e2e, fuzz, contract, load
- **Run**: `pytest tests/ -v`
