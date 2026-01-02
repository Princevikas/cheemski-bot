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
import random
import function as func

from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime, date, timezone

# Quest definitions - VERIFIED working commands with tracking hooks!
# Only include quests where we have actually implemented tracking
QUEST_POOL = [
    # === FUN COMMANDS (fun.py) - TRACKED via track_quest() ===
    {"id": "bonk_master", "name": "🐕 Bonk Master", "desc": "Bonk {target} people", "min": 2, "max": 4, "xp": 50, "category": "fun"},
    {"id": "slap_happy", "name": "👋 Slap Happy", "desc": "Slap {target} people", "min": 2, "max": 4, "xp": 45, "category": "fun"},
    {"id": "boop_master", "name": "👃 Boop Master", "desc": "Boop {target} people", "min": 2, "max": 4, "xp": 40, "category": "fun"},
    {"id": "coin_flipper", "name": "🪙 Coin Flipper", "desc": "Flip a coin {target} times", "min": 3, "max": 5, "xp": 25, "category": "fun"},
    {"id": "pat_giver", "name": "🤗 Pat Giver", "desc": "Pat {target} people", "min": 2, "max": 4, "xp": 40, "category": "fun"},
    {"id": "hug_dealer", "name": "🫂 Hug Dealer", "desc": "Hug {target} people", "min": 2, "max": 4, "xp": 45, "category": "fun"},
    {"id": "poke_master", "name": "👉 Poke Master", "desc": "Poke {target} people", "min": 2, "max": 4, "xp": 35, "category": "fun"},
    {"id": "punch_pro", "name": "👊 Punch Pro", "desc": "Punch {target} people", "min": 2, "max": 3, "xp": 50, "category": "fun"},
    {"id": "fortune_seeker", "name": "🎱 Fortune Seeker", "desc": "Ask the 8ball {target} times", "min": 3, "max": 5, "xp": 30, "category": "fun"},
    {"id": "rps_champion", "name": "✂️ RPS Champion", "desc": "Play Rock Paper Scissors {target} times", "min": 3, "max": 5, "xp": 35, "category": "fun"},
    {"id": "motivated", "name": "💪 Motivated", "desc": "Get {target} motivational quotes", "min": 2, "max": 4, "xp": 25, "category": "fun"},
    {"id": "decision_maker", "name": "🤔 Decision Maker", "desc": "Use /choose {target} times", "min": 2, "max": 4, "xp": 30, "category": "fun"},
    
    # === SOCIAL (leveling.py) - TRACKED via on_message ===
    {"id": "chatter_box", "name": "💬 Chatter Box", "desc": "Send {target} messages", "min": 10, "max": 25, "xp": 35, "category": "social"},
    
    # === LEVELING - TRACKED via command use ===
    {"id": "rank_checker", "name": "📊 Rank Checker", "desc": "Check your rank", "min": 1, "max": 1, "xp": 20, "category": "social"},
    {"id": "leaderboard_fan", "name": "🏆 Leaderboard Fan", "desc": "View the leaderboard", "min": 1, "max": 1, "xp": 20, "category": "social"},
    
    # === GAMES (games.py) ===
    {"id": "mind_reader", "name": "🧞 Mind Reader", "desc": "Play Akinator {target} times", "min": 1, "max": 2, "xp": 60, "category": "fun"},
    {"id": "trivia_master", "name": "🧠 Trivia Master", "desc": "Answer {target} trivia questions correctly", "min": 2, "max": 4, "xp": 45, "category": "fun"},
    {"id": "number_guesser", "name": "🔢 Number Guesser", "desc": "Guess the number correctly {target} times", "min": 1, "max": 3, "xp": 35, "category": "fun"},
]


def get_daily_seed(user_id: int, guild_id: int) -> int:
    """Generate a seed based on date + user + guild."""
    today = date.today().isoformat()
    return hash(f"{today}-{user_id}-{guild_id}")


def get_daily_quests_for_user(user_id: int, guild_id: int, count: int = 3) -> list:
    """Get deterministic daily quests for a user."""
    seed = get_daily_seed(user_id, guild_id)
    rng = random.Random(seed)
    
    # Select random quests
    selected = rng.sample(QUEST_POOL, min(count, len(QUEST_POOL)))
    
    # Generate specific targets
    quests = []
    for q in selected:
        target = rng.randint(q["min"], q["max"])
        quests.append({
            "id": q["id"],
            "name": q["name"],
            "desc": q["desc"].format(target=target),
            "target": target,
            "xp": q["xp"],
            "category": q["category"],
            "progress": 0,
            "claimed": False
        })
    
    return quests


class DailyQuests(commands.Cog):
    """🎯 Daily quests for XP rewards!"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        func.logger.info("DailyQuests cog loaded!")
    
    # ========== DATABASE HELPERS ==========
    
    async def _get_user_quests(self, guild_id: int, user_id: int) -> dict:
        """Get user's quest data for today."""
        db = func.MONGO_DB[func.settings.mongodb_name]
        collection = db["daily_quests"]
        today = date.today().isoformat()
        
        data = await collection.find_one({
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "date": today
        })
        
        if not data:
            # Generate new quests for today
            quests = get_daily_quests_for_user(user_id, guild_id, 3)
            data = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "date": today,
                "quests": quests
            }
            await collection.insert_one(data)
        
        return data
    
    async def _update_quest_progress(self, guild_id: int, user_id: int, quest_id: str, increment: int = 1):
        """Update progress for a specific quest."""
        db = func.MONGO_DB[func.settings.mongodb_name]
        collection = db["daily_quests"]
        today = date.today().isoformat()
        
        # First ensure user has quests for today
        await self._get_user_quests(guild_id, user_id)
        
        # Update the specific quest progress
        await collection.update_one(
            {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "date": today,
                "quests.id": quest_id
            },
            {"$inc": {"quests.$.progress": increment}}
        )
    
    async def _claim_quest(self, guild_id: int, user_id: int, quest_id: str) -> Optional[int]:
        """Claim a completed quest and return XP, or None if not claimable."""
        data = await self._get_user_quests(guild_id, user_id)
        
        for quest in data.get("quests", []):
            if quest["id"] == quest_id:
                if quest["claimed"]:
                    return None  # Already claimed
                if quest["progress"] < quest["target"]:
                    return None  # Not completed
                
                # Mark as claimed
                db = func.MONGO_DB[func.settings.mongodb_name]
                collection = db["daily_quests"]
                await collection.update_one(
                    {
                        "guild_id": str(guild_id),
                        "user_id": str(user_id),
                        "date": date.today().isoformat(),
                        "quests.id": quest_id
                    },
                    {"$set": {"quests.$.claimed": True}}
                )
                
                # Award XP via leveling system
                leveling_cog = self.bot.get_cog("Leveling")
                if leveling_cog:
                    await leveling_cog._update_user_level_data(guild_id, user_id, {
                        "$inc": {"xp": quest["xp"]}
                    })
                
                return quest["xp"]
        
        return None
    
    # ========== QUEST TRACKING HOOKS ==========
    
    async def track_quest(self, guild_id: int, user_id: int, quest_id: str, increment: int = 1) -> Optional[dict]:
        """
        Track progress for a quest if user has it today.
        Auto-claims the quest when completed and returns claim info, or None.
        Returns: {"name": str, "xp": int} if auto-claimed, None otherwise.
        """
        data = await self._get_user_quests(guild_id, user_id)
        
        for quest in data.get("quests", []):
            if quest["id"] == quest_id and not quest["claimed"]:
                # Update progress
                await self._update_quest_progress(guild_id, user_id, quest_id, increment)
                
                # Check if quest is now complete (progress + increment >= target)
                new_progress = quest["progress"] + increment
                if new_progress >= quest["target"]:
                    # Auto-claim!
                    xp = await self._claim_quest(guild_id, user_id, quest_id)
                    if xp:
                        func.logger.info(f"Quest '{quest_id}' auto-claimed for user {user_id}, +{xp} XP")
                        return {"name": quest["name"], "xp": xp}
                break
        
        return None
    
    # ========== COMMANDS ==========
    
    @app_commands.command(name="quests", description="View your daily quests")
    async def quests(self, interaction: discord.Interaction):
        """View daily quests."""
        await interaction.response.defer()
        
        data = await self._get_user_quests(interaction.guild.id, interaction.user.id)
        quests = data.get("quests", [])
        
        # Get Cheems translation
        texts = await func.get_lang(interaction.guild.id, "moodHappy")
        header = random.choice(texts) if isinstance(texts, list) else "🎯 Daily Quests vro!"
        
        embed = discord.Embed(
            title="🎯 Daily Quests",
            description=f"{header}\n\nComplete quests to earn bonus XP!",
            color=discord.Color.gold()
        )
        
        # Calculate time until reset
        now = datetime.now(timezone.utc)
        tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + __import__('datetime').timedelta(days=1)
        time_left = tomorrow - now
        hours_left = int(time_left.total_seconds() // 3600)
        mins_left = int((time_left.total_seconds() % 3600) // 60)
        
        for quest in quests:
            progress = quest["progress"]
            target = quest["target"]
            completed = progress >= target
            claimed = quest["claimed"]
            
            # Progress bar
            pct = min(progress / target, 1.0) if target > 0 else 0
            filled = int(pct * 10)
            bar = "█" * filled + "░" * (10 - filled)
            
            # Status
            if claimed:
                status = "✅ Claimed!"
            elif completed:
                status = "🎉 Complete! Use `/claim`"
            else:
                status = f"`{bar}` {progress}/{target}"
            
            embed.add_field(
                name=f"{quest['name']} (+{quest['xp']} XP)",
                value=f"{quest['desc']}\n{status}",
                inline=False
            )
        
        embed.set_footer(text=f"⏰ Resets in {hours_left}h {mins_left}m | Use /daily for bonus XP!")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="claim", description="Claim completed quest rewards")
    async def claim(self, interaction: discord.Interaction):
        """Claim all completed quests."""
        await interaction.response.defer()
        
        data = await self._get_user_quests(interaction.guild.id, interaction.user.id)
        quests = data.get("quests", [])
        
        total_xp = 0
        claimed_count = 0
        
        for quest in quests:
            if quest["progress"] >= quest["target"] and not quest["claimed"]:
                xp = await self._claim_quest(interaction.guild.id, interaction.user.id, quest["id"])
                if xp:
                    total_xp += xp
                    claimed_count += 1
        
        # Check for completion bonus (3/3 quests)
        all_completed = all(q["progress"] >= q["target"] for q in quests)
        all_claimed = all(q["claimed"] for q in quests)
        bonus_xp = 0
        
        if all_completed and claimed_count > 0:
            bonus_xp = 50  # Bonus for completing all quests
            total_xp += bonus_xp
            
            # Award bonus XP
            leveling_cog = self.bot.get_cog("Leveling")
            if leveling_cog:
                await leveling_cog._update_user_level_data(
                    interaction.guild.id, interaction.user.id,
                    {"$inc": {"xp": bonus_xp}}
                )
        
        if claimed_count == 0:
            texts = await func.get_lang(interaction.guild.id, "moodSad")
            msg = random.choice(texts) if isinstance(texts, list) else "No quests to claim!"
            await interaction.followup.send(f"{msg}\n\nNo completed quests to claim. Keep going vro!", ephemeral=True)
        else:
            texts = await func.get_lang(interaction.guild.id, "moodCelebrate")
            msg = random.choice(texts) if isinstance(texts, list) else "🎉 Quest rewards claimed!"
            
            bonus_text = f"\n🎁 **+{bonus_xp} XP** completion bonus!" if bonus_xp > 0 else ""
            
            embed = discord.Embed(
                title="🎁 Quest Rewards Claimed!",
                description=f"{msg}\n\nClaimed **{claimed_count}** quest(s)!\n**+{total_xp - bonus_xp} XP** from quests{bonus_text}\n\n**Total: +{total_xp} XP!**",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
    
    # ========== DAILY REWARD ==========
    
    @app_commands.command(name="daily", description="Claim your daily XP bonus!")
    async def daily(self, interaction: discord.Interaction):
        """Claim daily XP with streak bonuses."""
        await interaction.response.defer()
        
        db = func.MONGO_DB[func.settings.mongodb_name]
        collection = db["daily_rewards"]
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        today = date.today().isoformat()
        
        # Get user's daily data
        data = await collection.find_one({
            "guild_id": guild_id,
            "user_id": user_id
        })
        
        if data and data.get("last_claim") == today:
            # Already claimed today
            texts = await func.get_lang(interaction.guild.id, "moodSad")
            msg = random.choice(texts) if isinstance(texts, list) else "Already claimed!"
            
            # Calculate time until reset
            now = datetime.now(timezone.utc)
            tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + __import__('datetime').timedelta(days=1)
            time_left = tomorrow - now
            hours_left = int(time_left.total_seconds() // 3600)
            mins_left = int((time_left.total_seconds() % 3600) // 60)
            
            await interaction.followup.send(
                f"{msg}\n\nYou've already claimed your daily reward!\n⏰ Come back in **{hours_left}h {mins_left}m**",
                ephemeral=True
            )
            return
        
        # Calculate streak
        yesterday = (date.today() - __import__('datetime').timedelta(days=1)).isoformat()
        
        if data and data.get("last_claim") == yesterday:
            # Continuing streak
            streak = data.get("streak", 0) + 1
        else:
            # Streak broken or first time
            streak = 1
        
        # Calculate XP with streak bonus (like MEE6/Tatsu)
        base_xp = random.randint(50, 100)
        
        # Streak multipliers: Day 1 = 1x, Day 2 = 1.1x, ... Day 7+ = 2x
        if streak >= 7:
            multiplier = 2.0
        else:
            multiplier = 1 + (streak - 1) * 0.15  # 15% increase per day
        
        total_xp = int(base_xp * multiplier)
        
        # Save to database
        await collection.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {
                "$set": {
                    "last_claim": today,
                    "streak": streak
                },
                "$inc": {"total_claims": 1}
            },
            upsert=True
        )
        
        # Award XP
        leveling_cog = self.bot.get_cog("Leveling")
        if leveling_cog:
            await leveling_cog._update_user_level_data(
                interaction.guild.id, interaction.user.id,
                {"$inc": {"xp": total_xp}}
            )
        
        # Get Cheems celebration
        texts = await func.get_lang(interaction.guild.id, "moodCelebrate")
        msg = random.choice(texts) if isinstance(texts, list) else "🎉 Daily reward claimed!"
        
        # Streak fire emojis
        streak_fire = "🔥" * min(streak, 7)
        
        embed = discord.Embed(
            title="📅 Daily Reward Claimed!",
            description=f"{msg}",
            color=discord.Color.gold()
        )
        embed.add_field(name="XP Earned", value=f"**+{total_xp} XP**", inline=True)
        embed.add_field(name="Streak", value=f"{streak_fire} **{streak} day(s)**", inline=True)
        embed.add_field(name="Multiplier", value=f"**{multiplier:.1f}x**", inline=True)
        
        if streak < 7:
            next_mult = 1 + streak * 0.15
            embed.set_footer(text=f"Come back tomorrow for {next_mult:.1f}x bonus! Max: 2.0x at 7 days")
        else:
            embed.set_footer(text="🔥 MAX STREAK! You're on fire vro!")
        
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyQuests(bot))

