"""MIT License

Copyright (c) 2023 - present Vocard Development

Session Persistence - Save/Restore player state on restart using MongoDB
"""

import discord
import time
import voicelink

from discord.ext import commands, tasks
import function as func

SESSION_TIMEOUT = 900  # 15 minutes in seconds


class Session(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.sessions_restored = False
        self.sessions_db = None
    
    async def cog_load(self):
        """Initialize MongoDB collection and start save loop"""
        # Create sessions collection in MongoDB (MONGO_DB is client, need db_name first)
        db_name = func.settings.mongodb_name
        self.sessions_db = func.MONGO_DB[db_name]["sessions"]
        self.save_sessions_loop.start()
    
    async def cog_unload(self):
        """Save sessions one last time before unloading"""
        self.save_sessions_loop.cancel()
        await self.save_all_sessions()
    
    def serialize_track(self, track: voicelink.Track) -> dict:
        """Serialize a track to dict for storage"""
        if not track:
            return None
        return {
            "track_id": track.track_id,
            "title": track.title,
            "author": track.author,
            "uri": track.uri,
            "length": track.length,
            "requester_id": track.requester.id if track.requester else None
        }
    
    def serialize_player(self, player: voicelink.Player) -> dict:
        """Serialize a player's state to dict"""
        if not player or not player.channel:
            return None
        
        # Serialize queue
        queue_tracks = []
        for track in player.queue.tracks():
            serialized = self.serialize_track(track)
            if serialized:
                queue_tracks.append(serialized)
        
        return {
            "_id": player.guild.id,
            "guild_id": player.guild.id,
            "voice_channel_id": player.channel.id,
            "text_channel_id": getattr(player, 'text_channel', None).id if getattr(player, 'text_channel', None) else None,
            "current_track": self.serialize_track(player.current),
            "position": player.position,
            "queue": queue_tracks,
            "volume": player.volume,
            "loop_mode": player.queue._repeat.mode.name if player.queue._repeat else "OFF",
            "autoplay": player.settings.get("autoplay", False),
            "is_paused": player.is_paused,
            "timestamp": int(time.time())
        }
    
    async def save_all_sessions(self):
        """Save all active player sessions to MongoDB"""
        if self.sessions_db is None:
            return
        
        for guild in self.bot.guilds:
            player = guild.voice_client
            if player and isinstance(player, voicelink.Player):
                if player.is_playing or player.is_paused:
                    data = self.serialize_player(player)
                    if data:
                        try:
                            # Upsert session data
                            await self.sessions_db.replace_one(
                                {"_id": guild.id},
                                data,
                                upsert=True
                            )
                        except Exception as e:
                            func.logger.error(f"Failed to save session for guild {guild.id}: {e}")
                else:
                    # Remove session if not playing
                    try:
                        await self.sessions_db.delete_one({"_id": guild.id})
                    except:
                        pass
    
    async def load_sessions(self) -> list:
        """Load all sessions from MongoDB"""
        if self.sessions_db is None:
            return []
        
        try:
            sessions = await self.sessions_db.find({}).to_list(None)
            return sessions
        except Exception as e:
            func.logger.error(f"Failed to load sessions: {e}")
            return []
    
    async def restore_session(self, data: dict) -> bool:
        """Restore a single session"""
        try:
            guild_id = data["guild_id"]
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return False
            
            # Get channels
            voice_channel = guild.get_channel(data["voice_channel_id"])
            text_channel = guild.get_channel(data["text_channel_id"]) if data.get("text_channel_id") else None
            
            if not voice_channel:
                return False
            
            # Check if voice channel has members (don't restore if empty)
            if len(voice_channel.members) == 0:
                func.logger.debug(f"Session restore skipped for {guild.name}: voice channel is empty")
                return False
            
            # Get guild settings
            settings = await func.get_settings(guild.id)
            
            # Get a member for requester context (use first non-bot member)
            requester = None
            for member in voice_channel.members:
                if not member.bot:
                    requester = member
                    break
            if not requester:
                func.logger.debug(f"Session restore skipped for {guild.name}: no non-bot members")
                return False
            
            # Connect to voice channel with proper player initialization
            try:
                player = await voice_channel.connect(
                    cls=voicelink.Player(
                        self.bot, voice_channel, func.TempCtx(requester, voice_channel), settings
                    )
                )
                player.text_channel = text_channel
            except Exception as e:
                func.logger.error(f"Failed to connect for session restore: {e}")
                return False
            
            # Set volume
            await player.set_volume(data.get("volume", 100))
            
            # Set autoplay
            player.settings["autoplay"] = data.get("autoplay", False)
            
            # Restore current track
            current_data = data.get("current_track")
            if current_data and current_data.get("track_id"):
                try:
                    # Decode and create track
                    track_info = voicelink.decode(current_data["track_id"])
                    
                    # Get requester (use first member in channel as fallback)
                    requester = None
                    if current_data.get("requester_id"):
                        requester = guild.get_member(current_data["requester_id"])
                    if not requester and voice_channel.members:
                        requester = voice_channel.members[0]
                    
                    track = voicelink.Track(
                        track_id=current_data["track_id"],
                        info=track_info,
                        requester=requester
                    )
                    
                    # Add to queue first
                    await player.add_track(track)
                    
                    # Restore queue items
                    for track_data in data.get("queue", []):
                        if track_data.get("track_id"):
                            try:
                                info = voicelink.decode(track_data["track_id"])
                                req = guild.get_member(track_data.get("requester_id")) or requester
                                queue_track = voicelink.Track(
                                    track_id=track_data["track_id"],
                                    info=info,
                                    requester=req
                                )
                                await player.add_track(queue_track)
                            except:
                                continue
                    
                    # Start playing
                    if not player.is_playing:
                        await player.do_next()
                    
                    # Seek to saved position
                    saved_position = data.get("position", 0)
                    if saved_position > 0:
                        await player.seek(saved_position)
                    
                    # Set loop mode
                    loop_mode = data.get("loop_mode", "OFF")
                    if loop_mode in voicelink.LoopType.__members__:
                        await player.set_repeat(voicelink.LoopType[loop_mode])
                    
                    # Handle pause state
                    if data.get("is_paused"):
                        await player.set_pause(True)
                    
                    func.logger.info(f"Session restored for guild {guild.name} ({guild_id})")
                    return True
                    
                except Exception as e:
                    func.logger.error(f"Failed to restore track: {e}")
                    return False
            
            return False
            
        except Exception as e:
            func.logger.error(f"Session restore failed: {e}")
            return False
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Restore sessions when bot is ready"""
        if self.sessions_restored:
            return
        
        self.sessions_restored = True
        
        # Wait a bit for nodes to connect
        await self.bot.wait_until_ready()
        import asyncio
        await asyncio.sleep(5)
        
        sessions = await self.load_sessions()
        current_time = int(time.time())
        restored_count = 0
        
        for data in sessions:
            # Check if session is within 5 minute window
            session_time = data.get("timestamp", 0)
            if current_time - session_time > SESSION_TIMEOUT:
                # Delete old session
                try:
                    await self.sessions_db.delete_one({"_id": data["_id"]})
                except:
                    pass
                continue
            
            success = await self.restore_session(data)
            if success:
                restored_count += 1
            
            # Delete session after restoration attempt
            try:
                await self.sessions_db.delete_one({"_id": data["_id"]})
            except:
                pass
        
        if restored_count > 0:
            func.logger.info(f"Restored {restored_count} session(s) from last shutdown")
    
    @tasks.loop(seconds=5)
    async def save_sessions_loop(self):
        """Save all sessions every 5 seconds"""
        await self.save_all_sessions()
    
    @save_sessions_loop.before_loop
    async def before_save_loop(self):
        """Wait for bot to be ready before starting save loop"""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Session(bot))

