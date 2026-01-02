"""MIT License

Copyright (c) 2023 - present Vocard Development

Comprehensive Audit Logging System
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import datetime

import function as func
from function import send, cooldown_check, get_settings, update_settings


class AuditColors:
    """Color codes for different audit event types"""
    MEMBER_JOIN = 0x2ecc71  # Green
    MEMBER_LEAVE = 0xe74c3c  # Red
    MEMBER_UPDATE = 0x3498db  # Blue
    VOICE = 0x9b59b6  # Purple
    MESSAGE_DELETE = 0xe67e22  # Orange
    MESSAGE_EDIT = 0xf1c40f  # Yellow
    CHANNEL = 0x1abc9c  # Teal
    ROLE = 0xe91e63  # Pink
    SERVER = 0x34495e  # Dark gray
    BAN = 0x992d22  # Dark red


class AuditSetupModal(discord.ui.Modal, title="📋 Audit Log Setup"):
    """Modal for audit logging configuration"""
    
    channel_input = discord.ui.TextInput(
        label="Audit Log Channel",
        placeholder="Enter channel name or ID (e.g. audit-logs)",
        max_length=100,
        required=True
    )
    
    def __init__(self, guild: discord.Guild):
        super().__init__()
        self.guild = guild
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse channel input
        channel_str = self.channel_input.value.strip()
        channel = None
        
        # Try to find by ID
        if channel_str.isdigit():
            channel = self.guild.get_channel(int(channel_str))
        
        # Try to find by name
        if not channel:
            channel = discord.utils.get(self.guild.text_channels, name=channel_str.lstrip('#'))
        
        if not channel:
            return await interaction.response.send_message(
                f"❌ Channel not found! Make sure the channel exists and try again.",
                ephemeral=True
            )
        
        # Enable audit logging
        await update_settings(self.guild.id, {
            "$set": {
                "audit.enabled": True,
                "audit.channel_id": channel.id,
                "audit.events": {
                    "member_join": True,
                    "member_leave": True,
                    "member_update": True,
                    "member_ban": True,
                    "member_unban": True,
                    "voice_state": True,
                    "message_delete": True,
                    "message_edit": True,
                    "bulk_delete": True,
                    "channel_create": True,
                    "channel_delete": True,
                    "channel_update": True,
                    "role_create": True,
                    "role_delete": True,
                    "role_update": True
                }
            }
        })
        
        await interaction.response.send_message(
            f"✅ Audit logging enabled! Logs will be sent to {channel.mention}\n"
            f"All event types are enabled. Use `/audit status` to check configuration.",
            ephemeral=True
        )


def is_admin_or_bot_access():
    """Check if user is admin or in bot_access_user list"""
    async def predicate(ctx: commands.Context):
        # Check if user is in bot_access_user (safely get the list)
        bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
        if ctx.author.id in bot_access_users:
            return True
        # Otherwise check administrator permission
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)


class Audit(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    async def get_audit_channel(self, guild_id: int) -> Optional[discord.TextChannel]:
        """Get the configured audit channel for a guild"""
        settings = await get_settings(guild_id)
        audit_config = settings.get("audit", {})
        
        if not audit_config.get("enabled", False):
            return None
        
        channel_id = audit_config.get("channel_id")
        if not channel_id:
            return None
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        
        return guild.get_channel(channel_id)
    
    async def is_event_enabled(self, guild_id: int, event_name: str) -> bool:
        """Check if a specific event type is enabled"""
        settings = await get_settings(guild_id)
        audit_config = settings.get("audit", {})
        events = audit_config.get("events", {})
        return events.get(event_name, True)
    
    async def is_auditor(self, guild_id: int, user_id: int) -> bool:
        """Check if user is authorized to access audit logs"""
        settings = await get_settings(guild_id)
        audit_config = settings.get("audit", {})
        auditors = audit_config.get("auditors", [])
        return user_id in auditors
    
    async def send_audit_log(self, guild_id: int, embed: discord.Embed):
        """Send an audit log embed to the configured channel"""
        channel = await self.get_audit_channel(guild_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except:
                pass
    
    # ========== MEMBER EVENTS ==========
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log when a member joins"""
        if not await self.is_event_enabled(member.guild.id, "member_join"):
            return
        
        embed = discord.Embed(
            title="✅ Member Joined",
            description=f"{member.mention} joined the server",
            color=AuditColors.MEMBER_JOIN,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_audit_log(member.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log when a member leaves"""
        if not await self.is_event_enabled(member.guild.id, "member_leave"):
            return
        
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        
        embed = discord.Embed(
            title="❌ Member Left",
            description=f"{member.mention} left the server",
            color=AuditColors.MEMBER_LEAVE,
            timestamp=datetime.datetime.utcnow()
        )
        if roles:
            embed.add_field(name="Roles", value=", ".join(roles[:10]), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_audit_log(member.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log member updates (nickname, roles, avatar)"""
        if not await self.is_event_enabled(after.guild.id, "member_update"):
            return
        
        embed = None
        
        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(
                title="🏷️ Nickname Changed",
                color=AuditColors.MEMBER_UPDATE,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Member", value=after.mention, inline=False)
            embed.add_field(name="Before", value=before.nick or "None", inline=True)
            embed.add_field(name="After", value=after.nick or "None", inline=True)
        
        # Role changes
        elif before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            
            if added or removed:
                embed = discord.Embed(
                    title="👤 Member Roles Updated",
                    color=AuditColors.MEMBER_UPDATE,
                    timestamp=datetime.datetime.utcnow()
                )
                embed.add_field(name="Member", value=after.mention, inline=False)
                if added:
                    embed.add_field(name="➕ Added", value=", ".join([r.mention for r in added]), inline=False)
                if removed:
                    embed.add_field(name="➖ Removed", value=", ".join([r.mention for r in removed]), inline=False)
        
        # Avatar change
        elif before.avatar != after.avatar:
            embed = discord.Embed(
                title="🖼️ Avatar Changed",
                color=AuditColors.MEMBER_UPDATE,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Member", value=after.mention, inline=False)
            if before.avatar:
                embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)
        
        if embed:
            embed.set_footer(text=f"User ID: {after.id}")
            await self.send_audit_log(after.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Log global profile changes (avatar, username) - fires for all mutual guilds"""
        # Only track avatar changes
        if before.avatar == after.avatar and before.name == after.name:
            return
        
        # Send to all mutual guilds with audit enabled
        for guild in self.bot.guilds:
            member = guild.get_member(after.id)
            if not member:
                continue
            
            if not await self.is_event_enabled(guild.id, "member_update"):
                continue
            
            embed = None
            
            # Global avatar change
            if before.avatar != after.avatar:
                embed = discord.Embed(
                    title="🖼️ Profile Picture Changed",
                    description=f"{after.mention} changed their global profile picture",
                    color=AuditColors.MEMBER_UPDATE,
                    timestamp=datetime.datetime.utcnow()
                )
                embed.add_field(name="Member", value=f"{after} ({after.id})", inline=False)
                if before.avatar:
                    embed.set_thumbnail(url=before.display_avatar.url)
                embed.set_image(url=after.display_avatar.url)
            
            # Username change
            elif before.name != after.name:
                embed = discord.Embed(
                    title="✏️ Username Changed",
                    description=f"A member changed their username",
                    color=AuditColors.MEMBER_UPDATE,
                    timestamp=datetime.datetime.utcnow()
                )
                embed.add_field(name="Before", value=before.name, inline=True)
                embed.add_field(name="After", value=after.name, inline=True)
                embed.add_field(name="User ID", value=str(after.id), inline=False)
                embed.set_thumbnail(url=after.display_avatar.url)
            
            if embed:
                embed.set_footer(text=f"User ID: {after.id}")
                await self.send_audit_log(guild.id, embed)
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log when a member is banned"""
        if not await self.is_event_enabled(guild.id, "member_ban"):
            return
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{user.mention} was banned",
            color=AuditColors.BAN,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_audit_log(guild.id, embed)
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log when a member is unbanned"""
        if not await self.is_event_enabled(guild.id, "member_unban"):
            return
        
        embed = discord.Embed(
            title="🔓 Member Unbanned",
            description=f"{user.mention} was unbanned",
            color=AuditColors.MEMBER_JOIN,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_audit_log(guild.id, embed)
    
    # ========== VOICE EVENTS ==========
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Log voice channel activity"""
        if not await self.is_event_enabled(member.guild.id, "voice_state"):
            return
        
        embed = None
        
        # Joined voice
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🔊 Joined Voice Channel",
                color=AuditColors.VOICE,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Member", value=member.mention, inline=False)
            embed.add_field(name="Channel", value=after.channel.mention, inline=False)
        
        # Left voice
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🔇 Left Voice Channel",
                color=AuditColors.VOICE,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Member", value=member.mention, inline=False)
            embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        
        # Moved channels
        elif before.channel != after.channel and before.channel and after.channel:
            embed = discord.Embed(
                title="🔀 Moved Voice Channels",
                color=AuditColors.VOICE,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Member", value=member.mention, inline=False)
            embed.add_field(name="From", value=before.channel.mention, inline=True)
            embed.add_field(name="To", value=after.channel.mention, inline=True)
        
        # Mute/Unmute
        elif before.self_mute != after.self_mute:
            status = "Muted" if after.self_mute else "Unmuted"
            embed = discord.Embed(
                title=f"🎤 {status}",
                description=f"{member.mention} {status.lower()} themselves",
                color=AuditColors.VOICE,
                timestamp=datetime.datetime.utcnow()
            )
        
        # Deafen/Undeafen
        elif before.self_deaf != after.self_deaf:
            status = "Deafened" if after.self_deaf else "Undeafened"
            embed = discord.Embed(
                title=f"🔇 {status}",
                description=f"{member.mention} {status.lower()} themselves",
                color=AuditColors.VOICE,
                timestamp=datetime.datetime.utcnow()
            )
        
        # Streaming
        elif before.self_stream != after.self_stream:
            status = "Started" if after.self_stream else "Stopped"
            embed = discord.Embed(
                title=f"📹 {status} Streaming",
                description=f"{member.mention} {status.lower()} streaming",
                color=AuditColors.VOICE,
                timestamp=datetime.datetime.utcnow()
            )
        
        if embed:
            embed.set_footer(text=f"User ID: {member.id}")
            await self.send_audit_log(member.guild.id, embed)
    
    # ========== MESSAGE EVENTS ==========
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        if message.author.bot or not message.guild:
            return
        
        if not await self.is_event_enabled(message.guild.id, "message_delete"):
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=AuditColors.MESSAGE_DELETE,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        
        if message.content:
            content = message.content[:1024]
            embed.add_field(name="Content", value=content, inline=False)
        
        if message.attachments:
            embed.add_field(name="Attachments", value=f"{len(message.attachments)} file(s)", inline=False)
        
        embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
        
        await self.send_audit_log(message.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        """Log bulk message deletion"""
        if not messages or not messages[0].guild:
            return
        
        guild = messages[0].guild
        if not await self.is_event_enabled(guild.id, "bulk_delete"):
            return
        
        embed = discord.Embed(
            title="🗑️ Bulk Message Delete",
            description=f"{len(messages)} messages were deleted",
            color=AuditColors.MESSAGE_DELETE,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Channel", value=messages[0].channel.mention, inline=False)
        embed.set_footer(text=f"Guild ID: {guild.id}")
        
        await self.send_audit_log(guild.id, embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log edited messages"""
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        if not await self.is_event_enabled(before.guild.id, "message_edit"):
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=AuditColors.MESSAGE_EDIT,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before", value=before.content[:1024] if before.content else "*Empty*", inline=False)
        embed.add_field(name="After", value=after.content[:1024] if after.content else "*Empty*", inline=False)
        embed.set_footer(text=f"User ID: {before.author.id} | Message ID: {before.id}")
        
        await self.send_audit_log(before.guild.id, embed)
    
    # ========== CHANNEL EVENTS ==========
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Log channel creation"""
        if not await self.is_event_enabled(channel.guild.id, "channel_create"):
            return
        
        channel_type = str(channel.type).replace("_", " ").title()
        
        embed = discord.Embed(
            title="➕ Channel Created",
            description=f"{channel.mention} was created",
            color=AuditColors.CHANNEL,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Type", value=channel_type, inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.send_audit_log(channel.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Log channel deletion"""
        if not await self.is_event_enabled(channel.guild.id, "channel_delete"):
            return
        
        channel_type = str(channel.type).replace("_", " ").title()
        
        embed = discord.Embed(
            title="❌ Channel Deleted",
            description=f"**{channel.name}** was deleted",
            color=AuditColors.CHANNEL,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Type", value=channel_type, inline=True)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.send_audit_log(channel.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        """Log channel updates"""
        if not await self.is_event_enabled(after.guild.id, "channel_update"):
            return
        
        embed = None
        
        if before.name != after.name:
            embed = discord.Embed(
                title="✏️ Channel Name Changed",
                color=AuditColors.CHANNEL,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Channel", value=after.mention, inline=False)
            embed.add_field(name="Before", value=before.name, inline=True)
            embed.add_field(name="After", value=after.name, inline=True)
        
        if embed:
            embed.set_footer(text=f"Channel ID: {after.id}")
            await self.send_audit_log(after.guild.id, embed)
    
    # ========== ROLE EVENTS ==========
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Log role creation"""
        if not await self.is_event_enabled(role.guild.id, "role_create"):
            return
        
        embed = discord.Embed(
            title="➕ Role Created",
            description=f"{role.mention} was created",
            color=AuditColors.ROLE,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.send_audit_log(role.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Log role deletion"""
        if not await self.is_event_enabled(role.guild.id, "role_delete"):
            return
        
        embed = discord.Embed(
            title="❌ Role Deleted",
            description=f"**{role.name}** was deleted",
            color=AuditColors.ROLE,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await self.send_audit_log(role.guild.id, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Log role updates"""
        if not await self.is_event_enabled(after.guild.id, "role_update"):
            return
        
        embed = None
        
        if before.name != after.name:
            embed = discord.Embed(
                title="✏️ Role Name Changed",
                color=AuditColors.ROLE,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Role", value=after.mention, inline=False)
            embed.add_field(name="Before", value=before.name, inline=True)
            embed.add_field(name="After", value=after.name, inline=True)
        
        if embed:
            embed.set_footer(text=f"Role ID: {after.id}")
            await self.send_audit_log(after.guild.id, embed)
    
    # ========== COMMANDS ==========
    
    @commands.hybrid_group(name="audit")
    @is_admin_or_bot_access()
    async def audit(self, ctx: commands.Context):
        """Audit logging configuration commands"""
        if ctx.invoked_subcommand is None:
            await send(ctx, "Use `/audit setup`, `/audit toggle`, or `/audit status`", ephemeral=True)
    
    @audit.command(name="setup")
    @is_admin_or_bot_access()
    async def audit_setup(self, ctx: commands.Context):
        """Set up audit logging via interactive modal"""
        
        # Check if this is a slash command (required for modals)
        if not ctx.interaction:
            return await send(ctx, "❌ This command only works as a slash command! Use `/audit setup` instead.", ephemeral=True)
        
        # Show the modal
        modal = AuditSetupModal(ctx.guild)
        await ctx.interaction.response.send_modal(modal)
    
    @audit.command(name="disable")
    @is_admin_or_bot_access()
    async def audit_disable(self, ctx: commands.Context):
        """Disable audit logging"""
        
        await update_settings(ctx.guild.id, {"$set": {"audit.enabled": False}})
        await send(ctx, "❌ Audit logging disabled", ephemeral=True)
    
    @audit.command(name="status")
    @is_admin_or_bot_access()
    async def audit_status(self, ctx: commands.Context):
        """Check audit log configuration status"""
        
        settings = await get_settings(ctx.guild.id)
        audit_config = settings.get("audit", {})
        
        if not audit_config.get("enabled"):
            return await send(ctx, "❌ Audit logging is disabled. Use `/audit setup` to enable it.", ephemeral=True)
        
        channel_id = audit_config.get("channel_id")
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        
        embed = discord.Embed(
            title="📋 Audit Log Status",
            color=0x3498db
        )
        embed.add_field(name="Status", value="✅ Enabled", inline=False)
        embed.add_field(name="Channel", value=channel.mention if channel else "⚠️ Not set", inline=False)
        
        await ctx.send(embed=embed, ephemeral=True)
    
    @audit.command(name="export")
    @app_commands.describe(limit="Number of audit log entries to export (max 100)")
    async def audit_export(self, ctx: commands.Context, limit: int = 50):
        """Export audit logs as a text file and send to your DMs"""
        
        # Check if user is an authorized auditor
        if not await self.is_auditor(ctx.guild.id, ctx.author.id):
            return await send(ctx, "❌ You are not authorized to export audit logs. Contact an administrator to be added as an auditor.", ephemeral=True)
        
        if limit > 100:
            return await send(ctx, "❌ Maximum limit is 100 entries", ephemeral=True)
        
        audit_channel = await self.get_audit_channel(ctx.guild.id)
        if not audit_channel:
            return await send(ctx, "❌ Audit logging is not configured. Use `/audit setup` first.", ephemeral=True)
        
        await send(ctx, "📥 Generating audit log export...", ephemeral=True)
        
        try:
            # Fetch recent messages from audit channel
            messages = []
            async for message in audit_channel.history(limit=limit):
                if message.embeds:
                    embed = message.embeds[0]
                    timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                    
                    log_entry = f"[{timestamp}] {embed.title}\n"
                    if embed.description:
                        log_entry += f"{embed.description}\n"
                    for field in embed.fields:
                        log_entry += f"  {field.name}: {field.value}\n"
                    if embed.footer:
                        log_entry += f"  {embed.footer.text}\n"
                    log_entry += "-" * 50 + "\n"
                    
                    messages.append(log_entry)
            
            if not messages:
                return await send(ctx, "❌ No audit logs found to export", ephemeral=True)
            
            # Create text file
            import io
            content = f"Audit Logs Export - {ctx.guild.name}\n"
            content += f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            content += f"Total Entries: {len(messages)}\n"
            content += "=" * 50 + "\n\n"
            content += "\n".join(reversed(messages))  # Reverse to chronological order
            
            file = discord.File(io.BytesIO(content.encode('utf-8')), filename=f"audit_logs_{ctx.guild.name}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt")
            
            # Send to user's DM
            try:
                await ctx.author.send(
                    f"📋 **Audit Log Export from {ctx.guild.name}**\n"
                    f"Exported {len(messages)} entries",
                    file=file
                )
                await send(ctx, "✅ Audit logs sent to your DMs!", ephemeral=True)
            except discord.Forbidden:
                await send(ctx, "❌ I can't send you DMs! Please enable DMs from server members.", ephemeral=True)
        
        except Exception as e:
            await send(ctx, f"❌ Failed to export audit logs: {str(e)}", ephemeral=True)
    
    @audit.command(name="addauditor")
    @app_commands.describe(user="The user to authorize for audit log access")
    @is_admin_or_bot_access()
    async def audit_addauditor(self, ctx: commands.Context, user: discord.Member):
        """Add a user to the auditors list"""
        
        settings = await get_settings(ctx.guild.id)
        audit_config = settings.get("audit", {})
        auditors = audit_config.get("auditors", [])
        
        if user.id in auditors:
            return await send(ctx, f"❌ {user.mention} is already an auditor", ephemeral=True)
        
        auditors.append(user.id)
        await update_settings(ctx.guild.id, {"$set": {"audit.auditors": auditors}})
        await send(ctx, f"✅ {user.mention} has been added as an auditor and can now export audit logs", ephemeral=True)
    
    @audit.command(name="removeauditor")
    @app_commands.describe(user="The user to remove from audit log access")
    @is_admin_or_bot_access()
    async def audit_removeauditor(self, ctx: commands.Context, user: discord.Member):
        """Remove a user from the auditors list"""
        
        settings = await get_settings(ctx.guild.id)
        audit_config = settings.get("audit", {})
        auditors = audit_config.get("auditors", [])
        
        if user.id not in auditors:
            return await send(ctx, f"❌ {user.mention} is not an auditor", ephemeral=True)
        
        auditors.remove(user.id)
        await update_settings(ctx.guild.id, {"$set": {"audit.auditors": auditors}})
        await send(ctx, f"✅ {user.mention} has been removed from auditors", ephemeral=True)
    
    @audit.command(name="listauditors")
    @is_admin_or_bot_access()
    async def audit_listauditors(self, ctx: commands.Context):
        """List all authorized auditors"""
        
        settings = await get_settings(ctx.guild.id)
        audit_config = settings.get("audit", {})
        auditors = audit_config.get("auditors", [])
        
        if not auditors:
            return await send(ctx, "❌ No auditors configured. Use `/audit addauditor` to add users.", ephemeral=True)
        
        embed = discord.Embed(
            title="📋 Authorized Auditors",
            description=f"Users who can export audit logs",
            color=0x3498db
        )
        
        auditor_list = []
        for auditor_id in auditors:
            member = ctx.guild.get_member(auditor_id)
            if member:
                auditor_list.append(f"• {member.mention} ({member.name})")
            else:
                auditor_list.append(f"• <@{auditor_id}> (ID: {auditor_id})")
        
        embed.add_field(name=f"Total: {len(auditors)}", value="\n".join(auditor_list), inline=False)
        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Audit(bot))
