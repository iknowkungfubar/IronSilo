# IronSilo v3.0.0 Pivot - Issues & Improvements

## Source of Truth Document
This document tracks all issues and improvements required to achieve the v3.0.0 True Silo architecture vision.

---

## Current State Summary (v2.1.0)

| Metric | Value |
|--------|-------|
| Tests | 789 passed |
| Coverage | 83% |
| Architecture | True Silo with Traefik API Gateway |
| Port Exposure | Single port 8080 |

---

## Phase 1 COMPLETED Items (v2.1.0)

- [x] Traefik API Gateway with single port 8080
- [x] All services behind Traefik with X-Silo-Auth middleware
- [x] Proxy timeout reduced from 300s to 60s
- [x] Retry logic with exponential backoff
- [x] Input sanitization for chat completions

---

## Phase 2: Inference Isolation (v3.0.0 Priority)

### Issues

1. **LLM runs on host bare-metal** - Proxy connects to `host.docker.internal:8000`
   - Breaking the True Silo principle
   - Host LLM not containerized

2. **No GPU passthrough configuration** - Docker compose lacks hardware acceleration
   - Windows WSL2 GPU flags needed
   - Linux NVIDIA needs nvidia-container-toolkit
   - Linux AMD needs /dev/kfd and /dev/dri

3. **Resource limit paradox** - 4GB RAM cap may be too restrictive if LLM is containerized
   - Need separate limits: LLM (unbounded/greatful) vs Proxy/RAG/Memory (4GB)

### Improvements

- [ ] Add `inference-engine` service to docker-compose.yml (Ollama container)
- [ ] Configure GPU passthrough with deploy.resources.reservations.devices
- [ ] Update Proxy to point to `http://inference-engine:8000` on internal network
- [ ] Document hardware requirements per platform

---

## Phase 3: PDA Migration (v3.0.0 Priority)

### Issues

1. **IronClaw WASM on host** - Violates True Silo principle
   - Currently runs as native binary on host machine
   - Not isolated in Docker network

2. **OpenHands not integrated** - v3.0.0 plan recommends containerized OpenHands
   - Current swarm/orchestrator.py is partial implementation
   - No FastAPI frontend for PDA interface

### Improvements

- [ ] Deprecate IronClaw in documentation
- [ ] Integrate containerized OpenHands or build FastAPI frontend for swarm
- [ ] Expose PDA at /pda route via Traefik
- [ ] Connect PDA to SearXNG and Browser Node internally

---

## Phase 4: Documentation Alignment

### Issues

1. **SYSTEM_DESIGN.md references IronClaw** - Should reference OpenHands/PDA
2. **Route mapping outdated** - Some routes don't match current docker-compose labels
3. **Architecture diagram shows old stack** - Needs update to True Silo topology

### Improvements

- [ ] Update SYSTEM_DESIGN.md to v3.0.0 architecture
- [ ] Update README.md route mapping section
- [ ] Update ROADMAP.md to reflect completed phases
- [ ] Create architecture diagrams for True Silo

---

## Security Improvements (Ongoing)

### Issues

1. **CORS origins wildcard** - security/middleware.py allows all origins in dev
2. **No secret scanning** - .pre-commit-config.yaml lacks gitleaks
3. **Request ID not propagated** - All services should share request IDs

### Improvements

- [ ] Add strict CORS validation for production
- [ ] Add gitleaks to pre-commit hooks
- [ ] Add X-Request-ID propagation to all services
- [ ] Add audit logging for memory operations

---

## Reliability Improvements

### Issues

1. **No circuit breaker on proxy** - Failed upstream requests don't fail fast
2. **No connection pooling** - Each request creates new httpx client
3. **Swarm service lacks healthcheck** - docker-compose.yml missing healthcheck

### Improvements

- [ ] Implement circuit breaker pattern
- [ ] Add httpx connection pooling
- [ ] Add healthcheck to swarm-service
- [ ] Add restart policies to all services

---

## Testing Improvements

### Issues

1. **Async tests timeout** - swarm_harness_worker and orchestrator tests hang
2. **MCP coverage low** - 65-68% due to integration testing gaps
3. **genesys/app.py coverage** - 65% with database pooling untested

### Improvements

- [ ] Fix async test mocking for swarm modules
- [ ] Add MCP integration tests with Docker stack
- [ ] Add database connection pooling tests
- [ ] Achieve 90%+ coverage on all installed modules

---

## Execution Plan

### Step 1: Fix tests (Current)
```bash
pytest tests/ -q  # Must pass before proceeding
```

### Step 2: Update documentation
- Update CHANGELOG.md with v2.1.0 completed items
- Update ROADMAP.md with v3.0.0 priorities
- Update SYSTEM_DESIGN.md architecture diagrams

### Step 3: Implement Phase 2 (Inference Isolation)
- Add Ollama/Inference container
- Configure GPU passthrough
- Update proxy endpoint

### Step 4: Implement Phase 3 (PDA Migration)
- Deprecate IronClaw references
- Add OpenHands or FastAPI frontend
- Route via Traefik

---

*Document Status: ACTIVE*
*Last Updated: 2026-04-29*
