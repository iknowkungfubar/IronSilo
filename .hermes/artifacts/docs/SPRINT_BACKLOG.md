# IronSilo: Sprint Backlog (Task Checklist)
## Version: 2.0.0
## Date: 2026-04-23

---

## Overview
This sprint backlog translates the ROADMAP.md into actionable tasks with clear acceptance criteria. Each task follows the **Ralph Wiggum Loop** (Test → Implement → Refactor) and must pass all tests before completion.

---

## Phase 1: Dual-Agent Swarm Integration

### 1.1 MCP Integration for IronClaw [HIGH PRIORITY]

#### Task 1.1.1: Create MCP Server Framework
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 4 hours

**Description**: Create a reusable MCP server framework that wraps FastAPI endpoints as MCP tools.

**Acceptance Criteria**:
- [ ] Base MCP server class with tool registration
- [ ] Automatic OpenAPI schema generation
- [ ] Health check endpoint
- [ ] Logging and error handling
- [ ] Unit tests with 90% coverage

**Test Requirements**:
```python
# tests/unit/test_mcp_framework.py
def test_mcp_tool_registration():
    """Verify tools can be registered and invoked"""
    
def test_mcp_health_check():
    """Verify health endpoint responds"""
    
def test_mcp_error_handling():
    """Verify graceful error handling"""
```

**Implementation Files**:
- `mcp/framework.py`: Base MCP server implementation
- `mcp/models.py`: Pydantic models for MCP protocol
- `mcp/__init__.py`: Package exports

---

#### Task 1.1.2: Genesys MCP Server
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 3 hours

**Description**: Wrap Genesys memory API as MCP tools for IronClaw.

**Acceptance Criteria**:
- [ ] MCP tools for CRUD operations on memory nodes
- [ ] Query tool for causal graph traversal
- [ ] Session management tools
- [ ] Integration tests with mock Genesys API

**MCP Tools**:
1. `create_memory_node(content, metadata)` → node_id
2. `create_causal_edge(from_id, to_id, relationship)` → edge_id
3. `query_memories(query, limit)` → List[MemoryNode]
4. `get_causal_chain(node_id)` → List[MemoryEdge]
5. `create_session(user_id)` → session_id

**Implementation Files**:
- `mcp/genesys_server.py`: Genesys MCP wrapper
- `mcp/genesys_client.py`: Client for testing

---

#### Task 1.1.3: Khoj MCP Server
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 3 hours

**Description**: Create MCP interface for Khoj RAG engine.

**Acceptance Criteria**:
- [ ] Document search tool
- [ ] Document upload tool
- [ ] Index management tools
- [ ] Integration with Khoj's web interface

**MCP Tools**:
1. `search_documents(query, max_results)` → List[SearchResult]
2. `upload_document(file_path, content_type)` → document_id
3. `list_documents()` → List[Document]
4. `delete_document(document_id)` → bool

**Implementation Files**:
- `mcp/khoj_server.py`: Khoj MCP wrapper
- `mcp/khoj_client.py`: HTTP client for Khoj API

---

#### Task 1.1.4: Docker Compose MCP Services
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Add MCP services to Docker Compose with proper resource limits.

**Acceptance Criteria**:
- [ ] MCP services defined in docker-compose.yml
- [ ] Resource limits enforced (CPU/Memory)
- [ ] Network configuration for service discovery
- [ ] Environment variable injection
- [ ] Health checks for all services

**docker-compose.yml Additions**:
```yaml
mcp-genesys:
  build: ./mcp
  container_name: mcp-genesys
  environment:
    - MCP_SERVER_TYPE=genesys
    - GENESYS_API_URL=http://genesys-memory:8000
  ports:
    - "8003:8000"
  depends_on:
    - genesys-memory
    - ironclaw-db
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M

mcp-khoj:
  build: ./mcp
  container_name: mcp-khoj
  environment:
    - MCP_SERVER_TYPE=khoj
    - KHOJ_API_URL=http://khoj:42110
  ports:
    - "8004:8000"
  depends_on:
    - khoj
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
```

**Implementation Files**:
- `docker-compose.yml`: Updated with MCP services
- `mcp/Dockerfile`: MCP server container

---

#### Task 1.1.5: MCP Integration Tests
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 4 hours

**Description**: End-to-end tests for MCP integration with IronClaw.

**Acceptance Criteria**:
- [ ] IronClaw can discover MCP servers
- [ ] IronClaw can invoke MCP tools
- [ ] Error handling for MCP failures
- [ ] Performance benchmarks
- [ ] Security validation (no data leakage)

**Test Scenarios**:
1. IronClaw queries Genesys via MCP
2. IronClaw searches Khoj via MCP
3. MCP server failure handling
4. Concurrent MCP requests

**Implementation Files**:
- `tests/integration/test_mcp_integration.py`
- `tests/e2e/test_ironclaw_mcp.py`

---

### 1.2 Aider/IronClaw Handoff Pipeline [MEDIUM PRIORITY]

#### Task 1.2.1: Task Schema Definition
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 2 hours

**Description**: Define standardized task format for agent communication.

**Acceptance Criteria**:
- [ ] JSON Schema for tasks
- [ ] Pydantic models for validation
- [ ] Task status enumeration
- [ ] Priority levels defined
- [ ] Schema documentation

**Task Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": {"type": "string", "format": "uuid"},
    "title": {"type": "string"},
    "description": {"type": "string"},
    "research_findings": {"type": "array", "items": {"type": "string"}},
    "requirements": {"type": "array", "items": {"type": "string"}},
    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
    "priority": {"enum": ["low", "medium", "high", "critical"]},
    "status": {"enum": ["pending", "in_progress", "completed", "failed"]},
    "created_at": {"type": "string", "format": "date-time"},
    "assigned_to": {"type": "string"}
  },
  "required": ["id", "title", "description"]
}
```

**Implementation Files**:
- `pipeline/task_schema.py`: Pydantic models
- `pipeline/schemas/task.json`: JSON Schema definition

---

#### Task 1.2.2: File Watcher Service
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 3 hours

**Description**: Monitor workspace for new task files and trigger Aider.

**Acceptance Criteria**:
- [ ] Watchdog-based file monitoring
- [ ] Filter for TASK*.md and TASK*.json files
- [ ] Debouncing for rapid changes
- [ ] Integration with Aider CLI
- [ ] Logging of all triggers

**Trigger Flow**:
1. New task file created in workspace
2. File watcher detects change
3. Parse task file
4. Validate task schema
5. Generate Aider prompt
6. Execute Aider with prompt
7. Update task status

**Implementation Files**:
- `pipeline/file_watcher.py`: Watchdog implementation
- `pipeline/task_parser.py`: Task file parser

---

#### Task 1.2.3: Agent Bridge Service
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 4 hours

**Description**: HTTP service for inter-agent communication.

**Acceptance Criteria**:
- [ ] REST API for task submission
- [ ] Task status polling endpoint
- [ ] Webhook notifications for task completion
- [ ] Authentication (API key)
- [ ] Rate limiting

**API Endpoints**:
- `POST /tasks`: Submit new task
- `GET /tasks/{id}`: Get task status
- `GET /tasks`: List tasks
- `POST /tasks/{id}/complete`: Mark task complete
- `POST /tasks/{id}/fail`: Mark task failed

**Implementation Files**:
- `pipeline/agent_bridge.py`: FastAPI service
- `pipeline/models.py`: Database models
- `pipeline/database.py`: SQLite persistence

---

#### Task 1.2.4: Integration Tests
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 3 hours

**Description**: Test the complete handoff pipeline.

**Acceptance Criteria**:
- [ ] End-to-end task flow test
- [ ] File watcher trigger test
- [ ] Aider execution test (mocked)
- [ ] Status update test
- [ ] Error handling test

**Implementation Files**:
- `tests/integration/test_pipeline.py`
- `tests/e2e/test_handoff.py`

---

### 1.3 Private Web Search (SearxNG) [MEDIUM PRIORITY]

#### Task 1.3.1: SearxNG Docker Configuration
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Add SearxNG container to Docker Compose.

**Acceptance Criteria**:
- [ ] SearxNG image configured
- [ ] Custom settings.yml for privacy
- [ ] Resource limits enforced
- [ ] Persistent volume for settings
- [ ] Health check endpoint

**Docker Configuration**:
```yaml
searxng:
  image: searxng/searxng:latest
  container_name: searxng
  volumes:
    - ./searxng/settings.yml:/etc/searxng/settings.yml:ro
    - searxng-data:/etc/searxng
  ports:
    - "8888:8080"
  environment:
    - SEARXNG_BASE_URL=http://localhost:8888/
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
  healthcheck:
    test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/healthz"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Implementation Files**:
- `docker-compose.yml`: Updated with SearxNG
- `searxng/settings.yml`: Custom configuration

---

#### Task 1.3.2: SearxNG Custom Settings
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 1 hour

**Description**: Configure SearxNG for privacy-first operation.

**Acceptance Criteria**:
- [ ] Disable telemetry
- [ ] Disable unsafe content
- [ ] Configure result caching
- [ ] Set default language to English
- [ ] Enable/disable specific search engines

**Implementation Files**:
- `searxng/settings.yml`: Configuration file

---

#### Task 1.3.3: IronClaw Search Integration
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Integrate SearxNG search with IronClaw agent.

**Acceptance Criteria**:
- [ ] IronClaw can call SearxNG API
- [ ] Results parsed and formatted
- [ ] Error handling for search failures
- [ ] Rate limiting respected

**API Integration**:
```python
class SearxNGClient:
    def __init__(self, base_url: str = "http://searxng:8080"):
        self.base_url = base_url
    
    async def search(self, query: str, engines: List[str] = None) -> List[SearchResult]:
        """Perform search and return results"""
        params = {
            "q": query,
            "format": "json",
            "engines": ",".join(engines) if engines else "google,bing,duckduckgo"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/search", params=params)
            return self._parse_results(response.json())
```

**Implementation Files**:
- `search/searxng_client.py`: HTTP client
- `search/models.py`: Result models

---

#### Task 1.3.4: Search Tests
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 2 hours

**Description**: Test SearxNG integration.

**Acceptance Criteria**:
- [ ] Unit tests for search client
- [ ] Integration tests with SearxNG
- [ ] Mock tests for offline testing
- [ ] Performance tests

**Implementation Files**:
- `tests/unit/test_searxng_client.py`
- `tests/integration/test_searxng.py`

---

## Phase 2: Security & Performance

### 2.1 Application-Level Encryption (AES-256) [HIGH PRIORITY]

#### Task 2.1.1: Encryption Module
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 4 hours

**Description**: Implement AES-256-GCM encryption with key management.

**Acceptance Criteria**:
- [ ] AES-256-GCM implementation
- [ ] Key derivation from passphrase
- [ ] Nonce generation
- [ ] Tag verification
- [ ] Key rotation support
- [ ] Unit tests with 95% coverage

**Implementation Details**:
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class AESEncryptor:
    def __init__(self, key: bytes):
        self.aesgcm = AESGCM(key)
    
    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext
    
    def decrypt(self, data: bytes) -> bytes:
        nonce = data[:12]
        ciphertext = data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)
```

**Implementation Files**:
- `security/encryption.py`: Core encryption logic
- `security/key_manager.py`: Key rotation

---

#### Task 2.1.2: Key Management System
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 3 hours

**Description**: Secure key storage and rotation.

**Acceptance Criteria**:
- [ ] Key stored in environment variable
- [ ] Key rotation without downtime
- [ ] Key derivation from master password
- [ ] Audit logging for key operations
- [ ] Key backup and restore

**Key Rotation Flow**:
1. Generate new key
2. Re-encrypt all data with new key
3. Update key in environment
4. Backup old key for rollback

**Implementation Files**:
- `security/key_manager.py`: Key management
- `security/migrations/`: Data migration scripts

---

#### Task 2.1.3: Database Encryption Integration
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 4 hours

**Description**: Integrate encryption with PostgreSQL and Khoj.

**Acceptance Criteria**:
- [ ] Transparent column-level encryption
- [ ] Encrypted backups
- [ ] Migration from unencrypted to encrypted
- [ ] Performance benchmarking

**PostgreSQL Configuration**:
```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypted column example
CREATE TABLE encrypted_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encrypted_content BYTEA NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Encryption/decryption functions
CREATE FUNCTION encrypt_data(data TEXT, key TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, key);
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION decrypt_data(data BYTEA, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(data, key);
END;
$$ LANGUAGE plpgsql;
```

**Implementation Files**:
- `security/migrations/001_add_encryption.sql`
- `security/postgres_encryptor.py`: SQLAlchemy integration

---

#### Task 2.1.4: Encryption Tests
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 3 hours

**Description**: Comprehensive encryption testing.

**Acceptance Criteria**:
- [ ] Unit tests for encryption/decryption
- [ ] Integration tests with database
- [ ] Key rotation tests
- [ ] Performance tests
- [ ] Security audit tests

**Test Cases**:
1. Encrypt/decrypt cycle
2. Wrong key decryption
3. Tampered ciphertext
4. Key rotation
5. Large data encryption

**Implementation Files**:
- `tests/unit/test_encryption.py`
- `tests/integration/test_encryption_db.py`
- `tests/security/test_key_management.py`

---

### 2.2 Semantic Model Routing [HIGH PRIORITY]

#### Task 2.2.1: Semantic Classifier
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 4 hours

**Description**: Classify requests to determine optimal model.

**Acceptance Criteria**:
- [ ] Code detection (regex + heuristics)
- [ ] Simple query detection
- [ ] Complex reasoning detection
- [ ] Configurable thresholds
- [ ] Fallback to default model

**Classification Rules**:
```python
class SemanticClassifier:
    def classify(self, messages: List[Message]) -> ModelType:
        last_message = messages[-1].content
        
        # Code detection
        if self._is_code_request(last_message):
            return ModelType.CODE
        
        # Simple query detection (short, factual)
        if len(last_message.split()) < 20 and self._is_factual(last_message):
            return ModelType.FAST
        
        # Complex reasoning (long, multi-step)
        if len(last_message.split()) > 100 or self._requires_reasoning(last_message):
            return ModelType.COMPLEX
        
        return ModelType.DEFAULT
    
    def _is_code_request(self, text: str) -> bool:
        code_patterns = [
            r'```[\s\S]*```',  # Code blocks
            r'def\s+\w+\(',    # Python functions
            r'class\s+\w+',    # Class definitions
            r'function\s+\w+', # JS functions
            r'const\s+\w+',    # JS const
        ]
        return any(re.search(p, text) for p in code_patterns)
```

**Implementation Files**:
- `proxy/classifier.py`: Semantic classification
- `proxy/models.py`: Model type definitions

---

#### Task 2.2.2: Multi-Endpoint Router
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 3 hours

**Description**: Route requests to appropriate LLM endpoints.

**Acceptance Criteria**:
- [ ] Multiple endpoint support
- [ ] Health checking for endpoints
- [ ] Load balancing (optional)
- [ ] Fallback mechanism
- [ ] Configuration via YAML

**Configuration**:
```yaml
# proxy/config.yaml
models:
  code:
    name: "qwen2.5-coder-7b"
    endpoint: "http://host.docker.internal:8000/v1/chat/completions"
    priority: 1
  
  fast:
    name: "llama-3-8b-instruct"
    endpoint: "http://host.docker.internal:8002/v1/chat/completions"
    priority: 2
  
  complex:
    name: "claude-3.5-sonnet"
    endpoint: "http://host.docker.internal:8003/v1/chat/completions"
    priority: 3

routing:
  default_model: "code"
  fallback_model: "fast"
  timeout_ms: 30000
```

**Implementation Files**:
- `proxy/router.py`: Request routing
- `proxy/config.yaml`: Model configuration

---

#### Task 2.2.3: Router Integration with Proxy
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Integrate semantic routing into existing proxy.

**Acceptance Criteria**:
- [ ] Seamless integration with existing proxy
- [ ] Backward compatibility
- [ ] A/B testing support
- [ ] Metrics collection

**Implementation Files**:
- `proxy/proxy.py`: Updated with routing

---

#### Task 2.2.4: Routing Tests
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 3 hours

**Description**: Test semantic routing.

**Acceptance Criteria**:
- [ ] Unit tests for classifier
- [ ] Integration tests with multiple endpoints
- [ ] Fallback tests
- [ ] Performance tests

**Test Scenarios**:
1. Code request → Code model
2. Simple question → Fast model
3. Complex analysis → Complex model
4. Endpoint failure → Fallback
5. Mixed content → Appropriate model

**Implementation Files**:
- `tests/unit/test_classifier.py`
- `tests/unit/test_router.py`
- `tests/integration/test_routing.py`

---

### 2.3 Cross-Session KV Caching [MEDIUM PRIORITY]

#### Task 2.3.1: Cache Implementation
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 4 hours

**Description**: Implement in-memory KV cache with LRU eviction.

**Acceptance Criteria**:
- [ ] LRU eviction policy
- [ ] TTL support
- [ ] Size limits
- [ ] Thread-safe operations
- [ ] Statistics tracking

**Implementation**:
```python
from collections import OrderedDict
import threading
import time

class LRUCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return value
                else:
                    del self.cache[key]
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = (value, time.time())
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
```

**Implementation Files**:
- `cache/kv_store.py`: Cache implementation

---

#### Task 2.3.2: State Serialization
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Serialize/deserialize LLM states for caching.

**Acceptance Criteria**:
- [ ] Support for multiple serialization formats
- [ ] Compression for large states
- [ ] Integrity checks
- [ ] Format versioning

**Implementation Files**:
- `cache/serializer.py`: State serialization

---

#### Task 2.3.3: Cache Persistence
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Persist cache to disk for container restarts.

**Acceptance Criteria**:
- [ ] Save cache to file
- [ ] Load cache on startup
- [ ] Incremental saves
- [ ] Corruption recovery

**Implementation Files**:
- `cache/persistence.py`: Disk persistence

---

#### Task 2.3.4: Cache Integration with Proxy
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 2 hours

**Description**: Integrate cache with LLM proxy.

**Acceptance Criteria**:
- [ ] Cache key generation
- [ ] Cache invalidation
- [ ] Cache warming
- [ ] Metrics integration

**Implementation Files**:
- `proxy/proxy.py`: Cache integration

---

#### Task 2.3.5: Cache Tests
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Test KV caching.

**Acceptance Criteria**:
- [ ] Unit tests for cache operations
- [ ] Integration tests with proxy
- [ ] Persistence tests
- [ ] Performance tests

**Implementation Files**:
- `tests/unit/test_cache.py`
- `tests/integration/test_cache_proxy.py`

---

## Phase 3: Developer Experience

### 3.1 IronSilo Terminal Dashboard (TUI) [MEDIUM PRIORITY]

#### Task 3.1.1: TUI Framework Setup
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 3 hours

**Description**: Set up Textual TUI framework.

**Acceptance Criteria**:
- [ ] Textual installed and configured
- [ ] Main dashboard layout
- [ ] Theme configuration
- [ ] Keyboard navigation
- [ ] Responsive design

**Implementation Files**:
- `tui/__init__.py`: Package exports
- `tui/app.py`: Main TUI application
- `tui/theme.py`: Custom theme

---

#### Task 3.1.2: Container Status Widget
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Widget showing Docker container status.

**Acceptance Criteria**:
- [ ] Real-time container status
- [ ] Health indicators
- [ ] Resource usage bars
- [ ] Restart action

**Implementation Files**:
- `tui/widgets/container_status.py`: Container widget

---

#### Task 3.1.3: Resource Monitor Widget
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 3 hours

**Description**: Real-time resource usage visualization.

**Acceptance Criteria**:
- [ ] CPU usage graph
- [ ] Memory usage graph
- [ ] Network I/O
- [ ] Historical data

**Implementation Files**:
- `tui/widgets/resource_monitor.py`: Resource widget

---

#### Task 3.1.4: Log Viewer Widget
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 2 hours

**Description**: Container log streaming.

**Acceptance Criteria**:
- [ ] Log tailing for all containers
- [ ] Filter by container/level
- [ ] Search functionality
- [ ] Export capability

**Implementation Files**:
- `tui/widgets/log_viewer.py`: Log widget

---

#### Task 3.1.5: TUI Entry Point
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 1 hour

**Description**: CLI command to launch TUI.

**Acceptance Criteria**:
- [ ] `ironsilo monitor` command
- [ ] Command-line arguments
- [ ] Help text
- [ ] Error handling

**Implementation Files**:
- `tui/cli.py`: CLI entry point
- `setup.py` or `pyproject.toml`: Package configuration

---

#### Task 3.1.6: TUI Tests
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 2 hours

**Description**: Test TUI components.

**Acceptance Criteria**:
- [ ] Unit tests for widgets
- [ ] Integration tests
- [ ] Snapshot tests
- [ ] Accessibility tests

**Implementation Files**:
- `tests/unit/test_tui_widgets.py`
- `tests/integration/test_tui.py`

---

### 3.2 Interactive Setup Wizard [MEDIUM PRIORITY]

#### Task 3.2.1: LLM Host Detection
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Auto-detect installed LLM hosts.

**Acceptance Criteria**:
- [ ] Detect LM Studio
- [ ] Detect Ollama
- [ ] Detect Lemonade
- [ ] Verify port availability
- [ ] Version detection

**Detection Logic**:
```python
def detect_llm_hosts() -> List[LLMHost]:
    hosts = []
    
    # Check LM Studio
    if is_port_open(8000):
        if check_lm_studio_api():
            hosts.append(LLMHost.LM_STUDIO)
    
    # Check Ollama
    if is_port_open(11434):
        if check_ollama_api():
            hosts.append(LLMHost.OLLAMA)
    
    # Check Lemonade
    if is_port_open(8000):
        if check_lemonade_api():
            hosts.append(LLMHost.LEMONADE)
    
    return hosts
```

**Implementation Files**:
- `setup/detector.py`: LLM detection

---

#### Task 3.2.2: Interactive Prompts
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: User prompts for configuration.

**Acceptance Criteria**:
- [ ] LLM host selection
- [ ] Port configuration
- [ ] Memory limits
- [ ] IronClaw enable/disable
- [ ] Validation

**Implementation Files**:
- `setup/wizard.py`: Interactive wizard

---

#### Task 3.2.3: Configuration Generator
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 1 hour

**Description**: Generate .env file from configuration.

**Acceptance Criteria**:
- [ ] .env file generation
- [ ] Backup existing .env
- [ ] Template support
- [ ] Validation

**Implementation Files**:
- `setup/configurator.py`: Config generation

---

#### Task 3.2.4: Start Script Integration
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 1 hour

**Description**: Integrate wizard with start scripts.

**Acceptance Criteria**:
- [ ] `--interactive` flag
- [ ] Auto-run if no .env
- [ ] Skip wizard option

**Implementation Files**:
- `Start_Workspace.sh`: Updated with wizard
- `Start_Workspace.bat`: Windows version

---

#### Task 3.2.5: Wizard Tests
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 2 hours

**Description**: Test setup wizard.

**Acceptance Criteria**:
- [ ] Unit tests for detection
- [ ] Integration tests
- [ ] Mock user input tests

**Implementation Files**:
- `tests/unit/test_detector.py`
- `tests/unit/test_wizard.py`
- `tests/integration/test_setup.py`

---

## CI/CD & Infrastructure

### Task CI.1: GitHub Actions CI
**Status**: TODO  
**Priority**: HIGH  
**Estimate**: 2 hours

**Description**: Set up continuous integration.

**Acceptance Criteria**:
- [ ] Test workflow on PR
- [ ] Lint and format checks
- [ ] Docker build validation
- [ ] Coverage reporting

**Implementation Files**:
- `.github/workflows/ci.yml`: CI pipeline

---

### Task CI.2: GitHub Actions CD
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 2 hours

**Description**: Set up continuous deployment.

**Acceptance Criteria**:
- [ ] Docker image publishing
- [ ] Release automation
- [ ] Version tagging
- [ ] Changelog generation

**Implementation Files**:
- `.github/workflows/cd.yml`: CD pipeline

---

### Task CI.3: Pre-commit Hooks
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 1 hour

**Description**: Set up pre-commit hooks for code quality.

**Acceptance Criteria**:
- [ ] Black formatting
- [ ] isort imports
- [ ] flake8 linting
- [ ] mypy type checking

**Implementation Files**:
- `.pre-commit-config.yaml`: Hook configuration

---

## Documentation

### Task DOC.1: API Documentation
**Status**: TODO  
**Priority**: MEDIUM  
**Estimate**: 3 hours

**Description**: Generate API documentation.

**Acceptance Criteria**:
- [ ] OpenAPI/Swagger spec
- [ ] Auto-generated from code
- [ ] Examples
- [ ] Authentication docs

**Implementation Files**:
- `docs/api/openapi.json`: OpenAPI spec
- `docs/api/README.md`: API documentation

---

### Task DOC.2: Architecture Documentation
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 2 hours

**Description**: Update architecture documentation.

**Acceptance Criteria**:
- [ ] Component diagrams
- [ ] Data flow diagrams
- [ ] Deployment diagrams
- [ ] Security architecture

**Implementation Files**:
- `docs/ARCHITECTURE.md`: Updated architecture

---

### Task DOC.3: User Guides
**Status**: TODO  
**Priority**: LOW  
**Estimate**: 2 hours

**Description**: Update user manuals.

**Acceptance Criteria**:
- [ ] Setup wizard guide
- [ ] TUI guide
- [ ] Troubleshooting
- [ ] FAQ

**Implementation Files**:
- `docs/SIMPLE_MANUAL.md`: Updated manual
- `docs/ADVANCED_MANUAL.md`: Updated advanced guide

---

## Summary Statistics

| Phase | Tasks | Estimated Hours |
|-------|-------|-----------------|
| Phase 1 | 13 | 37 |
| Phase 2 | 12 | 34 |
| Phase 3 | 11 | 23 |
| CI/CD | 3 | 5 |
| Documentation | 3 | 7 |
| **Total** | **42** | **106** |

---

## Sprint Planning

### Sprint 1 (Week 1): Foundation & MCP
- Task 1.1.1: MCP Framework
- Task 1.1.2: Genesys MCP Server
- Task 1.1.3: Khoj MCP Server
- Task 1.1.4: Docker Compose MCP
- Task 1.1.5: MCP Integration Tests
- Task CI.1: GitHub Actions CI
- Task CI.3: Pre-commit Hooks

### Sprint 2 (Week 2): Pipeline & Encryption
- Task 1.2.1: Task Schema
- Task 1.2.2: File Watcher
- Task 1.2.3: Agent Bridge
- Task 1.2.4: Pipeline Tests
- Task 2.1.1: Encryption Module
- Task 2.1.2: Key Management

### Sprint 3 (Week 3): Routing & Cache
- Task 2.1.3: Database Encryption
- Task 2.1.4: Encryption Tests
- Task 2.2.1: Semantic Classifier
- Task 2.2.2: Multi-Endpoint Router
- Task 2.2.3: Router Integration
- Task 2.2.4: Routing Tests
- Task 2.3.1: Cache Implementation
- Task 2.3.2: State Serialization
- Task 2.3.3: Cache Persistence

### Sprint 4 (Week 4): Search & TUI
- Task 1.3.1: SearxNG Docker
- Task 1.3.2: SearxNG Settings
- Task 1.3.3: IronClaw Search
- Task 1.3.4: Search Tests
- Task 3.1.1: TUI Framework
- Task 3.1.2: Container Widget
- Task 3.1.3: Resource Widget

### Sprint 5 (Week 5): Wizard & Polish
- Task 3.1.4: Log Widget
- Task 3.1.5: TUI Entry Point
- Task 3.1.6: TUI Tests
- Task 3.2.1: LLM Detection
- Task 3.2.2: Interactive Prompts
- Task 3.2.3: Config Generator
- Task 3.2.4: Start Script Integration
- Task 3.2.5: Wizard Tests

### Sprint 6 (Week 6): Documentation & Release
- Task DOC.1: API Documentation
- Task DOC.2: Architecture Documentation
- Task DOC.3: User Guides
- Task CI.2: GitHub Actions CD
- Full Integration Testing
- Performance Optimization
- Release Preparation

---

## Definition of Done

For each task to be considered complete, it must satisfy:

1. **Code Complete**: All implementation files written
2. **Tests Passing**: 100% of acceptance criteria tests pass
3. **Coverage**: Meets coverage threshold (see Section 5.2)
4. **Documentation**: API docs and user guides updated
5. **Security**: No hardcoded secrets, inputs sanitized
6. **Performance**: No regression, meets resource limits
7. **Review**: Code reviewed and approved

---

*This backlog is a living document. Update as tasks are completed or requirements change.*
