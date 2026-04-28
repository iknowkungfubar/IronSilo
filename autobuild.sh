#!/bin/bash

# IronSilo Autonomous Orchestrator Loop v2.0
BACKLOG_FILE="docs/MASTER_BACKLOG.md"
JOURNAL_FILE="docs/DEV_JOURNAL.md"

echo "====================================================="
echo "  🚀 INITIATING AUTONOMOUS 3D-PRINTER SWARM LOOP 🚀  "
echo "====================================================="

# Ensure files exist
mkdir -p docs
touch "$BACKLOG_FILE"
touch "$JOURNAL_FILE"

# Failsafe: Check if the CLI tool exists
if ! command -v opencode &> /dev/null; then
    echo "❌ ERROR: 'opencode' command not found. Please ensure it is installed and in your PATH."
    exit 1
fi

while true; do
    # 1. Find next task (Tolerates leading spaces before the '- [ ]')
    NEXT_TASK=$(grep -m 1 -E "^\s*- \[ \]" "$BACKLOG_FILE")

    # 2. Handle Empty Backlog & Final Testing
    if [ -z "$NEXT_TASK" ]; then
        echo "✅ Backlog appears empty. Running final test suite..."
        pytest tests/ > test_output.txt 2>&1
        TEST_EXIT_CODE=$?
        
        if [ $TEST_EXIT_CODE -eq 0 ]; then
            echo "🎉 PROJECT COMPLETE AND FULLY TESTED."
            exit 0
        else
            echo "⚠️ Final tests failed! Forcing agent to fix..."
            NEXT_TASK="- [ ] Fix failing tests in final test suite."
            # BUGFIX: We MUST physically write this to the backlog so it isn't lost on the next loop
            echo "$NEXT_TASK" >> "$BACKLOG_FILE"
        fi
    fi

    echo "-----------------------------------------------------"
    echo "🎯 NEXT TASK: $NEXT_TASK"
    echo "-----------------------------------------------------"

    # 3. Create a temporary prompt file (safest way to pass multi-line text to LLM CLIs)
    cat <<EOF > .temp_prompt.txt
SYSTEM DIRECTIVE: You are an autonomous worker. 
1. Update $JOURNAL_FILE with your plan for this task.
2. Write the tests for this task.
3. Write the implementation code.
4. When complete, update $BACKLOG_FILE by changing the exact line "- [ ]" to "- [x]" for this task.

YOUR CURRENT TASK IS: $NEXT_TASK

Do not stop until this specific task is fully implemented and tested. Do not ask for human intervention.
EOF

    # Read the prompt back into a variable safely
    PROMPT=$(cat .temp_prompt.txt)
    
    echo "🤖 Waking up agent..."
    # BUGFIX: Add your auto-confirm flag (e.g., -y). If opencode crashes, sleep 3s to prevent CPU runaway loops.
    opencode --message "$PROMPT" -y || sleep 3
    
    echo "🧪 Agent finished. Running test suite..."
    pytest tests/ > test_output.txt 2>&1
    TEST_EXIT_CODE=$?

    if [ $TEST_EXIT_CODE -ne 0 ]; then
        echo "❌ Tests failed! Forcing agent to fix errors..."
        # Grab only the last 40 lines of the error to save token context limits
        tail -n 40 test_output.txt > .temp_error.txt
        
        cat <<EOF > .temp_error_prompt.txt
CRITICAL FAILURE. The test suite failed after your last changes. 
Read the following error log, find the bug, and fix the code immediately:

$(cat .temp_error.txt)
EOF
        ERROR_PROMPT=$(cat .temp_error_prompt.txt)
        opencode --message "$ERROR_PROMPT" -y || sleep 3
    else
        echo "✅ Tests passed! Checking if agent marked task complete..."
        
        # BUGFIX: The "Agent Forgot" Catcher
        # If the agent fixed the code but forgot to check off the box, we do it for them
        # so the script doesn't feed them the exact same task again.
        
        # Escape special characters in the task string so sed doesn't crash
        ESCAPED_TASK=$(echo "$NEXT_TASK" | sed 's/[.[\*^$]/\\&/g')
        
        if grep -q "$ESCAPED_TASK" "$BACKLOG_FILE"; then
            echo "⚠️ Agent forgot to check off the task. Auto-checking to prevent infinite loop..."
            
            # Cross-platform compatibility for sed (macOS vs Linux)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/$ESCAPED_TASK/${ESCAPED_TASK/- \[ \]/- \[x\]}/" "$BACKLOG_FILE"
            else
                sed -i "s/$ESCAPED_TASK/${ESCAPED_TASK/- \[ \]/- \[x\]}/" "$BACKLOG_FILE"
            fi
        fi
        
        echo "⏳ Cooling down for 2 seconds..."
        sleep 2
    fi
done