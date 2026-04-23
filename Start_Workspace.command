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

echo ""
echo "✅ [SUCCESS] Your AI Workspace is now running in the background!"
echo "Your tools are ready. Open your terminal for Aider, or browser for Khoj/IronClaw."
echo ""
read -p "Press Enter to close this window..."