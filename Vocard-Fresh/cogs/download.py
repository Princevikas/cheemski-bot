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
import asyncio
import os
import tempfile
import glob
import function as func

from discord import app_commands
from discord.ext import commands
from typing import Optional

# Try to import yt-dlp
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
    func.logger.info("yt-dlp is available for downloads")
except ImportError:
    YT_DLP_AVAILABLE = False
    func.logger.warning("yt-dlp not installed - download feature disabled")

class Download(commands.Cog):
    """Download currently playing songs as MP3."""
    
    # Track active downloads by URL to prevent concurrent downloads of same track
    _active_track_downloads = set()
    
    # Cheems/Doge GIFs
    DOGE_SUCCESS = "https://media.tenor.com/D-SlWEu_sDkAAAAd/dogs-doge.gif"
    CHEEMS_SAD = "https://media.tenor.com/a_oHg3CSkLcAAAPo/doge-dog.mp4"
    CHEEMS_LOADING = "https://media.tenor.com/JY8HkCI_W7oAAAAM/cheems-computer.gif"
    CHEEMS_WAIT = "https://media.tenor.com/Qv0rrO98fXYAAAAM/cheems-dog.gif"
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.download_dir = tempfile.gettempdir()
        func.logger.info(f"Download cog initialized. Temp dir: {self.download_dir}")

        
    def get_ydl_options(self, output_path: str) -> dict:
        """Get yt-dlp options for audio extraction."""
        return {
            'format': 'ba/b',  # best audio, fallback to best overall
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': False,  # Show output for debugging
            'verbose': True,  # Verbose logging
            'no_warnings': False,
            'noplaylist': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
    
    async def download_audio(self, url: str, title: str) -> Optional[str]:
        """Download audio from URL and return file path."""
        func.logger.info(f"[DOWNLOAD] Starting download for: {title}")
        func.logger.info(f"[DOWNLOAD] URL: {url}")
        
        if not YT_DLP_AVAILABLE:
            func.logger.error("[DOWNLOAD] yt-dlp not available!")
            return None
            
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        output_path = os.path.join(self.download_dir, f"{safe_title}")
        func.logger.info(f"[DOWNLOAD] Output path: {output_path}")
        
        ydl_opts = self.get_ydl_options(output_path)
        
        try:
            func.logger.info("[DOWNLOAD] Starting yt-dlp download...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._download(url, ydl_opts))
            
            # yt-dlp adds .mp3 extension
            mp3_path = f"{output_path}.mp3"
            func.logger.info(f"[DOWNLOAD] Checking for file: {mp3_path}")
            
            if os.path.exists(mp3_path):
                file_size = os.path.getsize(mp3_path)
                func.logger.info(f"[DOWNLOAD] SUCCESS! File size: {file_size / 1024 / 1024:.2f} MB")
                return mp3_path
            else:
                func.logger.error(f"[DOWNLOAD] File not found at: {mp3_path}")
                # Check for other extensions
                for ext in ['.m4a', '.webm', '.opus', '.ogg']:
                    alt_path = f"{output_path}{ext}"
                    if os.path.exists(alt_path):
                        func.logger.info(f"[DOWNLOAD] Found file with extension {ext}")
                
        except Exception as e:
            func.logger.error(f"[DOWNLOAD] Error: {type(e).__name__}: {e}")
            
        return None
    
    def _download(self, url: str, opts: dict):
        """Synchronous download function."""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                func.logger.info(f"[DOWNLOAD] yt-dlp extracting info...")
                info = ydl.extract_info(url, download=True)
                if info:
                    func.logger.info(f"[DOWNLOAD] Title: {info.get('title', 'Unknown')}")
                    func.logger.info(f"[DOWNLOAD] Duration: {info.get('duration', 0)}s")
        except Exception as e:
            func.logger.error(f"[DOWNLOAD] yt-dlp error: {e}")
            raise
    
    @commands.hybrid_command(name="download", aliases=["dl"])
    @app_commands.describe(query="URL or leave empty to download currently playing track")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def download(self, ctx: commands.Context, query: str = None):
        """Download the currently playing track as MP3."""
        func.logger.info(f"[DOWNLOAD CMD] Invoked by {ctx.author} in {ctx.guild}")
        
        if not YT_DLP_AVAILABLE:
            return await ctx.send(f"❌ Dowmload feamture is not availamble\n{self.CHEEMS_SAD}", ephemeral=True)
        
        # Get player and current track
        player = ctx.guild.voice_client if ctx.guild else None
        func.logger.info(f"[DOWNLOAD CMD] Player: {player}")
        
        if query:
            url = query
            title = "downloaded_track"
            duration = 0
            func.logger.info(f"[DOWNLOAD CMD] Using provided query: {query}")
        elif player and hasattr(player, 'current') and player.current:
            url = player.current.uri
            title = player.current.title
            duration = player.current.length
            func.logger.info(f"[DOWNLOAD CMD] Using current track: {title} (duration: {duration}ms)")
            
            # Warn if track is too long
            if duration > 600000:
                mins = duration // 60000
                return await ctx.send(
                    f"⚠️ **Tramck is too lomg** ({mins} min)\n"
                    f"At 128kbps, this would be ~{mins * 0.96:.0f}MB\n"
                    f"Cheems camnt handle this much 😢\n{self.CHEEMS_SAD}",
                    ephemeral=True
                )
        else:
            func.logger.warning("[DOWNLOAD CMD] No track playing and no query provided")
            return await ctx.send(f"❌ No tramck is curremtly playimg!\n{self.CHEEMS_SAD}", ephemeral=True)
        
        # Check if this track is already being downloaded
        if url in Download._active_track_downloads:
            func.logger.info(f"[DOWNLOAD CMD] Track already being downloaded: {url}")
            embed = discord.Embed(
                description="⏳ **This tramck is already being downloaded!**\nWait for it to finish, fren! 🐕",
                color=discord.Color.orange()
            )
            embed.set_image(url=self.CHEEMS_WAIT)
            return await ctx.send(embed=embed, ephemeral=True)
        
        # Check if it's a supported URL
        if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be', 'soundcloud.com']):
            func.logger.warning(f"[DOWNLOAD CMD] Unsupported URL: {url}")
            return await ctx.send(f"❌ Omly YouTube amd SoumdCloud URLs are supportmed\n{self.CHEEMS_SAD}", ephemeral=True)
        
        # Mark track as being downloaded
        Download._active_track_downloads.add(url)
        
        try:
            # Defer immediately
            func.logger.info("[DOWNLOAD CMD] Deferring response...")
            await ctx.defer()
            
            # Send starting download message with emoji
            start_embed = discord.Embed(
                title="📥 Dowmloading...",
                description=f"**{title[:60]}**\n\nCheems is workimg on it, fren! 🐕",
                color=0xffaa00
            )
            start_embed.set_image(url=self.CHEEMS_LOADING)
            start_msg = await ctx.send(embed=start_embed)

        
            # Download the audio
            file_path = await self.download_audio(url, title)
            
            if not file_path or not os.path.exists(file_path):
                func.logger.error("[DOWNLOAD CMD] Download failed - no file")
                error_embed = discord.Embed(
                    description="❌ Failmed to dowmload. Cheems is sad 😢",
                    color=discord.Color.red()
                )
                error_embed.set_image(url=self.CHEEMS_SAD)
                return await ctx.send(embed=error_embed)
            
            # Check file size
            file_size = os.path.getsize(file_path)
            func.logger.info(f"[DOWNLOAD CMD] File ready: {file_size / 1024 / 1024:.2f} MB")
            
            if file_size > 25 * 1024 * 1024:
                os.remove(file_path)
                error_embed = discord.Embed(
                    description="❌ File is too larmge (>25MB). Much big, very sad 😢",
                    color=discord.Color.red()
                )
                error_embed.set_image(url=self.CHEEMS_SAD)
                return await ctx.send(embed=error_embed)
            
            # Delete start message
            try:
                await start_msg.delete()
            except:
                pass
            
            # Send the file with Doge celebration (using embed to hide URL)
            func.logger.info("[DOWNLOAD CMD] Sending file to Discord...")
            file = discord.File(file_path, filename=f"{title[:50]}.mp3")
            
            embed = discord.Embed(
                title=f"🎵 {title[:80]}",
                description="Much music, very download, wow!\n*Powered by Cheemski Engine™ heuheuheuh* 🐕",
                color=0x00ff00
            )
            embed.set_image(url=self.DOGE_SUCCESS)
            embed.set_footer(text="heuheuheuh")
            
            await ctx.send(embed=embed, file=file)
            func.logger.info("[DOWNLOAD CMD] File sent successfully!")
            
            # Cleanup
            try:
                os.remove(file_path)
                func.logger.info("[DOWNLOAD CMD] Temp file cleaned up")
            except:
                pass
                
        except Exception as e:
            func.logger.error(f"[DOWNLOAD CMD] Exception: {type(e).__name__}: {e}")
            try:
                await start_msg.delete()
            except:
                pass
            error_embed = discord.Embed(
                description="❌ Error: Dowmload failmed. Cheems tried his best 😢",
                color=discord.Color.red()
            )
            error_embed.set_image(url=self.CHEEMS_SAD)
            await ctx.send(embed=error_embed)
        finally:
            # Always remove track from active downloads
            Download._active_track_downloads.discard(url)
            
    @download.error
    async def download_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                description=f"⏳ Waim {error.retry_after:.0f}s before dowmloading agaim, fren",
                color=discord.Color.orange()
            )
            embed.set_image(url=self.CHEEMS_WAIT)
            await ctx.send(embed=embed, ephemeral=True)
        else:
            func.logger.error(f"[DOWNLOAD ERROR] {type(error).__name__}: {error}")
    
    @commands.command(name="purgelogs", aliases=["clearlogs"])
    @commands.has_permissions(administrator=True)
    async def purge_logs(self, ctx: commands.Context):
        """Purge/clear the bot log files. Admin only."""
        log_dir = os.path.join(func.ROOT_DIR, "logs")
        
        if not os.path.exists(log_dir):
            return await ctx.send("❌ No logs directory found!", ephemeral=True)
        
        log_files = glob.glob(os.path.join(log_dir, "*.log"))
        
        if not log_files:
            return await ctx.send("❌ No log files found!", ephemeral=True)
        
        cleared_count = 0
        for log_file in log_files:
            try:
                # Clear the file content instead of deleting
                with open(log_file, 'w') as f:
                    f.write("")
                cleared_count += 1
            except Exception as e:
                func.logger.error(f"Failed to clear {log_file}: {e}")
        
        await ctx.send(f"✅ Cleared {cleared_count} log file(s)! 🐕", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Download(bot))
