# IronSilo Redesign Proposal — July 2026

Based on research across 4 parallel deep-dives (prompt compression, RAG/memory, vector databases, architecture modernization). Current state: 933 tests passing, 78% coverage.

---

## Architecture Comparison: Current vs Proposed

```
CURRENT IronSilo                                        PROPOSED IronSilo
─────────────────────────────                           ─────────────────────────────
┌── HOST ──────────────────┐                            ┌── HOST ──────────────────┐
│ Aider CLI / Swarm        │                            │ OpenCode / agents        │
│      │                   │                            │      │                   │
└──────┼───────────────────┘                            └──────┼───────────────────┘
       │                                                         │
┌──────▼──── DOCKER ──────┐                            ┌──────▼──── NATIVE ──────┐
│  Traefik Gateway :8080  │  ← REMOVE                   │  Caddy Gateway :8080    │
│       │                 │                             │       │                 │
│  ┌────▼───────────┐     │                             │  ┌────▼───────────┐     │
│  │ LLMLingua Proxy│     │  ← REPLACE                  │  │ Headroom Proxy │     │
│  │ (FastAPI+torch)│     │                             │  │ (CPU/ONNX)     │     │
│  │ :8001, ~3GB    │     │                             │  │ :8787, ~200MB  │     │
│  └────────────────┘     │                             │  └────────────────┘     │
│                         │                             │                         │
│  ┌────────────────┐     │                             │  ┌────────────────┐     │
│  │ Khoj (RAG)     │     │  ← REPLACE                  │  │ Onyx (RAG)     │     │
│  │ :42110, ~1GB   │     │                             │  │ :8081           │     │
│  └────────────────┘     │                             │  └────────────────┘     │
│                         │                             │                         │
│  ┌────────────────┐     │                             │  ┌────────────────┐     │
│  │ Genesys (Mem)  │     │  ← REPLACE                  │  │ Stash (Memory) │     │
│  │ :8002, ~512MB  │     │                             │  │ :8082          │     │
│  └────────────────┘     │                             │  └────────────────┘     │
│                         │                             │                         │
│  ┌────────────────┐     │                             │  ┌────────────────┐     │
│  │ pgvector       │     │  ← EVALUATE                  │  │ sqlite-vec OR  │     │
│  │ :5432, ~512MB  │     │                             │  │ pgvector       │     │
│  └────────────────┘     │                             │  └────────────────┘     │
│                         │                             │                         │
│  ┌────────────────┐     │                             │  ┌────────────────┐     │
│  │ Redis (cache)  │     │  ← REMOVE                   │  │ diskcache      │     │
│  │ :6379          │     │                             │  │ (in-process)   │     │
│  └────────────────┘     │                             │  └────────────────┘     │
│                         │                             │                         │
│  ┌────────────────┐     │                             │  ┌────────────────┐     │
│  │ SearxNG (search)│    │  ← KEEP (still best)         │  │ SearxNG        │     │
│  └────────────────┘     │                             │  └────────────────┘     │
│                         │                             │                         │
│  ┌────────────────┐     │                             │  ┌────────────────┐     │
│  │ Textual TUI    │     │  ← KEEP                      │  │ Textual TUI    │     │
│  └────────────────┘     │                             │  └────────────────┘     │
└─────────────────────────┘                            └─────────────────────────┘
```

---

## Component-by-Component Recommendations

### 1. Prompt Compression: LLMLingua + torch → Headroom
**Priority: HIGH** — torch dependency is ~2GB and requires GPU

| Factor | LLMLingua (Current) | Headroom (Proposed) |
|--------|-------------------|-------------------|
| Runtime | GPU + torch (2GB) | CPU/ONNX (200MB) |
| Stars | 6.4k | **57.7k** |
| Last commit | Oct 2025 | **3 hours ago** |
| Compress ratio | ~40% | **47-92%** (per benchmark) |
| Accuracy | Varies | ±0.000 GSM8K delta |
| Modes | Library only | Proxy, library, MCP, agent wrap |
| Extras | None | CacheAligner, CCR, cross-agent memory, output reduction |

**Integration path:** `headroom proxy --port 8787` — zero code changes to existing proxy. The Headroom proxy intercepts requests, compresses them, forwards to LLM. FastAPI proxy can be simplified to a pure routing layer, or removed entirely if Headroom's proxy mode handles OpenAI-compatible forwarding.

### 2. RAG Engine: Khoj → Onyx
**Priority: MEDIUM** — functional but replaced by better alternatives

| Factor | Khoj (Current) | Onyx (Proposed) |
|--------|---------------|-----------------|
| Stars | ~12k | **30.8k** |
| Maintenance | Questionable | **Active (v4.3.1)** |
| LLM support | Limited | **Any** (Ollama, vLLM, OpenAI) |
| MCP support | ❌ | **✅ Native** |
| Connectors | Files/PDF only | **40+** (Slack, GDrive, Notion, etc.) |
| Agentic | ❌ | **✅ Code exec, tools, web search** |
| Self-host | Docker | Docker Compose |

**Integration path:** Replace Khoj Docker container with Onyx. Onyx uses its own vector storage. Remove Khoj MCP server (`mcp/khoj_server.py`, ~3 files) and replace with Onyx's native MCP.

**Alternative:** If full Onyx is too heavy (~2 containers), consider **AnythingLLM** (single container, 30k⭐) for lighter drop-in replacement.

### 3. Agent Memory: Genesys → Stash
**Priority: MEDIUM** — Genesys is custom and complex

| Factor | Genesys (Current) | Stash (Proposed) |
|--------|-------------------|-------------------|
| Architecture | Causal graph (custom) | **8-stage consolidation pipeline** |
| MCP native | ❌ (separate server) | **✅ Built-in** |
| Backend | pgvector + Postgres | **Postgres only** |
| Deployment | Docker container | **Single Go binary** |
| Features | Custom graph | Contradiction detection, confidence decay, goals, self-model |

**Integration path:** `stash serve --mcp --pg $DATABASE_URL` replaces the separate Genesys container + Khoj MCP server. Remove `genesys/`, `mcp/genesys_server.py`, `mcp/khoj_server.py`.

### 4. Vector Database: pgvector → sqlite-vec or Keep pgvector
**Priority: MEDIUM** — depends on infrastructure goals

| Factor | pgvector (Current) | sqlite-vec (Proposed) |
|--------|-------------------|----------------------|
| Architecture | Docker container | **Zero infra (one file)** |
| RAM | ~512MB | **0 (in-process)** |
| ANN index | StreamingDiskANN | DiskANN (alpha) |
| Ecosystem | Mature | Growing |
| Best for | Multi-service | **Local-first, single-binary** |

**Decision tree:**
- If keeping Postgres for Stash → **Keep pgvector** (pgvectorscale makes it competitive)
- If going fully embedded → **sqlite-vec** (one less Docker container, simpler deployment)
- If only vector search needed → **sqlite-vec** (zero infrastructure)

### 5. API Gateway: Traefik → Caddy
**Priority: LOW** — works but overkill for local

| Factor | Traefik (Current) | Caddy (Proposed) |
|--------|-------------------|-------------------|
| Config complexity | High (docker labels + dynamic.yml) | **Low (1 Caddyfile)** |
| Auto HTTPS | ✅ | ✅ |
| Memory | ~50MB | **~20MB** |
| Extensibility | Middleware chain | Reverse proxy + file server |
| Best for | Multi-service production | **Local dev sandbox** |

### 6. Cache: Redis → diskcache
**Priority: LOW** — removes one Docker dependency

Replace `cache/kv_store.py` Redis backend with Python's `diskcache` library. One fewer container, same functionality.

### 7. Stay the Same: Textual TUI, FastAPI, SearxNG, Swarm workers
- **Textual** — still actively maintained (McGugan). Best Python TUI by wide margin.
- **FastAPI** — best Python ASGI framework for AI workloads. Native streaming, WebSockets.
- **SearxNG** — still the gold standard for private self-hosted search.
- **Swarm/workers** — architecture is sound; only the memory/rag components need updating.

---

## MCP Protocol 2026-07-28 Migration (Required)

**The July 2026 RC makes MCP stateless.** This is a breaking change that affects all MCP servers (`mcp/framework.py`, `mcp/genesys_server.py`, `mcp/khoj_server.py`).

### Migration checklist:
- [ ] Remove session store dependency — no more sticky sessions
- [ ] Add `_meta` injection to every request (version, client info, capabilities)
- [ ] Implement `server/discover` endpoint
- [ ] Add `Mcp-Method`, `Mcp-Name`, `MCP-Protocol-Version` headers
- [ ] Add `ttlMs`/`cacheScope` to list responses
- [ ] Implement W3C Trace Context (`traceparent`)
- [ ] Move state from session layer to explicit tool handles
- [ ] Update JSON Schema to 2020-12 (`$ref`, `oneOf`, etc.)

---

## Migration Path

### Phase 1 — Drop torch (Highest Impact)
1. Install Headroom: `pip install "headroom-ai[all]"`
2. Run in proxy mode alongside existing setup
3. Validate compression ratios and latency
4. Remove `llmlingua` and `torch` dependencies
5. Remove `proxy/compression.py` — replace with Headroom calls

### Phase 2 — Simplify Infrastructure
1. Replace Redis with diskcache in `cache/kv_store.py`
2. Run Onyx or Stash as memory backend
3. Evaluate sqlite-vec vs keeping pgvector

### Phase 3 — MCP Migration
1. Rewrite `mcp/framework.py` for stateless protocol
2. Replace Genesys MCP with Stash MCP
3. Replace Khoj MCP with Onyx MCP

### Phase 4 — Polish
1. Replace Traefik with Caddy (simpler config)
2. Update TUI to reflect new component layout
3. Remove deprecated code and Docker containers

## Files to Remove
- `proxy/compression.py` (replaced by Headroom)
- `mcp/genesys_server.py` (replaced by Stash)
- `mcp/khoj_server.py` (replaced by Onyx)
- `genesys/` (entire directory - replaced by Stash)
- `proxy/Dockerfile` (Headroom runs as proxy instead)
- `tracing.py` (W3C Trace Context replaces ad-hoc)

## What To Keep
- `proxy/proxy.py` (simplified to routing only, no compression)
- `proxy/circuit_breaker.py` (still relevant)
- `proxy/classifier.py` (semantic routing still needed)
- `proxy/models.py` (pydantic models)
- `swarm/` (orchestration architecture is sound)
- `pipeline/` (processing pipeline is sound)
- `security/` (encryption/key management)
- `tui/` (just update for new components)
- `tests/` (update for new component names)
