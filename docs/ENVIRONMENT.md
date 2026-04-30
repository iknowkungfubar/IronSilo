# IronSilo Environment Variables

Complete reference for all environment variables used in IronSilo.

---

## Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `IRONSILO_API_KEY` | (empty) | API key for authenticating requests. If set, all requests must include this key. |
| `ENVIRONMENT` | `development` | Environment mode: `development` or `production`. Affects CORS and security settings. |
| `CORS_ORIGINS` | (empty) | Comma-separated list of allowed CORS origins for production. |

---

## LLM Proxy

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_ENDPOINT` | `http://host.docker.internal:8000/v1/chat/completions` | Upstream LLM API endpoint |
| `COMPRESSION_THRESHOLD` | `1000` | Minimum content length to trigger compression (characters) |
| `COMPRESSION_RATE` | `0.6` | Target compression ratio (0.0-1.0) |
| `PROXY_VERSION` | `2.0.0` | Version string for the proxy service |
| `RETRY_MAX_ATTEMPTS` | `3` | Maximum retry attempts for failed upstream requests |
| `RETRY_BASE_DELAY` | `1.0` | Base delay for exponential backoff (seconds) |
| `RETRY_MAX_DELAY` | `10.0` | Maximum delay between retries (seconds) |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Number of failures before circuit opens |
| `CIRCUIT_BREAKER_TIMEOUT` | `30.0` | Time before attempting to close circuit (seconds) |

---

## Database (PostgreSQL)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `ironsilo_vault` | Database name |
| `POSTGRES_USER` | `silo_admin` | Database user |
| `POSTGRES_PASSWORD` | (required) | Database password. Must be set in `.env` file. |
| `DATABASE_URL` | (auto) | Full connection string. Auto-built from other DB variables. |

---

## Genesys Memory

| Variable | Default | Description |
|----------|---------|-------------|
| `GENESYS_BACKEND` | `postgres` | Backend type: `postgres` or `memory` |
| `GENESYS_EMBEDDER` | `local` | Embedding backend: `local` or `api` |
| `GENESYS_URL` | `http://genesys-memory:8000` | Internal URL for Genesys service |

---

## Swarm Service

| Variable | Default | Description |
|----------|---------|-------------|
| `CDP_URL` | `ws://browser-node:9222` | Chrome DevTools Protocol WebSocket URL |
| `OPENAI_API_BASE` | `http://llm-proxy:8001/api/v1` | OpenAI-compatible API base URL |
| `GENESYS_URL` | `http://genesys-memory:8000` | Genesys memory service URL |

---

## Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_REQUESTS` | `60` | Maximum requests per minute per client |
| `MAX_REQUEST_SIZE` | `10485760` | Maximum request size in bytes (10MB) |

---

## Security

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | (from `IRONSILO_API_KEY`) | Alternative API key source |
| `SECRET_KEY` | (auto-generated) | Secret key for encryption |

---

## Example .env File

```bash
# Core
IRONSILO_API_KEY=your-secret-api-key-here
ENVIRONMENT=production
CORS_ORIGINS=https://app.example.com,https://admin.example.com

# Database
POSTGRES_DB=ironsilo_vault
POSTGRES_USER=silo_admin
POSTGRES_PASSWORD=your-secure-password-here

# LLM
LLM_ENDPOINT=http://host.docker.internal:8000/v1/chat/completions
COMPRESSION_THRESHOLD=1000
COMPRESSION_RATE=0.6
RETRY_MAX_ATTEMPTS=3

# Rate Limiting
RATE_LIMIT_REQUESTS=60
MAX_REQUEST_SIZE=10485760
```

---

*Document Status: ACTIVE*
*Last Updated: 2026-04-29*