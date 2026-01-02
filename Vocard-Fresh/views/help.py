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
from discord.ext import commands

import function as func

class HelpDropdown(discord.ui.Select):
    def __init__(self, categories:list):
        self.view: HelpView

        super().__init__(
            placeholder="Select Category!",
            min_values=1, max_values=1,
            options=[
                discord.SelectOption(emoji="🆕", label="News", description="View new updates of Cheemski."),
                discord.SelectOption(emoji="🕹️", label="Tutorial", description="How to use Cheemski."),
            ] + [
                discord.SelectOption(emoji=emoji, label=f"{category} Commands", description=f"This is {category.lower()} Category.")
                for category, emoji in zip(categories, ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"])
            ],
            custom_id="select"
        )
    
    async def callback(self, interaction: discord.Interaction) -> None:
        embed = self.view.build_embed(self.values[0].split(" ")[0])
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, author: discord.Member) -> None:
        super().__init__(timeout=60)

        self.author: discord.Member = author
        self.bot: commands.Bot = bot
        self.response: discord.Message = None
        self.categories: list[str] = [ name.capitalize() for name, cog in bot.cogs.items() if len([c for c in cog.walk_commands()]) ]

        # Add dropdown
        self.add_item(HelpDropdown(self.categories))
        
        # Add URL link buttons (these show as clickable buttons!)
        # Invite Link
        invite_url = f"https://discord.com/oauth2/authorize?client_id={func.settings.client_id}&permissions=8&integration_type=0&scope=bot"
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="➕ Add Me",
            url=invite_url,
            row=1
        ))
        
        # Support Server (only if configured)
        support_url = getattr(func.settings, 'support_server', None)
        if support_url:
            self.add_item(discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="🆘 Support",
                url=support_url,
                row=1
            ))
        
        # Dashboard (if IPC enabled)
        if func.settings.ipc_client.get("enable", False):
            dashboard_host = func.settings.ipc_client.get("host", "127.0.0.1")
            dashboard_port = func.settings.ipc_client.get("port", 8000)
            dashboard_url = f"https://{dashboard_host}" if dashboard_host != "127.0.0.1" else f"http://{dashboard_host}:{dashboard_port}"
            self.add_item(discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="🎛️ Dashboard",
                url=dashboard_url,
                row=1
            ))
    
    async def on_error(self, error, item, interaction) -> None:
        return

    async def on_timeout(self) -> None:
        for child in self.children:
            if child.custom_id == "select":
                child.disabled = True
        try:
            await self.response.edit(view=self)
        except:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> None:
        return interaction.user == self.author

    def build_embed(self, category: str) -> discord.Embed:
        category = category.lower()
        if category == "news":
            embed = discord.Embed(
                title="🐕 Cheemski - The Ultimate Music Bot",
                description=(
                    "**Much music, very wow!** Cheemski is a feature-rich Discord music bot "
                    "with a unique Cheems personality, bringing joy and high-quality audio to your server!\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=func.settings.embed_color
            )
            
            # Features
            embed.add_field(
                name="🎵 Music Features",
                value=(
                    "• **Multi-Platform** - YouTube, Spotify, SoundCloud, Twitch & more\n"
                    "• **High Quality Audio** - Powered by Lavalink\n"
                    "• **Smart Queue** - Auto-play, shuffle, repeat modes\n"
                    "• **Lyrics** - Built-in lyrics from multiple sources\n"
                    "• **Effects** - Bass boost, nightcore, and more\n"
                    "• **Playlists** - Save favorites, share with friends"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔴 Spotify Sync (LIVE)",
                value=(
                    "• `/sp sync @user` - Sync with someone's Spotify!\n"
                    "• Real-time track following\n"
                    "• Auto-seek to match position"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🐕 Cheems Mode",
                value=(
                    "• All responses in Cheems speak!\n"
                    "• Fun commands: `/bonk`, `/pat`, `/hug`\n"
                    "• Hilarious GIF reactions"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🎛️ Web Dashboard",
                value=(
                    "• Control music from browser\n"
                    "• Manage playlists & settings\n"
                    "• Beautiful mobile-friendly UI"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🚀 Quick Start",
                value="```1. Join a voice channel\n2. Use /play <song name or URL>\n3. Enjoy the music! 🎶```",
                inline=False
            )
            
            # Prefix-only commands note
            embed.add_field(
                name="⚠️ Prefix Commands (use ! instead of /)",
                value=(
                    "Some commands use `!` prefix instead of `/`:\n"
                    "`!akistats` `!akilb` `!akiach`\n"
                    "`!kanye` `!urban` `!chuck`"
                ),
                inline=False
            )
            
            embed.add_field(
                name=f"📚 Categories [{2 + len(self.categories)}]",
                value="```" + " • ".join(['News', 'Tutorial'] + self.categories) + "```",
                inline=False
            )
            
            embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else None)
            embed.set_footer(text="heuheuheuh 🐕 | Use the dropdown to explore commands!")
            
            return embed

        embed = discord.Embed(title=f"Category: {category.capitalize()}", color=func.settings.embed_color)
        embed.add_field(name=f"Categories: [{2 + len(self.categories)}]", value="```py\n" + "\n".join(("👉 " if c == category.capitalize() else f"{i}. ") + c for i, c in enumerate(['News', 'Tutorial'] + self.categories, start=1)) + "```", inline=True)

        if category == 'tutorial':
            embed.description = "How to use Cheemski? Some simple commands you should know!"
            embed.set_image(url="https://cdn.discordapp.com/attachments/674788144931012638/917656288899514388/final_61aef3aa7836890135c6010c_669380.gif")
        else:
            cog = [c for _, c in self.bot.cogs.items() if _.lower() == category][0]

            commands = [command for command in cog.walk_commands()]
            embed.description = cog.description
            embed.add_field(
                name=f"{category} Commands: [{len(commands)}]",
                value="```{}```".format("".join(f"/{command.qualified_name}\n" for command in commands if not command.qualified_name == cog.qualified_name))
            )

        return embed