# Advanced Technical Architecture: IronSilo

## Infrastructure Provisioning (Prerequisites)
To deploy this stack on a bare-metal machine, ensure the host environment is provisioned with the following toolchain:

### 1. Container Engine
The workspace requires Docker Compose V2.
* **Windows / macOS:** Install Docker Desktop. Ensure the WSL2 backend is enabled on Windows.
* **Debian / Ubuntu:** `sudo apt update && sudo apt install docker.io docker-compose-v2 git code`
* **Arch / CachyOS:** `sudo pacman -S docker docker-compose git code` (Ensure daemon is enabled: `sudo systemctl enable --now docker`)

### 2. Inference Backend
Deploy an OpenAI-compatible inference server on the host machine.
* **Lemonade:** Ideal for AMD ROCm via Arch (`yay -S lemonade-bin`). Bind to `0.0.0.0:8000`.
* **Ollama:** `curl -fsSL https://ollama.com/install.sh | sh`. Override the proxy endpoint via `.env` file in the `proxy/` directory: `LLM_ENDPOINT="http://host.docker.internal:11434/v1/chat/completions"`.
* **LM Studio:** Configure local server port to `8000`.

## Architectural Pivot: Universal Containerization
To support Windows (WSL2), macOS (Hypervisor), and Linux uniformly, the stack utilizes Docker Compose. This normalizes namespace mapping and network bridging across OS architectures while enforcing strict cgroup resource caps.

### Resource Quotas (Strict Enforcement):
- **Total Sandbox RAM Ceiling:** ~4.0 GB
- **PostgreSQL (pgvector):** 512 MB
- **Mem0 API:** 512 MB
- **Khoj RAG Engine:** 1.0 GB
- **LLMLingua Proxy:** 2.0 GB (CPU-Bound PyTorch)

## Network Bridging (`host.docker.internal`)
Running a local LLM on the host while the proxy resides in a container creates a routing paradigm issue. Docker Desktop operates inside a hidden Linux VM, meaning `localhost` inside the container resolves to the container itself.
**The Solution:** The Compose file injects `host.docker.internal:host-gateway`. This allows the FastAPI proxy to route optimized payloads to the host's port natively across all operating systems.

## The Context Optimization Proxy
To support mid-range hardware (e.g., 8GB - 12GB VRAM GPUs), context window overflow is mitigated by a Python FastAPI proxy intercepting requests. It utilizes `microsoft/llmlingua-2-bert-base`. By restricting the `device_map` to `cpu`, we guarantee zero VRAM fragmentation, dedicating 100% of the GPU to the primary LLM inference server.

*Cache Persistence:* The proxy mounts a Docker volume `hf-cache`. This prevents the 1.1GB BERT model from redownloading upon container rebuilds.

## IronClaw Lifecycle Management
IronClaw executes in a WebAssembly sandbox natively on the host to avoid nested containerization issues. 
* On **macOS/Linux**, `Start_Workspace.sh` detects the binary, mounts the environment variables routing to the proxy and Postgres container, and backgrounds the process (`nohup ironclaw start &`). `Stop_Workspace.sh` safely kills it via `pkill`.
* On **Windows**, users must manually install and invoke IronClaw via WSL due to Rust compilation requirements:
  `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/nearai/ironclaw/releases/latest/download/ironclaw-installer.sh | sh`

## Stateful Data & Teardown
To avoid permission conflicts on Windows NTFS and macOS APFS, this architecture uses isolated Docker named volumes (`ironclaw-pg-data`, `khoj-data`). 
* Safe shutdown: `docker compose down` (persists data)
* Total wipe: `docker compose down -v` (destroys memory and databases)
