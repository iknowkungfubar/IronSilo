from __future__ import annotations

import asyncio
import json
import os
import signal
from typing import Any, Optional

import httpx
import structlog
import websockets

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

CDP_URL = os.getenv("CDP_URL", "ws://browser-node:9222")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://llm-proxy:8001/api/v1")

_shutdown_event: Optional[asyncio.Event] = None


def init_shutdown_handler() -> asyncio.Event:
    """Initialize shutdown signal handler."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
        
        def signal_handler():
            logger.info("harness_worker_shutdown_requested")
            if _shutdown_event:
                _shutdown_event.set()
        
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
        except (NotImplementedError, OSError):
            pass
    
    return _shutdown_event


class HarnessWorker:
    def __init__(self, cdp_url: str = CDP_URL):
        self.cdp_url = cdp_url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._message_id = 0
        self._response_futures: dict[int, asyncio.Future] = {}

    async def connect(self) -> None:
        logger.info("cwp_connecting", url=self.cdp_url)
        self.ws = await websockets.connect(self.cdp_url, extra_headers={"Origin": "chrome://inspect"})
        logger.info("cwp_connected", url=self.cdp_url)

    async def disconnect(self) -> None:
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info("cwp_disconnected")

    async def _send_command(self, method: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not self.ws:
            raise RuntimeError("WebSocket not connected. Call connect() first.")

        self._message_id += 1
        message_id = self._message_id

        command = {"id": message_id, "method": method}
        if params:
            command["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._response_futures[message_id] = future

        await self.ws.send(json.dumps(command))

        try:
            result = await asyncio.wait_for(future, timeout=60.0)
            return result
        except asyncio.TimeoutError:
            self._response_futures.pop(message_id, None)
            raise TimeoutError(f"CDP command '{method}' timed out")

    async def _receive_loop(self) -> None:
        if not self.ws:
            return

        try:
            async for raw_message in self.ws:
                message = json.loads(raw_message)

                if "id" in message and message["id"] in self._response_futures:
                    future = self._response_futures.pop(message["id"])
                    if "result" in message:
                        future.set_result(message["result"])
                    elif "error" in message:
                        future.set_exception(Exception(message["error"].get("message", "CDP error")))
                elif message.get("method") == "Runtime.consoleAPICalled":
                    logger.debug("cwp_console", params=message.get("params"))

        except websockets.exceptions.ConnectionClosed:
            logger.info("cwp_connection_closed")
        except Exception as e:
            logger.error("cwp_receive_error", error=str(e))

    async def get_dom(self) -> str:
        logger.info("cwp_get_dom")

        await self.ws.send(json.dumps({
            "id": self._message_id + 1,
            "method": "DOM.getDocument",
            "params": {"depth": -1}
        }))
        self._message_id += 1

        result = await self._send_command("DOM.getDocument", {"depth": -1})
        root = result.get("root", {})
        return json.dumps(root)

    async def click_element(self, selector: str) -> bool:
        logger.info("cwp_click_element", selector=selector)

        query_result = await self._send_command("Runtime.evaluate", {
            "expression": f'document.querySelector("{selector}")',
            "returnByValue": False
        })

        if not query_result.get("result") or not query_result["result"].get("objectId"):
            logger.warning("cwp_element_not_found", selector=selector)
            return False

        object_id = query_result["result"]["objectId"]

        await self._send_command("Runtime.callFunctionOn", {
            "objectId": object_id,
            "functionDeclaration": "function() { this.click(); }",
            "returnByValue": False
        })

        logger.info("cwp_element_clicked", selector=selector)
        return True

    async def evaluate_for_research(self, dom_content: str) -> str:
        logger.info("cwp_evaluating_dom", dom_length=len(dom_content))

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OPENAI_API_BASE}/chat/completions",
                json={
                    "model": "dom-analyzer",
                    "messages": [
                        {"role": "system", "content": "You are a research data extractor. Analyze the provided DOM tree and extract structured research data in JSON format."},
                        {"role": "user", "content": f"Extract research data from this DOM:\n{dom_content}"}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8000
                },
                headers={"X-Bypass-Compression": "true"},
            )
            response.raise_for_status()
            result = response.json()

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info("cwp_evaluation_complete", response_length=len(content))
        return content


async def main():
    shutdown_event = init_shutdown_handler()
    worker = HarnessWorker()

    try:
        await worker.connect()

        while not shutdown_event.is_set():
            dom = await worker.get_dom()
            research_data = await worker.evaluate_for_research(dom)
            print(research_data)
            
            await asyncio.wait_for(shutdown_event.wait(), timeout=5.0)
            break
            
    except asyncio.CancelledError:
        logger.info("main_cancelled")
    finally:
        await worker.disconnect()
        logger.info("main_shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
