@echo off
title IronSilo - True Silo API Gateway
echo ==========================================
echo   IronSilo - True Silo API Gateway Launch
echo ==========================================
echo.

cd /d "%~dp0"
docker compose up -d

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start. Please make sure Docker Desktop is open and running!
    pause
    exit /b %errorlevel%
)

echo.
echo Waiting for services to be healthy...
timeout /t 5 /nobreak > nul

echo.
echo ==========================================
echo            True Silo is Running!
echo ==========================================
echo.
echo API Gateway:     http://localhost:8080
echo.
echo Service Routes:
echo   /api/v1        LLM Proxy ^(OpenAI-compatible^)
echo   /khoj          Khoj Wiki RAG Engine
echo   /genesys       Genesys Memory API
echo   /mcp/genesys   Genesys MCP Server
echo   /mcp/khoj      Khoj MCP Server
echo   /search        SearxNG Private Search
echo   /swarm         Swarm Orchestrator
echo   /ws/swarm      Swarm WebSocket
echo.
echo For Aider, set environment:
echo   set OPENAI_API_BASE=http://localhost:8080/api/v1
echo   set OPENAI_API_KEY=local-sandbox
echo.
pause