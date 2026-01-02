# 🐕 Cheemski Bot

> A feature-rich Discord bot with music, fun commands, leveling, moderation, and a live web dashboard - all with Cheems personality!

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

---

## 📁 Project Structure

```
cheemski-bot/
├── Vocard-Fresh/           # 🤖 Discord Bot
│   ├── cogs/               # Bot commands
│   ├── views/              # UI components
│   ├── voicelink/          # Music engine
│   └── main.py             # Bot entry point
│
└── Vocard-Fresh/dashboard/ # 🌐 Web Dashboard
    ├── templates/          # HTML templates
    ├── static/             # CSS, JS, images
    └── main.py             # Dashboard entry point
```

---

## ✨ Features

### 🤖 Discord Bot
- **Music** - High-quality audio via Lavalink (YouTube, Spotify, SoundCloud, Apple Music)
- **Auto Node Switching** - Seamless failover on node errors
- **Fun Commands** - 30+ commands: bonk, pat, hug, slap, games
- **Akinator** - "Cheemski Nator" with achievements
- **XP & Leveling** - Rank cards, role rewards, leaderboards
- **Daily Quests** - Complete tasks for bonus XP
- **Moderation** - kick, ban, mute, warn, purge
- **Spotify Sync** - Real-time sync with adaptive latency compensation

### 🌐 Web Dashboard
- **Music Control** - Play, pause, skip, queue management
- **Settings** - Configure bot per-server
- **Discord OAuth** - Secure login with Discord
- **Real-time Updates** - Live sync with bot via IPC

---

## 📦 Requirements

### Bot Dependencies
```
discord.py==2.5.2       # Discord API
motor==3.6.0            # MongoDB async driver
aiohttp>=3.11.0         # HTTP client
lyricsgenius==3.0.1     # Genius lyrics
PyNaCl>=1.5.0           # Voice encryption
yt-dlp>=2024.0.0        # YouTube downloader
Pillow>=10.0.0          # Image processing
akinator>=2.0.2         # Akinator game
```

### Dashboard Dependencies
```
quart==0.20.0           # Async Flask-like framework
quart_babel==1.0.7      # Internationalization
hypercorn>=0.16.0       # ASGI server
websockets>=12.0        # Real-time communication
gunicorn>=21.0.0        # Production server
```

### External Services Required
- **MongoDB** - Database (Atlas recommended)
- **Lavalink v4** - Audio streaming server
- **Discord Application** - Bot token

### Optional APIs
- **Tenor API** - GIFs (for fun commands)
- **Genius API** - Song lyrics

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- MongoDB database
- Lavalink server (v4)
- Discord bot token

### Bot Installation

```bash
git clone https://github.com/Princevikas/cheemski-bot.git
cd cheemski-bot/Vocard-Fresh

pip install -r requirements.txt
cp settings.json.example settings.json
cp nodes.json.example nodes.json
# Edit settings.json with your credentials

python main.py
```

### Dashboard Installation

```bash
cd dashboard
pip install -r requirements.txt
cp settings.json.example settings.json
# Edit settings.json with your credentials

python main.py
```

**Full guide:** [INSTALLATION.md](Vocard-Fresh/INSTALLATION.md)

---

## ⚙️ Configuration

### Bot Settings (`settings.json`)
```json
{
    "token": "YOUR_DISCORD_BOT_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "genius_token": "YOUR_GENIUS_TOKEN (optional)",
    "mongodb_url": "YOUR_MONGODB_CONNECTION_STRING",
    "mongodb_name": "Vocard"
}
```

### Lavalink Nodes (`nodes.json`)
```json
{
    "nodes": {
        "Local-Node": {
            "host": "localhost",
            "port": 2333,
            "password": "youshallnotpass",
            "secure": false
        }
    }
}
```

---

## 🙏 Credits & Attribution

### Built Upon
- **[Vocard](https://github.com/ChocoMeow/Vocard)** by ChocoMeow - Core music bot framework
- **[Lavalink](https://github.com/lavalink-devs/Lavalink)** - Audio streaming server
- **[discord.py](https://github.com/Rapptz/discord.py)** - Discord API wrapper

### APIs & Services
- **[Tenor API](https://tenor.com/developer)** - GIF integration
- **[Genius API](https://genius.com/api-clients)** - Lyrics
- **[Akinator.py](https://github.com/NinjaSnail1080/akinator.py)** - Akinator game

---

## 🎯 Command Categories

| Category | Description |
|----------|-------------|
| 🎵 Music | Play, queue, filters, lyrics |
| 🎮 Fun | Bonk, pat, hug, games, memes |
| 📈 Leveling | Rank, XP, rewards |
| 🎯 Quests | Daily quests, streaks |
| 🛡️ Moderation | Kick, ban, warn, purge |
| ⚙️ Settings | Server configuration |

---

## 📄 License

MIT License - see [LICENSE](Vocard-Fresh/LICENSE)

This bot is built upon [Vocard](https://github.com/ChocoMeow/Vocard) by ChocoMeow. Please respect the original license.

---

## 💬 Support

- Report bugs: [GitHub Issues](https://github.com/Princevikas/cheemski-bot/issues)
- Feature requests: [GitHub Issues](https://github.com/Princevikas/cheemski-bot/issues)

---

**Made with ❤️ and Cheems energy** 🐕
