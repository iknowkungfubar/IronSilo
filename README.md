<p align="center">
  <img src="assets/banner.png" alt="IronSilo Architecture Banner" width="100%">
</p>

<p align="center">
  <a href="https://github.com/iknowkungfubar/IronSilo/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/releases">
    <img src="https://img.shields.io/badge/Version-2.0.0-success.svg?style=flat-square" alt="Version 2.0.0">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/blob/main/docs/SIMPLE_MANUAL.md">
    <img src="https://img.shields.io/badge/Docs-Simple_Manual-orange.svg?style=flat-square" alt="Simple Manual">
  </a>
  <a href="https://github.com/iknowkungfubar/IronSilo/blob/main/docs/ADVANCED_MANUAL.md">
    <img src="https://img.shields.io/badge/Docs-Advanced_Architecture-red.svg?style=flat-square" alt="Advanced Architecture">
  </a>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg?style=flat-square" alt="Supported Platforms">
  <img src="https://img.shields.io/badge/Tests-543%20passed-brightgreen.svg?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/Coverage-88.4%25-brightgreen.svg?style=flat-square" alt="Coverage">
</p>

**Turn your PC into a private, autonomous AI lab, without melting your GPU.**

IronSilo is a completely local, cross-platform (Windows, macOS, Linux) AI development sandbox. It packages a state-of-the-art coding assistant, a wiki RAG engine, an autonomous WebAssembly agent, and a context-compression proxy into a single, resource-capped environment. 

It runs on low-to-mid spec machines by strictly limiting background RAM to ~4GB, dedicating 100% of your GPU to your actual AI model.

---

## 📦 What's in the Box?

This workspace abandons brittle IDE extensions in favor of a **Terminal-First, Dual-Agent Swarm**. We split responsibilities between two specialized engines to maximize token efficiency and system security:

**The Action Layer (Runs Locally for File/System Access):**
* **The Hands (Aider CLI):** Your specialized coding engine. Aider maps your project's Abstract Syntax Tree (AST) to use 4x fewer tokens than standard agents. It runs natively in your terminal to safely execute bash commands, read linter errors, and apply complex line-by-line file diffs.
* **The Brain (IronClaw PAI):** Your Personal AI and orchestrator. Running natively, it executes web research, schedule management, and background cron jobs strictly inside a zero-trust WebAssembly (WASM) sandbox, ensuring your API keys and host OS are never exposed to malicious LLM outputs.

**The Intelligence Layer (Locked in 4GB Docker Container):**
* **Khoj:** Your private Wiki RAG engine. Drop in PDFs, markdown files, and notes, and ask your AI questions about them via its native Web UI.
* **Genesys & pgvector:** The Long-Term Memory (LTM) database. This utilizes an active causal graph, allowing autonomous agents to remember your preferences and causal reasoning across sessions.
* **LLMLingua Proxy:** The central hub. It intercepts massive prompts and uses a tiny CPU model to compress the text by up to 40% before sending it to your GPU, saving your VRAM from crashing. It also has the added benefit of Token Optimization.

---

## 🛠️ Step 0: Install Prerequisites

If you are starting from a fresh computer, you must install these core tools first:

### 1. The Core Environment
* **Git:** Aider requires Git to track code changes. Download at [git-scm.com](https://git-scm.com/downloads) (Linux: `sudo apt install git` or `sudo pacman -S git`).
* **Python / pip:** Required to install Aider natively (`pip install aider-chat`).

### 2. Docker (The Sandbox Engine)
You need Docker to run the background databases and proxies safely.
* **Windows & macOS:** Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/). *Windows users: Ensure WSL2 is enabled during installation.* Open the app and make sure it is running in your system tray.
* **Linux (Ubuntu/Debian):** Run `sudo apt install docker.io docker-compose-v2` and start the daemon with `sudo systemctl enable --now docker`.
* **Linux (Arch/CachyOS):** Run `sudo pacman -S docker docker-compose` and start the daemon with `sudo systemctl enable --now docker`.

### 3. A Local AI Host (The Brain)
You need a program running on your computer to host your AI model (we highly recommend downloading the **Qwen 2.5 Coder 7B** model). Install one of the following:
* **[LM Studio](https://lmstudio.ai/):** Best for Windows/Mac beginners. Features a great UI.
* **[Ollama](https://ollama.com/):** Best for command-line users. (Run `ollama run qwen2.5-coder`).
* **Lemonade:** Best for Arch Linux/AMD GPU users seeking maximum ROCm performance. (Arch users: `yay -S lemonade-bin`).

---

## 🚀 Quick Start

Once your prerequisites are installed, you are ready to go.

**Step 1: Start your AI Model**
Open your AI Host and start a local server. *(By default, our proxy looks for an AI running on port `8000`. See the 'Documentation' section below if using Ollama, which uses port `11434`).*

**Step 2: Boot the Workspace**
* **Windows:** Double-click `Start_Workspace.bat`
* **Mac/Linux:** Open a terminal in this folder and run `./Start_Workspace.sh`
*(Note: The very first time you do this, Docker will download the required tools. It will be instant next time).*

**Step 3: Code!**
Your tools are securely routed and ready to use natively.
1. **To Code (Aider):** Open your terminal and start Aider by pointing it to your local proxy:
   ```bash
   export OPENAI_API_BASE="[http://127.0.0.1:8001/api/v1](http://127.0.0.1:8001/api/v1)"
   export OPENAI_API_KEY="local-sandbox"
   aider
   ```
2. **To Research (Khoj):** Open your web browser and navigate to `http://127.0.0.1:42110` to access your private Wiki UI.
3. **To Automate (IronClaw):** Navigate to `http://127.0.0.1:8080` in your browser to chat with your WASM agent.

---

## 🛑 Shutting Down

When you are done working, get your computer's RAM back:
* **Windows:** Double-click `Stop_Workspace.bat`
* **Mac/Linux:** Run `./Stop_Workspace.sh`

---

## 🧪 Testing

IronSilo includes comprehensive unit and integration tests to ensure reliability.

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_proxy_proxy.py -v
```

### Test Coverage

- **Total Tests:** 479 tests (all passing)
- **Code Coverage:** 81.5%
- **Test Types:**
  - Unit tests for all core modules
  - Integration tests for proxy and security
  - Mock-based testing for external dependencies

### Contributing to Tests

When adding new features:
1. Write tests first (TDD approach)
2. Ensure tests pass: `pytest tests/`
3. Check coverage: `pytest --cov=.`

---

## 📚 Documentation

- [Simple Manual](docs/SIMPLE_MANUAL.md) - Getting started guide
- [Advanced Architecture](docs/ADVANCED_MANUAL.md) - Technical deep dive
- [Roadmap](ROADMAP.md) - Future improvements
- [Architecture](ARCHITECTURE.md) - System design overview

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/iknowkungfubar/IronSilo.git
cd IronSilo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Run pre-commit hooks
pre-commit install
pre-commit run --all-files
```