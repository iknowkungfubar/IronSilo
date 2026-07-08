# IronSilo Roadmap

> Planned features and improvements for IronSilo.

## Completed (July 2026 Redesign)

- [x] Replace LLMLingua+torch with Headroom (CPU/ONNX compression)
- [x] Replace Redis with diskcache (one fewer Docker container)
- [x] Replace Khoj RAG with LightRAG (34k⭐, graph-enhanced, CPU-only)
- [x] Replace Genesys memory with sqlite-vec (zero infra, embedded)
- [x] MCP protocol 2026-07-28 migration (stateless, discover, W3C trace)
- [x] Replace Traefik with Caddy (simpler config, lower memory)
- [x] W3C Trace Context replaces custom tracing
- [x] Tool annotations (readOnlyHint, idempotentHint, destructiveHint)
- [x] TUI updated for new component layout

## Security & Compliance

- [ ] AES-256 encryption for all data at rest
- [ ] Zero-trust auth middleware between Caddy and internal services
- [ ] Secrets management via environment-vault integration
- [ ] SBOM generation for all Docker images

## Performance & Reliability

- [ ] Semantic model routing for optimal performance (route by task type)
- [ ] Cross-session KV caching for faster responses
- [ ] Headroom cache alignment for inter-agent memory
- [ ] Auto-scaling background workers for batch processing
- [ ] Evaluate pgvectorscale vs sqlite-vec for production deployments

## User Experience

- [ ] Web-based admin panel for service configuration
- [ ] One-command install script (`curl | sh`)

## Agent Ecosystem

- [ ] Plugin system for custom agent types
- [ ] OpenCode integration improvements
- [ ] A2A (Agent-to-Agent) protocol support
- [ ] WebMCP browser-native tool support
