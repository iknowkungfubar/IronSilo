from __future__ import annotations

import asyncio
import json
import os
import signal
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog
from pydantic import BaseModel, Field

from swarm.harness_worker import HarnessWorker

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

GENESYS_URL = os.getenv("GENESYS_URL", "http://genesys-memory:8000")
RETRY_QUEUE: list[dict[str, Any]] = []
DEAD_LETTER_QUEUE: list[dict[str, Any]] = []
_shutdown_event: Optional[asyncio.Event] = None


def init_shutdown_handler() -> asyncio.Event:
    """Initialize shutdown signal handler."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
        
        def signal_handler():
            logger.info("orchestrator_shutdown_requested")
            if _shutdown_event:
                _shutdown_event.set()
        
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
        except (NotImplementedError, OSError):
            pass
    
    return _shutdown_event


class MemoryNodeInput(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    memory_type: str = "semantic"
    importance: float = 0.5
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class Manager:
    def __init__(self, worker: HarnessWorker):
        self.worker = worker
        self.genesys_url = GENESYS_URL

    async def extract_and_store(self, research_query: str) -> dict[str, Any]:
        logger.info("manager_extract_start", query=research_query)

        dom = await self.worker.get_dom()
        raw_data = await self.worker.evaluate_for_research(dom)

        try:
            parsed = json.loads(raw_data)
        except json.JSONDecodeError:
            parsed = {"raw_research": raw_data}

        memory_node = MemoryNodeInput(
            content=json.dumps(parsed, indent=2),
            memory_type="research",
            importance=0.7,
            tags=["web_scraping", "dom_analysis", research_query[:50]],
            metadata={
                "source": "browser_swarm",
                "research_query": research_query,
                "dom_size": len(dom),
            },
        )

        result = await self._store_memory(memory_node)
        logger.info("manager_store_complete", memory_id=result.get("id"))
        return result

    async def _store_memory(self, memory: MemoryNodeInput) -> dict[str, Any]:
        logger.info("manager_storing_memory", url=f"{self.genesys_url}/api/v1/memories")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.genesys_url}/api/v1/memories",
                json=memory.model_dump(),
            )
            response.raise_for_status()
            return response.json()

    async def _retry_failed_memory(self, memory: MemoryNodeInput, max_retries: int = 3) -> Optional[dict[str, Any]]:
        """Retry storing failed memory with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await self._store_memory(memory)
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 10.0)
                    logger.warning(
                        "memory_retry",
                        memory_id=memory.id,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "memory_retry_exhausted",
                        memory_id=memory.id,
                        error=str(e),
                    )
                    DEAD_LETTER_QUEUE.append({
                        "memory": memory.model_dump(),
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "error": str(e),
                    })
        return None

    async def run_research_session(self, queries: list[str]) -> list[dict[str, Any]]:
        logger.info("manager_session_start", query_count=len(queries))
        results = []
        shutdown_event = init_shutdown_handler()

        await self.worker.connect()

        try:
            for query in queries:
                if shutdown_event.is_set():
                    logger.info("manager_session_interrupted", queries_completed=len(results))
                    break
                result = await self.extract_and_store(query)
                results.append(result)
                await asyncio.sleep(0.5)
        finally:
            await self.worker.disconnect()

        logger.info("manager_session_complete", memories_stored=len(results))
        return results


async def main():
    shutdown_event = init_shutdown_handler()
    worker = HarnessWorker()
    manager = Manager(worker)

    try:
        await worker.connect()
        dom = await worker.get_dom()
        research_data = await worker.evaluate_for_research(dom)

        memory = MemoryNodeInput(
            content=research_data,
            memory_type="research",
            importance=0.7,
            tags=["web_scraping", "dom_analysis"],
            metadata={"source": "browser_swarm"},
        )

        await manager._store_memory(memory)
        logger.info("orchestrator_main_complete")
    except asyncio.CancelledError:
        logger.info("orchestrator_main_cancelled")
    finally:
        await worker.disconnect()
        logger.info("orchestrator_main_shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
