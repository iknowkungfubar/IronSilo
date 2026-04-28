from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog
from pydantic import BaseModel, Field

from harness_worker import HarnessWorker

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

    async def run_research_session(self, queries: list[str]) -> list[dict[str, Any]]:
        logger.info("manager_session_start", query_count=len(queries))
        results = []

        await self.worker.connect()

        try:
            for query in queries:
                result = await self.extract_and_store(query)
                results.append(result)
                await asyncio.sleep(0.5)
        finally:
            await self.worker.disconnect()

        logger.info("manager_session_complete", memories_stored=len(results))
        return results


async def main():
    worker = HarnessWorker()
    manager = Manager(worker)

    await worker.connect()

    try:
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
    finally:
        await worker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
