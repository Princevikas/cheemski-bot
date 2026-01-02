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
import voicelink

from function import (
    send,
    get_lang,
    cooldown_check
)
from discord import app_commands
from discord.ext import commands


async def check_access(ctx: commands.Context):
    player: voicelink.Player = ctx.guild.voice_client
    if not player:
        text = await get_lang(ctx.guild.id, "noPlayer")
        raise voicelink.exceptions.VoicelinkException(text)

    if ctx.author not in player.channel.members:
        if not ctx.author.guild_permissions.manage_guild:
            text = await get_lang(ctx.guild.id, "notInChannel")
            raise voicelink.exceptions.VoicelinkException(text.format(ctx.author.mention, player.channel.mention))

    return player


class Effect(commands.Cog):
    """Audio effects for the music player. DJ only."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.description = "This category is only available to DJ on this server."
    
    # All available effects
    EFFECTS = {
        "nightcore": "🎵 Nightcore - Higher pitch, faster tempo",
        "8d": "🎧 8D Audio - Rotating stereo effect",
        "vaporwave": "🌊 Vaporwave - Slower, dreamy sound",
        "speed": "⚡ Speed - Change playback speed",
        "karaoke": "🎤 Karaoke - Remove vocals",
        "tremolo": "📳 Tremolo - Volume oscillation",
        "vibrato": "🎸 Vibrato - Pitch oscillation", 
        "rotation": "🔄 Rotation - Stereo panning",
        "distortion": "🔊 Distortion - Crunchy sound",
        "lowpass": "🔈 Lowpass - Muffled bass",
        "hall": "⛪ Hall - Cathedral reverb",
    }

    async def effect_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        player: voicelink.Player = interaction.guild.voice_client
        if not player:
            return []
        if current:
            return [app_commands.Choice(name=effect.tag, value=effect.tag) for effect in player.filters.get_filters() if current in effect.tag]
        return [app_commands.Choice(name=effect.tag, value=effect.tag) for effect in player.filters.get_filters()]

    @commands.hybrid_command(name="effect")
    @app_commands.describe(
        type="Choose an audio effect to apply",
        value="Optional value (for speed: 0.5-2.0)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="🎵 Nightcore", value="nightcore"),
        app_commands.Choice(name="🎧 8D Audio", value="8d"),
        app_commands.Choice(name="🌊 Vaporwave", value="vaporwave"),
        app_commands.Choice(name="⚡ Speed", value="speed"),
        app_commands.Choice(name="🎤 Karaoke", value="karaoke"),
        app_commands.Choice(name="📳 Tremolo", value="tremolo"),
        app_commands.Choice(name="🎸 Vibrato", value="vibrato"),
        app_commands.Choice(name="🔄 Rotation", value="rotation"),
        app_commands.Choice(name="🔊 Distortion", value="distortion"),
        app_commands.Choice(name="🔈 Lowpass", value="lowpass"),
        app_commands.Choice(name="⛪ Hall Reverb", value="hall"),
        app_commands.Choice(name="❌ Clear All", value="clear"),
    ])
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def effect(self, ctx: commands.Context, type: str, value: float = None):
        """Apply audio effects to the music! 🎵"""
        player = await check_access(ctx)
        
        if type == "clear":
            await player.reset_filter()
            await send(ctx, "clearEffect")
            return
        
        # Remove existing filter if present
        if player.filters.has_filter(filter_tag=type):
            player.filters.remove_filter(filter_tag=type)
        
        # Apply the selected effect
        effect = None
        
        if type == "nightcore":
            effect = voicelink.Timescale.nightcore()
        
        elif type == "8d":
            effect = voicelink.Rotation.nightD()
        
        elif type == "vaporwave":
            effect = voicelink.Timescale.vaporwave()
        
        elif type == "speed":
            speed_value = value if value and 0.5 <= value <= 2.0 else 1.25
            effect = voicelink.Timescale(tag="speed", speed=speed_value)
        
        elif type == "karaoke":
            effect = voicelink.Karaoke(tag="karaoke", level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
        
        elif type == "tremolo":
            effect = voicelink.Tremolo(tag="tremolo", frequency=2.0, depth=0.5)
        
        elif type == "vibrato":
            effect = voicelink.Vibrato(tag="vibrato", frequency=2.0, depth=0.5)
        
        elif type == "rotation":
            effect = voicelink.Rotation(tag="rotation", rotation_hertz=0.2)
        
        elif type == "distortion":
            effect = voicelink.Distortion(tag="distortion", sin_offset=0.0, sin_scale=1.0, cos_offset=0.0, cos_scale=1.0, tan_offset=0.0, tan_scale=1.0, offset=0.0, scale=1.0)
        
        elif type == "lowpass":
            effect = voicelink.LowPass(tag="lowpass", smoothing=20.0)
        
        elif type == "hall":
            # Hall uses multiple filters
            for tag in ["hall_rotation", "hall_lowpass", "hall_vibrato"]:
                if player.filters.has_filter(filter_tag=tag):
                    player.filters.remove_filter(filter_tag=tag)
            
            rotation = voicelink.Rotation(tag="hall_rotation", rotation_hertz=0.1)
            await player.add_filter(rotation, ctx.author)
            
            lowpass = voicelink.LowPass(tag="hall_lowpass", smoothing=50)
            await player.add_filter(lowpass, ctx.author)
            
            vibrato = voicelink.Vibrato(tag="hall_vibrato", frequency=0.5, depth=0.1)
            await player.add_filter(vibrato, ctx.author)
            
            await send(ctx, "addEffect", "hall")
            return
        
        if effect:
            await player.add_filter(effect, ctx.author)
            await send(ctx, "addEffect", effect.tag)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Effect(bot))
