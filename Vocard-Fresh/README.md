# 🐕 Cheemski Bot

> A feature-rich Discord bot combining music, fun commands, leveling, and server management - all with Cheems personality!

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

---

## 🎯 About

Cheemski Bot is built on the excellent [Vocard](https://github.com/ChocoMeow/Vocard) music bot by ChocoMeow, with extensive custom additions including fun commands, games, leveling systems, and more. We're grateful to the Vocard team for providing such a solid foundation!

---

## ✨ Features

### 🎵 Music System (from Vocard)
- High-quality audio via Lavalink
- Multi-source support (YouTube, Spotify, SoundCloud, Apple Music)
- Queue management, filters, and effects
- Lyrics from multiple sources
- Live web dashboard

**Our additions:**
- Automatic node switching on errors
- Bot stays in voice channel during node failures
- Enhanced Spotify sync with adaptive latency compensation

### 🎮 Fun & Games (Custom)
- 30+ fun commands: bonk, pat, hug, slap, and more
- Akinator game ("Cheemski Nator") with achievements
- Mini-games: 8ball, RPS, coinflip, number guessing
- Memes & quotes from various APIs
- All responses in Cheems style!

### 📈 Progression Systems (Custom)
- **XP & Leveling** - Rank cards, role rewards, leaderboards
- **Daily Quests** - Complete tasks for bonus XP
- **Statistics** - Track interactions and command usage

### 🛡️ Server Management (Custom)
- Moderation: kick, ban, mute, warn, purge
- Audit logs for server actions
- Welcome/Goodbye cards with custom images
- Announcements and suggestions system

---

## 🙏 Credits & Attribution

### Built Upon
- **[Vocard](https://github.com/ChocoMeow/Vocard)** by ChocoMeow - Core music bot framework
- **[Lavalink](https://github.com/lavalink-devs/Lavalink)** - Audio streaming server
- **[discord.py](https://github.com/Rapptz/discord.py)** - Discord API wrapper

### APIs & Services
- **[Tenor API](https://tenor.com/developer)** - GIF integration
- **[Genius API](https://genius.com/api-clients)** - Lyrics
- **[Akinator.py](https://github.com/NinjaSnail1080/akinator.py)** - Akinator game library

### Inspiration
- Various Discord bots for feature ideas
- Community feedback and suggestions

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- MongoDB database
- Lavalink server
- Discord bot token

### Installation

```bash
# Clone repository
git clone https://github.com/Princevikas/cheemski-bot.git
cd cheemski-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Configure Lavalink nodes
cp nodes.json.example nodes.json
# Add your Lavalink servers

# Run the bot
python main.py
```

**Full guide:** [INSTALLATION.md](INSTALLATION.md)

---

## 📚 Documentation

- [Installation Guide](INSTALLATION.md)
- [Configuration Guide](CONFIGURATION.md)
- [Commands Reference](COMMANDS.md)

---

## 🎯 Command Categories

| Category | Description |
|----------|-------------|
| 🎵 Music | Play, queue, filters, lyrics (from Vocard) |
| 🎮 Fun | Bonk, pat, hug, games, memes (custom) |
| 📈 Leveling | Rank, XP, rewards (custom) |
| 🎯 Quests | Daily quests, streaks (custom) |
| 🛡️ Moderation | Kick, ban, warn, purge (custom) |
| ⚙️ Settings | Server configuration |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE)

### Important Attribution

This bot is built upon [Vocard](https://github.com/ChocoMeow/Vocard) by ChocoMeow. The core music functionality, player system, and many foundational features come from Vocard. We've added custom features on top of this excellent foundation.

**Please respect the original Vocard license and give credit where it's due.**

---

## 💬 Support

- Report bugs: [GitHub Issues](https://github.com/Princevikas/cheemski-bot/issues)
- Feature requests: [GitHub Issues](https://github.com/Princevikas/cheemski-bot/issues)

---

## 🌟 Acknowledgments

Special thanks to:
- **ChocoMeow** and the Vocard team for the amazing music bot foundation
- **Lavalink developers** for the robust audio streaming server
- **discord.py team** for the excellent Discord library
- Everyone who contributed ideas and feedback

---

**Made with ❤️ and Cheems energy** 🐕
