"""
Smart Command Sync Manager
Prevents Discord rate limiting by only syncing when commands actually change.

Uses MongoDB for state persistence (works with Railway/ephemeral containers).
Falls back to local file storage for local development.
"""
import hashlib
import json
import os
import time
import asyncio
from typing import Optional, Dict, Any
from discord.ext import commands
import function as func

# Discord's official rate limits
DAILY_COMMAND_LIMIT = 200
GLOBAL_SYNC_COOLDOWN = 3600  # 1 hour
GUILD_SYNC_COOLDOWN = 60
SYNC_QUOTA_RESET_HOURS = 24

# MongoDB collection name for sync state
SYNC_COLLECTION = "sync_state"

# Local file fallback for development
LOCAL_SYNC_FILE = os.path.join(func.ROOT_DIR, "sync_state.json")


def _get_command_signature(bot: commands.Bot) -> str:
    """Generate a hash of all registered commands to detect changes"""
    commands_data = []
    
    for cmd in bot.tree.get_commands():
        description = getattr(cmd, 'description', '') or ''
        
        cmd_dict = {
            "name": cmd.name,
            "description": description[:100] if description else "",
            "params": []
        }
        
        if hasattr(cmd, 'parameters'):
            for param in cmd.parameters:
                cmd_dict["params"].append({
                    "name": param.name,
                    "type": str(param.type),
                    "required": getattr(param, 'required', False)
                })
        
        if hasattr(cmd, 'commands'):
            for subcmd in cmd.commands:
                sub_desc = getattr(subcmd, 'description', '') or ''
                cmd_dict["params"].append({
                    "name": f"sub:{subcmd.name}",
                    "description": sub_desc[:50] if sub_desc else ""
                })
        
        commands_data.append(cmd_dict)
    
    commands_data.sort(key=lambda x: x["name"])
    data_str = json.dumps(commands_data, sort_keys=True)
    return hashlib.md5(data_str.encode()).hexdigest()


def _load_local_state() -> Dict[str, Any]:
    """Load sync state from local file (for local development)"""
    try:
        if os.path.exists(LOCAL_SYNC_FILE):
            with open(LOCAL_SYNC_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        func.logger.warning(f"Failed to load local sync state: {e}")
    return None


def _save_local_state(state: Dict[str, Any]):
    """Save sync state to local file (for local development)"""
    try:
        # Remove MongoDB-specific field for local storage
        local_state = {k: v for k, v in state.items() if k != "_id"}
        with open(LOCAL_SYNC_FILE, 'w') as f:
            json.dump(local_state, f, indent=2)
    except Exception as e:
        func.logger.warning(f"Failed to save local sync state: {e}")


async def _load_sync_state() -> Dict[str, Any]:
    """Load sync state from MongoDB, or local file as fallback"""
    # Try MongoDB first
    try:
        if func.MONGO_DB is not None:
            db_name = func.settings.mongodb_name
            collection = func.MONGO_DB[db_name][SYNC_COLLECTION]
            state = await collection.find_one({"_id": "global_sync_state"})
            
            if state:
                # Reset daily quota if 24 hours have passed
                current_time = time.time()
                quota_reset_time = state.get("quota_reset_time", 0)
                if current_time >= quota_reset_time:
                    state["daily_sync_count"] = 0
                    state["quota_reset_time"] = current_time + (SYNC_QUOTA_RESET_HOURS * 3600)
                    await _save_sync_state(state)
                    func.logger.info("Daily sync quota reset")
                return state
    except Exception as e:
        func.logger.warning(f"Failed to load sync state from MongoDB: {e}")
    
    # Fallback to local file (for local development)
    if func.MONGO_DB is None:
        func.logger.info("MongoDB not connected, using local file for sync state")
        local_state = _load_local_state()
        if local_state:
            local_state["_id"] = "global_sync_state"
            return local_state
    
    return _default_state()


def _default_state() -> Dict[str, Any]:
    """Return default sync state"""
    current_time = time.time()
    return {
        "_id": "global_sync_state",
        "last_global_sync": 0,
        "last_guild_syncs": {},
        "command_hash": "",
        "synced_command_count": 0,
        "daily_sync_count": 0,
        "quota_reset_time": current_time + (SYNC_QUOTA_RESET_HOURS * 3600)
    }


async def _save_sync_state(state: Dict[str, Any]):
    """Save sync state to MongoDB, or local file as fallback"""
    # Try MongoDB first
    try:
        if func.MONGO_DB is not None:
            db_name = func.settings.mongodb_name
            collection = func.MONGO_DB[db_name][SYNC_COLLECTION]
            state["_id"] = "global_sync_state"
            await collection.replace_one(
                {"_id": "global_sync_state"},
                state,
                upsert=True
            )
            return
    except Exception as e:
        func.logger.warning(f"Failed to save sync state to MongoDB: {e}")
    
    # Fallback to local file (for local development)
    if func.MONGO_DB is None:
        _save_local_state(state)


async def smart_sync(
    bot: commands.Bot,
    force: bool = False,
    guild_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Smart command sync that prevents rate limiting.
    """
    state = await _load_sync_state()
    current_time = time.time()
    current_hash = _get_command_signature(bot)
    
    result = {
        "synced": False,
        "reason": "",
        "count": 0,
        "was_rate_limited": False
    }
    
    commands_changed = current_hash != state.get("command_hash", "")
    
    if not force and not commands_changed:
        result["reason"] = "Commands unchanged, skipping sync"
        func.logger.info(result["reason"])
        return result
    
    # Check daily quota
    if state.get("daily_sync_count", 0) >= DAILY_COMMAND_LIMIT:
        result["reason"] = "Daily sync quota (200) reached. Try again tomorrow."
        result["was_rate_limited"] = True
        func.logger.warning(result["reason"])
        return result

    # Guild-specific sync
    if guild_id:
        last_guild_sync = state.get("last_guild_syncs", {}).get(str(guild_id), 0)
        cooldown_remaining = GUILD_SYNC_COOLDOWN - (current_time - last_guild_sync)
        
        if not force and cooldown_remaining > 0:
            result["reason"] = f"Guild sync on cooldown ({int(cooldown_remaining)}s remaining)"
            result["was_rate_limited"] = True
            return result
        
        try:
            guild = bot.get_guild(guild_id)
            if guild:
                synced = await bot.tree.sync(guild=guild)
                result["synced"] = True
                result["count"] = len(synced)
                result["reason"] = f"Synced {len(synced)} commands to guild {guild.name}"
                
                if "last_guild_syncs" not in state:
                    state["last_guild_syncs"] = {}
                state["last_guild_syncs"][str(guild_id)] = current_time
                state["daily_sync_count"] = state.get("daily_sync_count", 0) + 1
                await _save_sync_state(state)
                
                func.logger.info(result["reason"])
                return result
        except Exception as e:
            result["reason"] = f"Guild sync failed: {e}"
            func.logger.error(result["reason"])
            return result
    
    # Global sync - check cooldown
    last_global_sync = state.get("last_global_sync", 0)
    cooldown_remaining = GLOBAL_SYNC_COOLDOWN - (current_time - last_global_sync)
    
    if not force and cooldown_remaining > 0:
        result["reason"] = f"Global sync on cooldown ({int(cooldown_remaining)}s remaining). Skipping."
        result["was_rate_limited"] = True
        func.logger.info(result["reason"])
        return result
    
    try:
        synced = await bot.tree.sync()
        result["synced"] = True
        result["count"] = len(synced)
        result["reason"] = f"Synced {len(synced)} global commands"
        
        state["last_global_sync"] = current_time
        state["command_hash"] = current_hash
        state["synced_command_count"] = len(synced)
        state["daily_sync_count"] = state.get("daily_sync_count", 0) + 1
        await _save_sync_state(state)
        
        func.logger.info(result["reason"])
        
    except Exception as e:
        error_msg = str(e)
        if "rate" in error_msg.lower() or "429" in error_msg:
            result["was_rate_limited"] = True
            
            import re
            retry_after = 3600
            match = re.search(r"retry.+?(\d+\.?\d*)", error_msg.lower())
            if match:
                retry_after = float(match.group(1)) + 10
            
            result["reason"] = f"Rate limited. Will retry after {int(retry_after)}s"
            
            # Save the cooldown so next restart respects it
            state["last_global_sync"] = current_time + retry_after - GLOBAL_SYNC_COOLDOWN
            state["command_hash"] = current_hash  # Prevent retry on restart
            await _save_sync_state(state)
        else:
            result["reason"] = f"Sync failed: {e}"
        func.logger.warning(result["reason"])
    
    return result


async def get_sync_status(bot: commands.Bot) -> Dict[str, Any]:
    """Get current sync status without syncing"""
    state = await _load_sync_state()
    current_time = time.time()
    current_hash = _get_command_signature(bot)
    
    global_cooldown = max(0, GLOBAL_SYNC_COOLDOWN - (current_time - state.get("last_global_sync", 0)))
    
    return {
        "commands_changed": current_hash != state.get("command_hash", ""),
        "current_command_count": len(list(bot.tree.get_commands())),
        "last_synced_count": state.get("synced_command_count", 0),
        "global_cooldown_remaining": int(global_cooldown),
        "can_sync_global": global_cooldown <= 0,
        "last_global_sync": state.get("last_global_sync", 0)
    }


async def startup_sync(bot: commands.Bot, version_changed: bool = False):
    """
    Smart startup sync - only syncs if commands actually changed.
    Ignores version_changed to prevent unnecessary syncs on redeploy.
    """
    state = await _load_sync_state()
    current_hash = _get_command_signature(bot)
    stored_hash = state.get("command_hash", "")
    cmd_count = len(list(bot.tree.get_commands()))
    
    # First run on Railway - no hash stored yet
    # Actually sync commands to ensure they exist on Discord
    if not stored_hash:
        func.logger.info(f"First run detected. Syncing {cmd_count} commands to Discord...")
        result = await smart_sync(bot, force=True)
        if result["synced"]:
            func.logger.info(f"First run sync complete: {result['reason']}")
        else:
            func.logger.warning(f"First run sync issue: {result['reason']}")
        return result

    
    # Check if commands actually changed
    if current_hash != stored_hash:
        func.logger.info("Commands changed, syncing...")
        result = await smart_sync(bot, force=False)
        return result
    else:
        func.logger.info(f"No command changes detected. {cmd_count} commands loaded, skipping sync.")
        return {
            "synced": False,
            "reason": "No changes detected",
            "count": state.get("synced_command_count", cmd_count),
            "was_rate_limited": False
        }


async def guild_only_sync(bot: commands.Bot, guild_id: int) -> Dict[str, Any]:
    """
    Sync commands to a specific guild only (faster, no global rate limit).
    
    Args:
        bot: The bot instance
        guild_id: The guild to sync to
        
    Returns:
        Dict with sync result info
    """
    return await smart_sync(bot, guild_id=guild_id, force=False)
