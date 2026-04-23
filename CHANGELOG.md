# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
