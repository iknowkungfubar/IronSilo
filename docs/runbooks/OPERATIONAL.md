# IronSilo Runbooks

Operational runbooks for common failure scenarios.

---

## 1. Service Health Checks

### Check all services are healthy
```bash
docker compose ps
```

### Check specific service health
```bash
docker compose exec traefik curl http://localhost:8080/api/ping
docker compose exec llm-proxy curl http://localhost:8001/health
docker compose exec genesys-memory curl http://localhost:8000/health
docker compose exec swarm-service curl http://localhost:8095/health
```

---

## 2. Circuit Breaker Issues

### Check circuit breaker status
```bash
curl http://localhost:8080/api/v1/metrics | jq .circuit_breaker
```

### Reset circuit breaker (restart proxy)
```bash
docker compose restart llm-proxy
```

---

## 3. Memory Issues

### Check genesys memory count
```bash
curl http://localhost:8080/genesys/metrics | jq .memories_count
```

### Clear all memories (if needed)
```bash
curl -X DELETE http://localhost:8080/genesys/api/v1/memories/clear
```

---

## 4. Swarm Service Issues

### Check swarm WebSocket connections
```bash
curl http://localhost:8080/swarm/metrics | jq .connected_clients
```

### View swarm action history
```bash
curl http://localhost:8080/swarm/history | jq .history
```

---

## 5. Rate Limiting

### Check rate limit headers
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
```

### Adjust rate limit
```bash
export RATE_LIMIT_REQUESTS=120  # Double the limit
docker compose restart llm-proxy
```

---

## 6. Common Errors

### "Connection refused" errors
1. Check Docker containers are running: `docker compose ps`
2. Restart services: `docker compose restart`
3. Check logs: `docker compose logs --tail=100`

### "Proxy timeout" errors
1. Check upstream LLM is running
2. Check circuit breaker status
3. Adjust timeout: `export UPSTREAM_TIMEOUT=120`

### "Memory full" errors
1. Check disk space: `df -h`
2. Clean up old containers: `docker compose down && docker system prune`
3. Restart services: `docker compose up -d`

---

*Document Status: ACTIVE*
*Last Updated: 2026-04-29*