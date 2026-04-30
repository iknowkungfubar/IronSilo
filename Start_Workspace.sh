#!/bin/bash
cd "$(dirname "$0")"

echo "================================================="
echo "    IronSilo - True Silo API Gateway Launch      "
echo "================================================="
echo ""

docker compose up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to start. Please make sure Docker is running!"
    exit 1
fi

echo ""
echo "Waiting for services to be healthy..."
sleep 5

echo ""
echo "================================================="
echo "            True Silo is Running!                "
echo "================================================="
echo ""
echo "API Gateway:     http://localhost:8080"
echo ""
echo "Service Routes:"
echo "  /api/v1        LLM Proxy (OpenAI-compatible)"
echo "  /khoj          Khoj Wiki RAG Engine"
echo "  /genesys       Genesys Memory API"
echo "  /mcp/genesys   Genesys MCP Server"
echo "  /mcp/khoj      Khoj MCP Server"
echo "  /search        SearxNG Private Search"
echo "  /swarm         Swarm Orchestrator"
echo "  /ws/swarm      Swarm WebSocket"
echo ""
echo "For Aider, set environment:"
echo "  export OPENAI_API_BASE=\"http://localhost:8080/api/v1\""
echo "  export OPENAI_API_KEY=\"${IRONSILO_API_KEY:-local-sandbox}\""
echo ""