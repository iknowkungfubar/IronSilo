# IronSilo — Agent Context

## Overview

**IronSilo** is a local-first, cross-platform AI development sandbox (v2.1.1 Beta). Provides a complete local AI development environment with Docker-based orchestration, MCP server integration, proxy management, monitoring, and security auditing.

## Tech Stack

- **Language:** Python 3.10+
- **Build System:** setuptools
- **Package:** `ironsilo` (not yet published to PyPI)
- **Containerization:** Docker, docker-compose, Traefik reverse proxy
- **Testing:** pytest (unit, integration, e2e, fuzz, contract, load)
- **LLM Support:** Local models via SearXNG + Ollama/Lemonade

## Repository Structure

```
├── controller.py          # Core orchestration logic (root-level)
├── mcp/                   # MCP server integration
├── swarm/                 # Multi-agent swarm coordination
├── proxy/                 # Traefik reverse proxy configs
├── tui/                   # Terminal UI
├── monitoring/            # Observability stack
├── security/              # Security audits and configs
├── pipeline/              # CI/CD pipeline definitions
├── setup/                 # Installation and setup scripts
├── dev/                   # Development tooling
├── genesys/               # Genesis system configs
├── searxng/               # Meta-search engine integration
├── cache/                 # Caching layer
├── examples/              # Usage examples
├── tests/                 # Comprehensive test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   ├── fuzz/              # Fuzz testing
│   ├── contract/          # Contract tests
│   └── load/              # Load/performance tests
├── docs/                  # Documentation
├── assets/                # Static assets
└── ROADMAP.md             # Development roadmap
```

## Key Commands

- `pip install -e .` — Install from source (editable mode)
- `pytest tests/ -v` — Run all tests
- `docker-compose up -d` — Start services (MCP, proxy, monitoring)
- `docker-compose down` — Stop services

## Architecture

- **Controller** (`controller.py`): Central orchestration — agent lifecycle, task routing, state management
- **MCP Integration** (`mcp/`): Model Context Protocol server for external tool calling
- **Swarm System** (`swarm/`): Multi-agent coordination with role-based agents (Orchestrator, Consumer, SkillEngine, Memory, Security)
- **Proxy Layer** (`proxy/`): Traefik reverse proxy for service routing and TLS termination
- **TUI** (`tui/`): Terminal-based UI for local interaction
- **Monitoring** (`monitoring/`): Prometheus + Grafana observability stack
- **Security** (`security/`): Audit reports, vulnerability scanning, security configurations

## Quality Gates

- `pytest tests/ -v`
- `ruff check .`
- `docker-compose config` — Validate compose file
