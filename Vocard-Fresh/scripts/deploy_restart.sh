#!/bin/bash

# Gracefully restart the bot by killing the process
# The watchdog (start_bot.sh) will automatically restart it

echo "🔄 Triggering bot restart sequence..."

if pgrep -f "python3 main.py" > /dev/null; then
    pkill -f "python3 main.py"
    echo "✅ Bot process killed. Watchdog will restart it."
else
    echo "⚠️ Bot was not running. Watchdog should start it if active."
fi

# Always exit with success to keep GitHub Actions green
exit 0
