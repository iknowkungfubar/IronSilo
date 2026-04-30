# ADR-001: True Silo Architecture with Traefik API Gateway

## Status
Accepted

## Date
2026-04-28

## Context
IronSilo started as a collection of independent services with multiple exposed ports. This created security concerns:
- Each service had its own port exposed
- Authentication was inconsistent across services
- Network topology was complex and hard to secure

We needed a solution that:
1. Provided a single entry point for all services
2. Enforced authentication at the gateway level
3. Maintained service isolation while simplifying client connections
4. Supported WebSocket connections for real-time features

## Decision
We adopted a **True Silo Architecture** using Traefik as the API Gateway:

```
Client → Traefik (port 8080) → Internal Services
```

All internal services are now hidden behind Traefik with:
- Single port exposure (8080)
- X-Silo-Auth header middleware for authentication
- Path-based routing to internal services

## Implementation Details

### Routing Configuration
- `/api/v1` → LLM Proxy (port 8001)
- `/khoj` → Khoj Wiki (port 42110)
- `/genesys` → Genesys Memory (port 8000)
- `/mcp/*` → MCP Servers (port 8000)
- `/search` → SearxNG (port 8080)
- `/swarm` → Swarm Service (port 8095)
- `/ws/swarm` → Swarm WebSocket (port 8095)

### Security
- Traefik middleware validates `X-Silo-Auth` header
- Internal services do not expose ports directly
- CORS configured at gateway level

### Trade-offs

**Pros:**
- Single entry point simplifies client integration
- Centralized authentication and monitoring
- Better network isolation
- Simplified firewall rules

**Cons:**
- Traefik adds a potential single point of failure
- Additional latency (minimal, ~1ms)
- More complex local development debugging

## Consequences

### Positive
- Services are no longer directly accessible from the network
- Authentication is enforced consistently
- Easier to add new services behind the gateway

### Negative
- Traefik configuration must be kept in sync with service changes
- Debugging requires tracing through the gateway

## Related Decisions
- ADR-002: Circuit Breaker Pattern for Proxy Reliability
- ADR-003: Graceful Shutdown for Swarm Services

---

*Document Status: ACTIVE*
*Last Updated: 2026-04-29*