# 🐕 Cheemski Bot - Installation Guide

Complete guide to install and run the bot on **any platform**.

---

## 📋 Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Bot runtime |
| Java | 17+ | Lavalink audio server |
| MongoDB | Any | Database |
| Git | Any | Clone repository |

---

## 🚀 Quick Start (All Platforms)

### 1. Clone the Repository
```bash
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot
```

### 2. Run Platform-Specific Setup
```bash
# Linux/macOS
bash scripts/setup_unix.sh

# Windows (Run as Admin)
scripts\setup_windows.bat

# Termux (Android)
bash scripts/setup_termux.sh
```

### 3. Configure the Bot
Edit `settings.json` with your:
- Discord Bot Token
- MongoDB URI
- Lavalink credentials

### 4. Start the Bot
```bash
# Linux/macOS/Termux
./run.sh

# Windows
run.bat
```

---

## 🐧 Linux Installation (Detailed)

### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Java 17
sudo apt install -y openjdk-17-jre-headless

# Clone and setup
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot
bash scripts/setup_unix.sh
```

### Fedora/RHEL
```bash
sudo dnf install -y python3.11 python3-pip java-17-openjdk git
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot
bash scripts/setup_unix.sh
```

### Arch Linux
```bash
sudo pacman -S python python-pip jre17-openjdk git
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot
bash scripts/setup_unix.sh
```

---

## 🍎 macOS Installation

### Using Homebrew
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 openjdk@17 git

# Clone and setup
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot
bash scripts/setup_unix.sh
```

---

## 🪟 Windows Installation

### Prerequisites
1. **Python 3.11+**: Download from [python.org](https://python.org)
   - ⚠️ Check "Add Python to PATH" during installation!
2. **Java 17+**: Download from [Adoptium](https://adoptium.net/)
3. **Git**: Download from [git-scm.com](https://git-scm.com/)

### Setup
```cmd
# Open Command Prompt as Administrator
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot
scripts\setup_windows.bat
```

### Running
```cmd
# Start Lavalink (Terminal 1)
cd lavalink
java -jar Lavalink.jar

# Start Bot (Terminal 2)
run.bat
```

---

## 📱 Termux (Android) Installation

### Initial Setup
```bash
# Update Termux
pkg update && pkg upgrade -y

# Install dependencies
pkg install -y python python-pip git openjdk-17 build-essential

# Allow storage access
termux-setup-storage

# Clone repository
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot

# Run setup script
bash scripts/setup_termux.sh
```

### Running on Termux
```bash
# Prevent Android from killing the process
termux-wake-lock

# Start Lavalink (Session 1)
./run_lavalink.sh

# Start Bot (Session 2 - use tmux)
pkg install tmux
tmux new -s bot
./run_termux.sh
# Press Ctrl+B then D to detach
```

### Termux Tips
- Use `tmux` to run multiple sessions
- Run `termux-wake-lock` to prevent sleep
- Edit config: `nano settings.json`
- Check logs: `cat logs/vocard.log`

---

## 🐳 Docker Installation

### Using Docker Compose (Recommended)
```bash
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot

# Edit settings first
cp "settings Example.json" settings.json
nano settings.json

# Start with Docker Compose
docker-compose up -d
```

### Manual Docker
```bash
# Build image
docker build -t cheemskibot .

# Run container
docker run -d \
  --name cheemskibot \
  -v $(pwd)/settings.json:/app/settings.json \
  cheemskibot
```

---

## ☁️ Cloud Hosting

### Railway
1. Fork the repository on GitHub
2. Go to [railway.app](https://railway.app)
3. Create new project → Deploy from GitHub repo
4. Add environment variables from settings.json
5. Deploy!

### Heroku
```bash
heroku create cheemskibot
heroku buildpacks:add heroku/python
heroku buildpacks:add heroku/jvm
git push heroku main
```

### Replit
1. Import from GitHub
2. Add `settings.json` to Secrets
3. Click Run

---

## ⚙️ Configuration

### settings.json Structure
```json
{
    "token": "YOUR_DISCORD_BOT_TOKEN",
    "bot_prefix": "!",
    "activity": ["Playing music 🎵"],
    "mongo_uri": "mongodb+srv://...",
    "nodes": {
        "DEFAULT": {
            "host": "localhost",
            "port": 2333,
            "password": "youshallnotpass"
        }
    }
}
```

### Required Settings
| Key | Description |
|-----|-------------|
| `token` | Discord bot token from [Discord Developer Portal](https://discord.com/developers/applications) |
| `mongo_uri` | MongoDB connection string ([MongoDB Atlas](https://www.mongodb.com/atlas) for free) |
| `nodes` | Lavalink server configuration |

---

## 🔊 Lavalink Setup

### Option 1: Local Lavalink
```bash
cd lavalink
java -jar Lavalink.jar
```

### Option 2: Free Hosted Lavalink
Use free public Lavalink servers (less reliable):
```json
"nodes": {
    "DEFAULT": {
        "host": "lavalink.devamop.in",
        "port": 443,
        "password": "DevamOP",
        "secure": true
    }
}
```

---

## 🔧 Troubleshooting

### Bot won't start
- Check `settings.json` is valid JSON
- Verify bot token is correct
- Check MongoDB connection

### No music playing
- Ensure Lavalink is running
- Check Lavalink host/port/password in settings
- Verify bot has voice permissions

### Rate Limited (429)
- Wait 15-30 minutes
- Don't restart rapidly
- Check for credential leaks

### Termux crashes
- Enable wake lock: `termux-wake-lock`
- Use tmux for background running
- Check storage permissions

---

## 📞 Support

- GitHub Issues: [Report bugs](https://github.com/Princevikas/cheemskibot/issues)
- Discord Server: [Join for help](https://discord.gg/your-invite)

---

Made with ❤️ by Cheemski Team
