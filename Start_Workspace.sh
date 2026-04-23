#!/bin/bash
cd "$(dirname "$0")"

echo "================================================="
echo "    Starting Local AI Workspace (macOS / Linux)  "
echo "================================================="
echo ""

# Start the Docker containers
docker compose up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ [ERROR] Failed to start. Please make sure Docker/Podman is running!"
    exit 1
fi

# Check if IronClaw is installed and boot it in the background
if command -v ironclaw &> /dev/null; then
    echo "🦀 Starting IronClaw Agent Web UI..."
    export DATABASE_URL="postgres://ironclaw:ironclaw@127.0.0.1:5432/ironclaw"
    export OPENAI_API_BASE="http://127.0.0.1:8001/api/v1"
    export OPENAI_API_KEY="local-sandbox"

    # Run ironclaw in the background and discard output
    nohup ironclaw start > /dev/null 2>&1 &
    echo "🌐 IronClaw UI available at: http://127.0.0.1:8080"
fi

echo ""
echo "✅ [SUCCESS] Your AI Workspace is now running!"
echo "You can now open this folder in VS Code."
echo ""
