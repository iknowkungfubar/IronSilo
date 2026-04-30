# IronSilo Architecture Document

## Version: 2.1.0 (True Silo with Browser Swarm)

---

## 1. Architecture Overview

IronSilo is a private, local-first AI development sandbox using a **True Silo** architecture with a single entry point through a Traefik API Gateway.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HOST MACHINE                                       │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     Traefik API Gateway (Port 8080)                 │   │
│   │                                                                    │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐  │   │
│   │  │/api/v1   │  │/genesys   │  │/khoj     │  │/search   │  │/swarm│  │   │
│   │  │  ↓       │  │   ↓      │  │   ↓      │  │   ↓      │  │   ↓  │  │   │
│   │  │LLM Proxy │  │Genesys   │  │  Khoj    │  │ SearxNG  │  │Swarm │  │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────┘  │   │
│   │                                                                    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌────────────┐        ┌────────────┐        ┌────────────┐               │
│   │ Aider CLI  │        │  IronClaw  │        │ LM Studio  │               │
│   │  (Native)  │        │   (WASM)   │        │  Ollama    │               │
│   └────────────┘        └────────────┘        └────────────┘               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 True Silo Principles

1. **Single Entry Point**: All traffic flows through port 8080 (Traefik)
2. **No Direct Port Exposure**: Internal services are not directly accessible
3. **X-Silo-Auth Header**: Middleware validates requests through Traefik
4. **Internal Network Isolation**: Docker `internal_bridge` network

---

## 2. Service Architecture

### 2.1 Traefik API Gateway

**Container**: `traefik`
**Port**: 8080 (HTTP), 8443 (HTTPS)

**Responsibilities**:
- Route all external traffic to internal services
- Enforce `X-Silo-Auth` header validation
- SSL termination (if configured)
- Load balancing

**Configuration Files**:
- `traefik.yml` - Static configuration
- `dynamic.yml` - Dynamic middleware configuration

### 2.2 LLM Proxy (`/api/v1`)

**Container**: `llm-proxy`
**Internal Port**: 8001

**Features**:
- OpenAI-compatible chat completions API
- LLMLingua-2 prompt compression (40% reduction)
- Streaming response support
- Circuit breaker pattern (5 failures → open)
- Exponential backoff retry (3 attempts)
- KV cache for repeated requests
- Input sanitization (control char removal)
- Connection pooling (100 max connections)

**Environment Variables**:
```yaml
LLM_ENDPOINT: http://host.docker.internal:8000/v1/chat/completions
COMPRESSION_THRESHOLD: 1000
COMPRESSION_RATE: 0.6
KV_CACHE_ENABLED: "true"
CIRCUIT_BREAKER_FAILURE_THRESHOLD: 5
CIRCUIT_BREAKER_TIMEOUT: 30.0
```

### 2.3 Genesys Memory (`/genesys`)

**Container**: `genesys-memory`
**Internal Port**: 8000

**Architecture**:
- **PostgreSQL** (pgvector) for persistent storage
- **In-memory fallback** when DB unavailable
- **Connection pool** (min=1, max=10)

**Data Model**:
```
memories (id, content, memory_type, importance, tags, created_at, metadata)
edges (id, source_id, target_id, relationship, strength, created_at)
sessions (id, session_type, created_at, metadata)
```

**Indexes**:
- `idx_memories_type` on `memory_type`
- `idx_edges_source` on `source_id`
- `idx_edges_target` on `target_id`

### 2.4 Khoj Wiki (`/khoj`)

**Container**: `khoj`
**Internal Port**: 42110

**Features**:
- PDF/Markdown document ingestion
- Semantic search
- Anonymous mode (no auth required)
- Web UI at `/khoj`

### 2.5 SearxNG Search (`/search`)

**Container**: `searxng`
**Internal Port**: 8080

**Features**:
- Privacy-respecting web search
- Multiple search engine aggregation
- JSON/HTML/CSV response formats

### 2.6 Browser Swarm (`/swarm`, `/ws/swarm`)

**Container**: `swarm-service`
**Internal Port**: 8095

**Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│                    Swarm Service                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Orchestrator│  │ HarnessWorker│  │ WebSocket Server    │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │              │
│         └────────────────┼────────────────────┘              │
│                          ↓                                   │
│              ┌────────────────────────┐                      │
│              │  CDP WebSocket Client  │                      │
│              │  (browser-node:9222)   │                      │
│              └────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
              ┌────────────────────────┐
              │     browser-node       │
              │   (Chrome Headless)    │
              └────────────────────────┘
```

**Components**:

1. **Orchestrator** (`swarm/orchestrator.py`)
   - Manages task queue with priorities
   - Retry queue with exponential backoff (max 3 retries)
   - Dead letter queue for failed tasks
   - Graceful shutdown handling

2. **HarnessWorker** (`swarm/harness_worker.py`)
   - Raw CDP WebSocket connection
   - DOM extraction and element interaction
   - Screenshot capture
   - Graceful browser shutdown

3. **WebSocket Server** (`swarm/main.py`)
   - Real-time action broadcasting
   - Task submission endpoint
   - History and status endpoints
   - `/metrics` for Prometheus

**Task Flow**:
```
Client → WebSocket → Orchestrator → HarnessWorker → CDP → browser-node
                     ↓
              Genesys Memory
              (result storage)
```

### 2.7 MCP Servers

**Containers**: `mcp-genesys`, `mcp-khoj`
**Internal Port**: 8000 each

**Purpose**: Expose Genesys memory and Khoj RAG as MCP (Model Context Protocol) tools for IronClaw.

---

## 3. Network Architecture

### 3.1 Docker Networks

```yaml
networks:
  internal_bridge:
    driver: bridge
    internal: false  # Allows outbound for LLM calls
    name: internal_bridge
```

### 3.2 Service Communication

| Source | Destination | Protocol |
|--------|-------------|----------|
| Traefik | llm-proxy | HTTP |
| Traefik | genesys-memory | HTTP |
| Traefik | khoj | HTTP |
| Traefik | searxng | HTTP |
| Traefik | swarm-service | HTTP/WebSocket |
| llm-proxy | host.docker.internal:8000 | HTTP |
| swarm-service | browser-node:9222 | WebSocket |
| mcp-genesys | genesys-memory:8000 | HTTP |
| mcp-khoj | khoj:42110 | HTTP |

---

## 4. Security Architecture

### 4.1 Authentication Flow

```
Client Request → X-API-Key Header → Traefik Middleware → X-Silo-Auth → Service
```

**Middleware Chain**:
1. Rate limiting (60 req/min per key)
2. Request size limit (10MB max)
3. CORS validation
4. X-Silo-Auth validation
5. API key verification (via service middleware)

### 4.2 Security Features

| Feature | Implementation | Location |
|---------|---------------|----------|
| AES-256-GCM | cryptography library | `security/encryption.py` |
| API Key Derivation | PBKDF2 (100k iterations) | `security/key_manager.py` |
| SQL Injection Prevention | Parameterized queries | `genesys/app.py` |
| Input Sanitization | Control char removal | `proxy/proxy.py` |
| Secret Scanning | gitleaks pre-commit hook | `.pre-commit-config.yaml` |
| Request ID Tracking | X-Request-ID header | `security/middleware.py` |

---

## 5. Data Flow

### 5.1 LLM Request Flow

```
1. Client → POST /api/v1/chat/completions
2. Traefik → Route to llm-proxy:8001
3. llm-proxy:
   a. Validate API key
   b. Rate limit check
   c. KV cache check (if enabled)
   d. Prompt compression (if >1000 chars)
   e. Circuit breaker check
   f. Retry with backoff (if 5xx)
4. Upstream LLM (host.docker.internal:8000)
5. Response caching (if enabled)
6. Return to client
```

### 5.2 Swarm Task Flow

```
1. Client → WebSocket /ws/swarm
2. swarm-service:
   a. Validate connection
   b. Submit task to orchestrator
   c. Orchestrator queues task
   d. HarnessWorker executes via CDP
   e. Result stored in Genesys
   f. Action broadcast to all clients
3. Client receives real-time updates
```

---

## 6. Resource Allocation

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| traefik | 0.5 | 128M |
| ironclaw-db | 1.0 | 512M |
| genesys-memory | 1.0 | 512M |
| khoj | 1.5 | 1G |
| llm-proxy | 2.0 | 3G |
| mcp-genesys | 0.5 | 256M |
| mcp-khoj | 0.5 | 256M |
| searxng | 0.5 | 256M |
| browser-node | 1.0 | 1G |
| swarm-service | 1.0 | 1G |
| **Total** | **9.5** | **~7.7GB** |

---

## 7. Observability

### 7.1 Logging

All services use structured logging with `structlog`:
- JSON format for machine parsing
- ISO timestamps
- Request ID correlation

### 7.2 Metrics

Prometheus metrics available at:
- `/metrics` (llm-proxy)
- `/metrics` (genesys-memory)
- `/metrics` (swarm-service)

### 7.3 Health Checks

All services have health checks configured in `docker-compose.yml`.

---

## 8. Disaster Recovery

### 8.1 Backup Procedures

```bash
# Backup PostgreSQL
docker exec ironclaw-db pg_dump -U silo_admin ironsilo_vault > backup.sql

# Backup Khoj data
docker cp khoj:/root/.khoj ./khoj-backup
```

### 8.2 Recovery Procedures

```bash
# Restore PostgreSQL
docker exec -i ironclaw-db psql -U silo_admin ironsilo_vault < backup.sql
```

---

## 9. Future Enhancements

See [ROADMAP.md](ROADMAP.md) for planned features:
- Semantic Model Routing
- Cross-Session KV Caching
- IronSilo Studio (Desktop GUI)
- Interactive Setup Wizard

---

*Document Version: 2.1.0*
*Last Updated: 2026-04-30*
*Maintained by: Autonomous Swarm*