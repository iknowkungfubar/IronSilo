#!/bin/bash

# IronSilo Autonomous Orchestrator Loop
# This script forces the agentic CLI to run continuously until the backlog is empty.

BACKLOG_FILE="docs/MASTER_BACKLOG.md"
JOURNAL_FILE="docs/DEV_JOURNAL.md"

echo "====================================================="
echo "  🚀 INITIATING AUTONOMOUS 3D-PRINTER SWARM LOOP 🚀  "
echo "====================================================="

# Ensure files exist
mkdir -p docs
touch $BACKLOG_FILE
touch $JOURNAL_FILE

while true; do
    # 1. Check if there is work to do
    # (Looks for the first line in the backlog that has an unchecked box '- [ ]')
    NEXT_TASK=$(grep -m 1 "^- \[ \]" "$BACKLOG_FILE")

    if [ -z "$NEXT_TASK" ]; then
        echo "✅ Backlog is empty. Running final test suite..."
        pytest tests/
        if [ $? -eq 0 ]; then
            echo "🎉 PROJECT COMPLETE AND FULLY TESTED."
            exit 0
        else
            echo "⚠️ Final tests failed. Feeding errors back to agent..."
            NEXT_TASK="Fix failing tests in final test suite."
        fi
    fi

    echo "-----------------------------------------------------"
    echo "🎯 NEXT TASK: $NEXT_TASK"
    echo "-----------------------------------------------------"

    # 2. Formulate the prompt for this specific loop iteration
    PROMPT="SYSTEM DIRECTIVE: You are an autonomous worker. 
    1. Update $JOURNAL_FILE with your plan for this task.
    2. Write the tests for this task.
    3. Write the implementation code.
    4. When complete, update $BACKLOG_FILE by changing '- [ ]' to '- [x]' for this task.
    
    YOUR CURRENT TASK IS: $NEXT_TASK
    
    Do not stop until this specific task is fully implemented and tested. Do not ask for human intervention."

    # 3. Execute the Agent (Replace 'opencode' with your actual CLI command)
    # If using Aider, it would be: aider --message "$PROMPT" --yes
    opencode --message "$PROMPT"

    # 4. Agent finished. Run tests to verify.
    echo "🧪 Agent finished. Running test suite..."
    pytest tests/ > test_output.txt 2>&1
    TEST_EXIT_CODE=$?

    if [ $TEST_EXIT_CODE -ne 0 ]; then
        echo "❌ Tests failed! Forcing agent to fix errors..."
        ERROR_LOG=$(cat test_output.txt | tail -n 30)
        
        # Feed the error directly back into the agent
        ERROR_PROMPT="CRITICAL FAILURE. The test suite failed after your last changes. 
        Read the following error log, find the bug, and fix the code immediately:
        
        $ERROR_LOG"
        
        opencode --message "$ERROR_PROMPT"
    else
        echo "✅ Tests passed! Moving to next backlog item..."
        sleep 2 # Brief pause before hammering the API again
    fi

done