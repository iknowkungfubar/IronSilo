# IronSilo Roadmap

> Planned features and improvements for IronSilo.

## Security & Compliance

- [ ] AES-256 encryption for all data at rest
- [ ] Zero-trust auth middleware between Traefik and internal services
- [ ] Secrets management via environment-vault integration
- [ ] SBOM generation for all Docker images

## Performance & Reliability

- [ ] Semantic model routing for optimal performance (route by task type)
- [ ] Cross-session KV caching for faster responses
- [ ] Context compression via LLMLingua-2 (v2 model)
- [ ] Auto-scaling background workers for batch processing

## User Experience

- [ ] IronSilo Terminal Dashboard (TUI) — curses-based status monitor
- [ ] Desktop Command Center (GUI) — system tray app with service controls
- [ ] Web-based admin panel for service configuration
- [ ] One-command install script (`curl | sh`)

## Agent Ecosystem

- [ ] Plugin system for custom agent types
- [ ] MCP server integration for tool discovery
- [ ] Multi-agent orchestration (IronClaw improvements)
- [ ] Episodic memory via Genesys causal graphs

## Observability

- [ ] Distributed tracing (OpenTelemetry)
- [ ] Structured JSON logging for all services
- [ ] Prometheus metrics endpoint in Traefik
- [ ] Grafana dashboard (configurable)

## Platform

- [ ] Official Docker images on GitHub Container Registry
- [ ] Homebrew tap for macOS
- [ ] AUR package for Arch Linux
- [ ] Raspberry Pi 4/5 support
- [ ] Podman-compatible deployment (no Docker dependency)

## Community

- [ ] Contribution templates (bug report, feature request)
- [ ] User guide translations
- [ ] Example workflows and recipes
