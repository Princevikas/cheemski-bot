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

import discord, voicelink, re

from io import StringIO
from discord import app_commands
from discord.ext import commands
from function import (
    settings,
    send,
    time as ctime,
    format_time,
    get_source,
    get_user,
    get_lang,
    truncate_string,
    cooldown_check,
    get_aliases,
    logger
)

from voicelink import SearchType, LoopType
from addons import LYRICS_PLATFORMS
from views import SearchView, ListView, LinkView, LyricsView, HelpView
from validators import url

async def nowplay(ctx: commands.Context, player: voicelink.Player):
    track = player.current
    if not track:
        return await send(ctx, 'noTrackPlaying', ephemeral=True)

    texts = await get_lang(ctx.guild.id, "nowplayingDesc", "nowplayingField", "nowplayingLink")
    upnext = "\n".join(f"`{index}.` `[{track.formatted_length}]` [{truncate_string(track.title)}]({track.uri})" for index, track in enumerate(player.queue.tracks()[:2], start=2))
    
    embed = discord.Embed(description=texts[0].format(track.title), color=settings.embed_color)
    embed.set_author(
        name=track.requester.display_name,
        icon_url=track.requester.display_avatar.url
    )
    embed.set_thumbnail(url=track.thumbnail)

    if upnext:
        embed.add_field(name=texts[1], value=upnext)

    # Progress bar with ▰▱ style - shows passed / remaining
    if track.length > 0:
        progress = player.position / track.length
        filled = round(progress * 10)
        pbar = "▰" * filled + "▱" * (10 - filled)
        remaining = track.length - player.position
        remaining_str = ctime(remaining) if remaining > 0 else "00:00"
    else:
        pbar = "▱" * 10
        remaining_str = "∞"
    
    icon = "🔴" if track.is_stream else ("⏸️" if player.is_paused else "▶️")
    embed.add_field(name="\u2800", value=f"{icon} {pbar} `{ctime(player.position)}` / `-{remaining_str}`", inline=False)

    # Import and use InteractiveController to show full controls
    from views.controller import InteractiveController
    return await send(ctx, embed, view=InteractiveController(player))

class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.description = "This category is available to anyone on this server. Voting is required in certain commands."
        self.ctx_menu = app_commands.ContextMenu(
            name="play",
            callback=self._play
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def help_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        return [app_commands.Choice(name=c.capitalize(), value=c) for c in self.bot.cogs if c not in ["Nodes", "Task"] and current in c]

    async def play_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        if voicelink.pool.URL_REGEX.match(current):
            return []

        if current:
            node = voicelink.NodePool.get_node()
            if not node:
                return []
            
            tracks: list[voicelink.Track] = await node.get_tracks(current, requester=interaction.user)
            if not tracks:
                return []
            
            if isinstance(tracks, voicelink.Playlist):
                tracks = tracks.tracks

            return [app_commands.Choice(name=truncate_string(f"🎵 {track.author} - {track.title}", 100), value=truncate_string(f"{track.author} - {track.title}", 100)) for track in tracks]
        
        history = {track["identifier"]: track for track_id in reversed(await get_user(interaction.user.id, "history")) if (track := voicelink.decode(track_id))["uri"]}
        return [app_commands.Choice(name=truncate_string(f"🕒 {track['author']} - {track['title']}", 100), value=track['uri']) for track in history.values() if len(track['uri']) <= 100][:25]
            
                
    @commands.hybrid_command(name="play", aliases=get_aliases("play"))
    @app_commands.describe(
        query="Input a query or a searchable link.",
        start="Specify a time you would like to start, e.g. 1:00",
        end="Specify a time you would like to end, e.g. 4:00"
    )
    @app_commands.autocomplete(query=play_autocomplete)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def play(self, ctx: commands.Context, *, query: str, start: str = "0", end: str = "0") -> None:
        "Loads your input and added it to the queue."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            player = await voicelink.connect_channel(ctx)

        if not player.is_user_join(ctx.author):
            return await send(ctx, "notInChannel", ctx.author.mention, player.channel.mention, ephemeral=True)

        if ctx.interaction:
            await ctx.interaction.response.defer()

        tracks = await player.get_tracks(query, requester=ctx.author)
        if not tracks:
            return await send(ctx, "noTrackFound")

        try:
            if isinstance(tracks, voicelink.Playlist):
                index = await player.add_track(tracks.tracks, start_time=format_time(start), end_time=format_time(end))
                await send(ctx, "playlistLoad", tracks.name, index)
            else:
                position = await player.add_track(tracks[0], start_time=format_time(start), end_time=format_time(end))
                texts = await get_lang(ctx.guild.id, "live", "trackLoad_pos", "trackLoad")

                stream_content = f"`{texts[0]}`" if tracks[0].is_stream else ""
                additional_content = texts[1] if position >= 1 and player.is_playing else texts[2]

                await send(
                    ctx,
                    stream_content + additional_content,
                    tracks[0].title, tracks[0].uri, tracks[0].author, tracks[0].formatted_length,
                    position if position >= 1 and player.is_playing else None
                )
        finally:
            if not player.is_playing:
                await player.do_next()
    
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def _play(self, interaction: discord.Interaction, message: discord.Message):
        query = ""

        if message.content:
            url = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", message.content)
            if url:
                query = url[0]

        elif message.attachments:
            query = message.attachments[0].url

        if not query:
            return await send(interaction, "noPlaySource", ephemeral=True)

        player: voicelink.Player = interaction.guild.voice_client
        if not player:
            player = await voicelink.connect_channel(interaction)

        if not player.is_user_join(interaction.user):
            return await send(interaction, "notInChannel", interaction.user.mention, player.channel.mention, ephemeral=True)

        await interaction.response.defer()
        tracks = await player.get_tracks(query, requester=interaction.user)
        if not tracks:
            return await send(interaction, "noTrackFound")

        try:
            if isinstance(tracks, voicelink.Playlist):
                index = await player.add_track(tracks.tracks)
                await send(interaction, "playlistLoad", tracks.name, index)
            else:
                position = await player.add_track(tracks[0])
                texts = await get_lang(interaction.guild.id, "live", "trackLoad_pos", "trackLoad")

                stream_content = f"`{texts[0]}`" if tracks[0].is_stream else ""
                additional_content = texts[1] if position >= 1 and player.is_playing else texts[2]

                await send(
                    interaction,
                    stream_content + additional_content,
                    tracks[0].title, tracks[0].uri, tracks[0].author, tracks[0].formatted_length,
                    position if position >= 1 and player.is_playing else None
                )
        finally:
            if not player.is_playing:
                await player.do_next()


    @commands.hybrid_command(name="playnow", aliases=get_aliases("forceplay"))
    @app_commands.describe(
        query="Input a query or a searchable link.",
        start="Specify a time you would like to start, e.g. 1:00",
        end="Specify a time you would like to end, e.g. 4:00"
    )
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def playnow(self, ctx: commands.Context, *, query: str, start: str = "0", end: str = "0"):
        "Play a song immediately, skipping the queue."
        # Defer first to prevent interaction timeout
        if ctx.interaction:
            await ctx.interaction.response.defer()
            
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            player = await voicelink.connect_channel(ctx)

        if not player.is_privileged(ctx.author):
            return await send(ctx, "missingFunctionPerm", ephemeral=True)
            
        tracks = await player.get_tracks(query, requester=ctx.author)
        if not tracks:
            return await send(ctx, "noTrackFound")
        
        try:
            if isinstance(tracks, voicelink.Playlist):
                index = await player.add_track(tracks.tracks, start_time=format_time(start), end_time=format_time(end), at_front=True)
                await send(ctx, "playlistLoad", tracks.name, index)
            else:
                texts = await get_lang(ctx.guild.id, "live", "trackLoad")
                await player.add_track(tracks[0], start_time=format_time(start), end_time=format_time(end), at_front=True)

                stream_content = f"`{texts[0]}`" if tracks[0].is_stream else ""

                await send(
                    ctx,
                    stream_content + texts[1],
                    tracks[0].title, tracks[0].uri, tracks[0].author, tracks[0].formatted_length,
                )
        finally:
            if player.queue._repeat.mode == voicelink.LoopType.TRACK:
                await player.set_repeat(voicelink.LoopType.OFF)
                
            await player.stop() if player.is_playing else await player.do_next()

    @commands.hybrid_command(name="pause", aliases=get_aliases("pause"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def pause(self, ctx: commands.Context):
        "Pause the music."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if player.is_paused:
            return await send(ctx, "pauseError", ephemeral=True)

        if not player.is_privileged(ctx.author):
            if ctx.author in player.pause_votes:
                return await send(ctx, "voted", ephemeral=True)
            
            player.pause_votes.add(ctx.author)
            if len(player.pause_votes) < (required := player.required()):
                return await send(ctx, "pauseVote", ctx.author, len(player.pause_votes), required)

        await player.set_pause(True, ctx.author)
        await send(ctx, "paused", ctx.author)

    @commands.hybrid_command(name="resume", aliases=get_aliases("resume"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def resume(self, ctx: commands.Context):
        "Resume the music."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_paused:
            return await send(ctx, "resumeError")

        if not player.is_privileged(ctx.author):
            if ctx.author in player.resume_votes:
                return await send(ctx, "voted", ephemeral=True)
            
            player.resume_votes.add(ctx.author)
            if len(player.resume_votes) < (required := player.required()):
                return await send(ctx, "resumeVote", ctx.author, len(player.resume_votes), required)

        await player.set_pause(False, ctx.author)
        await send(ctx, "resumed", ctx.author)

    @commands.hybrid_command(name="skip", aliases=get_aliases("skip"))
    @app_commands.describe(index="Enter a index that you want to skip to.")
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def skip(self, ctx: commands.Context, index: int = 0):
        "Skips to the next song or skips to the specified song."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.node._available:
            return await send(ctx, "nodeReconnect")
        
        if not player.is_playing:
            return await send(ctx, "skipError", ephemeral=True)

        if not player.is_privileged(ctx.author):
            if ctx.author == player.current.requester:
                pass
            elif ctx.author in player.skip_votes:
                return await send(ctx, "voted", ephemeral=True)
            else:
                player.skip_votes.add(ctx.author)
                if len(player.skip_votes) < (required := player.required()):
                    return await send(ctx, "skipVote", ctx.author, len(player.skip_votes), required)

        if index:
            player.queue.skipto(index)

        await send(ctx, "skipped", ctx.author)
        if player.queue._repeat.mode == voicelink.LoopType.TRACK:
            await player.set_repeat(voicelink.LoopType.OFF)
            
        await player.stop()

    @commands.hybrid_command(name="back", aliases=get_aliases("back"))
    @app_commands.describe(index="Enter a index that you want to skip back to.")
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def back(self, ctx: commands.Context, index: int = 1):
        "Skips back to the previous song or skips to the specified previous song."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.node._available:
            return await send(ctx, "nodeReconnectode")
        
        if not player.is_privileged(ctx.author):
            if ctx.author in player.previous_votes:
                return await send(ctx, "voted", ephemeral=True)
            
            player.previous_votes.add(ctx.author)
            if len(player.previous_votes) < (required := player.required()):
                return await send(ctx, "backVote", ctx.author, len(player.previous_votes), required)

        if not player.is_playing:
            player.queue.backto(index)
            await player.do_next()
        else:
            player.queue.backto(index + 1)
            await player.stop()

        await send(ctx, "backed", ctx.author)
        if player.queue._repeat.mode == voicelink.LoopType.TRACK:
            await player.set_repeat(voicelink.LoopType.OFF)

    @commands.hybrid_command(name="seek", aliases=get_aliases("seek"))
    @app_commands.describe(position="Input position. Exmaple: 1:20.")
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def seek(self, ctx: commands.Context, position: str):
        "Change the player position."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_privileged(ctx.author):
            return await send(ctx, "missingPosPerm", ephemeral=True)

        if not player.current or player.position == 0:
            return await send(ctx, "noTrackPlaying", ephemeral=True)

        if not (num := format_time(position)):
            return await send(ctx, "timeFormatError", ephemeral=True)

        await player.seek(num, ctx.author)
        await send(ctx, "seek", position)

    @commands.hybrid_group(
        name="queue", 
        aliases=get_aliases("queue"),
        fallback="list",
        invoke_without_command=True
    )
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def queue(self, ctx: commands.Context):
        "Display the players queue songs in your queue."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_user_join(ctx.author):
            return await send(ctx, "notInChannel", ctx.author.mention, player.channel.mention, ephemeral=True)

        if player.queue.is_empty:
            return await nowplay(ctx, player)
        view = ListView(player=player, author=ctx.author)
        view.response = await send(ctx, await view.build_embed(), view=view)

    @queue.command(name="export", aliases=get_aliases("export"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def export(self, ctx: commands.Context):
        "Exports the entire queue to a text file"
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)
        
        if not player.is_user_join(ctx.author):
            return await send(ctx, "notInChannel", ctx.author.mention, player.channel.mention, ephemeral=True)
        
        if player.queue.is_empty and not player.current:
            return await send(ctx, "noTrackPlaying", ephemeral=True)

        await ctx.defer()

        tracks = player.queue.tracks(True)
        temp = ""
        raw = "----------->Raw Info<-----------\n"

        total_length = 0
        for index, track in enumerate(tracks, start=1):
            temp += f"{index}. {track.title} [{ctime(track.length)}]\n"
            raw += track.track_id
            if index != len(tracks):
                raw += ","
            total_length += track.length

        temp = "!Remember do not change this file!\n------------->Info<-------------\nGuild: {} ({})\nRequester: {} ({})\nTracks: {} - {}\n------------>Tracks<------------\n".format(
            ctx.guild.name, ctx.guild.id,
            ctx.author.display_name, ctx.author.id,
            len(tracks), ctime(total_length)
        ) + temp
        temp += raw

        await ctx.reply(content="", file=discord.File(StringIO(temp), filename=f"{ctx.guild.id}_Full_Queue.txt"))

    @queue.command(name="import", aliases=get_aliases("import"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def _import(self, ctx: commands.Context, attachment: discord.Attachment):
        "Imports the text file and adds the track to the current queue."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            player = await voicelink.connect_channel(ctx)

        if not player.is_user_join(ctx.author):
            return await send(ctx, "notInChannel", ctx.author.mention, player.channel.mention, ephemeral=True)

        try:
            bytes = await attachment.read()
            track_ids = bytes.split(b"\n")[-1]
            track_ids = track_ids.decode().split(",")
            
            tracks = [voicelink.Track(track_id=track_id, info=voicelink.decode(track_id), requester=ctx.author) for track_id in track_ids]
            if not tracks:
                return await send(ctx, "noTrackFound")

            index = await player.add_track(tracks)
            await send(ctx, "playlistLoad", attachment.filename, index)
        except Exception as e:
            logger.error("error", exc_info=e)
            raise e

        finally:
            if not player.is_playing:
                await player.do_next()

    @commands.hybrid_command(name="leave", aliases=get_aliases("leave"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def leave(self, ctx: commands.Context):
        "Disconnects the bot from your voice channel and chears the queue."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_privileged(ctx.author):
            if ctx.author in player.stop_votes:
                return await send(ctx, "voted", ephemeral=True)
            else:
                player.stop_votes.add(ctx.author)
                if len(player.stop_votes) >= (required := player.required(leave=True)):
                    pass
                else:
                    return await send(ctx, "leaveVote", ctx.author, len(player.stop_votes), required)

        await send(ctx, "left", ctx.author)
        await player.teardown()

    @commands.hybrid_command(name="nowplaying", aliases=get_aliases("nowplaying"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def nowplaying(self, ctx: commands.Context):
        "Shows details of the current track."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_user_join(ctx.author):
            return await send(ctx, "notInChannel", ctx.author.mention, player.channel.mention, ephemeral=True)

        await nowplay(ctx, player)

    @commands.hybrid_command(name="loop", aliases=get_aliases("loop"))
    @app_commands.describe(mode="Choose a looping mode.")
    @app_commands.choices(mode=[
        app_commands.Choice(name=loop_type.name.title(), value=loop_type.name)
        for loop_type in LoopType
    ])
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def loop(self, ctx: commands.Context, mode: str):
        "Changes Loop mode."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_privileged(ctx.author):
            return await send(ctx, "missingModePerm", ephemeral=True)

        await player.set_repeat(LoopType[mode] if mode in LoopType.__members__ else LoopType.OFF, ctx.author)
        await send(ctx, "repeat", mode.capitalize())

    @commands.hybrid_command(name="clear", aliases=get_aliases("clear"))
    @app_commands.describe(queue="Choose a queue that you want to clear.")
    @app_commands.choices(queue=[
        app_commands.Choice(name='Queue', value='queue'),
        app_commands.Choice(name='History', value='history')
    ])
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def clear(self, ctx: commands.Context, queue: str = "queue"):
        "Remove all the tracks in your queue or history queue."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_privileged(ctx.author):
            return await send(ctx, "missingQueuePerm", ephemeral=True)

        await player.clear_queue(queue, ctx.author)
        await send(ctx, "cleared", queue.capitalize())

    @commands.hybrid_command(name="remove", aliases=get_aliases("remove"))
    @app_commands.describe(
        position1="Input a position from the queue to be removed.",
        position2="Set the range of the queue to be removed.",
        member="Remove tracks requested by a specific member."
    )
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def remove(self, ctx: commands.Context, position1: int, position2: int = None, member: discord.Member = None):
        "Removes specified track or a range of tracks from the queue."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_privileged(ctx.author):
            return await send(ctx, "missingQueuePerm", ephemeral=True)

        removed_tracks = await player.remove_track(position1, position2, remove_target=member, requester=ctx.author)
        await send(ctx, "removed", len(removed_tracks.keys()))


    @commands.hybrid_command(name="shuffle", aliases=get_aliases("shuffle"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def shuffle(self, ctx: commands.Context):
        "Randomizes the tracks in the queue."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_privileged(ctx.author):
            if ctx.author in player.shuffle_votes:
                return await send(ctx, "voted", ephemeral=True)
            
            player.shuffle_votes.add(ctx.author)
            if len(player.shuffle_votes) < (required := player.required()):
                return await send(ctx, "shuffleVote", ctx.author, len(player.shuffle_votes), required)
        
        await player.shuffle("queue", ctx.author)
        await send(ctx, "shuffled")


    @commands.hybrid_command(name="lyrics", aliases=get_aliases("lyrics"))
    @app_commands.describe(title="Searches for your query and displays the returned lyrics.")
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def lyrics(self, ctx: commands.Context, title: str = "", artist: str = ""):
        "Displays lyrics for the playing track."
        
        # DEFER IMMEDIATELY to prevent timeout
        await ctx.defer()
        
        if not title:
            player: voicelink.Player = ctx.guild.voice_client
            if not player or not player.is_playing:
                return await send(ctx, "noTrackPlaying", ephemeral=True)
            
            title = player.current.title
            artist = player.current.author
       
        # Import lyrics providers
        from addons.lyrics import LYRICS_PLATFORMS
        
        # Define fallback order (try all sources)
        fallback_order = ["lrclib", "genius", "lyrist", "musixmatch", "a_zlyrics"]
        
        lyrics_result = None
        successful_platform = None
        
        # Try each lyrics platform in order until one succeeds
        for platform_name in fallback_order:
            try:
                lyrics_platform = LYRICS_PLATFORMS.get(platform_name)
                if not lyrics_platform:
                    continue
                
                lyrics_result = await lyrics_platform().get_lyrics(title, artist)
                if lyrics_result:
                    successful_platform = platform_name
                    break
            except Exception as e:
                # Log error but continue to next platform
                logger.debug(f"Lyrics platform {platform_name} failed: {e}")
                continue
        
        # If all platforms failed, send sad Cheems GIF
        if not lyrics_result:
            import aiohttp
            tenor_api_key = getattr(settings, 'tenor_key', None)
            
            if tenor_api_key:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://tenor.googleapis.com/v2/search?q=sad%20cheems&key={tenor_api_key}&client_key=vocard&limit=1"
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data.get("results"):
                                    gif_url = data["results"][0]["media_formats"]["gif"]["url"]
                                    
                                    embed = discord.Embed(
                                        title="😢 No Lyrics Found",
                                        description=f"Couldn't find lyrics for **{title}** by **{artist}**\n\nTried all sources: LrcLib, Genius, Lyrist, MusixMatch, A-ZLyrics",
                                        color=settings.embed_color
                                    )
                                    embed.set_image(url=gif_url)
                                    return await send(ctx, embed)
                except:
                    pass
            
            # Fallback if GIF fails or Tenor key not configured
            return await send(ctx, "lyricsNotFound", ephemeral=True)
        
        # Display lyrics with view
        from views.lyrics import LyricsView
        view = LyricsView(
            name=f"{title} (via {successful_platform.title()})", 
            source={_: re.findall(r'.*\n(?:.*\n){,22}', v or "") for _, v in lyrics_result.items()}, 
            author=ctx.author
        )
        view.response = await send(ctx, view.build_embed(), view=view)


    @commands.hybrid_command(name="autoplay", aliases=get_aliases("autoplay"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def autoplay(self, ctx: commands.Context):
        "Toggles autoplay mode, it will automatically queue the best songs to play."
        player: voicelink.Player = ctx.guild.voice_client
        if not player:
            return await send(ctx, "noPlayer", ephemeral=True)

        if not player.is_privileged(ctx.author):
            return await send(ctx, "missingAutoPlayPerm", ephemeral=True)

        check = not player.settings.get("autoplay", False)
        player.settings['autoplay'] = check
        await send(ctx, "autoplay", await get_lang(ctx.guild.id, "enabled" if check else "disabled"))

        if not player.is_playing:
            await player.do_next()
        
        if player.is_ipc_connected:
            await player.send_ws({"op": "toggleAutoplay", "status": check})

    @commands.hybrid_command(name="help", aliases=get_aliases("help"))
    @app_commands.autocomplete(category=help_autocomplete)
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def help(self, ctx: commands.Context, category: str = "News") -> None:
        "Lists all the commands in Vocard."
        if category not in self.bot.cogs:
            category = "News"
        view = HelpView(self.bot, ctx.author)
        embed = view.build_embed(category)
        view.response = await send(ctx, embed, view=view)

    @commands.command(name="ping", aliases=get_aliases("ping"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def ping(self, ctx: commands.Context):
        "Test if the bot is alive, and see the delay between your commands and my response."
        player: voicelink.Player = ctx.guild.voice_client

        value = await get_lang(ctx.guild.id, "pingTitle1", "pingField1", "pingTitle2", "pingField2")
        
        embed = discord.Embed(color=settings.embed_color)
        embed.add_field(
            name=value[0],
            value=value[1].format(
                "0", "0", self.bot.latency, '😭' if self.bot.latency > 5 else ('😨' if self.bot.latency > 1 else '👌'), "St Louis, MO, United States"
        ))

        if player:
            embed.add_field(
                name=value[2],
                value=value[3].format(
                    player.node._identifier, player.ping, player.node.player_count, player.channel.rtc_region),
                    inline=False
            )

        await send(ctx, embed)

    @commands.hybrid_command(name="dashboard", aliases=get_aliases("dashboard"))
    @commands.dynamic_cooldown(cooldown_check, commands.BucketType.guild)
    async def dashboard(self, ctx: commands.Context):
        """Get the link to the online dashboard to control the bot."""
        embed = discord.Embed(
            title="🎛️ Cheemski Dashboard",
            description="Control your music from anywhere with our web dashboard!",
            color=settings.embed_color
        )
        embed.add_field(
            name="🔗 Dashboard Link",
            value="**[Click here to open the Dashboard](https://cheemski.up.railway.app/)**",
            inline=False
        )
        embed.add_field(
            name="✨ Features",
            value="• Control music playback\n• Manage queue\n• Change settings\n• View now playing",
            inline=False
        )
        embed.set_footer(text="Login with Discord to get started!")
        
        await send(ctx, embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Basic(bot))