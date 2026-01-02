#!/bin/bash
# auto_update.sh - Automatically checks for GitHub updates and restarts bot if needed
# This script should be run via cron every 5 minutes

BOT_DIR="/home/ubuntu/repo/Vocard-Fresh"
LOG_FILE="/home/ubuntu/auto_update.log"
BRANCH="main"

cd "$BOT_DIR" || exit 1

# Fetch latest changes from remote
git fetch origin $BRANCH 2>/dev/null

# Check if there are new commits
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date)] Updates detected! Local: $LOCAL, Remote: $REMOTE" >> "$LOG_FILE"
    
    # Pull the latest changes
    git reset --hard origin/$BRANCH >> "$LOG_FILE" 2>&1
    
    echo "[$(date)] Code updated successfully. Restarting bot..." >> "$LOG_FILE"
    
    # Kill the bot (the start_bot.sh watchdog will restart it automatically)
    pkill -f main.py
    
    echo "[$(date)] Bot restarted!" >> "$LOG_FILE"
else
    # No updates (optional: uncomment to log every check)
    # echo "[$(date)] No updates found." >> "$LOG_FILE"
    :
fi
