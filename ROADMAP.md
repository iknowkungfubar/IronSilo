# 🗺️ IronSilo: Future Improvements & Roadmap

IronSilo is designed to be the ultimate offline fortress for AI-assisted development. As local LLMs and agentic frameworks evolve rapidly, this roadmap outlines the strategic upgrades planned for future releases. 

We welcome pull requests and community discussions on any of the following initiatives!

---

## 🚀 Phase 1: Enhanced Agent Capabilities

### 1. Model Context Protocol (MCP) Integration
Currently, Khoj, Aider, and IronClaw operate in slight silos, each managing their own toolsets. 
* **The Goal:** Implement the open-source **Model Context Protocol (MCP)** as a shared middleware layer.
* **The Benefit:** This allows a single, universal set of local tools (e.g., GitHub issue reading, local database querying, file system access) to be exposed as standard MCP servers. All agents in the Silo can then seamlessly share the exact same tools without redundant configurations.

### 2. Private Web Search (SearxNG)
Agents frequently hallucinate when they lack real-time information.
* **The Goal:** Add a lightweight `searxng` container to the `docker-compose.yml` with strict API limits.
* **The Benefit:** Allows IronClaw and Aider to autonomously browse the live internet for API documentation and bug fixes, completely privately, without leaking queries to Google or Bing.

### 3. Multi-Agent "Swarm" Orchestration
Right now, you talk to Aider for code, and IronClaw for tasks. 
* **The Goal:** Establish an inter-agent communication bus.
* **The Benefit:** You could ask IronClaw to "Research the new Stripe API, write a technical spec, and hand it to Aider." IronClaw does the web browsing, dumps the markdown spec into your workspace, and automatically triggers headless Aider to write the code.

### 4. Dynamic Cross-Agent Memory Sharing
* **The Goal:** Connect the Genesys/pgvector database seamlessly across Aider, IronClaw, and Khoj so they share a unified causal memory graph.
* **The Benefit:** If you tell IronClaw about your preferred coding style or architectural preferences, Aider automatically knows it without you having to repeat yourself.

---

## 🛡️ Phase 2: Architecture, Security & Performance

### 1. Application-Level Encryption (AES-256)
Currently, IronSilo relies on host-level OS disk encryption.
* **The Goal:** Implement native AES-256 encryption for all data at rest within the Postgres and Khoj Docker volumes.
* **The Benefit:** Ensures that even if the Docker volumes are physically copied or backed up to an insecure location, the vector data and chat histories remain completely impenetrable without the master key.

### 2. Role-Based Access Control (RBAC)
* **The Goal:** Add a lightweight authentication and permissions layer to the proxy and web dashboard.
* **The Benefit:** Allows multiple users (or autonomous agents) to have different permission scopes (e.g., "Read-only access to Khoj," "Full execution rights for IronClaw"). This paves the way for secure, team-based local deployments on shared hardware.

### 3. Semantic Model Routing
Currently, all requests go to a single LLM on port `8000`. This is inefficient for simple tasks.
* **The Goal:** Upgrade the Python proxy to include a **Semantic Router**.
* **The Benefit:** The proxy analyzes your prompt *before* sending it. If it's a complex coding task, it routes to `Qwen 2.5 Coder 7B`. If it's a simple grammar check or summary from Khoj, it routes to a lightning-fast, ultra-small model like `Llama-3-8B-Instruct`. This drastically saves compute resources.

### 4. Cross-Session KV Caching
* **The Goal:** Implement persistent KV (Key-Value) cache sharing between the proxy and the host inference engine.
* **The Benefit:** If you feed a massive 20,000-token codebase to Aider, the LLM processes it once. If you ask a follow-up question 10 minutes later, it doesn't need to re-read the code—it instantly loads the KV cache, reducing "Time to First Token" from 30 seconds to <1 second.

### 5. Multimodal / Vision Support
* **The Goal:** Upgrade the LLMLingua proxy to handle base64 image pass-through.
* **The Benefit:** You can drag and drop a screenshot of a broken UI into VS Code, and Aider will be able to "see" the image and write the CSS/HTML to fix it.

---

## 🖥️ Phase 3: Developer Experience (DX) & UI

### 1. The IronSilo Studio (Standalone GUI Application)
Not everyone wants to use VS Code. We need a dedicated frontend for the entire stack.
* **The Goal:** Build a native Desktop app (Tauri/Electron) or a unified Web UI that completely replaces the need for third-party text editors.
* **The Benefit:** A beautiful, consumer-friendly workspace where users can chat with Aider, browse Khoj documents, and delegate tasks to IronClaw all from a single window. It transforms IronSilo from a "developer tool" into a universal, standalone AI workstation for writers, researchers, and creators.

### 2. Unified Web Dashboard (The Control Center)
Command line interfaces are great, but managing databases visually is the gold standard.
* **The Goal:** Build a lightweight, local administrative web application accessible at `localhost:3000`.
* **The Benefit:** A single pane of glass where developers can visually browse Long-Term Memories (Genesys), track LLMLingua's token compression savings on live graphs, and toggle proxy routing between LM Studio, Ollama, and Lemonade.

### 3. IronSilo Terminal Dashboard (TUI)
For developers who refuse to leave the terminal.
* **The Goal:** Build a Terminal User Interface (TUI) using a tool like Textual (Python) or Gum (Go).
* **The Benefit:** Typing `ironsilo monitor` will open a sleek terminal dashboard showing real-time RAM usage, container health, and proxy traffic logs without needing a browser.

### 4. Interactive Setup Wizard
* **The Goal:** Replace the manual `.env` port configurations with an interactive CLI setup script.
* **The Benefit:** When a user runs the start script for the first time, it prompts them: *"Which LLM runner are you using? [1] LM Studio [2] Ollama [3] Lemonade"*, and automatically configures the ports and networking for them.

---

## 🤝 How to Contribute
If any of these sound exciting to you, please check out our Issues page or submit a Pull Request! IronSilo is built on the philosophy that AI should remain local, private, and incredibly efficient. Let's build the future of local development together.