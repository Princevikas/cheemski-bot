"""
Games Cog - Fun interactive games with Cheems personality
Includes: Cheemski Nator (Akinator with Cheems flavor)
"""
import discord
from discord.ext import commands
from discord import app_commands
import akinator
import asyncio
from typing import Optional, List
import function as func
from datetime import datetime, timedelta
import random

# Auto-deployment test trigger - Auto-Update Watchdog Test



# Cheems expressions for different situations
CHEEMS_THINKING = [
    "🤔 Hmm...", "🧐 Interesting...", "💭 Let me think...",
    "🐕 Cheems ponders...", "✨ Much think...", "🎯 Getting closer..."
]

CHEEMS_WIN_MESSAGES = [
    "Hehe! I knew it was {name}! 🐕✨",
    "Easy peasy! {name} was obvious vro! 😎",
    "Cheems brain = BIG BRAIN! I got {name}! 🧠",
    "Another win for Cheems! {name}! 🏆",
    "Too easy vro! {name} all the way! 💪"
]

CHEEMS_LOSE_MESSAGES = [
    "I guessed **{name}** but I was wrong... 😔",
    "Noooo! I thought it was **{name}**! You got me vro! 💀",
    "**{name}** wasn't right?! Cheems is confusion! 🤯",
    "Defeated by a mere hooman... **{name}** was wrong! 😢"
]

# Achievements definitions
ACHIEVEMENTS = {
    "first_game": {"name": "🎮 First Steps", "desc": "Play your first Akinator game", "requirement": 1},
    "win_5": {"name": "🌟 Rising Star", "desc": "Win 5 games against Cheems", "requirement": 5},
    "win_10": {"name": "⭐ Mastermind", "desc": "Win 10 games against Cheems", "requirement": 10},
    "win_25": {"name": "🏅 Legend", "desc": "Win 25 games against Cheems", "requirement": 25},
    "streak_3": {"name": "🔥 On Fire", "desc": "Get a 3 game win streak", "requirement": 3},
    "streak_5": {"name": "💎 Unstoppable", "desc": "Get a 5 game win streak", "requirement": 5},
    "games_10": {"name": "🎲 Regular Player", "desc": "Play 10 games total", "requirement": 10},
    "games_50": {"name": "🎯 Dedicated", "desc": "Play 50 games total", "requirement": 50},
    "quick_win": {"name": "⚡ Speed Demon", "desc": "Beat Cheems in under 10 questions", "requirement": 10},
}


def get_progress_bar(progression: float) -> str:
    """Create a visual progress bar for confidence level"""
    filled = int(progression / 10)
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    
    # Color indicator based on confidence
    if progression >= 80:
        emoji = "🔥"
    elif progression >= 50:
        emoji = "🟡"
    else:
        emoji = "🔵"
    
    return f"{emoji} {bar} {progression:.1f}%"


def get_rank_emoji(position: int) -> str:
    """Get emoji for leaderboard position"""
    if position == 1:
        return "🥇"
    elif position == 2:
        return "🥈"
    elif position == 3:
        return "🥉"
    else:
        return f"#{position}"



class AkinatorButton(discord.ui.Button):
    """Button for Akinator answers"""
    def __init__(self, answer: str, emoji: str):
        # Different styles for different answers
        if answer == "yes":
            style = discord.ButtonStyle.success
        elif answer == "no":
            style = discord.ButtonStyle.danger
        else:
            style = discord.ButtonStyle.secondary
            
        super().__init__(
            style=style,
            label=answer.title() if len(answer) < 12 else answer[:10] + "...",
            emoji=emoji,
            custom_id=f"aki_{answer}"
        )
        self.answer_value = answer
    
    async def callback(self, interaction: discord.Interaction):
        # Check if the user is the session owner
        if interaction.user.id != self.view.owner_id:
            await interaction.response.send_message(
                "❌ This isn't your game vro! Start your own with `/cheemskinator`",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        self.view.answer = self.answer_value
        self.view.stop()


class AkinatorView(discord.ui.View):
    """View for Akinator game buttons"""
    def __init__(self, owner_id: int, timeout: float = 60.0, show_give_up: bool = False):
        super().__init__(timeout=timeout)
        self.answer = None
        self.owner_id = owner_id
        
        # Add answer buttons
        self.add_item(AkinatorButton("yes", "✅"))
        self.add_item(AkinatorButton("no", "❌"))
        self.add_item(AkinatorButton("i don't know", "🤷"))
        self.add_item(AkinatorButton("probably", "👍"))
        self.add_item(AkinatorButton("probably not", "👎"))
        
        # Add back button
        back_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Back",
            emoji="⏮️",
            custom_id="aki_back",
            row=1
        )
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
        
        # Add give up button (only after 5 questions)
        if show_give_up:
            give_up_btn = discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Give Up",
                emoji="🏳️",
                custom_id="aki_give_up",
                row=1
            )
            give_up_btn.callback = self.give_up_callback
            self.add_item(give_up_btn)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This isn't your game vro! Start your own with `/cheemskinator`",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        self.answer = "back"
        self.stop()
    
    async def give_up_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This isn't your game vro! Start your own with `/cheemskinator`",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        self.answer = "give_up"
        self.stop()


class Games(commands.Cog):
    """🎮 Fun games to play with Cheems!"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games = {}  # Store active game sessions
        self.cooldowns = {}  # Cooldown tracker
        self.COOLDOWN_SECONDS = 30  # Cooldown between games

    def _check_cooldown(self, user_id: int) -> Optional[int]:
        """Check if user is on cooldown. Returns seconds remaining or None."""
        if user_id in self.cooldowns:
            remaining = (self.cooldowns[user_id] - datetime.now()).total_seconds()
            if remaining > 0:
                return int(remaining)
            del self.cooldowns[user_id]
        return None

    def _set_cooldown(self, user_id: int):
        """Set cooldown for user."""
        self.cooldowns[user_id] = datetime.now() + timedelta(seconds=self.COOLDOWN_SECONDS)

    async def _update_stats(self, guild_id: int, user_id: int, won: bool, questions: int = 0) -> List[str]:
        """Update user's Akinator game stats. Returns list of newly unlocked achievements."""
        new_achievements = []
        try:
            db = func.MONGO_DB[func.settings.mongodb_name]
            collection = db["game_stats"]
            
            # Get current stats
            current = await collection.find_one({
                "guild_id": str(guild_id),
                "user_id": str(user_id)
            }) or {}
            
            current_streak = current.get("current_streak", 0)
            best_streak = current.get("best_streak", 0)
            wins = current.get("akinator_losses", 0)  # User wins = Cheems losses
            total = current.get("akinator_games", 0)
            achievements = current.get("achievements", [])
            
            # Update streak (user streak, not Cheems)
            if not won:  # User won (Cheems lost)
                new_streak = current_streak + 1
                wins += 1
            else:
                new_streak = 0
            
            new_best = max(best_streak, new_streak)
            total += 1
            
            # Check for new achievements
            def check_achievement(key: str, value: int, requirement: int):
                if key not in achievements and value >= requirement:
                    achievements.append(key)
                    new_achievements.append(ACHIEVEMENTS[key]["name"])
            
            # Check all achievements
            check_achievement("first_game", total, 1)
            check_achievement("games_10", total, 10)
            check_achievement("games_50", total, 50)
            check_achievement("win_5", wins, 5)
            check_achievement("win_10", wins, 10)
            check_achievement("win_25", wins, 25)
            check_achievement("streak_3", new_streak, 3)
            check_achievement("streak_5", new_streak, 5)
            if not won and questions < 10:  # Quick win
                check_achievement("quick_win", 1, 1)
            
            # Update database
            stat_field = "akinator_wins" if won else "akinator_losses"
            
            await collection.update_one(
                {"guild_id": str(guild_id), "user_id": str(user_id)},
                {
                    "$inc": {stat_field: 1, "akinator_games": 1},
                    "$set": {
                        "last_played": datetime.now().isoformat(),
                        "current_streak": new_streak,
                        "best_streak": new_best,
                        "achievements": achievements
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            func.logger.error(f"Failed to update game stats: {e}")
        
        return new_achievements


    @commands.hybrid_command(name="cheemskinator", description="Play Akinator with Cheems! 🧞‍♂️")
    @app_commands.describe(child_mode="Enable safe mode for family-friendly content")
    async def akinator_game(self, ctx: commands.Context, child_mode: bool = True):
        """
        Play a game of Akinator with Cheems personality!
        
        Think of a character and Cheems will try to guess who it is.
        """
        # Check cooldown
        cooldown_remaining = self._check_cooldown(ctx.author.id)
        if cooldown_remaining:
            await ctx.send(
                f"⏳ Slow down vro! Wait **{cooldown_remaining}s** before playing again.",
                ephemeral=True
            )
            return
        
        # Check if user already has an active game
        if ctx.author.id in self.active_games:
            await ctx.send("❌ You already have an active game vro! Finish that one first.")
            return
        
        self.active_games[ctx.author.id] = True
        
        # Handle child_mode default
        if child_mode is None:
            child_mode = True
        
        # Initial embed
        embed = discord.Embed(
            title="🧞‍♂️ Cheemski Nator",
            description="**Think of a character...**\n\nCheems will try to read your mind! 🐕\n\n_Starting game..._",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Powered by Akinator • Safe Mode: " + ("✅" if child_mode else "❌"))
        message = await ctx.send(embed=embed)

        try:
            # Initialize Akinator
            aki = akinator.Akinator()
            using_bypass = False
            
            # Smart Retry Logic with Theme Fallback + curl_cffi bypass
            # Attempts: 1-2 = Characters, 3-4 = Animals, 5 = Objects, 6 = curl_cffi bypass
            themes = [None, None, 'a', 'a', 'o', 'bypass']
            theme_names = {None: "Characters", 'a': "Animals", 'o': "Objects", 'bypass': "Bypass Mode"}
            current_theme = None
            
            for attempt, theme_code in enumerate(themes):
                try:
                    if theme_code == 'bypass':
                        # Try curl_cffi bypass as last resort
                        func.logger.info("Trying curl_cffi bypass...")
                        from cogs.akinator_bypass import create_akinator_with_bypass
                        aki = create_akinator_with_bypass(child_mode=child_mode)
                        await asyncio.wait_for(asyncio.to_thread(aki.start_game, child_mode=child_mode), timeout=10.0)
                        using_bypass = True
                        current_theme = "Bypass"
                        func.logger.info("✅ curl_cffi bypass worked!")
                    elif theme_code:
                        await asyncio.wait_for(asyncio.to_thread(aki.start_game, child_mode=child_mode, theme=theme_code), timeout=10.0)
                        current_theme = theme_names[theme_code]
                        func.logger.info(f"Akinator started with backup theme: {current_theme}")
                    else:
                        await asyncio.wait_for(asyncio.to_thread(aki.start_game, child_mode=child_mode), timeout=10.0)
                        current_theme = theme_names[theme_code]
                    break
                    
                except Exception as e:
                    if attempt == len(themes) - 1:
                        func.logger.error(f"Akinator failed all methods including bypass: {e}")
                        error_embed = discord.Embed(
                            title="❌ Error!",
                            description="Sorry vro, my brain is completely fried! Cloudflare is blocking everything. 😔\n\nTry again in a few minutes!",
                            color=discord.Color.red()
                        )
                        await message.edit(embed=error_embed)
                        del self.active_games[ctx.author.id]
                        return
                    
                    next_theme = theme_names[themes[attempt+1]]
                    func.logger.warning(f"Akinator attempt {attempt+1} failed ({theme_names[theme_code]}): {e}")
                    
                    retry_embed = discord.Embed(
                        title="⏳ Connecting...",
                        description=f"Brain is loading... (Attempt {attempt+2}/5)\n_Trying **{next_theme}** mode..._",
                        color=discord.Color.orange()
                    )
                    await message.edit(embed=retry_embed)
                    await asyncio.sleep(2)

            # Tracks if we approved continuing past 25
            continue_after_25 = False
            last_guess_step = -1
            
            # Helper for guess details
            async def get_details():
                try:
                     if (not aki.finished or not getattr(aki, 'name_proposition', None)):
                          await asyncio.wait_for(asyncio.to_thread(aki.win), timeout=30.0)
                except: pass
                
                g_name = getattr(aki, 'name_proposition', None)
                g_desc = getattr(aki, 'description_proposition', None)
                g_img = getattr(aki, 'photo', None)
                
                if not g_name and hasattr(aki, 'first_guess') and aki.first_guess:
                    g_name = aki.first_guess.get('name')
                    g_desc = aki.first_guess.get('description')
                    g_img = aki.first_guess.get('absolute_picture_path')
                
                return g_name, g_desc, g_img

            # Outer loop to handle "Continue" logic
            game_running = True
            while game_running:
                
                # Check if we should make a guess (instead of asking another question)
                should_guess = False
                
                # 1. Force guess at 25 questions (if not already continued)
                if aki.step >= 25 and not continue_after_25:
                    func.logger.info("Reached 25 questions, forcing guess check.")
                    should_guess = True
                
                # 2. Hard limit at 40 questions
                elif aki.step >= 40:
                    func.logger.info("Reached 40 questions hard limit.")
                    should_guess = True
                
                # 3. High confidence check
                elif aki.progression >= 90 and aki.step != last_guess_step:
                    func.logger.info(f"Akinator reached high confidence ({aki.progression}%), triggering guess")
                    should_guess = True
                
                # If we should guess, skip to guess section (break out of question loop)
                if should_guess:
                    pass  # Fall through to guess section below
                
                # Otherwise, ask next question
                else:
                
                    # Create game embed with progress bar
                    progress_bar = get_progress_bar(aki.progression)
                    
                    embed = discord.Embed(
                        title="🧞‍♂️ Cheemski Nator",
                        description=f"**Question {aki.step + 1}**\n\n>>> {aki.question}",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="🎯 Confidence", value=progress_bar, inline=False)
                    
                    # Add theme indicator if not default
                    footer_text = "Cheems is thinking... 🤔"
                    if current_theme and current_theme != "Characters":
                        footer_text += f" • {current_theme} Mode"
                    embed.set_footer(text=footer_text)
                    
                    # Show give up button after 5 questions
                    view = AkinatorView(
                        owner_id=ctx.author.id, 
                        timeout=60.0,
                        show_give_up=(aki.step >= 5)
                    )
                    await message.edit(embed=embed, view=view)
                    
                    # Wait for interaction
                    if await view.wait():
                        timeout_embed = discord.Embed(
                            title="😴 Zzz...",
                            description="You took too long vro! Game cancelled.\n\n_Cheems fell asleep waiting..._",
                            color=discord.Color.red()
                        )
                        timeout_embed.set_thumbnail(url="https://i.imgur.com/7kZ562I.png")
                        await message.edit(embed=timeout_embed, view=None)
                        del self.active_games[ctx.author.id]
                        return
                    
                    # Handle give up
                    if view.answer == "give_up":
                        end_embed = discord.Embed(title="👋 Game Over", description="Thanks for playing!\n\n_You gave up - Cheems wins by default!_", color=discord.Color.dark_grey())
                        await message.edit(embed=end_embed, view=None)
                        game_running = False
                        break
                    
                    # Handle back button
                    if view.answer == "back":
                        if aki.step == 0:
                            continue
                        try:
                            await asyncio.wait_for(asyncio.to_thread(aki.back), timeout=30.0)
                        except Exception:
                            pass
                        continue
                    
                    # Process answer
                    try:
                        func.logger.debug(f"Akinator step {aki.step}, answering: {view.answer}")
                        await asyncio.wait_for(asyncio.to_thread(aki.answer, view.answer), timeout=30.0)
                        func.logger.debug(f"Answer accepted, new step: {aki.step}, progression: {aki.progression}")
                    except Exception as e:
                        error_msg = str(e)
                        func.logger.error(f"Akinator answer error at step {aki.step}: {error_msg}")
                        
                        # Check if Akinator has proposed a win - break to show the guess
                        if "proposed a win" in error_msg.lower() or "invalid answer" in error_msg.lower():
                            func.logger.info("Akinator has proposed a win, breaking to show guess")
                            break
                        
                        # Check if it's a connection/timeout issue - retry once
                        if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                            try:
                                func.logger.info("Retrying answer after connection error...")
                                await asyncio.sleep(1)
                                await asyncio.wait_for(asyncio.to_thread(aki.answer, view.answer), timeout=30.0)
                                continue
                            except Exception as retry_e:
                                func.logger.error(f"Retry also failed: {retry_e}")
                        
                        error_embed = discord.Embed(
                            title="❌ Something Went Wrong!",
                            description=f"Error processing answer vro! Let's try again...\n\n_Error: {error_msg[:100] if error_msg else 'Connection issue'}_",
                            color=discord.Color.red()
                        )
                        await message.edit(embed=error_embed, view=None)
                        del self.active_games[ctx.author.id]
                        return
                
                    # Restart loop to check conditions or ask next question
                    continue
            
                # --- End of Question Loop ---

                # Check if user gave up in loop
                if not game_running:
                    end_embed = discord.Embed(title="👋 Game Over", description="Thanks for playing!", color=discord.Color.dark_grey())
                    await message.edit(embed=end_embed, view=None)
                    break

                # Fetch Guess
                last_guess_step = aki.step
                guess_name, guess_desc, guess_img = await get_details()

                # Logic for "Defeat" condition (Unknown guess at hard stop)
                # Only give up if we hit hard limit AND have no guess
                if not guess_name or guess_name == "Unknown":
                    # If we are at the hard limit, we must admit defeat
                    if aki.step >= 40:
                        lose_embed = discord.Embed(
                            title="🏳️ I Give Up!",
                            description="I really don't know who this is! You win! 🏆\n\n_Cheems is defeated..._",
                            color=discord.Color.red()
                        )
                        lose_embed.set_thumbnail(url="https://i.imgur.com/Cpo0UMj.png")
                        await message.edit(embed=lose_embed, view=None)
                        await self._update_stats(ctx.guild.id, ctx.author.id, won=False)
                        del self.active_games[ctx.author.id]
                        return
                    
                    # If not at hard limit, just ignore "Unknown" guess and keep asking questions
                    else:
                        func.logger.info("Got 'Unknown' guess, skipping and continuing game...")
                        continue 

                # Display Guess Logic
                guess_view = None
                
                if guess_name and guess_name != "Unknown":
                    # Valid guess -> Show it and ask for confirmation
                    guess_embed = discord.Embed(
                        title="🎯 Is this your character?" if aki.step < 40 else "🤔 My Final Guess...",
                        color=discord.Color.gold()
                    )
                    guess_embed.add_field(name="Name", value=f"**{guess_name}**", inline=False)
                    if guess_desc:
                        guess_embed.add_field(name="Description", value=f"_{guess_desc}_", inline=False)
                    if guess_img:
                        guess_embed.set_thumbnail(url=guess_img)
                    
                    guess_embed.set_footer(text=f"Confidence: {aki.progression:.1f}% • Questions: {aki.step}")

                    # Define View only for valid guess
                    class GuessConfirmationView(discord.ui.View):
                        def __init__(self, owner_id):
                            super().__init__(timeout=60)
                            self.value = None
                            self.owner_id = owner_id
                        
                        @discord.ui.button(label="Yes! 🎉", style=discord.ButtonStyle.success)
                        async def yes(self, interaction, button):
                            if interaction.user.id != self.owner_id: return
                            self.value = "yes"
                            self.stop()
                            await interaction.response.defer()
                        
                        @discord.ui.button(label="Nope! 😏", style=discord.ButtonStyle.danger)
                        async def no(self, interaction, button):
                            if interaction.user.id != self.owner_id: return
                            self.value = "no"
                            self.stop()
                            await interaction.response.defer()

                    guess_view = GuessConfirmationView(ctx.author.id)
                    await message.edit(embed=guess_embed, view=guess_view)
                    
                    # Wait for user input
                    await guess_view.wait()
                    
                    if guess_view.value is None:
                        # Timeout
                        timeout_embed = discord.Embed(title="⏰ Timed Out", description="Game ended.", color=discord.Color.red())
                        await message.edit(embed=timeout_embed, view=None)
                        game_running = False
                        break
                else:
                    # Invalid/Unknown guess -> Treat as "No" automatically
                    # We create a dummy object to satisfy the logic below
                    class DummyView:
                        value = "no"
                    guess_view = DummyView()
                
                # Process Result (User Yes/No or Auto-No)
                if guess_view.value == "yes":
                    # WIN
                    win_msg = random.choice(CHEEMS_WIN_MESSAGES).format(name=guess_name)
                    win_embed = discord.Embed(title="🏆 CHEEMS WINS!", description=win_msg, color=discord.Color.green())
                    win_embed.set_image(url="https://media.tenor.com/ozRuXEb_l-UAAAAC/happy-cheems.gif")
                    await message.edit(embed=win_embed, view=None)
                    await self._update_stats(ctx.guild.id, ctx.author.id, won=True, questions=aki.step)
                    game_running = False # End game
                
                elif guess_view.value == "no":
                    # WRONG GUESS (or Unknown guess)
                    
                    # 1. If at Hard Limit (40) -> Loose
                    if aki.step >= 40:
                        lose_embed = discord.Embed(
                            title="🏳️ I Give Up!",
                            description=f"I guessed **{guess_name or 'Unknown'}** but I was wrong! You win! 🏆",
                            color=discord.Color.red()
                        )
                        await message.edit(embed=lose_embed, view=None)
                        await self._update_stats(ctx.guild.id, ctx.author.id, won=False)
                        game_running = False # End game
                    
                    # 2. If at Soft Limit (25) OR High Confidence Failure -> Ask Continue
                    elif (aki.step >= 25 and not continue_after_25) or aki.progression >= 90:
                        continue_embed = discord.Embed(
                            title="🤔 Hmm...",
                            description="I guessed wrong! Do you want me to keep trying?" + ("\n_(I'll ask 15 more questions)_" if aki.step < 35 else ""),
                            color=discord.Color.blue()
                        )
                        
                        class ContinueView(discord.ui.View):
                            def __init__(self, owner_id):
                                super().__init__(timeout=30)
                                self.value = None
                                self.owner_id = owner_id
                            
                            @discord.ui.button(label="Keep Going! 🏃", style=discord.ButtonStyle.primary)
                            async def yes(self, interaction, button):
                                if interaction.user.id != self.owner_id: return
                                self.value = True
                                self.stop()
                                await interaction.response.defer()

                            @discord.ui.button(label="Give Up 🛑", style=discord.ButtonStyle.secondary)
                            async def no(self, interaction, button):
                                if interaction.user.id != self.owner_id: return
                                self.value = False
                                self.stop()
                                await interaction.response.defer()
                        
                        cont_view = ContinueView(ctx.author.id)
                        await message.edit(embed=continue_embed, view=cont_view)
                        await cont_view.wait()
                        
                        if cont_view.value:
                            # Continue Game
                            continue_after_25 = True # Enable extension to 40
                            await message.edit(content="_Thinking of next question..._", embed=None, view=None)
                            # Loop continues back to 'while game_running'
                        elif cont_view.value is False or cont_view.value is None:
                            # User clicked Give Up OR Timeout
                            end_embed = discord.Embed(title="👋 Game Over", description="Thanks for playing!", color=discord.Color.dark_grey())
                            await message.edit(embed=end_embed, view=None)
                            game_running = False
                    
                    # 3. Early confidence failure -> Ask Continue (Same logic as #2 basically, or just continue)
                    else:
                        await message.edit(content="_Cheems thinks harder..._", embed=None, view=None)
                        # Loop continues
                
                else:
                    # Timeout on guess confirmation
                    timeout_embed = discord.Embed(title="⏰ Timed Out", description="Game ended.", color=discord.Color.red())
                    await message.edit(embed=timeout_embed, view=None)
                    game_running = False
            
            # Cleanup handled in finally block
            
        except Exception as e:
            func.logger.error(f"Critical error in Akinator game: {e}")
            error_embed = discord.Embed(
                title="❌ Error", 
                description="An unexpected error occurred while playing.", 
                color=discord.Color.red()
            )
            try:
                await message.edit(embed=error_embed, view=None)
            except: pass
        
        finally:
            if ctx.author.id in self.active_games:
                del self.active_games[ctx.author.id]

    @commands.command(name="akistats")
    async def akinator_stats(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """View Akinator game statistics for yourself or another member. (Prefix only)"""
        target = member or ctx.author
        
        try:
            db = func.MONGO_DB[func.settings.mongodb_name]
            collection = db["game_stats"]
            
            stats = await collection.find_one({
                "guild_id": str(ctx.guild.id),
                "user_id": str(target.id)
            })
            
            if not stats:
                await ctx.send(f"📊 {target.display_name} hasn't played any Akinator games yet!")
                return
            
            cheems_wins = stats.get("akinator_wins", 0)
            user_wins = stats.get("akinator_losses", 0)
            total = stats.get("akinator_games", cheems_wins + user_wins)
            win_rate = (user_wins / total * 100) if total > 0 else 0
            current_streak = stats.get("current_streak", 0)
            best_streak = stats.get("best_streak", 0)
            achievements = stats.get("achievements", [])
            
            embed = discord.Embed(
                title=f"📊 Akinator Stats - {target.display_name}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            
            # Stats
            embed.add_field(name="🏆 Cheems Wins", value=f"`{cheems_wins}`", inline=True)
            embed.add_field(name="👤 Your Wins", value=f"`{user_wins}`", inline=True)
            embed.add_field(name="🎮 Total Games", value=f"`{total}`", inline=True)
            embed.add_field(name="📈 Your Win Rate", value=f"`{win_rate:.1f}%`", inline=True)
            embed.add_field(name="🔥 Current Streak", value=f"`{current_streak}`", inline=True)
            embed.add_field(name="⭐ Best Streak", value=f"`{best_streak}`", inline=True)
            
            # Achievements count
            embed.add_field(
                name="🎖️ Achievements",
                value=f"`{len(achievements)}/{len(ACHIEVEMENTS)}`",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            func.logger.error(f"Error fetching akinator stats: {e}")
            await ctx.send("❌ Couldn't fetch stats vro!")

    @commands.command(name="akileaderboard", aliases=["akilb"])
    async def akinator_leaderboard(self, ctx: commands.Context):
        """View the server's Akinator leaderboard. (Prefix only)"""
        try:
            db = func.MONGO_DB[func.settings.mongodb_name]
            collection = db["game_stats"]
            
            # Get all users for this guild, sorted by user wins (Cheems losses)
            cursor = collection.find(
                {"guild_id": str(ctx.guild.id)}
            ).sort("akinator_losses", -1).limit(10)
            
            entries = await cursor.to_list(length=10)
            
            if not entries:
                await ctx.send("📊 No one has played Akinator in this server yet!")
                return
            
            embed = discord.Embed(
                title="🏆 Akinator Leaderboard",
                description="Top players who stumped Cheems the most!",
                color=discord.Color.gold()
            )
            
            leaderboard_text = ""
            for i, entry in enumerate(entries, 1):
                user_id = int(entry["user_id"])
                member = ctx.guild.get_member(user_id)
                name = member.display_name if member else f"User {user_id}"
                
                wins = entry.get("akinator_losses", 0)  # User wins = Cheems losses
                total = entry.get("akinator_games", 0)
                streak = entry.get("best_streak", 0)
                
                rank = get_rank_emoji(i)
                leaderboard_text += f"{rank} **{name}** - {wins} wins ({total} games) 🔥{streak}\n"
            
            embed.add_field(name="Rankings", value=leaderboard_text or "No data", inline=False)
            embed.set_footer(text="Play /cheemskinator to climb the leaderboard!")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            func.logger.error(f"Error fetching leaderboard: {e}")
            await ctx.send("❌ Couldn't fetch leaderboard vro!")

    @commands.command(name="akiachievements", aliases=["akiach"])
    async def akinator_achievements(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """View Akinator achievements for yourself or another member. (Prefix only)"""
        target = member or ctx.author
        
        try:
            db = func.MONGO_DB[func.settings.mongodb_name]
            collection = db["game_stats"]
            
            stats = await collection.find_one({
                "guild_id": str(ctx.guild.id),
                "user_id": str(target.id)
            })
            
            unlocked = stats.get("achievements", []) if stats else []
            
            embed = discord.Embed(
                title=f"🎖️ Achievements - {target.display_name}",
                description=f"Unlocked: **{len(unlocked)}/{len(ACHIEVEMENTS)}**",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            
            # Unlocked achievements
            unlocked_text = ""
            locked_text = ""
            
            for key, ach in ACHIEVEMENTS.items():
                if key in unlocked:
                    unlocked_text += f"✅ {ach['name']} - _{ach['desc']}_\n"
                else:
                    locked_text += f"🔒 {ach['name']} - _{ach['desc']}_\n"
            
            if unlocked_text:
                embed.add_field(name="✨ Unlocked", value=unlocked_text, inline=False)
            
            if locked_text:
                embed.add_field(name="🔒 Locked", value=locked_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            func.logger.error(f"Error fetching achievements: {e}")
            await ctx.send("❌ Couldn't fetch achievements vro!")

    # ==================== TRIVIA GAME ====================
    
    TRIVIA_CATEGORIES = {
        "any": 0,
        "general": 9,
        "books": 10,
        "film": 11,
        "music": 12,
        "videogames": 15,
        "science": 17,
        "computers": 18,
        "math": 19,
        "sports": 21,
        "geography": 22,
        "history": 23,
        "anime": 31,
        "cartoons": 32,
    }
    
    TRIVIA_CORRECT_RESPONSES = [
        "✅ **CORRECT!** Big brain energy vro! 🧠",
        "✅ **YOU GOT IT!** Cheems is impressed! 🐕",
        "✅ **NICE ONE!** You're smarter than Cheems thought! 💪",
        "✅ **CORRECT!** Much smart, very wow! ✨",
    ]
    
    TRIVIA_WRONG_RESPONSES = [
        "❌ **WRONG!** The answer was: **{answer}**\nBetter luck next time vro! 😔",
        "❌ **NOPE!** It was **{answer}**\nCheems is disappointed... 🐕",
        "❌ **INCORRECT!** The right answer: **{answer}**\nStudy more vro! 📚",
    ]

    @commands.hybrid_command(name="trivia", description="Test your knowledge with trivia! 🧠")
    @app_commands.describe(
        category="Choose a trivia category",
        difficulty="Choose difficulty: easy, medium, or hard"
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="🎲 Any", value="any"),
        app_commands.Choice(name="📚 General Knowledge", value="general"),
        app_commands.Choice(name="🎬 Film", value="film"),
        app_commands.Choice(name="🎵 Music", value="music"),
        app_commands.Choice(name="🎮 Video Games", value="videogames"),
        app_commands.Choice(name="💻 Computers", value="computers"),
        app_commands.Choice(name="🏀 Sports", value="sports"),
        app_commands.Choice(name="🌍 Geography", value="geography"),
        app_commands.Choice(name="📜 History", value="history"),
        app_commands.Choice(name="🎌 Anime & Manga", value="anime"),
    ])
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="😊 Easy", value="easy"),
        app_commands.Choice(name="🤔 Medium", value="medium"),
        app_commands.Choice(name="🔥 Hard", value="hard"),
    ])
    async def trivia_game(self, ctx: commands.Context, category: str = "any", difficulty: str = "medium"):
        """
        Play a trivia game! Answer questions to test your knowledge.
        """
        import aiohttp
        import html
        
        # Build API URL
        cat_id = self.TRIVIA_CATEGORIES.get(category.lower(), 0)
        url = f"https://opentdb.com/api.php?amount=1&type=multiple&difficulty={difficulty}"
        if cat_id > 0:
            url += f"&category={cat_id}"
        
        # Fetch question
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Couldn't fetch trivia question vro!")
                        return
                    data = await resp.json()
        except Exception as e:
            func.logger.error(f"Trivia API error: {e}")
            await ctx.send("❌ Trivia API is down vro!")
            return
        
        if data.get("response_code") != 0 or not data.get("results"):
            await ctx.send("❌ No trivia questions available for this category!")
            return
        
        question_data = data["results"][0]
        question = html.unescape(question_data["question"])
        correct_answer = html.unescape(question_data["correct_answer"])
        incorrect_answers = [html.unescape(a) for a in question_data["incorrect_answers"]]
        category_name = html.unescape(question_data["category"])
        
        # Shuffle answers
        all_answers = incorrect_answers + [correct_answer]
        random.shuffle(all_answers)
        correct_index = all_answers.index(correct_answer)
        
        # Create embed
        diff_emoji = {"easy": "😊", "medium": "🤔", "hard": "🔥"}.get(difficulty, "🤔")
        # Difficulty-based timeout: Hard is more competitive
        diff_timeout = {"easy": 30, "medium": 20, "hard": 15}.get(difficulty, 20)
        
        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"**{question}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Category", value=category_name, inline=True)
        embed.add_field(name="Difficulty", value=f"{diff_emoji} {difficulty.title()}", inline=True)
        embed.set_footer(text=f"You have {diff_timeout} seconds to answer!")
        
        # Create answer view
        owner_id = ctx.author.id
        
        class TriviaView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=float(diff_timeout))
                self.selected = None
                self.owner_id = owner_id
                
                # Add buttons for each answer
                labels = ["A", "B", "C", "D"]
                for i, answer in enumerate(all_answers):
                    btn = discord.ui.Button(
                        label=f"{labels[i]}: {answer[:40]}{'...' if len(answer) > 40 else ''}",
                        style=discord.ButtonStyle.secondary,
                        custom_id=f"trivia_{i}",
                        row=i // 2
                    )
                    btn.callback = self.make_callback(i)
                    self.add_item(btn)
            
            def make_callback(self, index):
                async def callback(interaction: discord.Interaction):
                    if interaction.user.id != self.owner_id:
                        await interaction.response.send_message("❌ Not your game!", ephemeral=True)
                        return
                    self.selected = index
                    self.stop()
                    await interaction.response.defer()
                return callback
        
        view = TriviaView()
        message = await ctx.send(embed=embed, view=view)
        
        # Wait for answer
        if await view.wait():
            # Timeout
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was: **{correct_answer}**\n\nToo slow vro! 🐢",
                color=discord.Color.orange()
            )
            await message.edit(embed=timeout_embed, view=None)
            return
        
        # Check answer
        if view.selected == correct_index:
            # Correct!
            response = random.choice(self.TRIVIA_CORRECT_RESPONSES)
            result_embed = discord.Embed(
                title="🎉 Correct!",
                description=response,
                color=discord.Color.green()
            )
            
            # Track quest
            quests_cog = self.bot.get_cog("DailyQuests")
            if quests_cog:
                await quests_cog.track_quest(ctx.guild.id, ctx.author.id, "trivia_master")
        else:
            # Wrong
            response = random.choice(self.TRIVIA_WRONG_RESPONSES).format(answer=correct_answer)
            result_embed = discord.Embed(
                title="💀 Wrong!",
                description=response,
                color=discord.Color.red()
            )
        
        await message.edit(embed=result_embed, view=None)

    # ==================== WOULD YOU RATHER ====================
    
    WYR_QUESTIONS = [
        ("Have the ability to fly", "Be invisible"),
        ("Be able to read minds", "Be able to teleport"),
        ("Live in the past", "Live in the future"),
        ("Have unlimited money", "Have unlimited knowledge"),
        ("Be famous", "Be rich but unknown"),
        ("Never use social media again", "Never watch TV/movies again"),
        ("Always be cold", "Always be hot"),
        ("Speak every language", "Talk to animals"),
        ("Have no internet for a week", "No phone for a week"),
        ("Be a superhero", "Be a supervillain"),
        ("Live in space", "Live underwater"),
        ("Have super strength", "Have super speed"),
        ("Control fire", "Control water"),
        ("Be immortal", "Have 3 extra lives"),
        ("Know how you die", "Know when you die"),
    ]

    @commands.hybrid_command(name="wyr", description="Would You Rather - Make a tough choice! 🤔")
    async def would_you_rather(self, ctx: commands.Context):
        """Play Would You Rather with your friends!"""
        
        option_a, option_b = random.choice(self.WYR_QUESTIONS)
        
        embed = discord.Embed(
            title="🤔 Would You Rather...",
            color=discord.Color.purple()
        )
        embed.add_field(name="🅰️ Option A", value=option_a, inline=False)
        embed.add_field(name="🅱️ Option B", value=option_b, inline=False)
        embed.set_footer(text="Vote below! Results in 30 seconds.")
        
        # Track votes
        votes = {"a": set(), "b": set()}
        
        class WYRView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30.0)
            
            @discord.ui.button(label="Option A", style=discord.ButtonStyle.primary, emoji="🅰️")
            async def vote_a(self, interaction: discord.Interaction, button: discord.ui.Button):
                user_id = interaction.user.id
                votes["b"].discard(user_id)
                votes["a"].add(user_id)
                await interaction.response.send_message(f"You voted for **Option A**!", ephemeral=True)
            
            @discord.ui.button(label="Option B", style=discord.ButtonStyle.danger, emoji="🅱️")
            async def vote_b(self, interaction: discord.Interaction, button: discord.ui.Button):
                user_id = interaction.user.id
                votes["a"].discard(user_id)
                votes["b"].add(user_id)
                await interaction.response.send_message(f"You voted for **Option B**!", ephemeral=True)
        
        view = WYRView()
        message = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        # Show results
        total = len(votes["a"]) + len(votes["b"])
        if total == 0:
            pct_a, pct_b = 50, 50
        else:
            pct_a = int(len(votes["a"]) / total * 100)
            pct_b = 100 - pct_a
        
        # Create visual bars
        bar_a = "█" * (pct_a // 10) + "░" * (10 - pct_a // 10)
        bar_b = "█" * (pct_b // 10) + "░" * (10 - pct_b // 10)
        
        result_embed = discord.Embed(
            title="📊 Results!",
            color=discord.Color.gold()
        )
        result_embed.add_field(
            name=f"🅰️ {option_a}",
            value=f"{bar_a} **{pct_a}%** ({len(votes['a'])} votes)",
            inline=False
        )
        result_embed.add_field(
            name=f"🅱️ {option_b}",
            value=f"{bar_b} **{pct_b}%** ({len(votes['b'])} votes)",
            inline=False
        )
        result_embed.set_footer(text=f"Total: {total} votes")
        
        await message.edit(embed=result_embed, view=None)

    # ==================== NUMBER GUESSING ====================

    @commands.hybrid_command(name="guess", description="Guess the number! 🔢")
    @app_commands.describe(max_number="Maximum number (default: 100)")
    async def guess_number(self, ctx: commands.Context, max_number: int = 100):
        """
        Guess the number Cheems is thinking of!
        """
        if max_number < 10:
            max_number = 10
        if max_number > 1000:
            max_number = 1000
        
        secret = random.randint(1, max_number)
        attempts = 0
        max_attempts = int(max_number ** 0.5) + 3  # Reasonable attempts based on range
        
        embed = discord.Embed(
            title="🔢 Guess The Number!",
            description=f"Cheems is thinking of a number between **1** and **{max_number}**!\n\n"
                       f"You have **{max_attempts}** attempts. Type your guess!",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Started by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        while attempts < max_attempts:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30.0)
                guess = int(msg.content)
                attempts += 1
                
                if guess == secret:
                    # Winner!
                    win_embed = discord.Embed(
                        title="🎉 You Got It!",
                        description=f"The number was **{secret}**!\n\n"
                                   f"You guessed it in **{attempts}** attempts! 🏆",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=win_embed)
                    
                    # Track quest
                    quests_cog = self.bot.get_cog("DailyQuests")
                    if quests_cog:
                        await quests_cog.track_quest(ctx.guild.id, ctx.author.id, "number_guesser")
                    return
                    
                elif guess < secret:
                    hint = f"📈 **{guess}** is too LOW! ({max_attempts - attempts} attempts left)"
                else:
                    hint = f"📉 **{guess}** is too HIGH! ({max_attempts - attempts} attempts left)"
                
                await ctx.send(hint)
                
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The number was **{secret}**.")
                return
        
        # Out of attempts
        lose_embed = discord.Embed(
            title="💀 Game Over!",
            description=f"You ran out of attempts!\n\nThe number was **{secret}**.",
            color=discord.Color.red()
        )
        await ctx.send(embed=lose_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))



