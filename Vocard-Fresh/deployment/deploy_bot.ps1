# Deploy Bot to Oracle VM
# Usage: ./deploy_bot.ps1

$IdentifyFile = "ssh-key-2025-12-28.key"
$HostName = "ubuntu@161.118.182.125"

Write-Host "🚀 Starting Deployment to Oracle Cloud..." -ForegroundColor Cyan

# 1. SSH Trigger Update
Write-Host "📡 Connecting to Server..."
ssh -i $IdentifyFile -o StrictHostKeyChecking=no $HostName "
    echo '📂 Navigating to repo...'
    cd /home/ubuntu/repo/Vocard-Fresh
    
    echo '⬇️ Pulling latest code...'
    git fetch origin main
    git reset --hard origin/main
    
    echo '🔄 Restarting Bot...'
    pkill -f main.py || true
    
    echo '✅ Deployment verification:'
    grep 'Auto-deployment test trigger' cogs/games.py || echo '⚠️ Comment not found (Check Git)'
"

Write-Host "✨ Deployment Command Sent! The watchdog script will restart the bot in ~5 seconds." -ForegroundColor Green
