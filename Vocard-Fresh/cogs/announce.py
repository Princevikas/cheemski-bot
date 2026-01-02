"""MIT License

Copyright (c) 2023 - present Vocard Development
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import function as func
from function import send, cooldown_check


class AnnounceModal(discord.ui.Modal, title="📢 Create Announcement"):
    """Modal form for creating announcements"""
    
    announcement_title = discord.ui.TextInput(
        label="Title",
        placeholder="Enter announcement title...",
        max_length=256,
        required=True
    )
    
    announcement_content = discord.ui.TextInput(
        label="Content",
        style=discord.TextStyle.paragraph,
        placeholder="Enter announcement content...",
        max_length=4000,
        required=True
    )
    
    announcement_color = discord.ui.TextInput(
        label="Color (hex code, e.g. #ff0000)",
        placeholder="#3498db",
        max_length=7,
        required=False,
        default="#3498db"
    )
    
    image_url = discord.ui.TextInput(
        label="Image URL (optional)",
        placeholder="https://example.com/image.png",
        max_length=500,
        required=False
    )
    
    def __init__(self, channel: discord.TextChannel, is_anonymous: bool = False):
        super().__init__()
        self.target_channel = channel
        self.is_anonymous = is_anonymous
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse color
        try:
            color_str = self.announcement_color.value.strip()
            if color_str.startswith("#"):
                color_str = color_str[1:]
            color = int(color_str, 16)
        except:
            color = 0x3498db  # Default blue
        
        # Create embed
        embed = discord.Embed(
            title=f"📢 {self.announcement_title.value}",
            description=self.announcement_content.value,
            color=color
        )
        
        # Add image if provided
        if self.image_url.value and self.image_url.value.strip():
            embed.set_image(url=self.image_url.value.strip())
        
        if self.is_anonymous:
            embed.set_footer(text="Anonymous Announcement")
        else:
            embed.set_footer(
                text=f"Announced by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
        
        embed.timestamp = discord.utils.utcnow()
        
        # Send to target channel
        try:
            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Announcement sent to {self.target_channel.mention}!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ I don't have permission to send messages in {self.target_channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to send announcement: {str(e)}",
                ephemeral=True
            )


class Announce(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    async def check_announce_permission(self, ctx: commands.Context) -> bool:
        """Check if user has permission to use announce command."""
        # Bot owner/admin always has access
        if ctx.author.id in func.settings.bot_access_user:
            return True
        
        # Check if user has manage_messages permission
        if ctx.author.guild_permissions.manage_messages:
            return True
        
        # Check if user has any of the announcer roles from guild settings
        try:
            guild_data = await func.get_settings(ctx.guild.id)
            if guild_data:
                # announce_roles is an array of role IDs
                announce_roles = guild_data.get("announce_roles", [])
                if announce_roles:
                    member_role_ids = [str(role.id) for role in ctx.author.roles]
                    # Check if user has any of the configured announce roles
                    for role_id in announce_roles:
                        if str(role_id) in member_role_ids:
                            return True
        except Exception as e:
            print(f"Error checking announce permission: {e}")
        
        return False
    
    @commands.hybrid_command(name="announce")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        anonymous="Hide your name from the announcement"
    )
    @app_commands.choices(anonymous=[
        app_commands.Choice(name="No - Show my name", value=0),
        app_commands.Choice(name="Yes - Anonymous", value=1)
    ])
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def announce(self, ctx: commands.Context, channel: discord.TextChannel = None, anonymous: int = 0):
        """Create and send an announcement embed to a channel."""
        
        # Check permission
        if not await self.check_announce_permission(ctx):
            return await send(ctx, "❌ You need the Announcer role or Manage Messages permission to use this command!", ephemeral=True)
        
        # Check if this is a slash command (required for modals)
        if not ctx.interaction:
            return await send(ctx, "❌ This command only works as a slash command! Use `/announce` instead.", ephemeral=True)
        
        # Default to current channel if not specified
        target_channel = channel or ctx.channel
        
        # Check bot permissions in target channel
        if not target_channel.permissions_for(ctx.guild.me).send_messages:
            return await send(ctx, f"❌ I don't have permission to send messages in {target_channel.mention}!", ephemeral=True)
        
        # Show the modal
        is_anonymous = bool(anonymous)
        modal = AnnounceModal(target_channel, is_anonymous)
        await ctx.interaction.response.send_modal(modal)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Announce(bot))
