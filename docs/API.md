# IronSilo API Documentation

## Version: 2.1.0

This document describes the API endpoints exposed through the Traefik API Gateway on port 8080.

## Base URL

```
http://localhost:8080
```

## Authentication

All API endpoints (except `/health`, `/metrics`) require authentication via the `X-API-Key` header:

```
X-API-Key: your-api-key
```

## Services

### LLM Proxy (`/api/v1`)

The LLMLingua-based context compression proxy providing OpenAI-compatible API.

#### POST `/api/v1/chat/completions`

OpenAI-compatible chat completions endpoint with automatic prompt compression.

**Request:**
```json
{
  "model": "qwen2.5-coder-7b",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, world!"}
  ],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "qwen2.5-coder-7b",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I assist you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 30,
    "total_tokens": 55
  }
}
```

#### GET `/api/v1/health`

Health check endpoint for the LLM proxy.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "uptime_seconds": 3600
}
```

#### GET `/api/v1/metrics`

Prometheus metrics endpoint.

**Response:** Text format Prometheus metrics including:
- `llm_proxy_requests_total` - Total requests
- `llm_proxy_compression_ratio` - Average compression ratio
- `circuit_breaker_state` - Current circuit breaker state

#### POST `/api/v1/key/rotate`

Rotate the API key at runtime (requires `KEY_ROTATION_ENABLED=true`).

**Request:**
```json
{
  "current_key": "old-key",
  "new_key": "new-key"
}
```

**Response:**
```json
{
  "success": true,
  "message": "API key rotated successfully"
}
```

---

### Genesys Memory (`/genesys`)

Causal graph memory system with PostgreSQL persistence.

#### POST `/genesys/memories`

Create a new memory node.

**Request:**
```json
{
  "content": "User prefers dark mode UI",
  "memory_type": "preference",
  "importance": 0.8,
  "tags": ["ui", "dark-mode"]
}
```

**Response:**
```json
{
  "id": "mem-uuid-123",
  "content": "User prefers dark mode UI",
  "memory_type": "preference",
  "importance": 0.8,
  "tags": ["ui", "dark-mode"],
  "created_at": "2026-04-30T12:00:00Z",
  "metadata": {}
}
```

#### GET `/genesys/memories`

List all memory nodes with optional filtering.

**Query Parameters:**
- `limit` (int, default 100) - Maximum results
- `offset` (int, default 0) - Pagination offset
- `memory_type` (string) - Filter by type

#### GET `/genesys/memories/{id}`

Get a specific memory node by ID.

#### PUT `/genesys/memories/{id}`

Update a memory node.

**Request:**
```json
{
  "content": "Updated content",
  "importance": 0.9
}
```

#### DELETE `/genesys/memories/{id}`

Delete a memory node.

#### POST `/genesys/edges`

Create a causal edge between two memory nodes.

**Request:**
```json
{
  "source_id": "mem-uuid-123",
  "target_id": "mem-uuid-456",
  "relationship": "leads_to",
  "strength": 0.95
}
```

#### GET `/genesys/edges`

List all edges with optional filtering.

#### GET `/genesys/sessions`

List all sessions.

#### POST `/genesys/sessions`

Create a new session.

**Request:**
```json
{
  "session_type": "research",
  "metadata": {"topic": "LLM optimization"}
}
```

#### GET `/genesys/metrics`

Prometheus metrics for the memory system.

---

### Khoj Wiki (`/khoj`)

Private RAG wiki engine for document search and retrieval.

#### Web UI

Access Khoj at `http://localhost:8080/khoj` for the web interface.

#### API (Internal)

Khoj provides internal API endpoints for:
- Document upload
- Semantic search
- Index management

---

### SearxNG Search (`/search`)

Privacy-respecting web search.

#### GET `/search?q=query`

Perform a web search.

**Query Parameters:**
- `q` (string, required) - Search query
- `engines` (string) - Comma-separated engine list
- `format` (string, default `json`) - Response format (json, html, csv)

---

### Browser Swarm (`/swarm`)

Autonomous browser control via headless Chrome.

#### GET `/swarm/status`

Get swarm service status.

**Response:**
```json
{
  "status": "running",
  "active_tasks": 3,
  "completed_tasks": 47,
  "failed_tasks": 2
}
```

#### GET `/swarm/history`

Get task history.

**Query Parameters:**
- `limit` (int, default 50) - Maximum history items

#### GET `/swarm/metrics`

Prometheus metrics for swarm operations.

#### WebSocket `/ws/swarm`

Real-time swarm action stream.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/swarm');
```

**Messages (Server -> Client):**
```json
{
  "type": "action",
  "action": "navigate",
  "url": "https://example.com",
  "timestamp": "2026-04-30T12:00:00Z"
}
```

**Messages (Client -> Server):**
```json
{
  "type": "command",
  "command": "browse",
  "params": {
    "url": "https://example.com",
    "action": "click",
    "selector": "#submit-button"
  }
}
```

---

### MCP Servers

#### GET `/mcp/genesys/health`

Health check for Genesys MCP server.

#### GET `/mcp/khoj/health`

Health check for Khoj MCP server.

---

## Error Responses

All endpoints may return error responses in this format:

```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "invalid_request_error",
    "code": "rate_limit_exceeded"
  }
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
| 502 | Bad Gateway |
| 503 | Service Unavailable |

---

## Rate Limiting

Rate limits are applied per API key:

- **Default:** 60 requests per minute
- **Headers Returned:**
  - `X-RateLimit-Limit` - Maximum requests per window
  - `X-RateLimit-Remaining` - Remaining requests in current window
  - `X-RateLimit-Reset` - Unix timestamp when the window resets

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IRONSILO_API_KEY` | (none) | API authentication key |
| `RATE_LIMIT_REQUESTS` | 60 | Requests per minute |
| `LLM_ENDPOINT` | `http://host.docker.internal:8000/v1/chat/completions` | Upstream LLM |
| `KEY_ROTATION_ENABLED` | `false` | Enable runtime key rotation |

---

## OpenAPI Specification

The OpenAPI specification is available at `/api/v1/openapi.json` when the proxy is running.

---

*Last updated: 2026-04-30*
*Generated by: Autonomous Swarm*