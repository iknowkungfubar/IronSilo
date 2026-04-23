#!/bin/bash
cd "$(dirname "$0")"

echo "=========================================="
echo "    Stopping Local AI Workspace (Mac/Linux)"
echo "=========================================="
echo ""

docker compose down

echo ""
echo "✅ [SUCCESS] Workspace stopped safely. Your computer's RAM has been freed."
echo ""
read -p "Press Enter to close this window..."
