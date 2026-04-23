#!/bin/bash
cd "$(dirname "$0")"

echo "================================================="
echo "    Stopping Local AI Workspace (macOS / Linux)  "
echo "================================================="
echo ""

# Stop the Docker containers
docker compose down

# Kill IronClaw if it was started by the script
if pgrep -f "ironclaw start" > /dev/null; then
    echo "🦀 Stopping IronClaw Agent..."
    pkill -f "ironclaw start"
fi

echo ""
echo "✅ [SUCCESS] Workspace stopped safely. RAM freed."
echo ""
