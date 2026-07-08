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
- MEMORY_URL: Memory service URL (default: http://memory:8020)
"""

from swarm.harness_worker import HarnessWorker
from swarm.orchestrator import Manager, MemoryNodeInput
from swarm.main import app, state

__all__ = [
    "HarnessWorker",
    "Manager",
    "MemoryNodeInput",
    "app",
    "state",
]
