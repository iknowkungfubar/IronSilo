from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx
from llmlingua import PromptCompressor
import os

app = FastAPI()

print("Loading LLMLingua... (Sandboxed to CPU)")
compressor = PromptCompressor(
    model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    use_llmlingua2=True,
    device_map="cpu"
)

# Routes to the host machine's LM Studio / Ollama / Lemonade instance
LEMONADE_URL = os.getenv("LLM_ENDPOINT", "http://host.docker.internal:8000/v1/chat/completions")

@app.post("/api/v1/chat/completions")
async def proxy_to_lemonade(request: Request):
    data = await request.json()
    messages = data.get("messages", [])

    for msg in messages:
        if len(msg.get("content", "")) > 1000:
            try:
                compressed = compressor.compress_prompt(
                    msg["content"],
                    rate=0.6,
                    force_tokens=["system", "user", "assistant", "```", "def", "class"]
                )
                msg["content"] = compressed["compressed_prompt"]
            except Exception:
                pass

    data["messages"] = messages

    if data.get("stream", False):
        async def stream_generator():
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", LEMONADE_URL, json=data) as response:
                    async for chunk in response.aiter_raw():
                        yield chunk
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(LEMONADE_URL, json=data)
            return response.json()
