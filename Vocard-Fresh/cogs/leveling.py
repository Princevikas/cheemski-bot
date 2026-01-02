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
import random
import function as func

from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# Default leveling settings
DEFAULT_SETTINGS = {
    "enabled": False,
    "channel_id": None,  # None = same channel as message
    "xp_min": 15,
    "xp_max": 25,
    "cooldown": 60,  # seconds
    "role_rewards": {},  # {level: role_id}
    "ignored_channels": [],
    "multipliers": {}  # {channel_id: multiplier}
}


def xp_for_level(level: int) -> int:
    """Calculate total XP needed to reach a level."""
    return 5 * (level ** 2) + 50 * level + 100


def level_from_xp(xp: int) -> int:
    """Calculate level from total XP."""
    level = 0
    while xp >= xp_for_level(level + 1):
        xp -= xp_for_level(level + 1)
        level += 1
    return level


def xp_progress(xp: int, level: int) -> tuple[int, int]:
    """Get current XP progress towards next level."""
    total_for_current = sum(xp_for_level(l) for l in range(1, level + 1))
    current_xp = xp - total_for_current
    next_level_xp = xp_for_level(level + 1)
    return current_xp, next_level_xp


class Leveling(commands.Cog):
    """📈 XP & Leveling system with rank cards!"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.cooldowns: dict = {}  # {guild_id: {user_id: last_xp_time}}
        func.logger.info("Leveling cog loaded!")
    
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        if self.session:
            await self.session.close()
    
    # ========== DATABASE HELPERS ==========
    
    async def _get_level_settings(self, guild_id: int) -> dict:
        """Get leveling settings for a guild."""
        settings = await func.get_settings(guild_id)
        return settings.get("leveling", DEFAULT_SETTINGS.copy())
    
    async def _update_level_settings(self, guild_id: int, data: dict):
        """Update leveling settings."""
        await func.update_settings(guild_id, {"$set": {"leveling": data}})
    
    async def _get_user_level_data(self, guild_id: int, user_id: int) -> dict:
        """Get user's level data."""
        db = func.MONGO_DB[func.settings.mongodb_name]
        collection = db["user_levels"]
        data = await collection.find_one({"guild_id": str(guild_id), "user_id": str(user_id)})
        if not data:
            return {"xp": 0, "level": 0, "messages": 0}
        return data
    
    async def _update_user_level_data(self, guild_id: int, user_id: int, update: dict):
        """Update user's level data."""
        db = func.MONGO_DB[func.settings.mongodb_name]
        collection = db["user_levels"]
        await collection.update_one(
            {"guild_id": str(guild_id), "user_id": str(user_id)},
            update,
            upsert=True
        )
    
    async def _get_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        """Get top users by XP."""
        db = func.MONGO_DB[func.settings.mongodb_name]
        collection = db["user_levels"]
        cursor = collection.find({"guild_id": str(guild_id)}).sort("xp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def _get_user_rank(self, guild_id: int, user_id: int) -> int:
        """Get user's rank in the guild."""
        db = func.MONGO_DB[func.settings.mongodb_name]
        collection = db["user_levels"]
        user_data = await self._get_user_level_data(guild_id, user_id)
        user_xp = user_data.get("xp", 0)
        
        # Count users with more XP
        count = await collection.count_documents({
            "guild_id": str(guild_id),
            "xp": {"$gt": user_xp}
        })
        return count + 1
    
    # ========== RANK CARD GENERATION ==========
    
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
    
    def _create_circular_avatar(self, avatar: Image.Image, size: int = 120) -> Image.Image:
        """Create circular avatar."""
        avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
        
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(avatar, (0, 0), mask)
        
        return output
    
    async def _generate_rank_card(
        self,
        member: discord.Member,
        xp: int,
        level: int,
        rank: int
    ) -> io.BytesIO:
        """Generate rank card image."""
        import gc
        
        width, height = 800, 250
        
        # Dark background
        card = Image.new("RGB", (width, height), (32, 34, 37))
        draw = ImageDraw.Draw(card)
        
        # Draw accent bar at top
        draw.rectangle([(0, 0), (width, 8)], fill=(88, 101, 242))  # Discord blurple
        
        # Download and draw avatar
        avatar_url = member.display_avatar.replace(size=128, format="png").url
        avatar = await self._download_image(avatar_url)
        
        if avatar:
            circular_avatar = self._create_circular_avatar(avatar, 120)
            avatar.close()
            card.paste(circular_avatar, (30, 65), circular_avatar)
            circular_avatar.close()
        
        # Fonts
        try:
            name_font = ImageFont.truetype("arial.ttf", 32)
            level_font = ImageFont.truetype("arial.ttf", 24)
            small_font = ImageFont.truetype("arial.ttf", 18)
        except:
            name_font = ImageFont.load_default()
            level_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Username
        username = member.display_name[:20]
        draw.text((170, 60), username, fill="white", font=name_font)
        
        # Rank and Level badges
        draw.text((170, 100), f"Rank #{rank}", fill=(180, 180, 180), font=level_font)
        draw.text((320, 100), f"Level {level}", fill=(88, 101, 242), font=level_font)
        
        # XP Progress
        current_xp, next_xp = xp_progress(xp, level)
        progress = current_xp / next_xp if next_xp > 0 else 0
        
        # Progress bar background
        bar_x, bar_y = 170, 160
        bar_width, bar_height = 580, 30
        draw.rounded_rectangle(
            [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
            radius=15,
            fill=(64, 68, 75)
        )
        
        # Progress bar fill
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            draw.rounded_rectangle(
                [(bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height)],
                radius=15,
                fill=(88, 101, 242)
            )
        
        # XP text
        xp_text = f"{current_xp:,} / {next_xp:,} XP"
        bbox = draw.textbbox((0, 0), xp_text, font=small_font)
        text_width = bbox[2] - bbox[0]
        draw.text((bar_x + bar_width - text_width, bar_y + bar_height + 8), 
                  xp_text, fill=(180, 180, 180), font=small_font)
        
        # Total XP
        draw.text((bar_x, bar_y + bar_height + 8), 
                  f"Total: {xp:,} XP", fill=(120, 120, 120), font=small_font)
        
        # Save to buffer
        buffer = io.BytesIO()
        card.save(buffer, format="JPEG", quality=90)
        card.close()
        buffer.seek(0)
        
        gc.collect()
        return buffer
    
    # ========== EVENTS ==========
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award XP on message and track quests."""
        # Ignore bots, DMs
        if message.author.bot or not message.guild:
            return
        
        guild_id = message.guild.id
        user_id = message.author.id
        
        # Track chatter_box quest FIRST (independent of leveling settings)
        # Uses its own faster cooldown to prevent spam
        try:
            if not hasattr(self, 'quest_cooldowns'):
                self.quest_cooldowns = {}
            
            now = datetime.utcnow()
            quest_key = f"{guild_id}_{user_id}"
            last_quest = self.quest_cooldowns.get(quest_key)
            
            # Quest has 5 second cooldown (faster than XP cooldown)
            if not last_quest or (now - last_quest).total_seconds() >= 5:
                self.quest_cooldowns[quest_key] = now
                quests_cog = self.bot.get_cog("DailyQuests")
                if quests_cog:
                    await quests_cog.track_quest(guild_id, user_id, "chatter_box")
        except:
            pass
        
        # Get settings for XP
        settings = await self._get_level_settings(guild_id)
        if not settings.get("enabled", False):
            return
        
        # Check ignored channels
        if str(message.channel.id) in settings.get("ignored_channels", []):
            return
        
        # Check XP cooldown
        cooldown = settings.get("cooldown", 60)
        now = datetime.utcnow()
        
        if guild_id not in self.cooldowns:
            self.cooldowns[guild_id] = {}
        
        last_xp = self.cooldowns[guild_id].get(user_id)
        if last_xp and (now - last_xp).total_seconds() < cooldown:
            return
        
        self.cooldowns[guild_id][user_id] = now
        
        # Calculate XP
        xp_min = settings.get("xp_min", 15)
        xp_max = settings.get("xp_max", 25)
        xp_gained = random.randint(xp_min, xp_max)
        
        # Apply multiplier
        multiplier = settings.get("multipliers", {}).get(str(message.channel.id), 1.0)
        xp_gained = int(xp_gained * multiplier)
        
        # Get current data
        user_data = await self._get_user_level_data(guild_id, user_id)
        old_level = user_data.get("level", 0)
        old_xp = user_data.get("xp", 0)
        
        # Update XP
        new_xp = old_xp + xp_gained
        new_level = level_from_xp(new_xp)
        
        await self._update_user_level_data(guild_id, user_id, {
            "$set": {"xp": new_xp, "level": new_level},
            "$inc": {"messages": 1}
        })
        
        # Level up?
        if new_level > old_level:
            await self._handle_level_up(message, settings, new_level)
    
    async def _handle_level_up(self, message: discord.Message, settings: dict, new_level: int):
        """Handle level up notification and role rewards."""
        # Get translated message
        text = await func.get_lang(message.guild.id, "levelUp")
        level_text = text.format(message.author.mention, new_level) if text else f"🎉 {message.author.mention} reached **Level {new_level}**!"
        
        # Send notification
        channel_id = settings.get("channel_id")
        channel = message.guild.get_channel(int(channel_id)) if channel_id else message.channel
        
        if channel:
            try:
                embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=level_text,
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                await channel.send(embed=embed)
            except:
                pass
        
        # Check role rewards
        role_rewards = settings.get("role_rewards", {})
        role_id = role_rewards.get(str(new_level))
        
        if role_id:
            try:
                role = message.guild.get_role(int(role_id))
                if role and role not in message.author.roles:
                    await message.author.add_roles(role, reason=f"Level {new_level} reward")
            except:
                pass
    
    # ========== COMMANDS ==========
    
    @app_commands.command(name="rank", description="Show your or someone's rank card")
    @app_commands.describe(user="User to check (leave empty for yourself)")
    async def rank(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Show rank card."""
        await interaction.response.defer()
        
        target = user or interaction.user
        
        # Get data
        user_data = await self._get_user_level_data(interaction.guild.id, target.id)
        xp = user_data.get("xp", 0)
        level = user_data.get("level", 0)
        rank = await self._get_user_rank(interaction.guild.id, target.id)
        
        # Generate card
        try:
            card_buffer = await self._generate_rank_card(target, xp, level, rank)
            file = discord.File(card_buffer, filename="rank.jpg")
            await interaction.followup.send(file=file)
            
            # Track rank_checker quest
            try:
                quests_cog = self.bot.get_cog("DailyQuests")
                if quests_cog:
                    await quests_cog.track_quest(interaction.guild.id, interaction.user.id, "rank_checker")
            except:
                pass
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating rank card: {e}")
    
    # NOTE: Leaderboard merged into stats.py /leaderboard command with XP category
    
    # ========== ADMIN COMMANDS ==========
    
    level = app_commands.Group(name="level", description="📈 Leveling system settings")
    
    @level.command(name="toggle", description="Enable/disable leveling")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def level_toggle(self, interaction: discord.Interaction):
        """Toggle leveling system."""
        settings = await self._get_level_settings(interaction.guild.id)
        settings["enabled"] = not settings.get("enabled", False)
        await self._update_level_settings(interaction.guild.id, settings)
        
        # Get Cheems translation
        text_key = "levelToggleOn" if settings["enabled"] else "levelToggleOff"
        text = await func.get_lang(interaction.guild.id, text_key)
        if not text:
            text = "Leveling system enabled ✅" if settings["enabled"] else "Leveling system disabled ❌"
        
        await interaction.response.send_message(text, ephemeral=True)
    
    @level.command(name="channel", description="Set level-up notification channel")
    @app_commands.describe(channel="Channel for level-up messages (leave empty for same channel)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def level_channel(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Set level-up channel."""
        settings = await self._get_level_settings(interaction.guild.id)
        settings["channel_id"] = str(channel.id) if channel else None
        await self._update_level_settings(interaction.guild.id, settings)
        
        if channel:
            await interaction.response.send_message(f"✅ Level-up notifications will be sent to {channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Level-up notifications will be sent in the same channel", ephemeral=True)
    
    @level.command(name="set", description="Set a user's level")
    @app_commands.describe(user="User to set level for", level_num="Level to set")
    @app_commands.checks.has_permissions(administrator=True)
    async def level_set(self, interaction: discord.Interaction, user: discord.Member, level_num: int):
        """Set user's level."""
        if level_num < 0 or level_num > 500:
            await interaction.response.send_message("❌ Level must be between 0 and 500", ephemeral=True)
            return
        
        # Calculate XP for level
        total_xp = sum(xp_for_level(l) for l in range(1, level_num + 1))
        
        await self._update_user_level_data(interaction.guild.id, user.id, {
            "$set": {"xp": total_xp, "level": level_num}
        })
        
        await interaction.response.send_message(f"✅ Set {user.mention}'s level to **{level_num}**", ephemeral=True)
    
    @level.command(name="reset", description="Reset a user's XP")
    @app_commands.describe(user="User to reset")
    @app_commands.checks.has_permissions(administrator=True)
    async def level_reset(self, interaction: discord.Interaction, user: discord.Member):
        """Reset user's XP."""
        await self._update_user_level_data(interaction.guild.id, user.id, {
            "$set": {"xp": 0, "level": 0, "messages": 0}
        })
        
        await interaction.response.send_message(f"✅ Reset {user.mention}'s XP and level", ephemeral=True)
    
    @level.command(name="reward", description="Add a role reward for reaching a level")
    @app_commands.describe(level_num="Level to reward at", role="Role to give")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def level_reward(self, interaction: discord.Interaction, level_num: int, role: discord.Role):
        """Add role reward."""
        if level_num < 1 or level_num > 500:
            await interaction.response.send_message("❌ Level must be between 1 and 500", ephemeral=True)
            return
        
        settings = await self._get_level_settings(interaction.guild.id)
        if "role_rewards" not in settings:
            settings["role_rewards"] = {}
        
        settings["role_rewards"][str(level_num)] = str(role.id)
        await self._update_level_settings(interaction.guild.id, settings)
        
        await interaction.response.send_message(
            f"✅ Users will receive {role.mention} at level **{level_num}**",
            ephemeral=True
        )
    
    @level.command(name="rewards", description="View all role rewards")
    async def level_rewards_list(self, interaction: discord.Interaction):
        """List role rewards."""
        settings = await self._get_level_settings(interaction.guild.id)
        rewards = settings.get("role_rewards", {})
        
        if not rewards:
            await interaction.response.send_message("📋 No role rewards configured", ephemeral=True)
            return
        
        embed = discord.Embed(title="🎁 Level Role Rewards", color=discord.Color.gold())
        
        description = ""
        for level_str, role_id in sorted(rewards.items(), key=lambda x: int(x[0])):
            role = interaction.guild.get_role(int(role_id))
            role_name = role.mention if role else f"Unknown ({role_id})"
            description += f"**Level {level_str}** → {role_name}\n"
        
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @level.command(name="settings", description="View leveling settings")
    async def level_settings_view(self, interaction: discord.Interaction):
        """View settings."""
        settings = await self._get_level_settings(interaction.guild.id)
        
        embed = discord.Embed(title="📈 Leveling Settings", color=discord.Color.blurple())
        embed.add_field(name="Status", value="✅ Enabled" if settings.get("enabled") else "❌ Disabled", inline=True)
        embed.add_field(name="XP Range", value=f"{settings.get('xp_min', 15)}-{settings.get('xp_max', 25)}", inline=True)
        embed.add_field(name="Cooldown", value=f"{settings.get('cooldown', 60)}s", inline=True)
        
        channel_id = settings.get("channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(int(channel_id))
            embed.add_field(name="Level-up Channel", value=channel.mention if channel else "Not set", inline=True)
        else:
            embed.add_field(name="Level-up Channel", value="Same channel", inline=True)
        
        rewards_count = len(settings.get("role_rewards", {}))
        embed.add_field(name="Role Rewards", value=f"{rewards_count} configured", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
