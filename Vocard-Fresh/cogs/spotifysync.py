"""MIT License

Copyright (c) 2023 - present Vocard Development

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import discord
import asyncio
import function as func

from discord import app_commands, ui
from discord.ext import commands, tasks
from typing import Optional, Dict
from datetime import datetime


class SpotifySession:
    """Tracks an active Spotify follow session."""
    
    # Latency compensation constants
    DISCORD_BUFFER_MS = 1500  # Audio pipeline delay
    LATENCY_SAMPLES = 5  # Number of samples for rolling average
    
    def __init__(self, target: discord.Member, follower: discord.Member, message: discord.Message, player, original_nick: str = None):
        self.target = target
        self.follower = follower
        self.message = message
        self.player = player
        self.guild_id = target.guild.id
        self.current_track_id = None
        self.last_spotify_position = 0  # Track last Spotify position for seek detection
        self.is_active = True
        self.started_at = datetime.now()
        self.tracks_synced = 0
        self.spotify_paused_at = None  # Track when Spotify was paused for grace period
        self.original_nick = original_nick  # Store original bot nickname to restore later
        
        # Latency compensation tracking
        self.latency_samples: list = []  # Rolling samples of measured drift
        self.last_measured_drift = 0  # Last measured drift in ms
        self.last_seek_time: datetime = None  # Cooldown to prevent excessive seeking
    
    def get_lavalink_ping_ms(self) -> int:
        """Get current Lavalink ping in ms."""
        if self.player and hasattr(self.player, '_ping'):
            return int(self.player._ping or 0)
        return 0
    
    def calculate_compensation_offset(self) -> int:
        """Calculate total latency compensation offset in ms using real metrics.
        
        Combines multiple latency sources:
        1. Lavalink player ping (network RTT to audio server)
        2. Node CPU load factor (high load = more processing delay)
        3. Base Discord buffer (encoding/transmission)
        4. Rolling average of measured drift (adaptive learning)
        5. Railway/cloud hosting overhead estimate
        
        Returns: compensation offset in milliseconds
        """
        # 1. Lavalink network latency (one-way, so divide RTT by 2)
        lavalink_ping = self.get_lavalink_ping_ms()
        network_latency = lavalink_ping // 2 if lavalink_ping else 50  # Default 50ms if unknown
        
        # 2. Node CPU load factor - more load means more processing delay
        # Get node stats if available
        cpu_factor = 0
        try:
            if self.player and hasattr(self.player, '_node') and self.player._node._stats:
                node_stats = self.player._node._stats
                # CPU process load is 0-1, each 10% adds ~50ms delay
                cpu_load = getattr(node_stats, 'cpu_process_load', 0) or 0
                cpu_factor = int(cpu_load * 300)  # 0-300ms based on load
        except:
            pass
        
        # 3. Base Discord voice buffer (encoding + transmission + decoding)
        discord_buffer = 150  # Reduced - was over-compensating
        
        # 4. Rolling average of measured drift (adaptive learning)
        avg_drift = 0
        if self.latency_samples:
            avg_drift = sum(self.latency_samples) // len(self.latency_samples)
        
        # 5. Cloud hosting overhead (Railway, etc.) - minimal
        cloud_overhead = 50  # Reduced - bot was ahead
        
        # Total compensation
        total_offset = network_latency + cpu_factor + discord_buffer + cloud_overhead
        
        # Apply drift correction (half of average drift to avoid oscillation)
        if avg_drift > 0:  # Player is behind, need more offset
            total_offset += avg_drift // 2
        elif avg_drift < 0:  # Player is ahead, reduce offset
            total_offset = max(0, total_offset + avg_drift // 2)
        
        func.logger.debug(
            f"Smart compensation: network={network_latency}ms, cpu_factor={cpu_factor}ms, "
            f"discord={discord_buffer}ms, cloud={cloud_overhead}ms, drift_adj={avg_drift//2}ms, total={total_offset}ms"
        )
        
        return max(0, total_offset)  # Never negative
    
    def record_drift(self, spotify_pos: int, player_pos: int) -> None:
        """Record measured drift between Spotify and player for adaptive compensation."""
        drift = spotify_pos - player_pos  # Positive = player behind, negative = player ahead
        self.last_measured_drift = drift
        
        # Add to rolling samples, keep only last N
        self.latency_samples.append(drift)
        if len(self.latency_samples) > self.LATENCY_SAMPLES:
            self.latency_samples.pop(0)
    
    def calculate_percent_position(self, spotify_pos_ms: int, spotify_duration_ms: int, youtube_duration_ms: int) -> int:
        """Calculate YouTube position based on Spotify percentage progress.
        
        This handles tracks with different lengths (e.g., music videos vs audio).
        Maps Spotify's progress percentage to the equivalent position in YouTube track.
        """
        if spotify_duration_ms <= 0 or youtube_duration_ms <= 0:
            return spotify_pos_ms  # Fallback to absolute position
        
        # Calculate percentage progress in Spotify
        percent = spotify_pos_ms / spotify_duration_ms
        
        # Map to YouTube position
        youtube_pos = int(youtube_duration_ms * percent)
        
        return youtube_pos


class SpotifySync(commands.Cog):
    """🎵 Live Spotify sync - play what users are listening to!"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions: Dict[int, SpotifySession] = {}
        self.update_loop.start()
        func.logger.info("SpotifySync cog loaded!")
    
    def cog_unload(self):
        self.update_loop.cancel()
    
    def _get_member(self, guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
        """Get fresh member with current activities."""
        return guild.get_member(user_id)
    
    def _get_spotify(self, member: discord.Member) -> Optional[discord.Spotify]:
        """Get Spotify activity from member."""
        if not member:
            return None
        for activity in member.activities:
            if isinstance(activity, discord.Spotify):
                return activity
        return None
    
    def _get_spotify_position_ms(self, spotify: discord.Spotify) -> int:
        """Get current position in the Spotify track in milliseconds."""
        if not spotify or not spotify.start:
            return 0
        try:
            now = datetime.now(spotify.start.tzinfo)
            elapsed_ms = int((now - spotify.start).total_seconds() * 1000)
            duration_ms = int(spotify.duration.total_seconds() * 1000)
            return min(max(0, elapsed_ms), duration_ms)
        except:
            return 0
    
    def _create_embed(self, member: discord.Member, spotify: discord.Spotify, session: SpotifySession = None) -> discord.Embed:
        """Create Spotify embed with optional session info."""
        embed = discord.Embed(
            title=f"🎵 {spotify.title}",
            description=f"by **{spotify.artist}**\nAlbum: *{spotify.album}*",
            color=discord.Color.green() if not session else discord.Color.blurple()
        )
        
        if spotify.album_cover_url:
            embed.set_thumbnail(url=spotify.album_cover_url)
        
        # Progress bar
        try:
            pos_ms = self._get_spotify_position_ms(spotify)
            dur_ms = int(spotify.duration.total_seconds() * 1000)
            pos_s, dur_s = pos_ms // 1000, dur_ms // 1000
            pct = pos_ms / dur_ms if dur_ms > 0 else 0
            filled = int(20 * pct)
            bar = "▓" * filled + "░" * (20 - filled)
            embed.add_field(
                name="Progress",
                value=f"`{pos_s//60}:{pos_s%60:02d}` {bar} `{dur_s//60}:{dur_s%60:02d}`",
                inline=False
            )
        except:
            pass
        
        if session:
            elapsed = datetime.now() - session.started_at
            mins = int(elapsed.total_seconds() // 60)
            secs = int(elapsed.total_seconds() % 60)
            embed.add_field(
                name="🔴 Live Syncing",
                value=f"Synced **{session.tracks_synced}** tracks\nFollowing for {mins}m {secs}s",
                inline=False
            )
            embed.set_footer(text=f"Syncing {member.display_name}'s Spotify | /sp stop to end")
        else:
            embed.set_footer(text=f"{member.display_name} on Spotify")
        
        return embed
    
    async def _get_or_create_player(self, interaction: discord.Interaction):
        """Get existing player or create new one by joining user's VC."""
        import voicelink
        
        player = interaction.guild.voice_client
        if player:
            return player
        
        # Auto-join user's voice channel
        if not interaction.user.voice:
            return None
        
        try:
            channel = interaction.user.voice.channel
            # Manually connect using TempCtx to avoid 'author' attribute error in connect_channel helper
            settings = await func.get_settings(interaction.guild.id)
            player = await channel.connect(
                cls=voicelink.Player(self.bot, channel, func.TempCtx(interaction.user, channel), settings)
            )
            player.text_channel = interaction.channel
            return player
        except Exception as e:
            func.logger.error(f"Failed to create player: {e}")
            return None
    
    async def _play_track(self, player, query: str, requester: discord.Member, seek_ms: int = 0, spotify_duration_ms: int = 0) -> tuple:
        """Search and play a track with predictive sync.
        
        Measures actual load time and predicts where Spotify will be
        when audio starts, then seeks to that predicted position.
        
        Returns:
            tuple: (success: bool, youtube_duration_ms: int)
        """
        import time
        
        try:
            from voicelink import NodePool, Playlist
            
            # Start timing the load process
            load_start = time.time()
            
            # Priority 1: Try Spotify source directly (same audio, same duration)
            # This requires LavaSrc plugin on Lavalink
            spotify_query = f"spsearch:{query}"
            func.logger.debug(f"Sync searching Spotify source: {spotify_query}")
            tracks = await NodePool.get_node().get_tracks(query=spotify_query, requester=requester)
            
            if not tracks:
                # Priority 2: Try YouTube with "audio" suffix to avoid music videos
                yt_audio_query = f"ytsearch:{query} audio"
                func.logger.debug(f"Spotify source failed, trying YouTube audio: {yt_audio_query}")
                tracks = await NodePool.get_node().get_tracks(query=yt_audio_query, requester=requester)
            
            if not tracks:
                # Priority 3: Fallback to regular YouTube search
                yt_query = f"ytsearch:{query}"
                func.logger.debug(f"YouTube audio failed, trying plain YouTube: {yt_query}")
                tracks = await NodePool.get_node().get_tracks(query=yt_query, requester=requester)
                if not tracks:
                    func.logger.debug(f"All searches failed for: {query}")
                    return (False, 0)
            
            track = tracks[0] if not isinstance(tracks, Playlist) else tracks.tracks[0]
            youtube_duration_ms = getattr(track, 'length', 0) or 0
            func.logger.debug(f"Sync found track: {track.title} (duration: {youtube_duration_ms}ms)")
            
            # Clear queue completely and reset position pointer
            player.queue._queue.clear()
            player.queue._position = 0  # Reset position to start of queue
            
            # Insert track at beginning (position 0)
            player.queue._queue.insert(0, track)
            func.logger.debug(f"Track inserted at position 0, queue length: {len(player.queue._queue)}")
            
            # Clear current track so do_next() doesn't skip
            if player._current:
                func.logger.debug("Clearing current track for sync...")
                player._current = None
            
            # Trigger playback
            await player.do_next()
            
            # Wait for playback to actually start
            await asyncio.sleep(0.5)
            
            # Calculate total load time
            load_time_ms = int((time.time() - load_start) * 1000)
            
            # Smart compensation: calculate based on real metrics
            # Get Lavalink ping if available
            lavalink_ping = 0
            cpu_factor = 0
            try:
                if hasattr(player, '_ping'):
                    lavalink_ping = int(player._ping or 0) // 2  # One-way latency
                if hasattr(player, '_node') and player._node._stats:
                    cpu_load = getattr(player._node._stats, 'cpu_process_load', 0) or 0
                    cpu_factor = int(cpu_load * 300)
            except:
                pass
            
            # Total compensation = load time + network + cpu + discord buffer + cloud overhead
            # Increased buffer to 1500ms to allow "overshoot" for stream startup latency
            stream_latency = 1500 
            smart_buffer = lavalink_ping + cpu_factor + 150 + 50 + stream_latency
            predicted_spotify_pos = seek_ms + load_time_ms + smart_buffer
            
            func.logger.debug(
                f"Smart track sync: load={load_time_ms}ms, ping={lavalink_ping}ms, "
                f"cpu_factor={cpu_factor}ms, buffer=200ms, stream_lat={stream_latency}ms, total_comp={smart_buffer}ms"
            )
            
            # Use percentage-based sync if durations differ significantly
            if spotify_duration_ms > 0 and youtube_duration_ms > 0:
                duration_diff = abs(spotify_duration_ms - youtube_duration_ms)
                if duration_diff > 10000:  # >10 seconds difference, use percentage
                    percent = predicted_spotify_pos / spotify_duration_ms
                    predicted_position = int(youtube_duration_ms * percent)
                    func.logger.debug(
                        f"Percentage sync: {percent:.2%} of Spotify ({spotify_duration_ms}ms) = {predicted_position}ms of YouTube ({youtube_duration_ms}ms)"
                    )
                else:
                    predicted_position = predicted_spotify_pos
                    func.logger.debug(
                        f"Absolute sync: original {seek_ms}ms + load {load_time_ms}ms + buffer {smart_buffer}ms = {predicted_position}ms"
                    )
            else:
                predicted_position = predicted_spotify_pos
                func.logger.debug(
                    f"Fallback sync: original {seek_ms}ms + load {load_time_ms}ms + buffer {smart_buffer}ms = {predicted_position}ms"
                )
            
            if player._current and predicted_position > 2000:
                func.logger.debug(f"Seeking to predicted position {predicted_position}ms...")
                try:
                    await player.seek(predicted_position, requester)
                except Exception as seek_err:
                    func.logger.debug(f"Seek failed: {seek_err}")
            
            if player._current:
                func.logger.debug(f"Sync playback started: {player._current.title}")
            else:
                func.logger.warning(f"Sync playback failed - queue pos: {player.queue._position}, queue len: {len(player.queue._queue)}")
            
            return (True, youtube_duration_ms)
        except Exception as e:
            func.logger.error(f"Play track error: {e}")
            return (False, 0)
    
    @tasks.loop(seconds=2)
    async def update_loop(self):
        """Update all active sync sessions."""
        for guild_id, session in list(self.active_sessions.items()):
            if not session.is_active:
                del self.active_sessions[guild_id]
                continue
            
            try:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    session.is_active = False
                    continue
                
                target = self._get_member(guild, session.target.id)
                spotify = self._get_spotify(target)
                
                if not spotify:
                    # Target stopped listening - start grace period
                    if session.spotify_paused_at is None:
                        # First time noticing pause
                        session.spotify_paused_at = datetime.now()
                        elapsed = 0
                    else:
                        elapsed = (datetime.now() - session.spotify_paused_at).total_seconds()
                    
                    # 5-minute grace period (300 seconds)
                    if elapsed < 300:
                        # Still in grace period, show waiting message
                        remaining = int((300 - elapsed) / 60)
                        embed = discord.Embed(
                            title="⏸️ Waiting for Spotify...",
                            description=f"**{session.target.display_name}** paused Spotify.\nWaiting **{remaining}m** before stopping sync...\n\nSynced **{session.tracks_synced}** tracks so far.",
                            color=discord.Color.orange()
                        )
                        try:
                            await session.message.edit(embed=embed, view=StopSyncView(self, session))
                        except:
                            pass
                        continue
                    
                    # Grace period expired - actually stop
                    embed = discord.Embed(
                        title="⏹️ Sync Ended",
                        description=f"**{session.target.display_name}** stopped Spotify for 5+ minutes.\nSynced **{session.tracks_synced}** tracks.",
                        color=discord.Color.orange()
                    )
                    try:
                        await session.message.edit(embed=embed, view=None)
                    except:
                        pass
                    
                    # Reset bot nickname when sync auto-ends (restore original)
                    try:
                        bot_member = guild.me
                        if bot_member:
                            await bot_member.edit(nick=session.original_nick)
                            func.logger.info(f"Restored nickname to '{session.original_nick}' in {guild.name} after sync ended")
                    except discord.Forbidden:
                        func.logger.warning(f"No permission to reset nickname in {guild.name}")
                    except Exception as e:
                        func.logger.error(f"Failed to reset nickname: {e}")
                    
                    # Reset voice channel status
                    try:
                        if session.player and session.player.channel:
                            await session.player.update_voice_status()
                    except:
                        pass
                    
                    session.is_active = False
                    del self.active_sessions[guild_id]
                    continue
                
                # Spotify is active - reset grace period timer
                session.spotify_paused_at = None
                
                # Get current Spotify position
                spotify_position_ms = self._get_spotify_position_ms(spotify)
                
                # Check if track changed
                if spotify.track_id != session.current_track_id:
                    query = f"{spotify.title} {spotify.artist}"
                    # Get Spotify track duration for percentage-based sync
                    spotify_duration_ms = int(spotify.duration.total_seconds() * 1000) if spotify.duration else 0
                    
                    # Note: we pass raw spotify_position_ms here, _play_track handles compensation internally
                    func.logger.debug(f"Track change: {query} (Spotify duration: {spotify_duration_ms}ms)")
                    result = await self._play_track(session.player, query, session.follower, spotify_position_ms, spotify_duration_ms)
                    success = result[0] if isinstance(result, tuple) else result
                    
                    if success:
                        session.current_track_id = spotify.track_id
                        session.last_spotify_position = spotify_position_ms
                        session.tracks_synced += 1
                        session.latency_samples.clear()  # Reset samples for new track
                else:
                    # Same track - check for seek by comparing Spotify position to player position
                    player_position_ms = getattr(session.player, 'position', 0) or 0
                    
                    # Record drift for adaptive compensation learning
                    session.record_drift(spotify_position_ms, player_position_ms)
                    
                    # Simple difference - no compensation during sync loop seeks
                    # (Compensation is only for initial track start prediction)
                    position_diff = abs(spotify_position_ms - player_position_ms)
                    
                    # 1:1 sync: seek if difference > 2 seconds
                    if position_diff > 2000:
                        # Cooldown: Don't seek more than once every 5 seconds (unless drift is huge)
                        can_seek = True
                        if session.last_seek_time:
                            elapsed_since_seek = (datetime.now() - session.last_seek_time).total_seconds()
                            if elapsed_since_seek < 5 and position_diff < 10000:  # Allow emergency seek if >10s drift
                                can_seek = False
                                func.logger.debug(f"Seek cooldown active ({elapsed_since_seek:.1f}s < 5s), skipping seek")
                        
                        if can_seek:
                            func.logger.debug(
                                f"Seek sync: player at {player_position_ms}ms, Spotify at {spotify_position_ms}ms, diff={position_diff}ms"
                            )
                            try:
                                # Seek to exact Spotify position - no compensation during mid-track sync
                                await session.player.seek(spotify_position_ms, session.follower)
                                session.last_seek_time = datetime.now()
                                func.logger.debug(f"Seek to {spotify_position_ms}ms successful")
                            except Exception as e:
                                func.logger.debug(f"Seek failed: {e}")
                
                # Update embed
                embed = self._create_embed(target, spotify, session)
                view = StopSyncView(self, session)
                try:
                    await session.message.edit(embed=embed, view=view)
                except discord.NotFound:
                    session.is_active = False
                    
            except Exception as e:
                func.logger.debug(f"Update loop error: {e}")
    
    @update_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
    
    # ========== COMMANDS ==========
    
    spotify = app_commands.Group(name="sp", description="🎵 Spotify sync commands")
    
    @spotify.command(name="sync", description="🔴 Live sync - play what someone listens to on Spotify!")
    @app_commands.describe(user="User to sync with (optional, defaults to yourself)")
    async def sp_sync(self, interaction: discord.Interaction, user: discord.Member = None):
        """Start syncing Spotify activity."""
        target = user or interaction.user
        
        if target.bot:
            await interaction.response.send_message("❌ Can't sync bots!", ephemeral=True)
            return
        
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Join a voice channel!", ephemeral=True)
            return
        
        if interaction.guild.id in self.active_sessions:
            await interaction.response.send_message("❌ Already syncing! Use `/sp stop` first.", ephemeral=True)
            return
        
        member = self._get_member(interaction.guild, target.id)
        spotify = self._get_spotify(member)
        
        if not spotify:
            name = "You're" if target.id == interaction.user.id else f"**{target.display_name}** isn't"
            await interaction.response.send_message(f"❌ {name} not on Spotify!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        player = await self._get_or_create_player(interaction)
        if not player:
            await interaction.followup.send("❌ Couldn't connect to voice!")
            return
        
        # Save original nickname before changing it
        original_nick = interaction.guild.me.nick
        
        # Update VC status to show who we're syncing - with enthusiasm!
        try:
            await interaction.guild.me.edit(nick=f"🔴 LIVE: {target.display_name}'s Spotify 🎧")
        except:
            pass  # Might not have permission
        
        # Update voice channel status for sync mode
        try:
            if player.channel and hasattr(player.channel, 'edit'):
                await player.channel.edit(status=f"🔴 Syncing: {target.display_name}'s Spotify")
        except:
            pass
        
        # Create initial embed
        embed = self._create_embed(member, spotify)
        embed.add_field(name="🔴 Starting sync...", value="Finding track...", inline=False)
        msg = await interaction.followup.send(embed=embed, wait=True)
        
        # Create session with original nickname saved
        session = SpotifySession(member, interaction.user, msg, player, original_nick)
        self.active_sessions[interaction.guild.id] = session
        
        # Play first track
        query = f"{spotify.title} {spotify.artist}"
        seek_ms = self._get_spotify_position_ms(spotify)
        success = await self._play_track(player, query, interaction.user, seek_ms)
        
        if success:
            session.current_track_id = spotify.track_id
            session.tracks_synced = 1
            embed = self._create_embed(member, spotify, session)
            view = StopSyncView(self, session)
            await msg.edit(embed=embed, view=view)
        else:
            embed = discord.Embed(title="❌ Couldn't find track", color=discord.Color.red())
            await msg.edit(embed=embed)
            del self.active_sessions[interaction.guild.id]
            # Restore original nickname on failure
            try:
                await interaction.guild.me.edit(nick=original_nick)
            except:
                pass
    
    @spotify.command(name="stop", description="⏹️ Stop syncing Spotify")
    async def sp_stop(self, interaction: discord.Interaction):
        """Stop syncing."""
        if interaction.guild.id not in self.active_sessions:
            await interaction.response.send_message("❌ Not syncing!", ephemeral=True)
            return
        
        session = self.active_sessions.pop(interaction.guild.id)
        session.is_active = False
        
        embed = discord.Embed(
            title="⏹️ Sync Stopped",
            description=f"Synced **{session.tracks_synced}** tracks",
            color=discord.Color.orange()
        )
        try:
            await session.message.edit(embed=embed, view=None)
        except:
            pass
        
        # Restore original bot nickname
        try:
            bot_member = interaction.guild.me
            if bot_member:
                await bot_member.edit(nick=session.original_nick)
                func.logger.info(f"Restored nickname to '{session.original_nick}' in {interaction.guild.name} after sp_stop")
        except discord.Forbidden:
            func.logger.warning(f"No permission to reset nickname in {interaction.guild.name}")
        except Exception as e:
            func.logger.error(f"Failed to reset nickname in sp_stop: {e}")
        
        # Reset voice channel status
        try:
            if session.player and session.player.channel and hasattr(session.player.channel, 'edit'):
                # Restore normal status or clear it
                await session.player.update_voice_status()
        except:
            pass
        
        await interaction.response.send_message("✅ Stopped syncing!", ephemeral=True)
    
    @spotify.command(name="list", description="📋 See who's listening to Spotify in the server")
    async def sp_list(self, interaction: discord.Interaction):
        """List all Spotify users in the entire server."""
        users = []
        
        # Always show ALL server members with Spotify activity
        members_to_check = interaction.guild.members
        title = "🎵 Spotify Listeners"
        
        for m in members_to_check:
            if m.bot:
                continue
            sp = self._get_spotify(m)
            if sp:
                users.append((m, sp))
        
        if not users:
            await interaction.response.send_message("🎵 No one's listening to Spotify right now!")
            return
        
        embed = discord.Embed(title=title, description=f"Found **{len(users)}** listener(s)", color=discord.Color.green())
        for m, sp in users[:25]:  # Limit to 25 to avoid embed limits
            embed.add_field(name=m.display_name, value=f"**{sp.title}**\nby {sp.artist}", inline=True)
        
        if len(users) > 25:
            embed.set_footer(text=f"Showing 25/{len(users)} | Use /sp sync @user to sync!")
        else:
            embed.set_footer(text="Use /sp sync @user to sync!")
        await interaction.response.send_message(embed=embed)


class QuickPlayView(ui.View):
    """Quick add button."""
    
    def __init__(self, cog, member, spotify):
        super().__init__(timeout=120)
        self.cog = cog
        self.member = member
        self.spotify = spotify
    
    @ui.button(label="🎵 Play This", style=discord.ButtonStyle.green)
    async def play(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        player = await self.cog._get_or_create_player(interaction)
        if not player:
            await interaction.followup.send("❌ Join voice first!", ephemeral=True)
            return
        
        query = f"{self.spotify.title} {self.spotify.artist}"
        success = await self.cog._play_track(player, query, interaction.user, 0)
        
        if success:
            await interaction.followup.send(f"✅ Added **{self.spotify.title}**!", ephemeral=True)
            button.disabled = True
            button.label = "✅ Added"
            await interaction.message.edit(view=self)
        else:
            await interaction.followup.send("❌ Couldn't find track!", ephemeral=True)


class StopSyncView(ui.View):
    """Stop button for sync sessions."""
    
    def __init__(self, cog, session):
        super().__init__(timeout=None)
        self.cog = cog
        self.session = session
    
    @ui.button(label="⏹️ Stop Sync", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.session.follower.id:
            await interaction.response.send_message("❌ Only the person who started can stop!", ephemeral=True)
            return
        
        self.session.is_active = False
        if self.session.guild_id in self.cog.active_sessions:
            del self.cog.active_sessions[self.session.guild_id]
        
        # Restore original bot nickname
        try:
            bot_member = interaction.guild.me
            if bot_member:
                await bot_member.edit(nick=self.session.original_nick)
                func.logger.info(f"Restored nickname to '{self.session.original_nick}' in {interaction.guild.name} after button stop")
        except discord.Forbidden:
            func.logger.warning(f"No permission to reset nickname in {interaction.guild.name}")
        except Exception as e:
            func.logger.error(f"Failed to reset nickname in button stop: {e}")
        
        # Reset voice channel status
        try:
            if self.session.player and self.session.player.channel and hasattr(self.session.player.channel, 'edit'):
                await self.session.player.update_voice_status()
        except:
            pass
        
        embed = discord.Embed(
            title="⏹️ Sync Stopped",
            description=f"Synced **{self.session.tracks_synced}** tracks",
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(SpotifySync(bot))
