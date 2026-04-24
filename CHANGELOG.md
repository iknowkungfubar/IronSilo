# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-24
### Added
- **Comprehensive Test Suite:** Added 543 tests covering all core modules with 88.4% code coverage
- **Unit Tests:** Extended coverage for TUI components, proxy models, security modules, MCP servers, and pipeline components
- **Integration Tests:** Added end-to-end integration tests for proxy with mock upstream LLM and security key manager workflows
- **Test Infrastructure:** Configured pytest with coverage reporting, markers for unit/integration/e2e tests
- **Textual Pilot Tests:** Added comprehensive TUI tests using Textual's Pilot framework for headless testing

### Changed
- **Version Bump:** Updated to version 2.0.0 to reflect stable, production-ready status
- **Documentation:** Enhanced README.md with testing instructions and coverage badges
- **TUI Refactor:** Renamed widget `refresh()` methods to `refresh_data()` to avoid conflicts with Textual's base class

### Fixed
- **Test Stability:** Fixed flaky tests related to Textual app context and datetime deprecation warnings
- **Coverage Compliance:** All modules now exceed the 80% minimum coverage threshold (88.4% achieved)
- **TUI Method Signatures:** Fixed method signature conflicts with Textual's Widget base class

---

## [1.0.2] - 2026-04-23
### Changed
- **Removed VS Code Extension Dependencies:** Deprecated the `.vscode` auto-configuration folder. IronSilo now strictly advocates using Aider via the native CLI and Khoj via its native Docker Web UI. This eliminates security risks from unmaintained 3rd-party wrappers (like `lee2py.aider-composer`) and future-proofs the RAG engine against Khoj's cloud deprecation.

## [1.0.1] - 2026-04-23
### Changed
- **Memory Architecture Pivot:** Replaced the Mem0 container with **Genesys**. This eliminates Docker manifest (`linux/amd64`) compatibility issues on Linux/CachyOS while upgrading the local stack from standard vector storage to an advanced causal graph memory system.
- **Proxy Optimization:** Reverted the `proxy/Dockerfile` to remove `psycopg2`, delegating all database interactions directly to the newly isolated Genesys API layer.

## [1.0.0] - 2026-04-22
### Added
- **IronSilo Rebranding:** Officially launched the cross-platform local AI workspace.
- **Cross-Platform Support:** Transitioned the core infrastructure to support Windows (WSL2), macOS (Hypervisor), and Linux uniformly.
- **1-Click Launchers:** Added `Start_Workspace` and `Stop_Workspace` scripts (`.bat` for Windows, `.sh` for macOS/Linux) to remove CLI friction.
- **VS Code Auto-Config:** Added `.vscode` directory to automatically recommend extensions (Aider, Khoj) and inject proxy routing configurations.
- **IronClaw Integration:** `Start_Workspace.sh` now automatically detects, injects environment variables, and backgrounds the IronClaw WASM agent on Unix systems.
- **Comprehensive Documentation:** Added `SIMPLE_MANUAL.md` for non-technical users and `ADVANCED_MANUAL.md` for infrastructure deployment.
- **Model Agnostic Routing:** Added `.env` support to dynamically route the proxy to different inference backends (e.g., LM Studio on `:8000`, Ollama on `:11434`).

### Changed
- **Migration to Docker Compose:** Pivoted from Arch/CachyOS-specific Podman rootless scripts to universal Docker Compose to resolve UID/GID mapping and network bridging (`host.docker.internal`) issues across operating systems.
- **Volume Management:** Shifted from local bind mounts to Docker Named Volumes (`ironclaw-pg-data`, `khoj-data`) to prevent NTFS/APFS permission denial errors.

### Security & Performance
- **Strict Resource Quotas:** Implemented hard cgroup limits in `docker-compose.yml`, capping the entire background stack (Postgres, Mem0, Khoj, Proxy) to ~4.0 GB of RAM.
- **VRAM Protection:** Forced the LLMLingua compression proxy to execute strictly on the CPU (`device_map="cpu"`) to prevent GPU fragmentation.

---

## [0.9.5-beta] - 2026-04-21
### Added
- Added Python FastAPI proxy to intercept standard OpenAI API calls.
- Integrated `microsoft/llmlingua-2-bert-base` to compress context payloads by up to 40%.
- Added HuggingFace cache volume mapping to prevent redundant 1.1GB model downloads.

### Fixed
- Resolved PyTorch CUDA bloat issue by strictly pulling the CPU-only `.whl` binaries in the proxy `Dockerfile`.

---

## [0.9.0-alpha] - 2026-04-20
### Added
- Initial proof-of-concept deployment script (`setup_ai_workspace.sh`) for Arch Linux / CachyOS.
- Implemented Podman rootless containers for Postgres (pgvector), Mem0, and Khoj.
- Added native host tooling requirements for Aider Composer and IronClaw CLI.