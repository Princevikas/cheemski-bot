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
import json
import os
import function as func

from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional


class Moderation(commands.Cog):
    """Server moderation commands - kick, ban, mute, warn!"""
    
    MOD_LOG_FILE = "data/mod_logs.json"
    WARNINGS_FILE = "data/warnings.json"
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.mod_logs = self._load_logs()
        self.warnings = self._load_warnings()
        func.logger.info("Moderation cog initialized - keeping servers safe!")
    
    def _load_logs(self) -> list:
        """Load moderation logs from file."""
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.MOD_LOG_FILE):
            try:
                with open(self.MOD_LOG_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_logs(self):
        """Save moderation logs to file."""
        os.makedirs("data", exist_ok=True)
        with open(self.MOD_LOG_FILE, "w") as f:
            json.dump(self.mod_logs[-1000:], f, indent=2)  # Keep last 1000 entries
    
    def _load_warnings(self) -> dict:
        """Load warnings from file."""
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.WARNINGS_FILE):
            try:
                with open(self.WARNINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_warnings(self):
        """Save warnings to file."""
        os.makedirs("data", exist_ok=True)
        with open(self.WARNINGS_FILE, "w") as f:
            json.dump(self.warnings, f, indent=2)
    
    def log_action(self, guild_id: int, mod_id: int, target_id: int, action: str, reason: str = None):
        """Log a moderation action."""
        entry = {
            "guild_id": guild_id,
            "mod_id": mod_id,
            "target_id": target_id,
            "action": action,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self.mod_logs.append(entry)
        self._save_logs()
    
    def get_warnings_key(self, guild_id: int, user_id: int) -> str:
        return f"{guild_id}_{user_id}"
    
    @commands.hybrid_command(name="kick")
    @app_commands.describe(user="User to kick", reason="Reason for kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Kick a user from the server! 👢"""
        
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await func.send(ctx, "❌ You can't kick someone with equal or higher role!", ephemeral=True)
            return
        
        if user == ctx.author:
            await func.send(ctx, "❌ You can't kick yourself!", ephemeral=True)
            return
        
        # Check if bot can kick this user (role hierarchy)
        if user.top_role >= ctx.guild.me.top_role:
            await func.send(ctx, f"❌ I can't kick {user.mention} - their role is higher than or equal to mine!", ephemeral=True)
            return
        
        try:
            await user.kick(reason=f"{reason} | By: {ctx.author}")
            
            self.log_action(ctx.guild.id, ctx.author.id, user.id, "kick", reason)
            
            embed = discord.Embed(
                title="👢 User Kicked",
                description=f"**{user}** has been kicked from the server.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"User ID: {user.id}")
            
            await func.send(ctx, embed)
            
        except discord.Forbidden:
            await func.send(ctx, "❌ I don't have permission to kick this user!", ephemeral=True)
    
    @commands.hybrid_command(name="ban")
    @app_commands.describe(user="User to ban", reason="Reason for ban", delete_days="Days of messages to delete (0-7)")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, delete_days: int = 0, *, reason: str = "No reason provided"):
        """Ban a user from the server! 🔨"""
        
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await func.send(ctx, "❌ You can't ban someone with equal or higher role!", ephemeral=True)
            return
        
        if user == ctx.author:
            await func.send(ctx, "❌ You can't ban yourself!", ephemeral=True)
            return
        
        # Check if bot can ban this user (role hierarchy)
        if user.top_role >= ctx.guild.me.top_role:
            await func.send(ctx, f"❌ I can't ban {user.mention} - their role is higher than or equal to mine!", ephemeral=True)
            return
        
        delete_days = max(0, min(7, delete_days))
        
        try:
            await user.ban(reason=f"{reason} | By: {ctx.author}", delete_message_days=delete_days)
            
            self.log_action(ctx.guild.id, ctx.author.id, user.id, "ban", reason)
            
            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"**{user}** has been banned from the server.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Messages Deleted", value=f"{delete_days} days", inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"User ID: {user.id}")
            
            await func.send(ctx, embed)
            
        except discord.Forbidden:
            await func.send(ctx, "❌ I don't have permission to ban this user!", ephemeral=True)
    
    @commands.hybrid_command(name="unban")
    @app_commands.describe(user_id="User ID to unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: str):
        """Unban a user from the server! 🔓"""
        
        try:
            user_id_int = int(user_id)
            user = await self.bot.fetch_user(user_id_int)
            await ctx.guild.unban(user)
            
            self.log_action(ctx.guild.id, ctx.author.id, user_id_int, "unban", None)
            
            embed = discord.Embed(
                title="🔓 User Unbanned",
                description=f"**{user}** has been unbanned.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await func.send(ctx, embed)
            
        except ValueError:
            await func.send(ctx, "❌ Invalid user ID!", ephemeral=True)
        except discord.NotFound:
            await func.send(ctx, "❌ User not found in ban list!", ephemeral=True)
        except discord.Forbidden:
            await func.send(ctx, "❌ I don't have permission to unban!", ephemeral=True)
    
    @commands.hybrid_command(name="mute", aliases=["timeout"])
    @app_commands.describe(user="User to mute", duration="Duration (e.g., 10m, 1h, 1d)", reason="Reason for mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, user: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
        """Mute/timeout a user! 🔇"""
        
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await func.send(ctx, "❌ You can't mute someone with equal or higher role!", ephemeral=True)
            return
        
        # Check if bot can mute this user (role hierarchy)
        if user.top_role >= ctx.guild.me.top_role:
            await func.send(ctx, f"❌ I can't mute {user.mention} - their role is higher than or equal to mine!", ephemeral=True)
            return
        
        # Parse duration
        duration_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            unit = duration[-1].lower()
            amount = int(duration[:-1])
            if unit not in duration_map:
                raise ValueError
            seconds = amount * duration_map[unit]
            seconds = min(seconds, 28 * 24 * 3600)  # Max 28 days
        except:
            await func.send(ctx, "❌ Invalid duration! Use format: 10m, 1h, 1d", ephemeral=True)
            return
        
        try:
            until = discord.utils.utcnow() + timedelta(seconds=seconds)
            await user.timeout(until, reason=f"{reason} | By: {ctx.author}")
            
            self.log_action(ctx.guild.id, ctx.author.id, user.id, "mute", f"{duration} - {reason}")
            
            embed = discord.Embed(
                title="🔇 User Muted",
                description=f"**{user}** has been muted.",
                color=discord.Color.dark_gray()
            )
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await func.send(ctx, embed)
            
        except discord.Forbidden:
            await func.send(ctx, "❌ I don't have permission to mute this user!", ephemeral=True)
    
    @commands.hybrid_command(name="unmute", aliases=["untimeout"])
    @app_commands.describe(user="User to unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, user: discord.Member):
        """Unmute a user! 🔊"""
        
        try:
            await user.timeout(None)
            
            self.log_action(ctx.guild.id, ctx.author.id, user.id, "unmute", None)
            
            embed = discord.Embed(
                title="🔊 User Unmuted",
                description=f"**{user}** has been unmuted.",
                color=discord.Color.green()
            )
            await func.send(ctx, embed)
            
        except discord.Forbidden:
            await func.send(ctx, "❌ I don't have permission to unmute this user!", ephemeral=True)
    
    @commands.hybrid_command(name="warn")
    @app_commands.describe(user="User to warn", reason="Reason for warning")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Warn a user! ⚠️"""
        
        key = self.get_warnings_key(ctx.guild.id, user.id)
        if key not in self.warnings:
            self.warnings[key] = []
        
        warning = {
            "mod_id": ctx.author.id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self.warnings[key].append(warning)
        self._save_warnings()
        
        self.log_action(ctx.guild.id, ctx.author.id, user.id, "warn", reason)
        
        warning_count = len(self.warnings[key])
        
        embed = discord.Embed(
            title="⚠️ User Warned",
            description=f"**{user}** has been warned.",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await func.send(ctx, embed)
        
        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ Warning in {ctx.guild.name}",
                description=f"You have been warned.\n\n**Reason:** {reason}",
                color=discord.Color.yellow()
            )
            dm_embed.set_footer(text=f"Total warnings: {warning_count}")
            await user.send(embed=dm_embed)
        except:
            pass
    
    @commands.hybrid_command(name="warnings")
    @app_commands.describe(user="User to check warnings for")
    @commands.has_permissions(kick_members=True)
    async def warnings_cmd(self, ctx: commands.Context, user: discord.Member):
        """View warnings for a user! 📋"""
        
        key = self.get_warnings_key(ctx.guild.id, user.id)
        user_warnings = self.warnings.get(key, [])
        
        if not user_warnings:
            await func.send(ctx, f"✅ **{user}** has no warnings!")
            return
        
        embed = discord.Embed(
            title=f"📋 Warnings for {user}",
            description=f"Total: **{len(user_warnings)}** warnings",
            color=discord.Color.yellow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        for i, w in enumerate(user_warnings[-10:], 1):  # Show last 10
            mod = await self.bot.fetch_user(w["mod_id"]) if w.get("mod_id") else None
            mod_name = mod.name if mod else "Unknown"
            embed.add_field(
                name=f"#{i} - {w['timestamp'][:10]}",
                value=f"**Reason:** {w['reason']}\n**By:** {mod_name}",
                inline=False
            )
        
        await func.send(ctx, embed)
    
    @commands.hybrid_command(name="clearwarnings", aliases=["clearwarns"])
    @app_commands.describe(user="User to clear warnings for")
    @commands.has_permissions(administrator=True)
    async def clearwarnings(self, ctx: commands.Context, user: discord.Member):
        """Clear all warnings for a user! 🧹"""
        
        key = self.get_warnings_key(ctx.guild.id, user.id)
        if key in self.warnings:
            count = len(self.warnings[key])
            del self.warnings[key]
            self._save_warnings()
            await func.send(ctx, f"✅ Cleared **{count}** warnings for **{user}**!")
        else:
            await func.send(ctx, f"**{user}** has no warnings to clear!")
    
    @commands.hybrid_command(name="purge", aliases=["clearmessages"])
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int = 10):
        """Purge messages from the channel! 🧹"""
        
        amount = max(1, min(100, amount))
        
        # Defer the response to prevent timeout on slash commands
        await ctx.defer(ephemeral=True)
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for the command itself
            
            self.log_action(ctx.guild.id, ctx.author.id, 0, "clear", f"{len(deleted)-1} messages")
            
            embed = discord.Embed(
                description=f"🧹 Deleted **{len(deleted)-1}** messages!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed, ephemeral=True, delete_after=3)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages!", ephemeral=True)
    
    @commands.hybrid_command(name="slowmode")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int = 5):
        """Set channel slowmode! 🐌"""
        
        seconds = max(0, min(21600, seconds))  # Max 6 hours
        
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                await func.send(ctx, "✅ Slowmode disabled!")
            else:
                await func.send(ctx, f"🐌 Slowmode set to **{seconds}** seconds!")
                
        except discord.Forbidden:
            await func.send(ctx, "❌ I don't have permission to change slowmode!", ephemeral=True)
    
    @commands.hybrid_command(name="modlogs", aliases=["modlog"])
    @commands.has_permissions(administrator=True)
    async def modlogs(self, ctx: commands.Context):
        """View recent moderation actions! 📜"""
        
        guild_logs = [l for l in self.mod_logs if l.get("guild_id") == ctx.guild.id][-10:]
        
        if not guild_logs:
            await func.send(ctx, "📭 No moderation logs yet!")
            return
        
        embed = discord.Embed(
            title="📜 Recent Mod Actions",
            color=discord.Color.blue()
        )
        
        for log in reversed(guild_logs):
            action_emoji = {"kick": "👢", "ban": "🔨", "unban": "🔓", "mute": "🔇", "unmute": "🔊", "warn": "⚠️", "clear": "🧹"}.get(log["action"], "📋")
            try:
                target = await self.bot.fetch_user(log["target_id"]) if log["target_id"] else None
                mod = await self.bot.fetch_user(log["mod_id"])
                target_name = target.name if target else "N/A"
            except:
                target_name = str(log["target_id"])
                mod = None
            
            embed.add_field(
                name=f"{action_emoji} {log['action'].upper()} - {log['timestamp'][:10]}",
                value=f"Target: {target_name}\nBy: {mod.name if mod else 'Unknown'}\nReason: {log.get('reason', 'N/A')[:50]}",
                inline=False
            )
        
        await func.send(ctx, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
