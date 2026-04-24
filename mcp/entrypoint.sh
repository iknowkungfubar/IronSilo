#!/bin/bash
set -e

# Default server type
SERVER_TYPE="${MCP_SERVER_TYPE:-genesys}"

echo "Starting MCP server: $SERVER_TYPE"

case "$SERVER_TYPE" in
    genesys)
        echo "Starting Genesys MCP server..."
        exec uvicorn mcp.genesys_server:app --host 0.0.0.0 --port 8000 --log-level info
        ;;
    khoj)
        echo "Starting Khoj MCP server..."
        exec uvicorn mcp.khoj_server:app --host 0.0.0.0 --port 8000 --log-level info
        ;;
    *)
        echo "Unknown server type: $SERVER_TYPE"
        echo "Available types: genesys, khoj"
        exit 1
        ;;
esac
