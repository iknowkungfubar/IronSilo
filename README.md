Warning... this is a work in progress, needs more development and testing.

<p align="center">
  <img src="assets/banner.png" alt="IronSilo Architecture Banner" width="100%">
</p>

<p align="center">
  <a href="https://github.com/iknowkungfubar/IronSilo/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/releases">
    <img src="https://img.shields.io/github/v/release/iknowkungfubar/IronSilo?style=flat-square&sort=semver" alt="GitHub Release">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/blob/main/docs/SIMPLE_MANUAL.md">
    <img src="https://img.shields.io/badge/Docs-Simple_Manual-orange.svg?style=flat-square" alt="Simple Manual">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/blob/main/docs/ADVANCED_MANUAL.md">
    <img src="https://img.shields.io/badge/Docs-Advanced_Architecture-red.svg?style=flat-square" alt="Advanced Architecture">
  </a>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg?style=flat-square" alt="Supported Platforms">
  <a href="https://github.com/iknowkungfubar/IronSilo/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/iknowkungfubar/IronSilo/ci.yml?style=flat-square&label=CI" alt="CI">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/actions/workflows/codeql.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/iknowkungfubar/IronSilo/codeql.yml?style=flat-square&label=CodeQL" alt="CodeQL">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/actions/workflows/cd.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/iknowkungfubar/IronSilo/cd.yml?style=flat-square&label=CD" alt="CD">
  </a>
</p>

**Turn your PC into a private, autonomous AI lab, without melting your GPU.**

IronSilo is a completely local, cross-platform (Windows, macOS, Linux) AI development sandbox. It packages a state-of-the-art coding assistant, a graph-enhanced RAG engine, an autonomous browser swarm agent, and a context-compression proxy into a single, resource-capped environment powered by a **Caddy API Gateway**.

It runs on low-to-mid spec machines by strictly limiting background RAM to ~4GB, dedicating 100% of your GPU to your actual AI model.

> **CLI namespace:** All TurinTech tools are also available under the `turintech-` prefix for consistency. Use `turintech-ironsilo` interchangeably with `ironsilo`. The prefixed name is the canonical entry point across the portfolio.

---

## 📦 What's in the Box?

IronSilo uses a **True Silo** architecture: a single API Gateway (Caddy) on port 8080 that routes all traffic to internal services with prefix stripping. No ports exposed to your network - everything stays private.

**The Intelligence Layer (Locked in Docker Container):**
* **Caddy API Gateway:** Single entry point on port 8080. Routes all traffic with automatic prefix stripping. Simple Caddyfile config replaces complex Traefik YAML.
* **LightRAG:** Graph-enhanced private RAG engine (replaces Khoj). CPU-only, pip-installable, 34k⭐. Drop in documents and ask questions about them.
* **Memory Service & sqlite-vec:** Persistent memory storage (replaces Genesys/pgvector). Zero infra — no separate Docker container needed.
* **Headroom Proxy:** The central hub. Intercepts prompts and compresses them (CPU/ONNX) before sending to your GPU. Saves VRAM without accuracy loss. Replaces LLMLingua+torch.
* **SearxNG:** Private, privacy-respecting web search. No Google/Bing tracking.
* **Browser Swarm:** Autonomous web browsing via headless Chrome, controlled by AI.

**The Action Layer (Runs via Aider CLI):**
* **Aider CLI:** Your specialized coding engine. Aider maps your project's Abstract Syntax Tree (AST) to use 4x fewer tokens than standard agents. It runs natively in your terminal to safely execute bash commands, read linter errors, and apply complex line-by-line file diffs.

---

## 🛠️ Step 0: Install Prerequisites

If you are starting from a fresh computer, you must install these core tools first:

### 1. The Core Environment
* **Git:** Aider requires Git to track code changes. Download at [git-scm.com](https://git-scm.com/downloads) (Linux: `sudo apt install git` or `sudo pacman -S git`).
* **Python / pip:** Required to install Aider natively (`pip install aider-chat`).

### 2. Docker (The Sandbox Engine)
You need Docker to run the background databases and proxies safely.
* **Windows & macOS:** Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/). *Windows users: Ensure WSL2 is enabled during installation.* Open the app and make sure it is running in your system tray.
* **Linux (tested on Ubuntu 24.04):** Do not install Docker Desktop. Install Docker Engine directly: `sudo apt install docker.io docker-compose-v2`. Then add your user to the `docker` group: `sudo usermod -aG docker $USER`. Log out and back in.

### 3. NVIDIA Container Toolkit (Linux only, for GPU acceleration)
* Install the NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit`
* Restart Docker: `sudo systemctl restart docker`

---

## 🚀 Step 1: Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/iknowkungfubar/IronSilo.git
cd IronSilo

# 2. Make the launch script executable
chmod +x ironsilo.sh

# 3. Run the setup wizard
python3 setup/wizard.py

# 4. Start the stack
docker compose up -d

# 5. Check status
python3 -m ironsilo status
```

**Power Tip:** Add this alias to your `~/.bashrc` or `~/.zshrc`:
```bash
alias ironsilo='python3 -m ironsilo'
```

---

## 🧪 Testing

IronSilo uses pytest for comprehensive testing. Tests are organized in:

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Unit tests for individual modules |
| `tests/integration/` | Integration tests for cross-module workflows |
| `tests/fuzz/` | Fuzz testing for edge cases and security |

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_proxy_proxy.py

# Run with coverage
pytest --cov=.
```

### Test Coverage

- **Total Tests:** 870+ tests (870 passing, 4 skipped)
- **Code Coverage:** 82%
- **Test Types:**
  - Unit tests for all core modules
  - Integration tests for proxy and security
  - Fuzz testing for input edge cases

---

## 💡 Usage

### Command Line Interface

IronSilo provides a CLI for managing your AI development environment:

```bash
# Show status of all services
ironsilo status

# View real-time logs
ironsilo logs

# Access the web dashboard
ironsilo dashboard

# Run diagnostics
ironsilo health
```

All commands also have `turintech-` prefixed aliases for portfolio consistency:

```bash
# Same commands with Turintech prefix
turintech-ironsilo status
turintech-ironsilo logs
turintech-ironsilo dashboard
turintech-ironsilo health
turintech-ironsilo-setup
turintech-ironsilo-monitor
```

### Web Dashboard

Once the stack is running, access the monitoring dashboard:

* **Health Dashboard:** http://localhost:8080/health
* **RAG Search:** http://localhost:8080/rag/
* **MCP Discover:** http://localhost:8080/mcp/rag/discover
* **Prometheus Metrics:** http://localhost:8080/metrics

### Configuration

Environment variables can be set in a `.env` file or exported directly:

```bash
# LLM Configuration
export LLM_API_KEY=your_key          # API key for LLM provider
export LLM_MODEL=gpt-4               # Model name to use
export LLM_PROVIDER=openai           # Provider (openai, anthropic, ollama, etc.)

# Infrastructure Paths
export IRON_SILO_ROOT=/path/to/data  # Where IronSilo stores data (default: ~/.ironsilo/)

# Debugging
export IRONSILO_DEBUG=true           # Enable verbose logging
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Simple Manual](docs/SIMPLE_MANUAL.md) | Getting started guide for new users |
| [Advanced Architecture](docs/ADVANCED_MANUAL.md) | Deep dive into components and internals |
| [OpenCode Integration](.opencode/README.md) | Using IronSilo with OpenCode IDE |

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes
5. Run tests: `pytest tests/`
6. Check coverage: `pytest --cov=.`
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Style
- We use `ruff` for linting and formatting
- Run `ruff check .` before committing
- Type hints are required for all public APIs

### Commit Guidelines
- Use conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `security`
- Keep commits focused on a single change

### Testing Guidelines
- Write tests for all new features
- Ensure existing tests continue to pass
- Aim for >80% coverage on new code

### Reporting Issues
Found a bug? Open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, Docker version)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔒 Security

**Important:** IronSilo is designed for local, single-user environments. It has not been audited for multi-user or public-facing security. Running it on a network exposes internal services to potential attacks.

### Reporting Security Issues
If you discover a security vulnerability, please open a draft security advisory on GitHub rather than a public issue.
