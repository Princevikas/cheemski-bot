# 🎵 Cheemski Bot

<div align="center">

![Cheemski Bot](https://i.imgur.com/dIFBwU7.png)

**A powerful Discord music bot with a beautiful web dashboard**

[![Discord](https://img.shields.io/badge/Discord-Bot-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## ✨ Features

- 🎶 **High Quality Music** - Stream from YouTube, Spotify, SoundCloud, Twitch & more
- 🎛️ **Audio Effects** - Nightcore, Bass Boost, Vaporwave, 8D Audio, and more
- 📋 **Playlists** - Save and manage your favorite playlists
- 🌐 **Web Dashboard** - Beautiful web interface to control your music
- 🔁 **Autoplay** - Automatically queue similar songs when your queue ends
- 📥 **Download** - Download songs directly to Discord
- 🌍 **Multi-language** - Support for multiple languages
- ⚡ **Fast & Reliable** - Built on Lavalink for smooth playback

---

## 📋 Table of Contents

1. [Requirements](#-requirements)
2. [Quick Start (Local)](#-quick-start-local)
3. [Railway Deployment](#-railway-deployment)
4. [Configuration](#-configuration)
5. [Environment Variables](#-environment-variables)
6. [Commands](#-commands)
7. [Troubleshooting](#-troubleshooting)

---

## 📦 Requirements

### Software Requirements
- **Python 3.11+** - [Download Python](https://python.org/downloads)
- **MongoDB** - [MongoDB Atlas](https://mongodb.com/atlas) (free tier available)
- **Lavalink Server** - Music streaming server (free public nodes available)
- **Discord Bot Token** - [Discord Developer Portal](https://discord.com/developers/applications)

### Discord Application Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** → Name it "Cheemski" → Create
3. Go to **Bot** tab → Click **"Add Bot"**
4. Copy the **Token** (keep it secret!)
5. Enable these **Privileged Gateway Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Go to **OAuth2** tab → Copy **Client ID** and **Client Secret**

---

## 🚀 Quick Start (Local)

### Step 1: Clone the Repository

```bash
git clone https://github.com/Princevikas/cheemskibot.git
cd cheemskibot
```

### Step 2: Install Dependencies

**For the Bot:**
```bash
cd Vocard-Fresh
pip install -r requirements.txt
```

**For the Dashboard:**
```bash
cd Dashboard-Fresh
pip install -r requirements.txt
```

### Step 3: Configure Settings

#### Bot Configuration (`Vocard-Fresh/settings.json`)

Copy `settings Example.json` to `settings.json` and fill in:

```json
{
    "token": "YOUR_BOT_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "mongodb_url": "mongodb+srv://username:password@cluster.mongodb.net/",
    "mongodb_name": "Cheemski",
    "spotify_client_id": "YOUR_SPOTIFY_CLIENT_ID",
    "spotify_client_secret": "YOUR_SPOTIFY_CLIENT_SECRET",
    "genius_token": "YOUR_GENIUS_TOKEN",
    "tenor_api_key": "YOUR_TENOR_API_KEY"
}
```

#### Dashboard Configuration (`Dashboard-Fresh/settings.json`)

```json
{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "http://127.0.0.1:8000/callback",
    "bot_token": "YOUR_BOT_TOKEN",
    "ipc": {
        "secret": "YOUR_SECRET_KEY",
        "port": 8880
    }
}
```

### Step 4: Configure Lavalink Nodes

In `settings.json`, add your Lavalink nodes:

```json
"nodes": [
    {
        "identifier": "Main",
        "host": "lavalink.server.com",
        "port": 443,
        "password": "your_password",
        "secure": true
    }
]
```

**Free Public Lavalink Nodes:**
- `lavalink.ajiedev.me:443` (password: `https://dsc.gg/ajidevserver`)
- Check [Lavalink Node List](https://lavalink-list.darrennathanael.com/) for more

### Step 5: Run the Bot

**Option A: Run Both Together**
```bash
# Windows - Use the batch file
start_all.bat
```

**Option B: Run Separately**
```bash
# Terminal 1 - Bot
cd Vocard-Fresh
python main.py

# Terminal 2 - Dashboard
cd Dashboard-Fresh
python main.py
```

### Step 6: Invite the Bot

Generate invite URL:
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

---

## ☁️ Railway Deployment

### Step 1: Fork the Repository

1. Go to [GitHub Repository](https://github.com/Princevikas/cheemskibot)
2. Click **Fork** button

### Step 2: Create Railway Account

1. Go to [Railway.app](https://railway.app)
2. Sign up with GitHub

### Step 3: Create New Project

1. Click **"New Project"** → **"Deploy from GitHub repo"**
2. Select your forked repository
3. **Important:** You need to create **2 services**:
   - One for the **Bot** (using `Dockerfile`)
   - One for the **Dashboard** (using `Dockerfile.dashboard`)

### Step 4: Configure Bot Service

1. Click the service → **Settings**
2. Set **Root Directory**: `./`
3. Set **Dockerfile Path**: `Dockerfile`
4. Go to **Variables** tab and add:

| Variable | Value |
|----------|-------|
| `TOKEN` | Your Discord bot token |
| `CLIENT_ID` | Your Discord client ID |
| `CLIENT_SECRET` | Your Discord client secret |
| `MONGODB_URL` | Your MongoDB connection string |
| `MONGODB_NAME` | Database name (e.g., `Cheemski`) |
| `SPOTIFY_CLIENT_ID` | Spotify client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify client secret |
| `GENIUS_TOKEN` | Genius API token |
| `TENOR_API_KEY` | Tenor API key |
| `BOT_ACCESS_USER` | Your Discord ID for admin access |
| `IPC_SECRET` | A secret key for bot-dashboard communication |

### Step 5: Configure Dashboard Service

1. Create another service in the same project
2. Set **Root Directory**: `./`
3. Set **Dockerfile Path**: `Dockerfile.dashboard`
4. Go to **Variables** tab and add:

| Variable | Value |
|----------|-------|
| `CLIENT_ID` | Your Discord client ID |
| `CLIENT_SECRET` | Your Discord client secret |
| `BOT_TOKEN` | Your Discord bot token |
| `REDIRECT_URI` | `https://your-dashboard-url.railway.app/callback` |
| `IPC_SECRET` | Same secret as bot service |

5. Go to **Settings** → **Networking** → **Generate Domain**
6. Copy the generated URL (e.g., `dashboard-xyz.up.railway.app`)

### Step 6: Update Redirect URI

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application → **OAuth2**
3. Add Redirect URL: `https://your-dashboard-url.railway.app/callback`

### Step 7: Deploy

Railway will automatically deploy when you push changes. You can also manually trigger with **"Deploy"** button.

---

## ⚙️ Configuration

### Lavalink Nodes Configuration

```json
"nodes": [
    {
        "identifier": "AjieDev-V4",
        "host": "lavalink.ajiedev.me",
        "port": 443,
        "password": "https://dsc.gg/ajidevserver",
        "secure": true
    }
]
```

### Controller Buttons

Customize your music controller buttons in `settings.json`:

```json
"default_controller": {
    "buttons": [
        {
            "back": {"emoji": "⏮️"},
            "play-pause": {"states": {"pause": {"emoji": "⏸️"}, "resume": {"emoji": "▶️"}}},
            "skip": {"emoji": "⏭️"},
            "stop": {"emoji": "⏹️", "style": "red"},
            "add-fav": {"emoji": "❤️"}
        },
        {
            "autoplay": {"emoji": "📻"},
            "shuffle": {"emoji": "🔀"},
            "loop": {"emoji": "🔂"},
            "download": {"emoji": "📥"},
            "effects": {"emoji": "🎛️"}
        }
    ]
}
```

### Available Button Types
- `back` - Previous track
- `play-pause` - Toggle play/pause
- `skip` - Skip current track
- `stop` - Stop and disconnect
- `add-fav` - Add to favorites
- `autoplay` - Toggle autoplay
- `shuffle` - Shuffle queue
- `loop` - Toggle loop mode
- `download` - Download current track
- `volumeup` / `volumedown` / `volumemute` - Volume controls
- `forward` / `rewind` - Seek controls
- `effects` - Effects dropdown
- `lyrics` - Show lyrics
- `tracks` - Queue dropdown

---

## 🔐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TOKEN` | Discord bot token | ✅ |
| `CLIENT_ID` | Discord application client ID | ✅ |
| `CLIENT_SECRET` | Discord application client secret | ✅ |
| `MONGODB_URL` | MongoDB connection string | ✅ |
| `MONGODB_NAME` | MongoDB database name | ✅ |
| `SPOTIFY_CLIENT_ID` | Spotify API client ID | ❌ |
| `SPOTIFY_CLIENT_SECRET` | Spotify API client secret | ❌ |
| `GENIUS_TOKEN` | Genius API token for lyrics | ❌ |
| `TENOR_API_KEY` | Tenor API key for GIFs | ❌ |
| `BOT_ACCESS_USER` | Discord user IDs with admin access (comma-separated) | ❌ |
| `IPC_SECRET` | Secret key for bot-dashboard IPC | ✅ (for dashboard) |
| `REDIRECT_URI` | OAuth2 callback URL | ✅ (for dashboard) |

---

## 🎮 Commands

### Music Commands
| Command | Description |
|---------|-------------|
| `/play <query>` | Play a song or add to queue |
| `/pause` | Pause the current track |
| `/resume` | Resume playback |
| `/skip` | Skip to next track |
| `/back` | Go to previous track |
| `/stop` | Stop and leave voice channel |
| `/queue` | View the current queue |
| `/nowplaying` | Show current track info |
| `/volume <1-100>` | Set volume level |
| `/loop <off/track/queue>` | Set loop mode |
| `/shuffle` | Shuffle the queue |
| `/seek <time>` | Seek to position |

### Playlist Commands
| Command | Description |
|---------|-------------|
| `/playlist create <name>` | Create a new playlist |
| `/playlist add <name>` | Add current track to playlist |
| `/playlist play <name>` | Play a saved playlist |
| `/playlist list` | View your playlists |

### Fun Commands
| Command | Description |
|---------|-------------|
| `/bonk <user>` | Bonk someone! |
| `/pat <user>` | Pat someone! |
| `/hug <user>` | Hug someone! |

---

## 🔧 Troubleshooting

### Bot won't start
- Check if all required environment variables are set
- Verify your bot token is correct
- Make sure MongoDB is accessible

### Music not playing
- Check if Lavalink nodes are online
- Verify the node password is correct
- Try a different Lavalink node

### Dashboard login loop
- Ensure `REDIRECT_URI` matches exactly (including https)
- Add the redirect URI to Discord OAuth2 settings
- Clear browser cookies and try again

### IPC not connecting
- Verify `IPC_SECRET` is the same on both bot and dashboard
- Check if bot's IPC client is enabled in settings
- For Railway, use the internal service URL

### Download not working
- Ensure `ffmpeg` is installed (included in Docker)
- Check if yt-dlp is up to date

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by Cheemski Team**

</div>
