FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy MCP server code and requirements (build context is mcp/)
COPY . /app/mcp/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /app/cache && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: memory server. Override with MCP_SERVER_TYPE=rag for RAG MCP
CMD ["sh", "-c", "if [ \"${MCP_SERVER_TYPE:-memory}\" = \"rag\" ]; then exec python -m uvicorn mcp.khoj_server:app --host 0.0.0.0 --port 8000; else exec python -m uvicorn mcp.genesys_server:app --host 0.0.0.0 --port 8000; fi"]
