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
import function as func

from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from datetime import datetime


class Stats(commands.Cog):
    """User stats tracking - listening minutes, bonks, and more! Uses MongoDB for persistence."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.track_listening_time.start()
        func.logger.info("Stats cog initialized - tracking listening time with MongoDB!")
    
    def cog_unload(self):
        """Stop the background task when cog is unloaded."""
        self.track_listening_time.cancel()
    
    @tasks.loop(seconds=60)
    async def track_listening_time(self):
        """Track listening minutes for users in voice with active players."""
        try:
            for guild in self.bot.guilds:
                # Check if there's an active player in this guild
                player = getattr(guild, 'voice_client', None)
                if player and hasattr(player, 'is_playing') and player.is_playing:
                    # Get the voice channel
                    if player.channel:
                        for member in player.channel.members:
                            if not member.bot:
                                await self.add_stat(member.id, guild.id, "listening_minutes", 1)
        except Exception as e:
            func.logger.debug(f"Error tracking listening time: {e}")
    
    @track_listening_time.before_loop
    async def before_track_listening(self):
        """Wait for bot to be ready before starting the loop."""
        await self.bot.wait_until_ready()
    
    async def _get_user_stats(self, user_id: int, guild_id: int) -> dict:
        """Get user stats from MongoDB."""
        user_data = await func.get_user(user_id)
        stats = user_data.get("stats", {}).get(str(guild_id), {})
        
        # Return with defaults
        return {
            "listening_minutes": stats.get("listening_minutes", 0),
            "songs_played": stats.get("songs_played", 0),
            "bonks_given": stats.get("bonks_given", 0),
            "bonks_received": stats.get("bonks_received", 0),
            "hugs_given": stats.get("hugs_given", 0),
            "hugs_received": stats.get("hugs_received", 0),
            "pats_given": stats.get("pats_given", 0),
            "pats_received": stats.get("pats_received", 0),
            "kills_given": stats.get("kills_given", 0),
            "kills_received": stats.get("kills_received", 0),
            "slaps_given": stats.get("slaps_given", 0),
            "slaps_received": stats.get("slaps_received", 0),
            "pokes_given": stats.get("pokes_given", 0),
            "pokes_received": stats.get("pokes_received", 0),
            "punches_given": stats.get("punches_given", 0),
            "punches_received": stats.get("punches_received", 0),
            "commands_used": stats.get("commands_used", 0),
            "last_active": stats.get("last_active"),
        }
    
    async def add_stat(self, user_id: int, guild_id: int, stat_name: str, amount: int = 1):
        """Add to a user's stat using MongoDB $inc operator."""
        try:
            await func.update_user(user_id, {
                "$inc": {f"stats.{guild_id}.{stat_name}": amount},
                "$set": {f"stats.{guild_id}.last_active": datetime.now().isoformat()}
            })
        except Exception as e:
            func.logger.debug(f"Failed to add stat: {e}")
    
    @commands.Cog.listener()
    async def on_voicelink_track_start(self, player, track):
        """Track songs played per user."""
        if hasattr(player, 'context') and player.context:
            try:
                user_id = player.context.author.id
                guild_id = player.context.guild.id
                await self.add_stat(user_id, guild_id, "songs_played")
            except:
                pass
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Track command usage."""
        if ctx.guild:
            await self.add_stat(ctx.author.id, ctx.guild.id, "commands_used")
    
    @commands.hybrid_command(name="stats")
    @app_commands.describe(user="User to check stats for (optional)")
    async def stats_command(self, ctx: commands.Context, user: discord.User = None):
        """View your or another user's stats! 📊"""
        
        if user is None:
            user = ctx.author
        
        stats = await self._get_user_stats(user.id, ctx.guild.id)
        
        embed = discord.Embed(
            title=f"📊 Stats for {user.display_name}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Music stats
        music_stats = f"🎵 Songs Played: **{stats['songs_played']}**\n"
        music_stats += f"⏱️ Listening Time: **{stats['listening_minutes']} min**"
        embed.add_field(name="🎶 Music", value=music_stats, inline=True)
        
        # Fun command stats
        fun_stats = f"🐕 Bonks: {stats['bonks_given']} given / {stats['bonks_received']} received\n"
        fun_stats += f"🤗 Hugs: {stats['hugs_given']} given / {stats['hugs_received']} received\n"
        fun_stats += f"👋 Pats: {stats['pats_given']} given / {stats['pats_received']} received\n"
        fun_stats += f"💀 Kills: {stats['kills_given']} given / {stats['kills_received']} received\n"
        fun_stats += f"👊 Slaps: {stats['slaps_given']} given / {stats['slaps_received']} received\n"
        fun_stats += f"👉 Pokes: {stats['pokes_given']} given / {stats['pokes_received']} received\n"
        fun_stats += f"🥊 Punches: {stats['punches_given']} given / {stats['punches_received']} received"
        embed.add_field(name="🎮 Fun Commands", value=fun_stats, inline=False)
        
        # General
        embed.add_field(name="⚡ Commands Used", value=f"**{stats['commands_used']}**", inline=True)
        
        if stats['last_active']:
            embed.set_footer(text=f"Last active: {stats['last_active'][:10]}")
        
        await func.send(ctx, embed)
    
    @commands.hybrid_command(name="leaderboard", aliases=["lb", "top"])
    @app_commands.describe(category="What to rank by")
    @app_commands.choices(category=[
        app_commands.Choice(name="XP / Level", value="xp"),
        app_commands.Choice(name="Listening Minutes", value="listening_minutes"),
        app_commands.Choice(name="Songs Played", value="songs_played"),
        app_commands.Choice(name="Bonks Given", value="bonks_given"),
        app_commands.Choice(name="Hugs Given", value="hugs_given"),
        app_commands.Choice(name="Commands Used", value="commands_used"),
    ])
    async def leaderboard(self, ctx: commands.Context, category: str = "xp"):
        """View the server leaderboard! 🏆"""
        
        await ctx.defer()
        guild_id = str(ctx.guild.id)
        
        # XP leaderboard uses different collection
        if category == "xp":
            db = func.MONGO_DB[func.settings.mongodb_name]
            cursor = db["user_levels"].find(
                {"guild_id": guild_id}
            ).sort("xp", -1).limit(10)
            leaderboard_data = await cursor.to_list(length=10)
            
            embed = discord.Embed(title="🏆 Leaderboard: XP / Level", color=discord.Color.gold())
            
            if not leaderboard_data:
                embed.description = "No XP data yet! Chat to earn XP."
            else:
                lines = []
                medals = ["🥇", "🥈", "🥉"]
                for i, data in enumerate(leaderboard_data):
                    try:
                        user_id = int(data["user_id"])
                        member = ctx.guild.get_member(user_id)
                        name = member.display_name if member else f"User {user_id}"
                        level = data.get("level", 0)
                        xp = data.get("xp", 0)
                        medal = medals[i] if i < 3 else f"**{i+1}.**"
                        lines.append(f"{medal} {name}: Level **{level}** ({xp:,} XP)")
                    except:
                        pass
                embed.description = "\n".join(lines) if lines else "No data available."
        else:
            # Stats-based leaderboard
            cursor = func.USERS_DB.find(
                {f"stats.{guild_id}.{category}": {"$exists": True, "$gt": 0}},
                {"_id": 1, f"stats.{guild_id}.{category}": 1}
            ).sort(f"stats.{guild_id}.{category}", -1).limit(10)
            leaderboard_data = await cursor.to_list(length=10)
            
            category_display = category.replace("_", " ").title()
            embed = discord.Embed(title=f"🏆 Leaderboard: {category_display}", color=discord.Color.gold())
            
            if not leaderboard_data:
                embed.description = "No stats yet! Start using the bot to appear here."
            else:
                lines = []
                medals = ["🥇", "🥈", "🥉"]
                for i, data in enumerate(leaderboard_data):
                    try:
                        user = await self.bot.fetch_user(data["_id"])
                        value = data.get("stats", {}).get(guild_id, {}).get(category, 0)
                        medal = medals[i] if i < 3 else f"**{i+1}.**"
                        lines.append(f"{medal} {user.display_name}: **{value}**")
                    except:
                        pass
                embed.description = "\n".join(lines) if lines else "No data available."
        
        await func.send(ctx, embed)
        
        # Track leaderboard_fan quest
        try:
            quests_cog = self.bot.get_cog("DailyQuests")
            if quests_cog:
                await quests_cog.track_quest(ctx.guild.id, ctx.author.id, "leaderboard_fan")
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))
