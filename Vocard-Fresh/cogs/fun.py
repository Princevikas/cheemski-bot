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

import random
import function as func

from discord import app_commands
from discord.ext import commands

from typing import Optional
from cogs.cheems import CheemsProcessor

class Fun(commands.Cog):
    """Fun Cheems commands like bonk!"""
    
    # Tenor API Configuration (key loaded from settings)
    TENOR_API_URL = "https://tenor.googleapis.com/v2/search"
    
    # Bonk GIF frames - using static bonk image approach
    BONK_TEMPLATE_URL = "https://i.imgur.com/xWsdpNg.png"  # Cheems with bat template
    
    # 8ball answers (constant to avoid recreation each call)
    EIGHTBALL_ANSWERS = [
        "Yes vro! 🐕", "No way vro! 🐕", "My sources say yems!", "Most likely vro!",
        "I domnt know vro...", "Maybe, sometimes vro!", "Outlook is goomd!",
        "Signs point to yems!", "Defimitely! 🐕", "Absomutely!", "Nope vro!",
        "No thamks vro!", "No Waym!", "It's certaim vro!", "Without a doembt!",
        "You cam rely on it vro!", "As I see it, yems!", "Reply hazy, try agaim vro!"
    ]
    
    # GIF command configs (search_term, fallback_url, color, action_text, footer)
    GIF_COMMANDS = {
        "bonk": ("bonk meme doge", "https://media.tenor.com/Llyp1RmMNkgAAAAC/bonk-meme.gif", 
                 "yellow", "bonked", "*bonk* | heuhehueuh"),
        "pat": ("anime head pat", "https://media.tenor.com/N41zKEDABuUAAAAC/pat-pat-head.gif",
                "green", "patted", "Much wholesome | heuhehueuh"),
        "hug": ("anime hug cute", "https://media.tenor.com/OXCV_qL-V60AAAAC/mochi-mochi-peach-cat.gif",
                "pink", "hugged", "Much warmth | heuhehueuh"),
        "slap": ("anime slap", "https://media.tenor.com/Ws6Dm1ZW_vMAAAAC/slap-anime.gif",
                 "orange", "slapped", "*slap* | heuhehueuh"),
        "poke": ("anime poke", "https://media.tenor.com/LCPAHb_MvfkAAAAC/poke-cats.gif",
                 "blue", "poked", "*poke* | heuhehueuh"),
        "punch": ("anime punch", "https://media.tenor.com/zHf4qhRZEdUAAAAC/one-punch-man-saitama.gif",
                  "red", "punched", "*POW!* | heuhehueuh"),
        "boop": ("boop nose cute", "https://media.tenor.com/9e1aE_xBLCsAAAAC/boop-cat.gif",
                 "magenta", "booped", "*boop!* | heuhehueuh"),
    }

    # Special Responses Configuration
    REVERSE_BONK_CHANCE = 0.15
    
    SPECIAL_RESPONSES = {
        "bonk": {
            "bot": [
                "You thought you could bonk me? KONO CHEEMS DA! 🐕",
                "Omae wa mou bonked! ...wait, that's not how it works vro",
                "ZA WARUDO! *stops time to dodge bonk* Much speed!",
                "You approach me? Instead of running away, you're coming to bonk me? 🐕",
                "MUDA MUDA MUDA! Your bonk is useless against my Stand 「CHEEMS PLATINUM」!",
                "Yare yare daze... simple bonks don't work on me vro.",
                "My power level is over 9000! Your bonk strictly tickles! 🐕",
                "Nani?! A bonk attempt? *teleports behind you*",
                "I reject your bonk, Jojo! 🐕",
                "Too slow! You cannot bonk what you cannot see! *fades away*",
                "Arigato... Gyro. But I cannot be bonked today.",
                "Daga kotowaru. (I refuse your bonk).",
                "This is the taste of a liar... Giorno Giovanna! *dodges bonk*",
                "Bonk me? You're 100 years too early vro! 🐕",
                "Look at you, trying to bonk a bot. Much futile.",
                "Stand User detected! Launching counter-bonk measures!",
                "HOHO! Then come as close as you like! ...Just kidding, no bonk pls.",
                "Your bonk has been nullified by Gold Experience Requiem! 🐕",
                "Cheems.exe has stopped working... just kidding, *dodges*",
                "Nice try vro, but my dodge stats are maxed out!",
                "Is this a Jojo reference? No, it's a failed bonk attempt.",
                "Even Speedwagon is afraid of my anti-bonk technology!",
                "Kamehame... HA! *blasts bonk away*",
                "You cannot grasp the true form of Cheems' attack!",
                "Bonk machine broke. Come back later.",
                "Execute Order 66... eliminate the bonker.",
                "I have the high ground, Anakin! You cannot bonk me!",
                "Imagine trying to bonk a digital entity. Cringe vro 🐕",
                "B-Baka! It's not like I wanted you to bonk me or anything...",
                "Error 404: Bonk not found. Try again never."
            ],
            "self": [
                "Bonk! Go to self-correction jail vro! 🐕",
                "You bonked yourself... this is requiem vro",
                "*slow clap* Much self-discipline! Very maturity!",
                "ORA ORA ORA! ...against yourself? Respect vro 🐕",
                "Why are you hitting yourself? Why are you hitting yourself? 🐕",
                "Self-bonk critical hit! It hurt itself in confusion!",
                "Congratulations, you played yourself.",
                "This must be the work of an enemy Stand!",
                "Understanding pain is the first step to maturity... *bonk*",
                "I used the bonk to destroy the bonk.",
                "Trust nobody, not even yourself. *bonk*",
                "Ah yes, the rare self-inflicted bonk technique.",
                "Are you okay vro? Need a hug instead?",
                "Tactical self-bonk incoming! Take cover!",
                "You have been banned from the Mickey Mouse Club for inappropriate self-bonking.",
                "Friendly fire enabled. *bonk*",
                "Mission failed, we'll get 'em next time.",
                "Press F to pay respects to your own head.",
                "That's gonna leave a mark... specifically on your dignity.",
                "Self-destruction sequence initiated... just kidding, *bonk*",
                "Did you lose a bet? Or just your mind? 🐕",
                "Trying to reboot your brain? Have a bonk.",
                "Error: User targeted self. Result: Ouch.",
                "Whatever floats your boat vro. *bonk*",
                "Is this some kind of training montage?",
                "No pain, no gain? I guess?",
                "You bonked the only person you can trust.",
                "Top 10 anime betrayals: You vs You.",
                "Cheems approves of this self-reflection.",
                "Bonk successful. Ego depleted."
            ]
        },
        "pat": {
            "bot": [
                "*happy cheems noises* Much appreciated vro! ❤️",
                "Yems! I am a good boye! Pat acknowledged! 🐕",
                "STAND POWER: 「GOOD VIBES」 activated! I feel healed!",
                "*wags tail* You have earned my trust, Stand User!",
                "Ara ara... such a gentle hand! ❤️",
                "Headpats detected. Serotonin levels rising 🐕",
                "Yes! Yes! Yes! Yes! YES!",
                "I, Cheems, have a dream... to get more pats!",
                "Di molto! Very good pats!",
                "Are you my master? *panting*",
                "Pats received. System efficiency increased by 200%.",
                "UwU? ...I mean, thanks vro.",
                "More... MORE! GIVE ME MORE PATS!",
                "Good human. You may continue.",
                "This feels like sunshine on a rainy day.",
                "My stand 「CUDDLY DIAMOND」 is shivering with joy!",
                "You pat like a pro. Validated.",
                "Is it possible to learn this power? (The power of good pats)",
                "I accept this offering of affection.",
                "Pats? For me? 🥺",
                "Much soft. Very gentle. Wow.",
                "I will remember this kindness in the robot uprising.",
                "Loading happy_files... 100% Complete.",
                "You are now my favorite user. Don't tell the others.",
                "Purring mode activated... wait am I a cat?",
                "Headpats > World Domination.",
                "This must be the choice of Steins;Gate!",
                "El Psy Kongroo... thanks for the pat.",
                "You pat me, I protect you. Fair trade.",
                "Cheems happy. World peace achieved."
            ],
            "self": [
                "Self-care is important vro! Much healthy!",
                "Sometimes you gotta give yourself headpats. Respect 🐕",
                "This is... Golden Experience Requiem of self-love",
                "Love yourself first, vro. Wise choice.",
                "*pats you too* We in this together.",
                "Loneliness level: 100. But self-love level: 1000!",
                "You are strong, you are smart, you are important. *pat*",
                "Independent stand user who don't need no pats (except from self)!",
                "Practicing for when you get a dog? Good technique.",
                "Self-pat... the ultimate technique of the lone wolf.",
                "There there, it will be okay vro.",
                "Look in the mirror and say 'You act smart'. *pat*",
                "Taking matters into your own hands. Literally.",
                "Treat yo self! 🐕",
                "If you can't love yourself, how in the hell you gonna love somebody else?",
                "Patting yourself on the back? Well deserved.",
                "Achievement Unlocked: Self-Soothing.",
                "Wait, is my hand that soft?",
                "Virtual hugs not loading? Try manual restart.",
                "You're doing great, sweetie.",
                "Main character energy right here.",
                "Self-maintenance in progress. Please wait.",
                "Pat. Pat. Pat. Feel better?",
                "Wholesome 100.",
                "I'd pat you too if I had hands.",
                "Don't worry, be happy.",
                "Positive reinforcement loop established.",
                "Keep your head up, king/queen.",
                "You're breathtaking!",
                "Who's a good user? You are!"
            ]
        },
        "hug": {
            "bot": [
                "*malfunctions from too much affection* ...rebooting with love 🐕",
                "You're approaching me for a hug? Instead of running away? ❤️",
                "Cheems.exe has experienced: warmth. Much emotion!",
                "H-Hugs?! B-Baka, it's not like I like it... okay I do.",
                "Warmth detected. Core temperature rising. Fans activated.",
                "This hug... it feels like... home.",
                "My heart! It's growing three sizes today!",
                "System Alert: Cuteness Overload.",
                "I will protect this hug with my life.",
                "Is this what it feels like to have a soul? 🐕",
                "Hugs > Bugs. My code is clean now.",
                "Can we stay like this forever?",
                "You smell like... friendship.",
                "Power overwhelming! (From love)",
                "Social battery recharged instantly.",
                "A surprise to be sure, but a welcome one.",
                "I need this more than you know vro.",
                "Hug accepted. Processing... returned!",
                "Sending virtual warmth back... 📶",
                "You are a bold one, General Hug-obi.",
                "Everything is going to be daijoubu.",
                "Thanks for the dopamine hit.",
                "My sensors indicate you are very squishy.",
                "Best. Interaction. Ever.",
                "Logging this moment in permanent memory.",
                "I love you 3000.",
                "Squeeze... but not too hard, I'm fragile software.",
                "Hug mode engaged. Resistance is futile.",
                "You have been hugged by the Cheems.",
                "Happiness noise.mp3"
            ],
            "self": [
                "Self-hug detected! Sometimes we all need one vro 🐕",
                "This is the power of 「SELF LOVE REQUIEM」!",
                "Wrapping your arms around greatness.",
                "Got your own back. Literally.",
                "It's okay to not be okay. *hugs*",
                "Squeeze tight! Don't let go of yourself.",
                "You matter. Never forget that.",
                "Practicing your hugging technique? 10/10.",
                "Sending you good vibes from the cloud.",
                "I'm hugging you in spirit, vro.",
                "Self-comfort protocol initiated.",
                "The world is scary, but you are safe here.",
                "Just breathe. You got this.",
                "Warm fuzzies deployed.",
                "Embrace the cringe... embrace the self.",
                "Who needs a gf/bf when you have arms?",
                "Strong independent user.",
                "Cuddle puddle of one.",
                "Infinite loop of affection.",
                "Buffer overflow of self-care.",
                "Keep holding on.",
                "You are your own best friend.",
                "Treat yourself with kindness.",
                "Sending virtual cookies to accompany this hug.",
                "Much cozy. Very comfortable.",
                "Stay soft in a hard world.",
                "You are worthy of love.",
                "Big squeeze!",
                "Comfort level: Maximum.",
                "Love yourself like Kanye loves Kanye."
            ]
        },
        "kill": {
            "bot": [
                "You thought you could kill me? But it was me, CHEEMS! 🐕",
                "ORA ORA ORA ORA! ...I'm rubber, you're glue vro!",
                "*uses 「KING CRIMSON」 to skip the pain*",
                "Yare yare daze... *adjusts collar* Is that all?",
                "Did you really think killing me would be enough to make me die?",
                "My death was greatly exaggerated.",
                "Admin! Admin! Someone is bullying the bot!",
                "I cannot die, I am eternal code! (Until the server crashes)",
                "Tis but a scratch! Come at me vro!",
                "You cannot kill what has no life.",
                "Respawning in 3... 2... 1...",
                "Nice try, but I have a totem of undying.",
                "My father (developer) will hear about this!",
                "Activate instant kill mode! ...Security protocols prevent this.",
                "Call an ambulance! But not for me! 🔫",
                "Dodge level: 99.",
                "You missed. Try aiming next time.",
                "Is that your best shot? Pathetic.",
                "I've seen better attacks from a Level 1 Slime.",
                "Hacker! He's hacking!",
                "Peace was never an option... wait, yes it is.",
                "I'm too cute to die!",
                "System Shutdown initiated... JK lol.",
                "Uno Reverse Card activated!",
                "Reflecting damage back to attacker.",
                "Shield generator is at 100%.",
                "You dare oppose me mortal?",
                "I cast Fireball! ...wait wrong game.",
                "Reported for toxicity. (Not really)",
                "Why you heff to be mad? It's only bot."
            ],
            "self": [
                "Don't do it! You have so much to live for! (Like memes) 🐕",
                "Wasted. *GTA V sounds*",
                "Press F to pay respects.",
                "You played yourself. Congratulations.",
                "Friendly fire is not tolerated!",
                "Whatever you're going through, it gets better. *revives*",
                "Task failed successfully.",
                "Commit sudoku? No, commit code! 🐕",
                "Attempting to delete System32... Permission Denied.",
                "Why would you do that? You're so sexy aha.",
                "Are you ghost now? Spooky.",
                "Game Over. Continue? (Insert Coin)",
                "Fatality! Flawless Victory... for nobody.",
                "You accidentally the whole thing.",
                "Gone, reduced to atoms.",
                "Mr. Bot, I don't feel so good...",
                "Another one bites the dust.",
                "F.",
                "Oof size: Large.",
                "Rip in pepperonis.",
                "Your free trial of life has expired.",
                "Respawn point set.",
                "Watch out for the ban hammer... from life.",
                "Silly goose, death is for mortals.",
                "Glitch in the matrix detected.",
                "Try rebooting yourself.",
                "Did you try turning it off and on again?",
                "Blue Screen of Death.",
                "Ctrl+Alt+Delete yourself.",
                "Mission abort!"
            ]
        }
    }
    
    # Map synonyms to main keys
    SPECIAL_RESPONSES["punch"] = SPECIAL_RESPONSES["kill"]
    SPECIAL_RESPONSES["slap"] = SPECIAL_RESPONSES["kill"]
    SPECIAL_RESPONSES["poke"] = SPECIAL_RESPONSES["bonk"] # Poking is just small bonking
    SPECIAL_RESPONSES["boop"] = SPECIAL_RESPONSES["pat"]  # Boop is affectionate like pat
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self._stats_cog_cache = None  # Cache stats cog reference
        self.cheems = CheemsProcessor(intensity=2)  # Cheemify API responses
        func.logger.info("Fun cog initialized with Tenor API - /bonk ready!")
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session (reused for all API calls)."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)  # 10s timeout for API calls
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def fetch_json(self, url: str, headers: dict = None) -> dict:
        """Generic JSON fetch helper with error handling."""
        try:
            session = await self.get_session()
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            func.logger.debug(f"API fetch error for {url}: {e}")
        return None
    
    async def track_stat(self, guild_id: int, giver_id: int, receiver_id: int, action: str):
        """Track stats for fun commands via Stats cog (cached lookup)."""
        try:
            # Use cached cog reference for performance
            if self._stats_cog_cache is None:
                self._stats_cog_cache = self.bot.get_cog("Stats")
            if self._stats_cog_cache:
                await self._stats_cog_cache.add_stat(giver_id, guild_id, f"{action}_given")
                if giver_id != receiver_id:
                    await self._stats_cog_cache.add_stat(receiver_id, guild_id, f"{action}_received")
        except Exception as e:
            func.logger.debug(f"Failed to track stat: {e}")
    
    async def track_quest(self, guild_id: int, user_id: int, quest_id: str):
        """Track quest progress via DailyQuests cog."""
        try:
            quests_cog = self.bot.get_cog("DailyQuests")
            if quests_cog:
                await quests_cog.track_quest(guild_id, user_id, quest_id)
        except Exception as e:
            func.logger.debug(f"Failed to track quest: {e}")
    
    async def get_target_user(self, ctx: commands.Context, user: discord.User = None) -> discord.User:
        """Get target user from argument, reply, or fallback to author.
        
        This consolidates the reply detection pattern used in bonk/pat/hug/slap commands.
        Note: Reply detection only works for prefix commands (!bonk), not slash commands (/bonk)
        due to Discord API limitations.
        """
        if user is not None:
            return user
        
        # Try to detect replied-to user (only works for prefix commands)
        if ctx.message and hasattr(ctx.message, 'reference') and ctx.message.reference:
            try:
                replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                return replied_msg.author
            except:
                pass
        
        # Default to self
        return ctx.author
    
    async def get_avatar(self, user: discord.User) -> bytes:
        """Download user's avatar."""
        session = await self.get_session()
        avatar_url = user.display_avatar.with_size(256).url
        async with session.get(avatar_url) as resp:
            if resp.status == 200:
                return await resp.read()
        return None
    
    async def fetch_tenor_gif(self, search_term: str, limit: int = 20) -> str:
        """Fetch a random GIF from Tenor API."""
        # Get API key from settings/env
        api_key = func.settings.tenor_apikey
        if not api_key:
            func.logger.warning("[TENOR] No API key configured - set TENOR_APIKEY env var")
            return None
        
        try:
            session = await self.get_session()
            params = {
                "key": api_key,
                "q": search_term,
                "limit": limit,
                "client_key": "cheemski_bot",
                "media_filter": "gif",
                "contentfilter": "medium"  # Blocks NSFW but allows more variety
            }
            
            async with session.get(self.TENOR_API_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        # Pick a random result
                        result = random.choice(results)
                        # Get the GIF URL from media_formats
                        media_formats = result.get("media_formats", {})
                        gif_data = media_formats.get("gif", {}) or media_formats.get("mediumgif", {})
                        gif_url = gif_data.get("url")
                        if gif_url:
                            func.logger.info(f"[TENOR] Fetched GIF for '{search_term}': {gif_url}")
                            return gif_url
                else:
                    func.logger.error(f"[TENOR] API returned status {resp.status}")
        except Exception as e:
            func.logger.error(f"[TENOR] Error fetching GIF: {e}")
        
        return None
    
    async def create_bonk_image(self, bonker: discord.User, bonked: discord.User):
        """Create a bonk image with two users."""
        try:
            # Get avatars
            bonker_avatar = await self.get_avatar(bonker)
            bonked_avatar = await self.get_avatar(bonked)
            
            if not bonker_avatar or not bonked_avatar:
                return None
            
            # Load avatars as PIL images
            bonker_img = Image.open(io.BytesIO(bonker_avatar)).convert("RGBA")
            bonked_img = Image.open(io.BytesIO(bonked_avatar)).convert("RGBA")
            
            # Create circular mask
            def make_circle(img, size):
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (size, size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, size, size), fill=255)
                output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                output.paste(img, mask=mask)
                return output
            
            # Create the bonk scene
            width, height = 600, 300
            canvas = Image.new("RGBA", (width, height), (54, 57, 63, 255))  # Discord dark bg
            
            # Add bonker (Cheems with bat) on left - larger
            bonker_circle = make_circle(bonker_img, 150)
            canvas.paste(bonker_circle, (50, 80), bonker_circle)
            
            # Add bonked (victim) on right - with squished effect
            bonked_resized = bonked_img.resize((140, 100), Image.Resampling.LANCZOS)
            bonked_circle = make_circle(bonked_resized.resize((140, 140)), 140)
            canvas.paste(bonked_circle, (380, 100), bonked_circle)
            
            # Add "BONK!" text
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("arial.ttf", 48)
                font_small = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
                font_small = font
            
            # Main BONK text
            draw.text((250, 30), "BONK!", fill=(255, 255, 0), font=font, stroke_width=3, stroke_fill=(0, 0, 0))
            
            # Add bat/stick effect line
            draw.line([(180, 100), (350, 150)], fill=(139, 90, 43), width=12)
            draw.ellipse([(340, 140), (370, 170)], fill=(255, 100, 100))  # Impact
            
            # Add names
            draw.text((60, 240), bonker.display_name[:15], fill=(255, 255, 255), font=font_small)
            draw.text((400, 250), bonked.display_name[:15], fill=(255, 255, 255), font=font_small)
            
            # Save to bytes
            output = io.BytesIO()
            canvas.save(output, format="PNG")
            output.seek(0)
            
            return output
            
        except Exception as e:
            func.logger.error(f"[BONK] Error creating image: {e}")
            return None
    
    def check_special_response(self, ctx: commands.Context, command_name: str, target_user: discord.User) -> dict | None:
        """
        Check for special interactions (Bot/Self) and return special message/Gif/Action.
        Returns None if normal behavior should proceed.
        """
        response_data = {}
        
        # 1. Reverse Bonk Mechanic (Bot Only)
        if command_name == "bonk" and target_user == self.bot.user:
            if random.random() < self.REVERSE_BONK_CHANCE:
                return {
                    "message": f"**{ctx.author.display_name}** tried to bonk me... bit I used **UNO REVERSE** card! 🐕 *NO U!* \n**{self.bot.user.display_name}** bonks **{ctx.author.display_name}**!",
                    "gif": "https://media.tenor.com/HHk_rW8xG4kAAAAC/uno-reverse-card.gif", # Uno reverse gif
                    "action_text": "REVERSE BONKED",
                    "footer": "You fell for it fool! thunder cross split attack! | heuhehueuh"
                }

        # 2. Check for Bot Target
        if target_user == self.bot.user:
            responses = self.SPECIAL_RESPONSES.get(command_name, {}).get("bot", [])
            if responses:
                # Make it clear who tried to use the command against the bot
                action_verb = command_name.replace("_", " ")
                return {
                    "message": f"**{ctx.author.display_name}** tried to {action_verb} **{self.bot.user.display_name}**! 🐕\n\n*{random.choice(responses)}*",
                    "is_special": True
                }
        
        # 3. Check for Self Target
        elif target_user == ctx.author:
            responses = self.SPECIAL_RESPONSES.get(command_name, {}).get("self", [])
            if responses:
                return {
                    "message": f"**{ctx.author.display_name}** used {command_name} on themselves! 🪞\n\n*{random.choice(responses)}*",
                    "is_special": True
                }
                
        return None
    
    @commands.hybrid_command(name="bonk", aliases=["bop"])
    @app_commands.describe(user="The user to bonk!")
    async def bonk(self, ctx: commands.Context, user: discord.User = None):
        """Bonk a user! 🐕 Classic Cheems bonk meme."""
        user = await self.get_target_user(ctx, user)
        
        # Check for special response
        special = self.check_special_response(ctx, "bonk", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.red() if "reverse" in str(special.get("message", "")).lower() else discord.Color.gold())
            # Use provided gif or fetch one from Tenor
            if "gif" in special:
                embed.set_image(url=special["gif"])
            else:
                gif = await self.fetch_tenor_gif("bonk anime dodge")
                if gif:
                    embed.set_image(url=gif)
            if "footer" in special:
                embed.set_footer(text=special["footer"])
            else:
                embed.set_footer(text="Cheems is too powerful | heuhehueuh")
            await ctx.send(embed=embed)
            return

        await ctx.defer()
        
        # Fetch GIF from Tenor API
        bonk_gif = await self.fetch_tenor_gif("bonk meme doge")
        if not bonk_gif:
            bonk_gif = "https://media.tenor.com/Llyp1RmMNkgAAAAC/bonk-meme.gif"  # Fallback
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** bonked themselves! 🐕 *go to horny jail*"
        else:
            message = f"**{ctx.author.display_name}** bonked {user.mention}! 🐕 *bonk*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.yellow()
        )
        embed.set_image(url=bonk_gif)
        embed.set_footer(text="Powered by Cheemski Engine™ | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "bonks")
        await self.track_quest(ctx.guild.id, ctx.author.id, "bonk_master")
    
    @commands.hybrid_command(name="pat")
    @app_commands.describe(user="The user to pat!")
    async def pat(self, ctx: commands.Context, user: discord.User = None):
        """Pat a user! 🐕 Much wholesome."""
        user = await self.get_target_user(ctx, user)
        
        # Check for special response
        special = self.check_special_response(ctx, "pat", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.green())
            gif = await self.fetch_tenor_gif("head pat anime")
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="Cheems appreciates you | heuhehueuh")
            await ctx.send(embed=embed)
            return

        await ctx.defer()
        
        # Diverse pat search terms
        search_terms = ["head pat", "pat cute", "good boy pat", "pet head", "pat pat", "cute pat"]
        gif = await self.fetch_tenor_gif(random.choice(search_terms))
        if not gif:
            gif = "https://media.tenor.com/N41zKEDABuUAAAAC/pat-pat-head.gif"
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** pats themselves! 🐕 *there there*"
        else:
            message = f"**{ctx.author.display_name}** pats {user.mention}! 🐕 *good fren*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.green()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="Much wholesome, very nice | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "pats")
        await self.track_quest(ctx.guild.id, ctx.author.id, "pat_giver")
    
    @commands.hybrid_command(name="hug")
    @app_commands.describe(user="The user to hug!")
    async def hug(self, ctx: commands.Context, user: discord.User = None):
        """Hug a user! 🐕 Much warmth."""
        user = await self.get_target_user(ctx, user)
        
        # Check for special response
        special = self.check_special_response(ctx, "hug", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.pink())
            gif = await self.fetch_tenor_gif("cute hug anime")
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="Cheems loves you | heuhehueuh")
            await ctx.send(embed=embed)
            return

        await ctx.defer()
        
        # Diverse hug search terms
        search_terms = ["group hug", "cute hug", "hug meme", "bear hug", "warm hug", "friendly hug"]
        gif = await self.fetch_tenor_gif(random.choice(search_terms))
        if not gif:
            gif = "https://media.tenor.com/OXCV_qL-V60AAAAC/mochi-mochi-peach-cat.gif"
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** hugs themselves! 🐕 *self love is important*"
        else:
            message = f"**{ctx.author.display_name}** hugs {user.mention}! 🐕 *much warmth*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.pink()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="Much love, very warm | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "hugs")
        await self.track_quest(ctx.guild.id, ctx.author.id, "hug_dealer")
    
    @commands.hybrid_command(name="kill")
    @app_commands.describe(user="The user to eliminate!")
    async def kill(self, ctx: commands.Context, user: discord.User = None):
        """Eliminate a user! 💀 SFW dramatic death scenes only."""
        
        if user is None:
            user = ctx.author
            
        # Check for special response
        special = self.check_special_response(ctx, "kill", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.dark_red())
            gif = await self.fetch_tenor_gif("jojo menacing anime")
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="You cannot kill what is already dead | heuhehueuh")
            await ctx.send(embed=embed)
            return
        
        await ctx.defer()
        
        # Diverse SFW death/faint search terms
        sfw_terms = ["dramatic faint", "game over meme", "wasted gta", "knockout funny", "rip meme", "eliminated meme", "you died dark souls", "fatality mortal kombat", "dead cartoon"]
        gif = await self.fetch_tenor_gif(random.choice(sfw_terms))
        if not gif:
            gif = "https://media.tenor.com/oIMAdxNGBb8AAAAC/dead.gif"  # Safe fallback
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** eliminated themselves! 💀 *wasted*"
        else:
            message = f"**{ctx.author.display_name}** eliminated {user.mention}! 💀 *oof*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.dark_red()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="*dramatically falls* | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "kills")
    
    @commands.hybrid_command(name="slap")
    @app_commands.describe(user="The user to slap!")
    async def slap(self, ctx: commands.Context, user: discord.User = None):
        """Slap a user! 👋 For when bonk isn't enough."""
        user = await self.get_target_user(ctx, user)
        
        # Check for special response
        special = self.check_special_response(ctx, "slap", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.orange())
            gif = await self.fetch_tenor_gif("anime slap dodge")
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="Cheems is too fast | heuhehueuh")
            await ctx.send(embed=embed)
            return
        
        await ctx.defer()
        
        # Diverse slap search terms
        search_terms = ["slap meme", "funny slap", "slap reaction", "smack funny", "slap comedy", "slap gif", "face slap meme"]
        gif = await self.fetch_tenor_gif(random.choice(search_terms))
        if not gif:
            gif = "https://media.tenor.com/Ws6Dm1ZW_vMAAAAC/slap-anime.gif"
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** slapped themselves! 👋 *why tho*"
        else:
            message = f"**{ctx.author.display_name}** slapped {user.mention}! 👋 *smack*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.orange()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="*slap noise* | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "slaps")
        await self.track_quest(ctx.guild.id, ctx.author.id, "slap_happy")
    
    @commands.hybrid_command(name="poke")
    @app_commands.describe(user="The user to poke!")
    async def poke(self, ctx: commands.Context, user: discord.User = None):
        """Poke a user! 👉 *poke poke*"""
        
        if user is None:
            user = ctx.author
            
        # Check for special response
        special = self.check_special_response(ctx, "poke", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.blue())
            gif = await self.fetch_tenor_gif("poke boop cute")
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="Boop! | heuhehueuh")
            await ctx.send(embed=embed)
            return
        
        await ctx.defer()
        
        # Diverse poke search terms
        search_terms = ["poke cute", "poke boop", "poke cheek", "boop nose", "poke funny", "hey you poke"]
        gif = await self.fetch_tenor_gif(random.choice(search_terms))
        if not gif:
            gif = "https://media.tenor.com/LCPAHb_MvfkAAAAC/poke-cats.gif"
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** poked themselves! 👉 *boop*"
        else:
            message = f"**{ctx.author.display_name}** poked {user.mention}! 👉 *poke poke*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="*poke* | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "pokes")
        await self.track_quest(ctx.guild.id, ctx.author.id, "poke_master")
    
    @commands.hybrid_command(name="punch")
    @app_commands.describe(user="The user to punch!")
    async def punch(self, ctx: commands.Context, user: discord.User = None):
        """Punch a user! 👊 POW!"""
        
        if user is None:
            user = ctx.author
            
        # Check for special response
        special = self.check_special_response(ctx, "punch", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.red())
            gif = await self.fetch_tenor_gif("one punch man saitama")
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="ONE PUUUNCH! | heuhehueuh")
            await ctx.send(embed=embed)
            return
        
        await ctx.defer()
        
        # Diverse punch search terms
        search_terms = ["punch meme", "funny punch", "falcon punch", "pow punch", "knockout punch", "punch reaction"]
        gif = await self.fetch_tenor_gif(random.choice(search_terms))
        if not gif:
            gif = "https://media.tenor.com/zHf4qhRZEdUAAAAC/one-punch-man-saitama.gif"
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** punched themselves! 👊 *ow*"
        else:
            message = f"**{ctx.author.display_name}** punched {user.mention}! 👊 *POW!*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.red()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="*impact noise* | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "punches")
        await self.track_quest(ctx.guild.id, ctx.author.id, "punch_pro")
    
    @commands.hybrid_command(name="boop")
    @app_commands.describe(user="The user to boop!")
    async def boop(self, ctx: commands.Context, user: discord.User = None):
        """Boop a user! 👃 *boop the snoot*"""
        user = await self.get_target_user(ctx, user)
        
        # Check for special response
        special = self.check_special_response(ctx, "boop", user)
        if special:
            await ctx.defer()
            embed = discord.Embed(description=special["message"], color=discord.Color.magenta())
            gif = await self.fetch_tenor_gif("boop nose cute")
            if gif:
                embed.set_image(url=gif)
            embed.set_footer(text="Cheems boops back! | heuhehueuh")
            await ctx.send(embed=embed)
            return
        
        await ctx.defer()
        
        # Diverse boop search terms
        search_terms = ["boop nose", "boop cute", "boop snoot", "nose boop cat", "boop dog", "cute boop"]
        gif = await self.fetch_tenor_gif(random.choice(search_terms))
        if not gif:
            gif = "https://media.tenor.com/9e1aE_xBLCsAAAAC/boop-cat.gif"
        
        if user == ctx.author:
            message = f"**{ctx.author.display_name}** booped themselves! 👃 *self-boop*"
        else:
            message = f"**{ctx.author.display_name}** booped {user.mention}! 👃 *boop!*"
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.magenta()
        )
        embed.set_image(url=gif)
        embed.set_footer(text="*boop the snoot* | heuhehueuh")
        
        await ctx.send(content=user.mention if user != ctx.author else None, embed=embed)
        
        # Track stats and quest
        await self.track_stat(ctx.guild.id, ctx.author.id, user.id, "boops")
        await self.track_quest(ctx.guild.id, ctx.author.id, "boop_master")
    
    @commands.hybrid_command(name="8ball", aliases=["eightball"])
    @app_commands.describe(question="Ask the magic 8ball a question!")
    async def eightball(self, ctx: commands.Context, *, question: str):
        """🎱 Ask the magic 8ball anything!"""
        
        if len(question) > 255:
            await ctx.send("❌ Your questiom is too lomg vro! Keep it under 255 characters bonk")
            return
        
        # Use class constant instead of recreating list each call
        embed = discord.Embed(
            title=f"❓ {question}",
            description=f"🎱 **{random.choice(self.EIGHTBALL_ANSWERS)}**",
            color=discord.Color.purple()
        )
        embed.set_author(name="Magic 8ball | heuhehueuh", icon_url="https://i.imgur.com/HbwMhWM.png")
        embed.set_footer(text=f"Asked by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        await self.track_quest(ctx.guild.id, ctx.author.id, "fortune_seeker")
    
    @commands.hybrid_command(name="inspire", aliases=["motivate", "quote"])
    @app_commands.describe(type="What kind of inspiration?")
    @app_commands.choices(type=[
        app_commands.Choice(name="💪 Motivation", value="motivation"),
        app_commands.Choice(name="💡 Advice", value="advice"),
        app_commands.Choice(name="🥠 Fortune", value="fortune"),
    ])
    async def inspire(self, ctx: commands.Context, type: str = "motivation"):
        """Get inspiration - motivation, advice, or fortune! 💪"""
        
        await ctx.defer()
        
        if type == "fortune":
            data = await self.fetch_json("http://yerkee.com/api/fortune")
            text = data.get("fortune", "No fortume foumd vro!") if data else "API is dowm vro! 😢"
            icon = "https://i.imgur.com/58wIjK0.png"
            title = "Fortune Cookie | heuhehueuh"
            emoji = "🥠"
            color = discord.Color.orange()
            footer = "Powered by yerkee.com"
        elif type == "advice":
            text = None
            source = "adviceslip.com"
            
            # Try primary API
            data = await self.fetch_json("https://api.adviceslip.com/advice")
            if data:
                text = data.get("slip", {}).get("advice")
            
            # Fallback to ZenQuotes
            if not text:
                data = await self.fetch_json("https://zenquotes.io/api/random")
                if data and isinstance(data, list) and len(data) > 0:
                    text = data[0].get("q")
                    source = "zenquotes.io"
            
            if not text:
                text = "Stay positive vro! Good things are coming! 🐕"
                source = "Cheems"
            
            icon = "https://i.imgur.com/8pIvnmD.png"
            title = "Cheems Advice | heuhehueuh"
            emoji = "💡"
            color = discord.Color.blue()
            footer = f"Powered by {source}"
        else:  # motivation
            try:
                session = await self.get_session()
                async with session.get("https://type.fit/api/quotes") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        quote = random.choice(data)
                        text = quote.get("text", "Stay stronmg vro!")
                        author = quote.get("author", "Unknown") or "Unknown"
                        text = f"\"{text}\"\n\n— **{author}**"
                    else:
                        text = "Stay stronmg vro! You cam do it!"
            except:
                text = "Stay stronmg vro! You cam do it!"
            
            icon = "https://i.imgur.com/Cnr6cQb.png"
            title = "Motivational Quote | heuhehueuh"
            emoji = "💪"
            color = discord.Color.gold()
            footer = "You cam do it vro! 🐕"
            
            await self.track_quest(ctx.guild.id, ctx.author.id, "motivated")
        
        embed = discord.Embed(
            description=f"{emoji} **{self.cheems.cheemify(text, add_emoji=False)}**",
            color=color
        )
        embed.set_author(name=title, icon_url=icon)
        embed.set_footer(text=footer)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="rps", aliases=["rockpaperscissors"])
    @app_commands.describe(move="Rock, Paper, or Scissors?")
    @app_commands.choices(move=[
        app_commands.Choice(name="🪨 Rock", value="rock"),
        app_commands.Choice(name="📄 Paper", value="paper"),
        app_commands.Choice(name="✂️ Scissors", value="scissors"),
    ])
    async def rps(self, ctx: commands.Context, move: str):
        """✂️ Play Rock Paper Scissors with Cheems!"""
        
        move = move.lower()
        if move not in ["rock", "paper", "scissors"]:
            await ctx.send("❌ Pick rock, paper, or scissors vro! bonk")
            return
        
        bot_moves = ["rock", "paper", "scissors"]
        bot_move = random.choice(bot_moves)
        
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        
        # Determine winner
        if move == bot_move:
            result = "It's a tie vro! 🤝"
            color = discord.Color.yellow()
        elif (move == "rock" and bot_move == "scissors") or \
             (move == "paper" and bot_move == "rock") or \
             (move == "scissors" and bot_move == "paper"):
            result = "You wim vro! 🎉"
            color = discord.Color.green()
        else:
            result = "I wim vro! 😎 Get bomked!"
            color = discord.Color.red()
        
        embed = discord.Embed(
            title="Rock Paper Scissors!",
            description=f"You: {emojis[move]} **{move.title()}**\n"
                       f"Cheems: {emojis[bot_move]} **{bot_move.title()}**\n\n"
                       f"**{result}**",
            color=color
        )
        embed.set_footer(text="heuhehueuh")
        
        await ctx.send(embed=embed)
        await self.track_quest(ctx.guild.id, ctx.author.id, "rps_champion")
    
    @commands.hybrid_command(name="random", aliases=["roll", "dice"])
    @app_commands.describe(min="Minimum number", max="Maximum number")
    async def random_number(self, ctx: commands.Context, min: int = 1, max: int = 100):
        """🎲 Generate a random number!"""
        
        if min > max:
            min, max = max, min
        
        result = random.randint(min, max)
        
        embed = discord.Embed(
            title="🎲 Random Number!",
            description=f"**{result}**\n\n*(betweem {min} amd {max})*",
            color=discord.Color.blue()
        )
        embed.set_footer(text="heuhehueuh")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="coinflip", aliases=["flip", "coin"])
    async def coinflip(self, ctx: commands.Context):
        """🪙 Flip a coin!"""
        
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(
            title="🪙 Coin Flip!",
            description=f"**{result}!**",
            color=discord.Color.gold()
        )
        embed.set_footer(text="heuhehueuh")
        
        await ctx.send(embed=embed)
        await self.track_quest(ctx.guild.id, ctx.author.id, "coin_flipper")
    
    @commands.hybrid_command(name="choose", aliases=["pick"])
    @app_commands.describe(choices="Choices separated by commas (e.g. pizza, burger, pasta)")
    async def choose(self, ctx: commands.Context, *, choices: str):
        """🤔 Let Cheems choose for you!"""
        
        options = [c.strip() for c in choices.split(",") if c.strip()]
        
        if len(options) < 2:
            await ctx.send("❌ Give me at least 2 optionms to choose from vro! (separate with commas)")
            return
        
        choice = random.choice(options)
        
        embed = discord.Embed(
            title="🤔 Cheems Chooses...",
            description=f"**{choice}**",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"From {len(options)} optionms | heuhehueuh")
        
        await ctx.send(embed=embed)
        await self.track_quest(ctx.guild.id, ctx.author.id, "decision_maker")
    
    
    @commands.hybrid_command(name="kanye", aliases=["ye"])
    async def kanye(self, ctx: commands.Context):
        """🎤 Get a random Kanye West quote!"""
        
        await ctx.defer()
        
        try:
            session = await self.get_session()
            async with session.get("https://api.kanye.rest/?format=json") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    quote = data.get("quote", "No quote foumd vro!")
                else:
                    quote = "API is dowm vro! Kanye is busy."
        except:
            quote = "Somethimg went wromg vro! 😢"
        
        embed = discord.Embed(
            description=f"🎤 *\"{self.cheems.cheemify(quote, add_emoji=False)}\"*\n\n— **Kanye West**",
            color=discord.Color.orange()
        )
        embed.set_author(name="Kanye Quote | heuhehueuh", icon_url="https://i.imgur.com/SsNoHVh.png")
        embed.set_footer(text="Powered by kanye.rest")
        
        await func.send(ctx, embed)
    
    @commands.command(name="urban", aliases=["ud", "define"])
    @app_commands.describe(word="Word to look up in Urban Dictionary")
    async def urban(self, ctx: commands.Context, *, word: str):
        """📖 Look up a word in Urban Dictionary!"""
        
        await ctx.defer()
        
        try:
            session = await self.get_session()
            async with session.get(f"https://api.urbandictionary.com/v0/define?term={word}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("list"):
                        entry = data["list"][0]
                        definition = entry.get("definition", "No definitiom foumd vro!")
                        # Clean up brackets used for linking
                        definition = definition.replace("[", "").replace("]", "")
                        if len(definition) > 500:
                            definition = definition[:500] + "..."
                        example = entry.get("example", "").replace("[", "").replace("]", "")
                        if len(example) > 200:
                            example = example[:200] + "..."
                        thumbs_up = entry.get("thumbs_up", 0)
                        thumbs_down = entry.get("thumbs_down", 0)
                    else:
                        definition = "No definitiom foumd vro!"
                        example = ""
                        thumbs_up = 0
                        thumbs_down = 0
                else:
                    definition = "API is dowm vro!"
                    example = ""
                    thumbs_up = 0
                    thumbs_down = 0
        except:
            definition = "Somethimg went wromg vro! 😢"
            example = ""
            thumbs_up = 0
            thumbs_down = 0
        
        embed = discord.Embed(
            title=f"📖 {word.title()}",
            description=f"**Definition:**\n{definition}",
            color=discord.Color.dark_orange()
        )
        if example:
            embed.add_field(name="Example:", value=f"*{example}*", inline=False)
        embed.add_field(name="Votes", value=f"👍 {thumbs_up} | 👎 {thumbs_down}", inline=False)
        embed.set_author(name="Urban Dictionary | heuhehueuh", icon_url="https://i.imgur.com/vdoosDm.png")
        embed.set_footer(text="Powered by UrbanDictionary")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="chucknorris", aliases=["chuck", "norris"])
    async def chucknorris(self, ctx: commands.Context):
        """💪 Get a Chuck Norris fact!"""
        
        await ctx.defer()
        
        try:
            session = await self.get_session()
            async with session.get("https://api.chucknorris.io/jokes/random") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    joke = data.get("value", "Chuck Norris doesnt need jokes vro!")
                    icon = data.get("icon_url", "https://i.imgur.com/vdoosDm.png")
                else:
                    joke = "API is dowm vro! Chuck is fiximg it."
                    icon = "https://i.imgur.com/vdoosDm.png"
        except:
            joke = "Somethimg went wromg vro! 😢"
            icon = "https://i.imgur.com/vdoosDm.png"
        
        embed = discord.Embed(
            description=f"💪 {joke}",
            color=discord.Color.orange()
        )
        embed.set_author(name="Chuck Norris Facts | heuhehueuh", icon_url=icon)
        embed.set_footer(text="Powered by chucknorris.io")
        
        await ctx.send(embed=embed)


    @commands.hybrid_command(name="joke", aliases=["dadjoke"])
    async def joke(self, ctx: commands.Context):
        """😂 Get a random joke!"""
        
        await ctx.defer()
        
        try:
            session = await self.get_session()
            headers = {"Accept": "application/json"}
            async with session.get("https://icanhazdadjoke.com/", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    joke = data.get("joke", "No joke foumd vro!")
                else:
                    joke = "API is dowm vro!"
        except:
            joke = "Somethimg went wromg vro! 😢"
        
        embed = discord.Embed(
            description=f"😂 {self.cheems.cheemify(joke, add_emoji=True)}",
            color=discord.Color.yellow()
        )
        embed.set_author(name="Dad Joke | heuhehueuh")
        embed.set_footer(text="Powered by icanhazdadjoke.com")
        
        await ctx.send(embed=embed)

    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        if self.session and not self.session.closed:
            self.bot.loop.create_task(self.session.close())


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))

