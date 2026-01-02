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

from discord import app_commands, ui
from discord.ext import commands
from datetime import datetime
from typing import Optional


class FeedbackModal(ui.Modal):
    """Modal for submitting feedback/suggestions/bugs."""
    
    content = ui.TextInput(
        label="Your Message",
        style=discord.TextStyle.paragraph,
        placeholder="Describe your suggestion, bug report, or feedback here...",
        required=True,
        min_length=10,
        max_length=1000
    )
    
    def __init__(self, cog, feedback_type: str):
        self.feedback_type = feedback_type
        titles = {
            "suggestion": "💡 Submit Suggestion",
            "bug": "🐛 Report Bug", 
            "feedback": "💬 Give Feedback"
        }
        super().__init__(title=titles.get(feedback_type, "📝 Submit Feedback"))
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.save_suggestion(
            user=interaction.user,
            guild_id=interaction.guild_id,
            category=self.feedback_type,
            content=self.content.value,
            include_name=False  # Always anonymous
        )
        
        emojis = {"suggestion": "💡", "bug": "🐛", "feedback": "💬"}
        
        embed = discord.Embed(
            title=f"✅ {self.feedback_type.title()} Submitted!",
            description=f"{emojis.get(self.feedback_type, '📝')} Your anonymous {self.feedback_type} has been sent to the bot owner.",
            color=discord.Color.green()
        )
        embed.set_footer(text="We appreciate your input! | heuhehueuh")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Suggestions(commands.Cog):
    """Anonymous feedback system! Sends to dashboard inbox."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.feedback_prompted_users = set()
        func.logger.info("Suggestions cog initialized - /feedback ready! Sends to dashboard inbox.")
    
    async def save_suggestion(self, user: discord.User, guild_id: int, category: str, content: str, include_name: bool = False):
        """Save a suggestion to bot owner's inbox in MongoDB."""
        owner_ids = func.settings.bot_access_user if hasattr(func.settings, 'bot_access_user') else []
        
        if not owner_ids:
            func.logger.warning("No bot_access_user configured - suggestion not saved to inbox")
            return
        
        import time as time_module
        current_time = int(time_module.time())
        
        sender_name = user.display_name if include_name else "Anonymous"
        
        inbox_message = {
            "title": f"💡 {category.title()}: {content[:40]}{'...' if len(content) > 40 else ''}",
            "description": content,
            "type": "suggestion",
            "sender": user.id if include_name else None,
            "sender_name": sender_name,
            "time": str(current_time),
            "category": category,
            "guild_id": str(guild_id),
            "created_at": datetime.now().isoformat(),
            "read": False
        }
        
        for owner_id in owner_ids:
            try:
                await func.update_user(owner_id, {
                    "$push": {"inbox": inbox_message}
                })
                func.logger.info(f"{'Named' if include_name else 'Anonymous'} {category} sent to owner {owner_id}'s inbox")
                
                try:
                    owner = await self.bot.fetch_user(owner_id)
                    if owner:
                        title = f"📬 New Anonymous {category.title()}"
                        
                        dm_embed = discord.Embed(
                            title=title,
                            description=content[:500] + ("..." if len(content) > 500 else ""),
                            color=discord.Color.blue()
                        )
                        dm_embed.set_footer(text="This submission is anonymous")
                        await owner.send(embed=dm_embed)
                except Exception as dm_error:
                    func.logger.debug(f"Could not DM owner {owner_id}: {dm_error}")
                    
            except Exception as e:
                func.logger.error(f"Failed to send suggestion to inbox: {e}")
        
        return inbox_message
    
    @commands.hybrid_command(name="feedback")
    @app_commands.describe(
        type="What type of feedback?",
        message="Your message (optional - opens a form if empty)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="💡 Suggestion", value="suggestion"),
        app_commands.Choice(name="🐛 Bug Report", value="bug"),
        app_commands.Choice(name="💬 General Feedback", value="feedback"),
    ])
    async def feedback(self, ctx: commands.Context, type: str = "feedback", *, message: str = None):
        """Submit feedback, suggestions, or bug reports! 💡 (Anonymous)"""
        
        if message:
            # Quick inline submission
            if len(message) < 10:
                await func.send(ctx, "❌ Message must be at least 10 characters!", ephemeral=True)
                return
            
            await self.save_suggestion(
                user=ctx.author,
                guild_id=ctx.guild.id,
                category=type,
                content=message,
                include_name=False
            )
            
            emojis = {"suggestion": "💡", "bug": "🐛", "feedback": "💬"}
            embed = discord.Embed(
                title=f"✅ {type.title()} Submitted!",
                description=f"{emojis.get(type, '📝')} Your anonymous {type} has been sent.",
                color=discord.Color.green()
            )
            await func.send(ctx, embed, ephemeral=True)
        else:
            # Open modal for longer form
            if ctx.interaction:
                modal = FeedbackModal(self, type)
                await ctx.interaction.response.send_modal(modal)
            else:
                await func.send(ctx, "❌ Please include a message: `!feedback suggestion Your message here`")
    
    @commands.Cog.listener()
    async def on_voicelink_track_end(self, player, track, _):
        """Randomly prompt users for feedback after songs."""
        if not hasattr(player, 'context') or not player.context:
            return
        
        if random.randint(1, 100) != 1:
            return
        
        user = player.context.author
        if user.id in self.feedback_prompted_users:
            return
        
        self.feedback_prompted_users.add(user.id)
        
        try:
            embed = discord.Embed(
                title="💭 Quick Question!",
                description="Enjoying Cheemski Bot? We'd love your feedback!\n\n"
                           "Use `/feedback` to share your thoughts!",
                color=discord.Color.purple()
            )
            embed.set_footer(text="This prompt won't appear again for a while | heuhehueuh")
            
            await player.context.send(embed=embed, delete_after=60)
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Suggestions(bot))
