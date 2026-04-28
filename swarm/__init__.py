"""
IronSilo Swarm Module.

Provides browser automation via Chrome DevTools Protocol and orchestration
for distributed AI agent workflows.

Main Components:
- HarnessWorker: CDP WebSocket client for DOM extraction and interaction
- Manager: Orchestrator for research data extraction and memory storage
- SwarmState: Server state management for WebSocket broadcast

Environment Variables:
- CDP_URL: Chrome DevTools Protocol WebSocket URL (default: ws://browser-node:9222)
- OPENAI_API_BASE: LLM Proxy endpoint (default: http://llm-proxy:8001/api/v1)
- GENESYS_URL: Genesys memory service URL (default: http://genesys-memory:8000)
"""

from swarm.harness_worker import HarnessWorker
from swarm.orchestrator import Manager, MemoryNodeInput

__all__ = [
    "HarnessWorker",
    "Manager",
    "MemoryNodeInput",
]
