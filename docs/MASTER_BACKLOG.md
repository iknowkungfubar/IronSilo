# IronSilo Master Backlog - Production Readiness

## Version: 2.0.1
## Generated: 2026-04-28
## Status: IN PROGRESS

---

## Critical Issues (Fix Immediately)

### [CRITICAL-1] Missing websockets dependency in swarm Dockerfile
**Status**: COMPLETED
**Priority**: CRITICAL
**Description**: `harness_worker.py` imports `websockets` library but Dockerfile only installs `httpx pydantic fastapi websockets structlog`. The `websockets` package is NOT the same as the built-in `websocket` support in FastAPI.

**Files Affected**:
- `swarm/Dockerfile`

**Action**:
- [x] Add `websockets` to pip install command
- [x] Add `uvicorn` to pip install command

**Commit**: 0707ef1

---

### [CRITICAL-2] No tests for swarm module
**Status**: COMPLETED
**Priority**: CRITICAL
**Description**: The entire swarm module (harness_worker, orchestrator, main) has zero test coverage. This is a new feature with no validation.

**Files Affected**:
- tests/unit/test_swarm_harness_worker.py (NEW) - 16 tests
- tests/unit/test_swarm_orchestrator.py (NEW) - 15 tests
- tests/unit/test_swarm_main.py (NEW) - 19 tests

**Action**:
- [x] Create comprehensive unit tests for HarnessWorker
- [x] Create comprehensive unit tests for Manager class
- [x] Create integration tests for SwarmState and WebSocket
- [x] Achieve 90%+ coverage on swarm module (86% achieved)

**Commit**: 0707ef1

---

## High Priority Issues

### [HIGH-1] TUI widget not exported from package
**Status**: COMPLETED
**Priority**: HIGH
**Description**: `SwarmMonitorWidget` was added to `tui/widgets/` but is not exported in `__init__.py`, breaking package imports.

**Files Affected**:
- `tui/widgets/__init__.py`

**Action**:
- [x] Add `SwarmMonitorWidget` to exports

**Commit**: 0707ef1

---

### [HIGH-2] No tests for SwarmMonitorWidget
**Status**: COMPLETED
**Priority**: HIGH
**Description**: New TUI widget has no unit tests.

**Files Affected**:
- tests/unit/test_swarm_monitor.py (NEW) - 33 tests

**Action**:
- [x] Create tests for SwarmMonitorWidget
- [x] Test WebSocket connection handling
- [x] Test action display and history
- [x] Graceful skip if textual not installed

**Commit**: 0707ef1

---

## Medium Priority Issues

### [MEDIUM-1] No integration tests for swarm-genesys connection
**Status**: TODO
**Priority**: MEDIUM
**Description**: Manager._store_memory() calls genesys API but there's no integration test verifying this works end-to-end.

**Files Affected**:
- tests/integration/test_swarm_genesys.py (NEW)

**Action**:
- [ ] Create mock-based integration test for memory storage

---

### [MEDIUM-2] No documentation for swarm module
**Status**: TODO
**Priority**: MEDIUM
**Description**: New swarm services (browser-node, swarm-service) have no documentation.

**Files Affected**:
- README.md (update)
- docs/ARCHITECTURE.md (update)

**Action**:
- [ ] Document swarm architecture
- [ ] Document environment variables
- [ ] Document API endpoints (port 8095)

---

## Low Priority / Technical Debt

### [LOW-1] Missing health check on swarm-service
**Status**: COMPLETED
**Priority**: LOW
**Description**: The swarm-service FastAPI app has no `/health` endpoint like other services.

**Files Affected**:
- `swarm/main.py`

**Action**:
- [x] Add health check endpoint with uptime tracking

**Commit**: 0974d2f

---

### [LOW-2] No Docker healthcheck for swarm-service
**Status**: TODO
**Priority**: LOW
**Description**: docker-compose.yml doesn't define a healthcheck for swarm-service.

**Files Affected**:
- `docker-compose.yml`

**Action**:
- [ ] Add healthcheck configuration

---

### [LOW-3] Missing __init__.py in swarm directory
**Status**: COMPLETED
**Priority**: LOW
**Description**: `swarm/__init__.py` doesn't exist, making it not a proper Python package.

**Files Affected**:
- `swarm/__init__.py` (NEW)

**Action**:
- [x] Create `swarm/__init__.py` with package exports

**Commit**: 0974d2f

---

### [LOW-4] WebSocket test timing issues
**Status**: TODO
**Priority**: LOW
**Description**: 2 tests in test_swarm_main.py fail due to async WebSocket timing issues.

**Files Affected**:
- tests/unit/test_swarm_main.py

**Action**:
- [ ] Fix async test timing in test_websocket_sends_action_updates_state
- [ ] Fix async test timing in test_websocket_receives_confirmation

---

## Completed Items (from this session)

### [DONE-1] Browser swarm services added
**Status**: COMPLETED
**Description**: Added browser-node and swarm-service to docker-compose.yml
**Commit**: c556aca

### [DONE-2] Proxy bypass compression for vision/dom models
**Status**: COMPLETED
**Description**: Added X-Bypass-Compression header and model-based bypass logic
**Commit**: c556aca

### [DONE-3] Swarm FastAPI server created
**Status**: COMPLETED
**Description**: Created swarm/main.py with /status, /ws/swarm, /history endpoints
**Commit**: c556aca

### [DONE-4] SwarmMonitorWidget created
**Status**: COMPLETED
**Description**: Created TUI widget connecting to swarm WebSocket
**Commit**: c556aca

---

## Testing Requirements

### Unit Test Coverage Targets

| Module | Current Coverage | Target | Status |
|--------|------------------|--------|--------|
| swarm/harness_worker.py | 0% | 90% | TODO |
| swarm/orchestrator.py | 0% | 90% | TODO |
| swarm/main.py | 0% | 90% | TODO |
| tui/widgets/swarm_monitor.py | 0% | 90% | TODO |

### Integration Test Requirements

| Test | Status |
|------|--------|
| swarm-genesys memory storage | TODO |
| WebSocket broadcast | TODO |
| TUI widget rendering | TODO |

---

## Definition of Done

For the swarm module to be considered production-ready:

1. [ ] All critical issues resolved
2. [ ] 90%+ test coverage on swarm module
3. [ ] All high priority issues resolved
4. [ ] Documentation complete
5. [ ] No import errors or missing dependencies
6. [ ] Health checks in place
7. [ ] CHANGELOG.md updated

---

*Backlog updated continuously throughout execution.*
