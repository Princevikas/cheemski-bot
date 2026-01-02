#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Cheemski Bot - Termux (Android) Installation Script
# =============================================================================
# This script sets up the bot from scratch on Termux
# Run with: bash setup_termux.sh
# =============================================================================

set -e

echo "🐕 Cheemski Bot - Termux Installation"
echo "======================================"
echo ""

# Update packages
echo "[1/7] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install Python
echo ""
echo "[2/7] Installing Python..."
pkg install -y python python-pip

# Install Git (if not already)
echo ""
echo "[3/7] Installing Git..."
pkg install -y git

# Install Java (for Lavalink)
echo ""
echo "[4/7] Installing Java..."
pkg install -y openjdk-17

# Install required build tools
echo ""
echo "[5/7] Installing build dependencies..."
pkg install -y build-essential libffi openssl

# Create virtual environment
echo ""
echo "[6/7] Creating virtual environment..."
python -m venv venv
source venv/bin/activate

# Install Python dependencies
echo ""
echo "[7/7] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create settings if not exists
if [ ! -f "settings.json" ]; then
    if [ -f "settings Example.json" ]; then
        cp "settings Example.json" settings.json
        echo ""
        echo "⚠️  Created settings.json - EDIT IT WITH YOUR BOT TOKEN!"
    fi
fi

# Create run script for Termux
cat > run_termux.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
source venv/bin/activate
python main.py
EOF
chmod +x run_termux.sh

# Create Lavalink run script
cat > run_lavalink.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd lavalink
java -jar Lavalink.jar
EOF
chmod +x run_lavalink.sh

echo ""
echo "======================================"
echo "🎉 Termux Installation Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. nano settings.json  (edit with your bot token)"
echo "  2. ./run_lavalink.sh   (start Lavalink in one session)"
echo "  3. ./run_termux.sh     (start bot in another session)"
echo ""
echo "Tips for Termux:"
echo "  - Use 'termux-wake-lock' to prevent Android from killing the bot"
echo "  - Run in tmux/screen for background operation"
echo "  - pkg install tmux (recommended)"
echo ""
