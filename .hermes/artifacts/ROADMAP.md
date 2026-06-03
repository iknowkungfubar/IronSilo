# 🗺️ IronSilo: Future Improvements & Roadmap

IronSilo is designed to be the ultimate offline fortress for AI-assisted development. As local LLMs and agentic frameworks evolve rapidly, this roadmap outlines our strict commitment to a **Terminal-First, Post-IDE** architecture. 

We welcome pull requests and community discussions on any of the following initiatives!

---

## 🚀 Phase 1: The Dual-Agent Swarm

### 1. Model Context Protocol (MCP) Integration for IronClaw
Currently, Khoj and Genesys operate securely in the background. 
* **The Goal:** Expose the Genesys memory graph and Khoj RAG as standard MCP servers.
* **The Benefit:** IronClaw (acting as your Personal AI) can seamlessly query your local documents and causal memory graph to make complex autonomous decisions without leaving its zero-trust WASM sandbox.

### 2. Aider / IronClaw Handoff Pipeline
Right now, you use IronClaw for secure web research, and Aider for AST-based code editing. 
* **The Goal:** Establish an inter-agent communication bus (Swarm Orchestration).
* **The Benefit:** You ask IronClaw to "Research the new Stripe API, write a technical spec, and pass it to the coder." IronClaw safely browses the web, writes the spec, and automatically triggers headless Aider in your terminal to implement the code.

### 3. Private Web Search (SearxNG)
* **The Goal:** Add a lightweight `searxng` container to the `docker-compose.yml`.
* **The Benefit:** Allows IronClaw to autonomously browse the live internet for API documentation completely privately, without leaking queries to Google or Bing.

---

## 🛡️ Phase 2: Architecture, Security & Performance

### 1. Application-Level Encryption (AES-256)
* **The Goal:** Implement native AES-256 encryption for all data at rest within the Postgres and Khoj Docker volumes.
* **The Benefit:** Ensures that even if the Docker volumes are physically copied, the vector data and chat histories remain impenetrable without the master key.

### 2. Semantic Model Routing
Currently, all requests go to a single LLM on port `8000`. This is inefficient.
* **The Goal:** Upgrade the Python proxy to include a **Semantic Router**.
* **The Benefit:** If Aider sends a complex code-diff request, it routes to `Qwen 2.5 Coder 7B`. If IronClaw asks a simple logical routing question, it routes to a lightning-fast, ultra-small model like `Llama-3-8B-Instruct`.

### 3. Cross-Session KV Caching
* **The Goal:** Implement persistent KV (Key-Value) cache sharing between the proxy and the host inference engine.
* **The Benefit:** If you feed a massive 20,000-token codebase to Aider, the LLM processes it once. Follow-up questions load instantly from the KV cache, reducing "Time to First Token" to <1 second.

---

## 🖥️ Phase 3: The Post-IDE Developer Experience (DX)

### 1. IronSilo Terminal Dashboard (TUI)
We are abandoning the IDE. Serious agents live in the shell.
* **The Goal:** Build a Terminal User Interface (TUI) using a tool like Textual (Python) or Gum (Go).
* **The Benefit:** Typing `ironsilo monitor` opens a sleek terminal dashboard showing real-time RAM usage, container health, and proxy traffic logs without needing a browser or VS Code.

### 2. Interactive Setup Wizard
* **The Goal:** Replace the manual `.env` port configurations with an interactive CLI setup script.
* **The Benefit:** When a user runs the start script, it prompts: *"Which LLM runner are you using? [1] LM Studio [2] Ollama [3] Lemonade"*, and automatically configures the ports.

### 3. IronSilo Studio: Desktop Command Center (GUI)
While agents thrive in the terminal, managing the underlying infrastructure shouldn't require juggling Docker CLI commands or multiple browser tabs.
* **The Goal:** Build a lightweight, native Desktop application (using frameworks like Tauri or Electron) to serve as a unified control center.
* **The Benefit:** A single pane of glass to visually manage your local AI fortress. You can effortlessly browse the Genesys causal memory graph, track token compression savings via live charts, monitor strict 4GB container health, and toggle LLM host endpoints—all from one beautiful desktop dashboard.

### 4. IronSilo Command Center: The Shell Dashboard (TUI)
For power users who refuse to leave the command line but still require deep system visibility and interactive orchestration tracking.
* **The Goal:** Expand the baseline monitoring TUI into a fully-featured command center using advanced terminal-native frameworks.
* **The Benefit:** A single pane of glass directly in your shell. Beyond just monitoring, this allows you to trigger Swarm task handoffs between IronClaw and Aider, manage memory states, and view logs simultaneously. It is completely keyboard-navigable, ensuring you never have to touch a mouse to control your AI sandbox.