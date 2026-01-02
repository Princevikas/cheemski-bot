#!/bin/bash
# Auto-restart watchdog script for Vocard Bot
# Prevents duplicate instances using PID lock file

BOT_DIR="/home/ubuntu/repo/Vocard-Fresh"
PID_FILE="/home/ubuntu/bot.pid"

cd "$BOT_DIR" || { echo "Directory not found!"; exit 1; }

# Function to check if bot is already running
is_bot_running() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            return 0  # Running
        fi
    fi
    return 1  # Not running
}

# Function to kill any existing bot processes
kill_existing() {
    echo "Killing any existing bot processes..."
    pkill -f "main.py" 2>/dev/null || true
    sleep 1
}

# Ensure only one instance of this script runs
if is_bot_running; then
    echo "Bot is already running (PID: $(cat $PID_FILE)). Exiting."
    exit 0
fi

# Cleanup any stale processes before starting
kill_existing

echo "Starting Vocard Auto-Restart Watchdog..."
echo "Press Ctrl+C to stop the loop."

while true; do
    echo "----------------------------------------"
    echo "Launching Bot at $(date)"
    echo "----------------------------------------"
    
    # Run the bot in background, save PID
    ./venv/bin/python3 main.py 2>> crash.log &
    BOT_PID=$!
    echo $BOT_PID > "$PID_FILE"
    echo "Bot started with PID: $BOT_PID"
    
    # Wait for the bot process to finish
    wait $BOT_PID
    EXIT_CODE=$?
    
    echo "Bot stopped with exit code $EXIT_CODE"
    rm -f "$PID_FILE"
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Bot stopped safely. Restarting in 5 seconds..."
    else
        echo "⚠️ Bot crashed! Restarting in 5 seconds..."
    fi
    
    sleep 5
done
