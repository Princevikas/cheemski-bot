# 📦 Installation Guide

## Prerequisites

Before installing Cheemski Bot, ensure you have:

- **Python 3.10 or higher**
- **MongoDB** (local or cloud instance like MongoDB Atlas)
- **Lavalink server** (for music functionality)
- **Discord bot token** from [Discord Developer Portal](https://discord.com/developers/applications)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/YourUsername/cheemski-bot.git
cd cheemski-bot
```

---

## Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Required packages include:**
- `discord.py` - Discord API wrapper
- `pymongo` - MongoDB driver
- `aiohttp` - Async HTTP client
- `Pillow` - Image processing
- `akinator.py` - Akinator game
- And more...

---

## Step 3: Set Up MongoDB

### Option A: MongoDB Atlas (Cloud - Recommended)

1. Create a free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster
3. Add a database user
4. Whitelist your IP address (or use `0.0.0.0/0` for all IPs)
5. Get your connection string

### Option B: Local MongoDB

```bash
# Install MongoDB locally
# Windows: Download from mongodb.com
# Linux: sudo apt install mongodb
# macOS: brew install mongodb-community

# Start MongoDB
mongod
```

---

## Step 4: Set Up Lavalink (Music Server)

### Quick Start with Docker

```bash
cd lavalink
docker-compose up -d
```

### Manual Setup

1. Download Lavalink from [GitHub](https://github.com/lavalink-devs/Lavalink/releases)
2. Create `application.yml` (see `lavalink/application.yml` for example)
3. Run: `java -jar Lavalink.jar`

---

## Step 5: Configure Environment Variables

1. Copy the example file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```env
DISCORD_TOKEN=your_bot_token_here
MONGODB_URL=your_mongodb_connection_string_here
GENIUS_TOKEN=your_genius_token_here
TENOR_API_KEY=your_tenor_api_key_here
```

### Getting API Keys

- **Discord Token**: [Discord Developer Portal](https://discord.com/developers/applications)
- **Genius Token**: [Genius API](https://genius.com/api-clients)
- **Tenor API Key**: [Tenor API](https://tenor.com/developer/keyregistration)

---

## Step 6: Configure Lavalink Nodes

1. Copy the example file:
```bash
cp nodes.json.example nodes.json
```

2. Edit `nodes.json` with your Lavalink server details:
```json
{
    "nodes": {
        "Local-Node": {
            "host": "localhost",
            "port": 2333,
            "password": "youshallnotpass",
            "secure": false,
            "identifier": "Local-Node"
        }
    }
}
```

---

## Step 7: Run the Bot

```bash
python main.py
```

You should see:
```
[INFO] Logged in as YourBot#1234
[INFO] Node [Local-Node] is connected!
```

---

## 🎉 Success!

Your bot is now running! Invite it to your server using:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

---

## 🐛 Troubleshooting

### Bot won't start
- Check your `DISCORD_TOKEN` is correct
- Ensure MongoDB is running and accessible
- Verify Python version: `python --version`

### Music not working
- Ensure Lavalink is running: `docker ps` or check Java process
- Verify `nodes.json` has correct host/port/password
- Check Lavalink logs for errors

### Commands not showing
- Run `/help` to sync commands
- Check bot has `applications.commands` scope
- Verify bot permissions in server

---

## 📚 Next Steps

- Read [CONFIGURATION.md](CONFIGURATION.md) for advanced settings
- Check [COMMANDS.md](COMMANDS.md) for command reference
- Report issues on [GitHub](https://github.com/YourUsername/cheemski-bot/issues)
