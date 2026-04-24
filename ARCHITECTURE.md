# IronSilo Architecture

## Overview

IronSilo is a local-first, cross-platform AI development sandbox that provides a secure, resource-capped environment for AI-assisted coding. It combines multiple specialized tools into a cohesive workspace that runs entirely on your local machine.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HOST MACHINE                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Aider CLI     │  │   IronClaw PAI  │  │   Local LLM (LM Studio/     │  │
│  │   (The Hands)   │  │   (The Brain)   │  │   Ollama/Lemonade)          │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘  │
│           │                    │                          │                  │
│           │                    │                          │ :8000            │
│           ▼                    ▼                          ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     DOCKER CONTAINER LAYER                           │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │    │
│  │  │ LLMLingua    │  │   Khoj       │  │   Genesys    │  │  pgvector│  │    │
│  │  │ Proxy        │  │   (RAG)      │  │   (LTM)      │  │  (DB)   │  │    │
│  │  │ :8001        │  │   :42110     │  │   :8002      │  │  :5432  │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Resource Limits: ~4GB RAM total | CPU per service capped                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Action Layer (Runs on Host)

#### Aider CLI - "The Hands"
- **Purpose**: Specialized coding engine with AST-based code editing
- **Location**: Installed natively on host via `pip install aider-chat`
- **Features**:
  - Abstract Syntax Tree (AST) mapping for 4x token efficiency
  - Direct file system access for reading/writing code
  - Bash command execution for running tests, linters, builds
  - Git integration for version control

#### IronClaw PAI - "The Brain"
- **Purpose**: Personal AI orchestrator for research and automation
- **Location**: Runs in WebAssembly (WASM) sandbox
- **Features**:
  - Web research with privacy (via SearxNG)
  - Schedule management and cron jobs
  - Zero-trust execution environment
  - API key isolation from host OS

### 2. Intelligence Layer (Docker Containers)

#### LLMLingua Proxy (`proxy/`)
- **Port**: 8001
- **Purpose**: Context compression and API proxy
- **Technology**: FastAPI + LLMLingua-2-BERT
- **Features**:
  - Automatic prompt compression (up to 40% reduction)
  - OpenAI-compatible API endpoint
  - Streaming response support
  - Semantic model routing via classifier
  - Health check endpoint
- **Key Files**:
  - `proxy/proxy.py` - Main FastAPI application
  - `proxy/models.py` - Pydantic request/response models
  - `proxy/classifier.py` - Semantic routing classifier

#### Khoj - Wiki RAG Engine
- **Port**: 42110
- **Purpose**: Private document search and Q&A
- **Features**:
  - PDF, Markdown, and text document ingestion
  - Semantic search over personal knowledge base
  - Web UI for interactive queries
  - API for programmatic access

#### Genesys - Long-Term Memory
- **Port**: 8002
- **Purpose**: Causal graph memory system
- **Features**:
  - Persistent memory across sessions
  - Causal relationship tracking
  - Preference learning
  - Reasoning chain storage
- **Backend**: PostgreSQL with pgvector

#### pgvector - Vector Database
- **Port**: 5432
- **Purpose**: Vector storage for Genesys and semantic search
- **Technology**: PostgreSQL 15 with pgvector extension
- **Database**: `ironsilo_vault`

#### MCP Servers (`mcp/`)
- **Genesys MCP** (port 8003): Exposes Genesys memory as MCP server
- **Khoj MCP** (port 8004): Exposes Khoj RAG as MCP server
- **Purpose**: Standardized interface for agent memory and knowledge access

## Data Flow

### Code Editing Flow
```
User -> Aider CLI -> LLMLingua Proxy -> Local LLM
         |              |
         |              +-- Compress context
         |              +-- Forward to LLM
         |
         +-- Apply diffs to files
         +-- Run tests/linters
         +-- Commit to Git
```

### Research Flow
```
User -> IronClaw -> SearxNG (private search)
         |
         +-- LLMLingua Proxy -> Local LLM
         |
         +-- Store findings in Genesys
         +-- Query Khoj for related docs
```

### Memory Flow
```
Agent Action -> Genesys API -> pgvector
                |
                +-- Store causal relationships
                +-- Update preference model
                +-- Index for retrieval
```

## Security Architecture

### Resource Isolation
- **Memory**: Docker containers limited to ~4GB total
- **CPU**: Per-container CPU limits (0.5-2.0 cores)
- **GPU**: 100% dedicated to host LLM (proxy runs on CPU only)

### Network Isolation
- **Internal**: Docker bridge network for inter-container communication
- **External**: Only necessary ports exposed (8001, 42110, 8080)
- **Sandbox**: IronClaw runs in WASM sandbox, no direct host access

### Data Security
- **Encryption at rest**: AES-256-GCM for sensitive data
- **Key management**: Secure key rotation and storage
- **No hardcoded secrets**: Environment-based configuration

## Configuration

### Environment Variables
```bash
# LLM Endpoint
LLM_ENDPOINT=http://host.docker.internal:8000/v1/chat/completions

# Compression Settings
COMPRESSION_THRESHOLD=1000  # Characters before compression
COMPRESSION_RATE=0.6        # Target compression ratio

# Database
POSTGRES_DB=ironsilo_vault
POSTGRES_USER=silo_admin
POSTGRES_PASSWORD=silo_password
```

### Resource Limits
```yaml
# docker-compose.yml resource limits
ironclaw-db:       1.0 CPU, 512MB RAM
genesys-memory:    1.0 CPU, 512MB RAM
khoj:              1.5 CPU, 1GB RAM
llm-proxy:         2.0 CPU, 3GB RAM
mcp-genesys:       0.5 CPU, 256MB RAM
mcp-khoj:          0.5 CPU, 256MB RAM
```

## Development

### Project Structure
```
IronSilo/
├── proxy/              # LLMLingua proxy service
│   ├── proxy.py        # FastAPI application
│   ├── models.py       # Pydantic models
│   ├── classifier.py   # Semantic routing
│   └── Dockerfile
├── mcp/                # MCP server implementations
│   ├── genesys_server.py
│   ├── khoj_server.py
│   └── framework.py
├── genesys/            # Memory system
│   └── Dockerfile
├── security/           # Encryption modules
│   ├── encryption.py
│   └── key_manager.py
├── tui/                # Terminal UI
│   ├── app.py
│   └── widgets/
├── tests/              # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docs/               # Documentation
```

### Testing Strategy
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test full system workflows
- **Coverage Target**: 80%+

### Build & Run
```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start workspace
./Start_Workspace.sh

# Stop workspace
./Stop_Workspace.sh
```

## API Reference

### LLMLingua Proxy API

#### POST /api/v1/chat/completions
OpenAI-compatible chat completion endpoint.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hello, world!"}
  ],
  "model": "qwen2.5-coder",
  "temperature": 0.7,
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "compression_enabled": true,
  "llm_endpoint": "http://host.docker.internal:8000/v1/chat/completions",
  "uptime_seconds": 3600.5
}
```

## Future Roadmap

See [ROADMAP.md](./ROADMAP.md) for planned features including:
- AES-256 encryption for all data at rest
- Semantic model routing for optimal performance
- Cross-session KV caching for faster responses
- IronSilo Terminal Dashboard (TUI)
- Desktop Command Center (GUI)
