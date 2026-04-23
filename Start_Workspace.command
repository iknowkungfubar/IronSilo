#!/bin/bash
cd "$(dirname "$0")"

echo "=========================================="
echo "    Starting Local AI Workspace (Mac/Linux)"
echo "=========================================="
echo ""

docker compose up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ [ERROR] Failed to start. Please make sure Docker is open and running!"
    read -p "Press Enter to close..."
    exit 1
fi

# Check if IronClaw is installed and boot it in the background
if command -v ironclaw &> /dev/null; then
    echo "🦀 Starting IronClaw Agent Web UI..."
    export DATABASE_URL="postgres://silo_admin:silo_password@127.0.0.1:5432/ironsilo_vault"
    export OPENAI_API_BASE="http://127.0.0.1:8001/api/v1"
    export OPENAI_API_KEY="local-sandbox"

    nohup ironclaw start > /dev/null 2>&1 &
    echo "🌐 IronClaw UI available at: http://127.0.0.1:8080"
fi

echo ""
echo "✅ [SUCCESS] Your AI Workspace is now running in the background!"
echo "Your tools are ready. Open your terminal for Aider, or browser for Khoj/IronClaw."
echo ""
read -p "Press Enter to close this window..."