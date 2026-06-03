# IronSilo: System Design Document (SDD)
## Version: 2.0.0 (Enterprise Orchestrator Edition)
## Date: 2026-04-23

---

## 1. Executive Summary

IronSilo is a local-first, cross-platform AI development sandbox that transforms any modern PC into a private AI laboratory. By leveraging Docker Compose with strict resource constraints (~4GB RAM ceiling), IronSilo provides a secure, isolated environment for running:

- **Aider CLI**: AST-aware coding assistant
- **IronClaw**: WebAssembly-based autonomous agent
- **Khoj**: Private Wiki RAG engine  
- **Genesys**: Causal graph memory system (PostgreSQL + pgvector)
- **LLMLingua Proxy**: Context compression and semantic routing

### 1.1 Core Architecture Principles

1. **Monolith-First**: Single Docker Compose stack with clearly bounded service contexts
2. **Terminal-First**: No IDE dependencies; all tools accessible via CLI and native web UIs
3. **Security-by-Isolation**: WASM sandbox for agent execution, Docker for backend services
4. **Resource Discipline**: Hard cgroup limits prevent system degradation

---

## 2. System Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          HOST MACHINE (Action Layer)                    │
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │
│  │   Aider CLI     │    │   IronClaw      │    │   User Workspace    │ │
│  │  (Native Bin)   │    │  (WASM Runtime) │    │   (Source Code)     │ │
│  └────────┬────────┘    └────────┬────────┘    └─────────────────────┘ │
│           │                      │                                      │
└───────────┼──────────────────────┼──────────────────────────────────────┘
            │                      │
            ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   DOCKER COMPOSE SANDBOX (~4GB RAM)                     │
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │
│  │  LLMLingua      │    │   Genesys       │    │   Khoj RAG          │ │
│  │  Proxy          │◄──►│   Memory API    │◄──►│   Engine            │ │
│  │  (CPU-Bound)    │    │   (FastAPI)     │    │   (Web UI)          │ │
│  │  :8001          │    │   :8002         │    │   :42110            │ │
│  └────────┬────────┘    └────────┬────────┘    └─────────────────────┘ │
│           │                      │                                      │
│           ▼                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              PostgreSQL (pgvector) - :5432                      │   │
│  │              ironsilo_vault database                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LOCAL LLM HOST (Inference Layer)                     │
│                                                                         │
│    LM Studio / Ollama / Lemonade (Port 8000 or 11434)                  │
│    Qwen 2.5 Coder 7B / Llama 3 8B Instruct / etc.                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Service Specifications

| Service | Image | Port | RAM Limit | CPU Limit | Purpose |
|---------|-------|------|-----------|-----------|---------|
| ironclaw-db | pgvector/pgvector:pg15 | 5432 | 512MB | 1.0 | Vector database for memory |
| genesys-memory | ./genesys (custom) | 8002→8000 | 512MB | 1.0 | Causal graph memory API |
| khoj | ghcr.io/khoj-ai/khoj:latest | 42110 | 1GB | 1.5 | Private Wiki RAG |
| llm-proxy | ./proxy (custom) | 8001 | 3GB | 2.0 | Context compression & routing |

### 2.3 Network Architecture

- **External Ports**: 5432 (Postgres), 8001 (Proxy), 42110 (Khoj), 8080 (IronClaw)
- **Internal Network**: Docker bridge network for service-to-service communication
- **Host Bridge**: `host.docker.internal` mapping for proxy→LLM communication

---

## 3. Component Deep Dive

### 3.1 LLMLingua Proxy (Context Optimization Layer)

**Location**: `./proxy/proxy.py`

**Core Functions**:
1. **Context Compression**: Intercepts requests >1000 tokens, applies LLMLingua-2 compression (40% reduction)
2. **Streaming Support**: Forwards Server-Sent Events (SSE) from LLM host
3. **Semantic Routing** (Phase 2): Routes requests to appropriate models based on content analysis

**Dependencies**:
- `fastapi`, `uvicorn`: HTTP server
- `httpx`: Async HTTP client
- `llmlingua`: Microsoft's prompt compressor
- `torch` (CPU-only): PyTorch backend

**Current Limitations**:
- Single endpoint routing (hardcoded to port 8000)
- No semantic model selection
- No persistent KV cache

### 3.2 Genesys Memory System

**Location**: `./genesys/`

**Architecture**:
- **Backend**: PostgreSQL with pgvector extension
- **API**: FastAPI REST interface
- **Embedding**: Local sentence-transformers (no external API)

**Data Model**:
- **Nodes**: Entity representations with embeddings
- **Edges**: Causal/temporal relationships
- **Sessions**: Conversation context tracking

**Integration Points**:
- Exposes REST API for memory CRUD operations
- Connects to PostgreSQL via SQLAlchemy
- Will support MCP protocol (Phase 1)

### 3.3 Khoj RAG Engine

**Configuration**: Docker container with persistent volume

**Features**:
- PDF/Markdown document ingestion
- Semantic search over personal knowledge base
- Web UI at `http://localhost:42110`
- Anonymous mode (no authentication required)

**Limitations**:
- No programmatic API exposed
- Limited to local document search
- No integration with memory graph

### 3.4 IronClaw Agent (WASM Runtime)

**Architecture**: WebAssembly sandbox running natively on host

**Capabilities**:
- Web browsing via headless browser
- Autonomous task execution
- Memory persistence via PostgreSQL
- OpenAI-compatible API integration

**Security Model**:
- Zero-trust WASM sandbox
- No direct filesystem access
- API key isolation

---

## 4. Implementation Roadmap

### 4.1 Phase 1: Dual-Agent Swarm Integration

#### 4.1.1 MCP Integration for IronClaw
**Goal**: Expose Genesys memory and Khoj RAG as MCP servers

**Implementation**:
```
┌─────────────────┐    MCP Protocol    ┌─────────────────┐
│   IronClaw      │◄─────────────────►│   MCP Servers   │
│  (WASM Client)  │                    │                 │
└─────────────────┘                    │  ┌───────────┐  │
                                       │  │ Genesys   │  │
                                       │  │ Memory    │  │
                                       │  └───────────┘  │
                                       │  ┌───────────┐  │
                                       │  │ Khoj RAG  │  │
                                       │  └───────────┘  │
                                       └─────────────────┘
```

**Files to Create/Modify**:
- `mcp/genesys_server.py`: MCP wrapper for Genesys API
- `mcp/khoj_server.py`: MCP wrapper for Khoj
- `mcp/Dockerfile`: MCP server container
- `docker-compose.yml`: Add MCP services

**Acceptance Criteria**:
- [ ] IronClaw can query Genesys via MCP
- [ ] IronClaw can search Khoj documents via MCP
- [ ] MCP servers run in Docker with resource limits
- [ ] End-to-end test passes

#### 4.1.2 Aider/IronClaw Handoff Pipeline
**Goal**: Enable agent-to-agent task delegation

**Implementation**:
```
User Request → IronClaw (Research) → Task File → Aider (Implementation)
```

**Protocol**:
1. IronClaw creates `TASK.md` with research findings
2. Aider watches for task files via file watcher
3. Aider parses requirements and executes
4. Results posted back to IronClaw memory

**Files to Create**:
- `pipeline/task_schema.py`: Task definition
- `pipeline/file_watcher.py`: File system monitor
- `pipeline/agent_bridge.py`: Inter-agent communication

**Acceptance Criteria**:
- [ ] Task file creation triggers Aider
- [ ] Research findings preserved in memory
- [ ] Implementation results stored in Genesys

#### 4.1.3 Private Web Search (SearxNG)
**Goal**: Add privacy-respecting search to IronClaw

**Implementation**:
```yaml
# docker-compose.yml addition
searxng:
  image: searxng/searxng:latest
  container_name: searxng
  ports:
    - "8888:8080"
  volumes:
    - searxng-data:/etc/searxng
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
```

**Acceptance Criteria**:
- [ ] SearxNG runs in Docker container
- [ ] IronClaw can query search API
- [ ] No external API keys required
- [ ] Search queries remain private

### 4.2 Phase 2: Security & Performance

#### 4.2.1 Application-Level Encryption (AES-256)
**Goal**: Encrypt data at rest in PostgreSQL and Khoj volumes

**Implementation**:
- PostgreSQL: Transparent Data Encryption (TDE) via `pgcrypto`
- Khoj: Application-layer encryption before storage
- Key management: Environment variable with key rotation support

**Files to Create**:
- `security/encryption.py`: AES-256 implementation
- `security/key_manager.py`: Key rotation logic
- `security/migrations/`: Database migration scripts

**Acceptance Criteria**:
- [ ] All sensitive data encrypted at rest
- [ ] Keys rotated without downtime
- [ ] Performance impact < 10%

#### 4.2.2 Semantic Model Routing
**Goal**: Route requests to optimal LLM based on content

**Implementation**:
```python
class SemanticRouter:
    def route(self, request: Request) -> str:
        # Code editing → Qwen 2.5 Coder 7B
        # Simple queries → Llama 3 8B Instruct
        # Research → Claude 3.5 Sonnet (if available)
```

**Models**:
- Code tasks: `qwen2.5-coder-7b` (port 8000)
- Fast inference: `llama-3-8b-instruct` (port 8002)
- Complex reasoning: User-configured (port 8003)

**Files to Modify**:
- `proxy/proxy.py`: Add routing logic
- `proxy/config.yaml`: Model definitions
- `proxy/router.py`: Semantic classification

**Acceptance Criteria**:
- [ ] Requests routed based on content analysis
- [ ] Fallback for misclassified requests
- [ ] Configurable model endpoints
- [ ] Latency overhead < 50ms

#### 4.2.3 Cross-Session KV Caching
**Goal**: Cache key-value pairs for faster inference

**Implementation**:
```
Request → Check Cache → Hit? → Return
                ↓
              Miss → Compress → LLM → Cache → Return
```

**Storage**: Redis-like in-memory cache with LRU eviction

**Files to Create**:
- `cache/kv_store.py`: Cache implementation
- `cache/serializer.py`: State serialization
- `cache/persistence.py`: Disk persistence

**Acceptance Criteria**:
- [ ] Cache hit rate > 60% for repetitive tasks
- [ ] Cache survives container restarts
- [ ] Memory usage bounded (500MB max)

### 4.3 Phase 3: Developer Experience

#### 4.3.1 IronSilo Terminal Dashboard (TUI)
**Goal**: Real-time monitoring terminal UI

**Implementation**:
- Framework: Textual (Python) or Ratatui (Rust)
- Metrics: Container health, RAM usage, proxy traffic, cache stats

**Features**:
- Real-time container status
- Resource usage graphs
- Log streaming
- Interactive controls (restart services)

**Files to Create**:
- `tui/dashboard.py`: Main TUI application
- `tui/widgets/`: UI components
- `tui/monitoring.py`: Metrics collection

**Acceptance Criteria**:
- [ ] Dashboard runs with `ironsilo monitor`
- [ ] Updates in real-time (1s refresh)
- [ ] Keyboard navigation
- [ ] No browser required

#### 4.3.2 Interactive Setup Wizard
**Goal**: Automated configuration for new users

**Implementation**:
```bash
./Start_Workspace.sh --interactive

# Prompts:
# 1. Which LLM host? [LM Studio/Ollama/Lemonade]
# 2. Which port? [8000/11434/custom]
# 3. Enable IronClaw? [Y/n]
# 4. Memory allocation? [default/custom]
```

**Files to Create**:
- `setup/wizard.py`: Interactive setup
- `setup/detector.py`: Auto-detect installed tools
- `setup/configurator.py`: Write .env file

**Acceptance Criteria**:
- [ ] Detects installed LLM hosts
- [ ] Configures ports automatically
- [ ] Validates configuration before start
- [ ] Generates .env file

---

## 5. Testing Strategy

### 5.1 Test Pyramid

```
         ┌─────────────────┐
         │   E2E Tests     │  ← Full stack integration
         │   (Playwright)  │
         └─────────────────┘
                │
         ┌─────────────────┐
         │ Integration     │  ← Service-to-service
         │ Tests           │
         └─────────────────┘
                │
         ┌─────────────────┐
         │ Unit Tests      │  ← Individual functions
         │ (pytest)        │
         └─────────────────┘
```

### 5.2 Test Coverage Requirements

| Component | Unit | Integration | E2E |
|-----------|------|-------------|-----|
| Proxy | 90% | 80% | 60% |
| Genesys | 90% | 85% | 70% |
| MCP Servers | 85% | 80% | 60% |
| TUI | 70% | 60% | 50% |
| Setup Wizard | 80% | 75% | 60% |

### 5.3 Test Commands

```bash
# Run all tests
pytest tests/ -v --cov=. --cov-report=html

# Run specific test suite
pytest tests/unit/test_proxy.py -v
pytest tests/integration/test_mcp.py -v
pytest tests/e2e/ -v

# Run with coverage enforcement
pytest --cov-fail-under=80
```

---

## 6. Security Considerations

### 6.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| Malicious LLM output | WASM sandbox isolation |
| Data exfiltration | No internet access from containers |
| Key compromise | Key rotation + encryption |
| Resource exhaustion | Docker cgroup limits |
| API key theft | Environment variable injection |

### 6.2 Security Checklist

- [ ] No hardcoded secrets in source code
- [ ] All inputs sanitized before processing
- [ ] SQL injection prevention via ORM
- [ ] XSS prevention in web UIs
- [ ] CSRF protection on state-changing endpoints
- [ ] Rate limiting on API endpoints
- [ ] Audit logging for sensitive operations

---

## 7. Deployment & Operations

### 7.1 Prerequisites

1. Docker Compose V2
2. Git
3. Python 3.11+ (for local development)
4. Local LLM host (LM Studio/Ollama/Lemonade)

### 7.2 Quick Start

```bash
# Clone repository
git clone https://github.com/iknowkungfubar/IronSilo.git
cd IronSilo

# Start workspace (auto-detects configuration)
./Start_Workspace.sh

# Or with interactive setup
./Start_Workspace.sh --interactive
```

### 7.3 Monitoring

- **Prometheus**: Metrics collection (Phase 3)
- **Grafana**: Visualization dashboards (Phase 3)
- **Loki**: Log aggregation (Phase 3)

### 7.4 Backup & Recovery

```bash
# Backup PostgreSQL
docker exec ironclaw-db pg_dump -U silo_admin ironsilo_vault > backup.sql

# Backup Khoj data
docker cp khoj:/root/.khoj ./khoj-backup

# Restore
docker exec -i ironclaw-db psql -U silo_admin ironsilo_vault < backup.sql
```

---

## 8. Future Enhancements

### 8.1 Phase 4: Production Hardening
- Kubernetes deployment option
- High availability configuration
- Multi-region support
- Enterprise SSO integration

### 8.2 Phase 5: Advanced Features
- Code review automation
- Automated testing generation
- Documentation generation
- Performance profiling

---

## 9. Appendices

### 9.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_ENDPOINT` | `http://host.docker.internal:8000/v1/chat/completions` | LLM API endpoint |
| `POSTGRES_PASSWORD` | `silo_password` | Database password |
| `GENESYS_BACKEND` | `postgres` | Memory backend |
| `HF_HOME` | `/root/.cache/huggingface` | HuggingFace cache |

### 9.2 Port Reference

| Service | Internal | External | Protocol |
|---------|----------|----------|----------|
| PostgreSQL | 5432 | 5432 | TCP |
| Genesys API | 8000 | 8002 | HTTP |
| LLMLingua Proxy | 8001 | 8001 | HTTP |
| Khoj | 42110 | 42110 | HTTP |
| IronClaw | 8080 | 8080 | HTTP |
| SearxNG | 8080 | 8888 | HTTP |

### 9.3 Resource Allocation Summary

| Component | RAM | CPU | Storage |
|-----------|-----|-----|---------|
| PostgreSQL | 512MB | 1.0 | 2GB |
| Genesys | 512MB | 1.0 | 100MB |
| Khoj | 1GB | 1.5 | 5GB |
| Proxy | 3GB | 2.0 | 1.1GB |
| SearxNG | 256MB | 0.5 | 100MB |
| **Total** | **~5.3GB** | **6.0** | **8.2GB** |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-04-22 | Initial | Base architecture |
| 2.0.0 | 2026-04-23 | Enterprise Orchestrator | Added Phase 1-3 roadmap, MCP, encryption, TUI |

---

*This document is a living specification. Update it as features are implemented.*
