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
import psutil
import function as func

from discord import app_commands
from discord.ext import commands
from function import (
    LANGS,
    send,
    update_settings,
    get_settings,
    get_lang,
    time as ctime,
    get_aliases,
    cooldown_check,
    format_bytes
)

from views import DebugView, HelpView, EmbedBuilderView

def status_icon(status: bool) -> str:
    return "✅" if status else "❌"

class Settings(commands.Cog, name="settings"):
    def __init__(self, bot) -> None:
        self.bot: commands.Bot = bot
        self.description = "This category is only available to admin permissions on the server."
    
    @commands.hybrid_group(
        name="settings",
        aliases=get_aliases("settings"),
        invoke_without_command=True
    )
    async def settings(self, ctx: commands.Context):
        view = HelpView(self.bot, ctx.author)
        embed = view.build_embed(self.qualified_name)
        view.response = await send(ctx, embed, view=view)
    
    @settings.command(name="prefix", aliases=get_aliases("prefix"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def prefix(self, ctx: commands.Context, prefix: str):
        "Change the default prefix for message commands."
        if not self.bot.intents.message_content:
            return await send(ctx, "missingIntents", "MESSAGE_CONTENT", ephemeral=True)
        
        await update_settings(ctx.guild.id, {"$set": {"prefix": prefix}})
        await send(ctx, "setPrefix", prefix, prefix)

    @settings.command(name="language", aliases=get_aliases("language"))
    @app_commands.describe(language="Choose your preferred language for bot messages.")
    @app_commands.choices(language=[
        app_commands.Choice(name="English", value="EN"),
        app_commands.Choice(name="CHEEMS (Doge speak)", value="CHEEMS"),
        app_commands.Choice(name="Español", value="ES"),
        app_commands.Choice(name="Français", value="FR"),
        app_commands.Choice(name="Deutsch", value="DE"),
        app_commands.Choice(name="Русский", value="RU"),
        app_commands.Choice(name="中文", value="CH"),
        app_commands.Choice(name="日本語", value="JA"),
        app_commands.Choice(name="한국어", value="KO"),
        app_commands.Choice(name="Polski", value="PL"),
        app_commands.Choice(name="Українська", value="UA"),
        app_commands.Choice(name="Tiếng Việt", value="VN"),
    ])
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def language(self, ctx: commands.Context, language: str):
        "You can choose your preferred language, the bot message will change to the language you set."
        language = language.upper()
        if language not in LANGS:
            # Try to load it anyway
            LANGS[language] = {}
        
        await update_settings(ctx.guild.id, {"$set": {'lang': language}})
        await send(ctx, 'changedLanguage', language)

    @settings.command(name="dj", aliases=get_aliases("dj"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def dj(self, ctx: commands.Context, role: discord.Role = None):
        "Set a DJ role or remove DJ role."
        await update_settings(ctx.guild.id, {"$set": {'dj': role.id}} if role else {"$unset": {'dj': None}})
        await send(ctx, 'setDJ', f"<@&{role.id}>" if role else "None")

    @settings.command(name="lyricsplatform", aliases=get_aliases("lyricsplatform"))
    @app_commands.describe(platform="Choose the lyrics provider to use.")
    @app_commands.choices(platform=[
        app_commands.Choice(name="Genius (Plain text, large library)", value="genius"),
        app_commands.Choice(name="LrcLib (Synced lyrics)", value="lrclib"),
        app_commands.Choice(name="MusixMatch (Popular songs)", value="musixmatch"),
        app_commands.Choice(name="Lyrist (Fast, simple)", value="lyrist"),
        app_commands.Choice(name="A-Z Lyrics (Web scraping)", value="a_zlyrics"),
    ])
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def lyricsplatform(self, ctx: commands.Context, platform: str):
        "Choose which lyrics provider to use for fetching song lyrics."
        valid_platforms = ["genius", "lrclib", "musixmatch", "lyrist", "a_zlyrics"]
        platform = platform.lower()
        if platform not in valid_platforms:
            return await send(ctx, f"Invalid platform! Choose from: {', '.join(valid_platforms)}", ephemeral=True)
        
        await update_settings(ctx.guild.id, {"$set": {'lyrics_platform': platform}})
        await send(ctx, f"🎤 Lyrics platform set to **{platform.title()}**!")


    @settings.command(name="queue", aliases=get_aliases("queue"))
    @app_commands.choices(mode=[
        app_commands.Choice(name=queue_type.capitalize(), value=queue_type)
        for queue_type in voicelink.queue.QUEUE_TYPES.keys()
    ])
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def queue(self, ctx: commands.Context, mode: str):
        "Change to another type of queue mode."
        mode = mode if mode.lower() in voicelink.queue.QUEUE_TYPES else next(iter(voicelink.queue.QUEUE_TYPES))
        await update_settings(ctx.guild.id, {"$set": {"queue_type": mode}})
        await send(ctx, "setQueue", mode.capitalize())

    @settings.command(name="247", aliases=get_aliases("247"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def playforever(self, ctx: commands.Context):
        "Toggles 24/7 mode, which disables automatic inactivity-based disconnects."
        settings = await get_settings(ctx.guild.id)
        toggle = settings.get('24/7', False)
        await update_settings(ctx.guild.id, {"$set": {'24/7': not toggle}})
        await send(ctx, '247', await get_lang(ctx.guild.id, "enabled" if not toggle else "disabled"))

    @settings.command(name="bypassvote", aliases=get_aliases("bypassvote"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def bypassvote(self, ctx: commands.Context):
        "Toggles voting system."
        settings = await get_settings(ctx.guild.id)
        toggle = settings.get('disabled_vote', True)
        await update_settings(ctx.guild.id, {"$set": {'disabled_vote': not toggle}})
        await send(ctx, 'bypassVote', await get_lang(ctx.guild.id, "enabled" if not toggle else "disabled"))

    @settings.command(name="view", aliases=get_aliases("view"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def view(self, ctx: commands.Context):
        "Show all the bot settings in your server."
        settings = await get_settings(ctx.guild.id)

        texts = await get_lang(ctx.guild.id, "settingsMenu", "settingsTitle", "settingsValue", "settingsTitle2", "settingsValue2", "settingsTitle3", "settingsPermTitle", "settingsPermValue")
        embed = discord.Embed(color=func.settings.embed_color)
        embed.set_author(name=texts[0].format(ctx.guild.name), icon_url=self.bot.user.display_avatar.url)
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        dj_role = ctx.guild.get_role(settings.get('dj', 0))
        embed.add_field(name=texts[1], value=texts[2].format(
            settings.get('prefix', func.settings.bot_prefix) or 'None',
            settings.get('lang', 'EN'),
            settings.get('controller', True),
            dj_role.name if dj_role else 'None',
            settings.get('disabled_vote', False),
            settings.get('24/7', False),
            settings.get('volume', 100),
            ctime(settings.get('played_time', 0) * 60 * 1000),
            inline=True)
        )
        embed.add_field(name=texts[3], value=texts[4].format(
            settings.get("queue_type", "Queue"),
            func.settings.max_queue,
            settings.get("duplicate_track", True)
        ))

        if stage_template := settings.get("stage_announce_template"):
            embed.add_field(name=texts[5], value=f"```{stage_template}```", inline=False)

        perms = ctx.guild.me.guild_permissions
        embed.add_field(name=texts[6], value=texts[7].format(
                status_icon(perms.administrator),
                status_icon(perms.manage_guild),
                status_icon(perms.manage_channels),
                status_icon(perms.manage_messages)
            ),
            inline=False
        )
        await send(ctx, embed)

    @commands.hybrid_command(name="volume", aliases=get_aliases("volume"))
    @app_commands.describe(value="Input a integer.")
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def volume(self, ctx: commands.Context, value: commands.Range[int, 1, 150]):
        "Set the player's volume."
        player: voicelink.Player = ctx.guild.voice_client
        if player:
            await player.set_volume(value, ctx.author)

        await update_settings(ctx.guild.id, {"$set": {'volume': value}})
        await send(ctx, 'setVolume', value)

    @settings.command(name="togglecontroller", aliases=get_aliases("togglecontroller"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def togglecontroller(self, ctx: commands.Context):
        "Toggles the music controller."
        settings = await get_settings(ctx.guild.id)
        toggle = not settings.get('controller', True)

        player: voicelink.Player = ctx.guild.voice_client
        if player and toggle is False and player.controller:
            try:
                await player.controller.delete()
            except:
                discord.ui.View.from_message(player.controller).stop()

        await update_settings(ctx.guild.id, {"$set": {'controller': toggle}})
        await send(ctx, 'toggleController', await get_lang(ctx.guild.id, "enabled" if toggle else "disabled"))

    @settings.command(name="duplicatetrack", aliases=get_aliases("duplicatetrack"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def duplicatetrack(self, ctx: commands.Context):
        "Toggle Vocard to prevent duplicate songs from queuing."
        settings = await get_settings(ctx.guild.id)
        toggle = not settings.get('duplicate_track', False)
        player: voicelink.Player = ctx.guild.voice_client
        if player:
            player.queue._allow_duplicate = toggle

        await update_settings(ctx.guild.id, {"$set": {'duplicate_track': toggle}})
        return await send(ctx, "toggleDuplicateTrack", await get_lang(ctx.guild.id, "disabled" if toggle else "enabled"))
    
    @settings.command(name="customcontroller", aliases=get_aliases("customcontroller"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def customcontroller(self, ctx: commands.Context):
        "Customizes music controller embeds."
        settings = await get_settings(ctx.guild.id)
        controller_settings = settings.get("default_controller", func.settings.controller)

        view = EmbedBuilderView(ctx, controller_settings.get("embeds").copy())
        view.response = await send(ctx, view.build_embed(), view=view)

    @settings.command(name="controllermsg", aliases=get_aliases("controllermsg"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def controllermsg(self, ctx: commands.Context):
        "Toggles to send a message when clicking the button in the music controller."
        settings = await get_settings(ctx.guild.id)
        toggle = not settings.get('controller_msg', True)

        await update_settings(ctx.guild.id, {"$set": {'controller_msg': toggle}})
        await send(ctx, 'toggleControllerMsg', await get_lang(ctx.guild.id, "enabled" if toggle else "disabled"))
    
    @settings.command(name="silentmsg", aliases=get_aliases("silentmsg"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def silentmsg(self, ctx: commands.Context):
        "Toggle silent messaging to send discreet messages without alerting recipients."
        settings = await get_settings(ctx.guild.id)
        toggle = not settings.get('silent_msg', False)

        await update_settings(ctx.guild.id, {"$set": {'silent_msg': toggle}})
        await send(ctx, 'toggleSilentMsg', await get_lang(ctx.guild.id, "enabled" if toggle else "disabled"))

    @settings.command(name="stageannounce", aliases=get_aliases("stageannounce"))
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def stageannounce(self, ctx: commands.Context, template: str = None):
        "Customize the channel topic template"
        await update_settings(ctx.guild.id, {"$set": {'stage_announce_template': template}})
        await send(ctx, "setStageAnnounceTemplate")

    @settings.command(name="setupchannel", aliases=get_aliases("setupchannel"))
    @app_commands.describe(
        channel="Provide a request channel. If not, a text channel will be generated."
    )
    @commands.has_permissions(manage_guild=True)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def setupchannel(self, ctx: commands.Context, channel: discord.TextChannel = None) -> None:
        "Sets up a dedicated channel for song requests in your server."
        if not self.bot.intents.message_content:
            return await send(ctx, "missingIntents", "MESSAGE_CONTENT", ephemeral=True)
        
        if not channel:
            try:
                overwrites = {
                    ctx.guild.me: discord.PermissionOverwrite(
                        read_messages=True,
                        manage_messages=True
                    )
                }
                channel = await ctx.guild.create_text_channel("vocard-song-requests", overwrites=overwrites)
            except:
                return await send(ctx, "noCreatePermission")

        channel_perms = channel.permissions_for(ctx.me)
        if not channel_perms.text() and not channel_perms.manage_messages:
            return await send(ctx, "noCreatePermission")
        
        settings = await func.get_settings(ctx.guild.id)
        controller = settings.get("default_controller", func.settings.controller).get("embeds", {}).get("inactive", {})        
        message = await channel.send(embed=voicelink.build_embed(controller, voicelink.Placeholders(self.bot)))

        await update_settings(ctx.guild.id, {"$set": {'music_request_channel': {
            "text_channel_id": channel.id,
            "controller_msg_id": message.id,
        }}})
        await send(ctx, "createSongRequestChannel", channel.mention)

    @app_commands.command(name="debug")
    async def debug(self, interaction: discord.Interaction):
        if interaction.user.id not in func.settings.bot_access_user:
            return await interaction.response.send_message("You are not able to use this command!")

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(func.ROOT_DIR)

        available_memory, total_memory = memory.available, memory.total
        used_disk_space, total_disk_space = disk.used, disk.total
        embed = discord.Embed(title="📄 Debug Panel", color=func.settings.embed_color)
        embed.description = "```==    System Info    ==\n" \
                            f"• CPU:     {psutil.cpu_freq().current}Mhz ({psutil.cpu_percent()}%)\n" \
                            f"• RAM:     {format_bytes(total_memory - available_memory)}/{format_bytes(total_memory, True)} ({memory.percent}%)\n" \
                            f"• DISK:    {format_bytes(total_disk_space - used_disk_space)}/{format_bytes(total_disk_space, True)} ({disk.percent}%)```"

        embed.add_field(
            name="🤖 Bot Information",
            value=f"```• VERSION: {func.settings.version}\n" \
                  f"• LATENCY: {self.bot.latency:.2f}ms\n" \
                  f"• GUILDS:  {len(self.bot.guilds)}\n" \
                  f"• USERS:   {sum([guild.member_count or 0 for guild in self.bot.guilds])}\n" \
                  f"• PLAYERS: {len(self.bot.voice_clients)}```",
            inline=False
        )

        node: voicelink.Node
        for name, node in voicelink.NodePool._nodes.items():
            if node._available:
                total_memory = node.stats.used + node.stats.free
                embed.add_field(
                    name=f"{name} Node - 🟢 Connected",
                    value=f"```• ADDRESS: {node._host}:{node._port}\n" \
                        f"• PLAYERS: {len(node._players)}\n" \
                        f"• CPU:     {node.stats.cpu_process_load:.1f}%\n" \
                        f"• RAM:     {format_bytes(node.stats.free)}/{format_bytes(total_memory, True)} ({(node.stats.free/total_memory) * 100:.1f}%)\n"
                        f"• LATENCY: {node.latency:.2f}ms\n" \
                        f"• UPTIME:  {func.time(node.stats.uptime)}```"
                )
            else:
                embed.add_field(
                    name=f"{name} Node - 🔴 Disconnected",
                    value=f"```• ADDRESS: {node._host}:{node._port}\n" \
                        f"• PLAYERS: {len(node._players)}\nNo extra data is available for display```",
                )

        await interaction.response.send_message(embed=embed, view=DebugView(self.bot), ephemeral=True)
    
    @commands.command(name="forcesync")
    async def forcesync(self, ctx: commands.Context):
        """Force sync all slash commands to Discord (bot owner/access only)"""
        # Check if user has access
        bot_access_users = getattr(func.settings, 'bot_access_user', []) or []
        is_owner = await self.bot.is_owner(ctx.author)
        
        if ctx.author.id not in bot_access_users and not is_owner:
            return await send(ctx, "❌ You don't have permission to force sync commands.", ephemeral=True)
        
        from sync_manager import smart_sync, get_sync_status
        
        # Get current status
        status = await get_sync_status(self.bot)
        
        if not status["can_sync_global"] and not ctx.guild:
            cooldown = status["global_cooldown_remaining"]
            return await send(ctx, f"⏳ Global sync on cooldown. Try again in {cooldown}s or use in a guild for faster sync.", ephemeral=True)
        
        await send(ctx, "🔄 Syncing commands to Discord...", ephemeral=True)
        
        try:
            # Prefer guild sync if in a guild (faster, no global rate limit)
            if ctx.guild:
                result = await smart_sync(self.bot, force=True, guild_id=ctx.guild.id)
                if result["synced"]:
                    # Also do global sync if possible
                    if status["can_sync_global"]:
                        global_result = await smart_sync(self.bot, force=True)
                        await send(ctx, f"✅ {result['reason']}\n📡 Global: {global_result['reason']}", ephemeral=True)
                    else:
                        await send(ctx, f"✅ {result['reason']}\n⏳ Global sync on cooldown ({status['global_cooldown_remaining']}s)", ephemeral=True)
                else:
                    await send(ctx, f"⚠️ {result['reason']}", ephemeral=True)
            else:
                result = await smart_sync(self.bot, force=True)
                if result["synced"]:
                    await send(ctx, f"✅ {result['reason']}", ephemeral=True)
                else:
                    await send(ctx, f"⚠️ {result['reason']}", ephemeral=True)
                    
        except Exception as e:
            func.logger.error(f"Force sync failed: {e}")
            await send(ctx, f"❌ Sync failed: {str(e)}", ephemeral=True)
    
    @commands.command(name="guildsync")
    @commands.has_permissions(manage_guild=True)
    async def guildsync(self, ctx: commands.Context):
        """Sync slash commands to this server only (faster, avoids global rate limits)"""
        if not ctx.guild:
            return await send(ctx, "❌ This command can only be used in a server.", ephemeral=True)
        
        from sync_manager import guild_only_sync
        
        await send(ctx, "🔄 Syncing commands to this server...", ephemeral=True)
        
        try:
            result = await guild_only_sync(self.bot, ctx.guild.id)
            if result["synced"]:
                await send(ctx, f"✅ {result['reason']}", ephemeral=True)
            else:
                await send(ctx, f"⚠️ {result['reason']}", ephemeral=True)
        except Exception as e:
            func.logger.error(f"Guild sync failed: {e}")
            await send(ctx, f"❌ Sync failed: {str(e)}", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Settings(bot))
