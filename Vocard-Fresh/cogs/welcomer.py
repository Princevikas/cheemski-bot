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
import aiohttp
import io
import function as func

from discord import app_commands
from discord.ext import commands
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Default background
DEFAULT_BACKGROUND = "https://cdn.discordapp.com/attachments/910400703862833192/910426253947994112/121177.png"

# Default welcome/goodbye messages
DEFAULT_WELCOME_MSG = "Welcome {user} to **{server}**! You are member **#{count}**! 🎉"
DEFAULT_GOODBYE_MSG = "Goodbye **{user}**! We'll miss you. 😢"


class Welcomer(commands.Cog):
    """🎉 Welcome & Goodbye messages with beautiful cards!"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        func.logger.info("Welcomer cog loaded!")
    
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        if self.session:
            await self.session.close()
    
    async def _get_welcomer_settings(self, guild_id: int) -> dict:
        """Get welcomer settings for a guild."""
        settings = await func.get_settings(guild_id)
        return settings.get("welcomer", {
            "enabled": False,
            "channel_id": None,
            "background_url": None,
            "message": DEFAULT_WELCOME_MSG,
            "show_card": True
        })
    
    async def _get_goodbye_settings(self, guild_id: int) -> dict:
        """Get goodbye settings for a guild."""
        settings = await func.get_settings(guild_id)
        return settings.get("goodbye", {
            "enabled": False,
            "channel_id": None,
            "message": DEFAULT_GOODBYE_MSG
        })
    
    async def _update_welcomer_settings(self, guild_id: int, data: dict):
        """Update welcomer settings."""
        await func.update_settings(guild_id, {"$set": {"welcomer": data}})
    
    async def _update_goodbye_settings(self, guild_id: int, data: dict):
        """Update goodbye settings."""
        await func.update_settings(guild_id, {"$set": {"goodbye": data}})
    
    async def _download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL."""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception as e:
            func.logger.debug(f"Failed to download image: {e}")
        return None
    
    def _create_circular_avatar(self, avatar: Image.Image, size: int = 230) -> Image.Image:
        """Create circular avatar with border."""
        avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
        
        # Create mask for circular crop
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        # Apply mask
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(avatar, (0, 0), mask)
        
        # Add border
        border_size = size + 10
        bordered = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(bordered)
        border_draw.ellipse((0, 0, border_size, border_size), fill=(47, 49, 54, 255))
        bordered.paste(output, (5, 5), output)
        
        return bordered
    
    async def _generate_welcome_card(
        self, 
        member: discord.Member, 
        background_url: Optional[str] = None
    ) -> io.BytesIO:
        """Generate welcome card image (optimized for low memory)."""
        import gc
        
        # Smaller card dimensions for low memory (512MB server)
        width, height = 800, 350
        
        # Load background
        bg_url = background_url or DEFAULT_BACKGROUND
        background = await self._download_image(bg_url)
        
        if background:
            background = background.resize((width, height), Image.Resampling.LANCZOS)
        else:
            # Fallback gradient background
            background = Image.new("RGBA", (width, height), (47, 49, 54, 255))
        
        # Apply slight blur/darken for text visibility
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 100))
        background = Image.alpha_composite(background, overlay)
        overlay.close()  # Free memory
        
        # Download avatar (smaller size)
        avatar_url = member.display_avatar.replace(size=128, format="png").url
        avatar = await self._download_image(avatar_url)
        
        if avatar:
            circular_avatar = self._create_circular_avatar(avatar, 150)
            avatar.close()  # Free memory
            # Center avatar horizontally
            avatar_x = (width - circular_avatar.width) // 2
            avatar_y = 30
            background.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
            circular_avatar.close()  # Free memory
        
        # Draw text
        draw = ImageDraw.Draw(background)
        
        # Try to load custom font, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            name_font = ImageFont.truetype("arial.ttf", 32)
            sub_font = ImageFont.truetype("arial.ttf", 22)
        except:
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()
        
        # Welcome text
        welcome_text = "Welcome!"
        bbox = draw.textbbox((0, 0), welcome_text, font=title_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, 210), welcome_text, fill="white", font=title_font)
        
        # Username
        username = member.display_name[:25]  # Limit length
        bbox = draw.textbbox((0, 0), username, font=name_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, 270), username, fill="white", font=name_font)
        
        # Server name + member count
        sub_text = f"Member #{member.guild.member_count} of {member.guild.name}"
        if len(sub_text) > 50:
            sub_text = sub_text[:47] + "..."
        bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, 310), sub_text, fill=(180, 180, 180), font=sub_font)
        
        # Save to buffer (use JPEG for smaller size)
        buffer = io.BytesIO()
        # Convert to RGB for JPEG (no alpha)
        rgb_image = background.convert("RGB")
        background.close()  # Free memory
        rgb_image.save(buffer, format="JPEG", quality=85, optimize=True)
        rgb_image.close()  # Free memory
        buffer.seek(0)
        
        # Force garbage collection
        gc.collect()
        
        return buffer
    
    def _format_message(self, template: str, member: discord.Member) -> str:
        """Format message template with member info."""
        return template.format(
            user=member.mention,
            username=member.display_name,
            server=member.guild.name,
            count=member.guild.member_count
        )
    
    # ========== EVENTS ==========
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Send welcome message when member joins."""
        if member.bot:
            return
        
        settings = await self._get_welcomer_settings(member.guild.id)
        if not settings.get("enabled"):
            return
        
        channel_id = settings.get("channel_id")
        if not channel_id:
            return
        
        channel = member.guild.get_channel(int(channel_id))
        if not channel:
            return
        
        try:
            # Generate card if enabled
            files = []
            if settings.get("show_card", True):
                card_buffer = await self._generate_welcome_card(
                    member, 
                    settings.get("background_url")
                )
                files.append(discord.File(card_buffer, filename="welcome.jpg"))
            
            # Format message
            message = self._format_message(
                settings.get("message", DEFAULT_WELCOME_MSG),
                member
            )
            
            # Create embed
            embed = discord.Embed(
                title=f"🎉 Welcome to {member.guild.name}!",
                description=message,
                color=discord.Color.green()
            )
            
            if files:
                embed.set_image(url="attachment://welcome.jpg")
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{member.guild.member_count}")
            
            await channel.send(embed=embed, files=files)
            
        except Exception as e:
            func.logger.error(f"Failed to send welcome message: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Send goodbye message when member leaves."""
        if member.bot:
            return
        
        settings = await self._get_goodbye_settings(member.guild.id)
        if not settings.get("enabled"):
            return
        
        channel_id = settings.get("channel_id")
        if not channel_id:
            return
        
        channel = member.guild.get_channel(int(channel_id))
        if not channel:
            return
        
        try:
            message = self._format_message(
                settings.get("message", DEFAULT_GOODBYE_MSG),
                member
            )
            
            embed = discord.Embed(
                title=f"👋 Goodbye, {member.display_name}!",
                description=message,
                color=discord.Color.orange()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"{member.name} has left the server")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            func.logger.error(f"Failed to send goodbye message: {e}")
    
    # ========== COMMANDS ==========
    
    welcome = app_commands.Group(name="welcome", description="🎉 Welcome message settings")
    
    @welcome.command(name="channel", description="Set the welcome channel")
    @app_commands.describe(channel="Channel for welcome messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set welcome channel."""
        settings = await self._get_welcomer_settings(interaction.guild.id)
        settings["enabled"] = True
        settings["channel_id"] = str(channel.id)
        await self._update_welcomer_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message(
            f"✅ Welcome channel set to {channel.mention}!\n"
            f"New members will receive a welcome message there.",
            ephemeral=True
        )
    
    @welcome.command(name="background", description="Set custom background image for welcome cards")
    @app_commands.describe(url="Image URL for background (or attach an image)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_background(self, interaction: discord.Interaction, url: Optional[str] = None):
        """Set welcome card background."""
        # Check for attachment
        bg_url = url
        if not bg_url and interaction.message and interaction.message.attachments:
            bg_url = interaction.message.attachments[0].url
        
        if not bg_url:
            await interaction.response.send_message(
                "❌ Please provide an image URL or attach an image!",
                ephemeral=True
            )
            return
        
        # Validate URL
        if not bg_url.startswith(("http://", "https://")):
            await interaction.response.send_message(
                "❌ Please provide a valid image URL!",
                ephemeral=True
            )
            return
        
        settings = await self._get_welcomer_settings(interaction.guild.id)
        settings["background_url"] = bg_url
        await self._update_welcomer_settings(interaction.guild.id, settings)
        
        embed = discord.Embed(
            title="✅ Background Updated!",
            description=f"[Click to view]({bg_url})",
            color=discord.Color.green()
        )
        embed.set_image(url=bg_url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @welcome.command(name="message", description="Set custom welcome message")
    @app_commands.describe(message="Welcome message template. Use {user}, {username}, {server}, {count}")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_message(self, interaction: discord.Interaction, message: str):
        """Set welcome message template."""
        settings = await self._get_welcomer_settings(interaction.guild.id)
        settings["message"] = message
        await self._update_welcomer_settings(interaction.guild.id, settings)
        
        # Preview
        preview = self._format_message(message, interaction.user)
        
        await interaction.response.send_message(
            f"✅ Welcome message updated!\n\n**Preview:**\n{preview}",
            ephemeral=True
        )
    
    @welcome.command(name="test", description="Test the welcome card with yourself")
    async def welcome_test(self, interaction: discord.Interaction):
        """Test welcome card."""
        await interaction.response.defer()
        
        settings = await self._get_welcomer_settings(interaction.guild.id)
        
        try:
            card_buffer = await self._generate_welcome_card(
                interaction.user,
                settings.get("background_url")
            )
            
            file = discord.File(card_buffer, filename="welcome_test.jpg")
            
            message = self._format_message(
                settings.get("message", DEFAULT_WELCOME_MSG),
                interaction.user
            )
            
            embed = discord.Embed(
                title=f"🎉 Welcome Card Preview",
                description=message,
                color=discord.Color.green()
            )
            embed.set_image(url="attachment://welcome_test.jpg")
            embed.set_footer(text="This is how welcome cards will look!")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating card: {e}")
    
    @welcome.command(name="disable", description="Disable welcome messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_disable(self, interaction: discord.Interaction):
        """Disable welcomer."""
        settings = await self._get_welcomer_settings(interaction.guild.id)
        settings["enabled"] = False
        await self._update_welcomer_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message("✅ Welcome messages disabled!", ephemeral=True)
    
    @welcome.command(name="card", description="Toggle welcome card image on/off")
    @app_commands.describe(enabled="Show welcome card image?")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_card(self, interaction: discord.Interaction, enabled: bool):
        """Toggle card display."""
        settings = await self._get_welcomer_settings(interaction.guild.id)
        settings["show_card"] = enabled
        await self._update_welcomer_settings(interaction.guild.id, settings)
        
        status = "enabled" if enabled else "disabled"
        await interaction.response.send_message(f"✅ Welcome card images {status}!", ephemeral=True)
    
    # ========== GOODBYE COMMANDS ==========
    
    goodbye = app_commands.Group(name="goodbye", description="👋 Goodbye message settings")
    
    @goodbye.command(name="channel", description="Set the goodbye channel")
    @app_commands.describe(channel="Channel for goodbye messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set goodbye channel."""
        settings = await self._get_goodbye_settings(interaction.guild.id)
        settings["enabled"] = True
        settings["channel_id"] = str(channel.id)
        await self._update_goodbye_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message(
            f"✅ Goodbye channel set to {channel.mention}!",
            ephemeral=True
        )
    
    @goodbye.command(name="message", description="Set custom goodbye message")
    @app_commands.describe(message="Goodbye message template. Use {user}, {username}, {server}, {count}")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def goodbye_message(self, interaction: discord.Interaction, message: str):
        """Set goodbye message template."""
        settings = await self._get_goodbye_settings(interaction.guild.id)
        settings["message"] = message
        await self._update_goodbye_settings(interaction.guild.id, settings)
        
        preview = self._format_message(message, interaction.user)
        
        await interaction.response.send_message(
            f"✅ Goodbye message updated!\n\n**Preview:**\n{preview}",
            ephemeral=True
        )
    
    @goodbye.command(name="disable", description="Disable goodbye messages")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def goodbye_disable(self, interaction: discord.Interaction):
        """Disable goodbye."""
        settings = await self._get_goodbye_settings(interaction.guild.id)
        settings["enabled"] = False
        await self._update_goodbye_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message("✅ Goodbye messages disabled!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer(bot))
