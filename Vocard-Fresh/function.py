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

import discord, json, os, copy, logging, re, random

from discord.ext import commands
from time import strptime
from addons import Settings

from typing import (
    Optional,
    Union,
    Dict,
    Any
)

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

if not os.path.exists(os.path.join(ROOT_DIR, "settings.json")):
    raise Exception("Settings file not set!")

#--------------- Cache Var ---------------
settings: Settings
logger: logging.Logger = logging.getLogger("vocard")

MONGO_DB: AsyncIOMotorClient = None
SETTINGS_DB: AsyncIOMotorCollection = None
USERS_DB: AsyncIOMotorCollection = None

LANGS: dict[str, dict[str, str]] = {} #Stores all the languages in ./langs
LOCAL_LANGS: dict[str, dict[str, str]] = {} #Stores all the localization languages in ./local_langs
SETTINGS_BUFFER: dict[int, dict[str, Any]] = {} #Cache guild language
USERS_BUFFER: dict[str, dict] = {}

MISSING_TRANSLATOR: dict[str, list[str]] = {}

USER_BASE: dict[str, Any] = {
    'playlist': {
        '200': {
            'tracks':[],
            'perms': {'read': [], 'write':[], 'remove': []},
            'name':'Favourite',
            'type':'playlist'
        }
    },
    'history': [],
    'inbox':[]
}

ALLOWED_MENTIONS = discord.AllowedMentions().none()
LAST_SESSION_FILE_NAME = "last-session.json"

#-------------- Vocard Classes --------------
class TempCtx():
    def __init__(self, author: discord.Member, channel: discord.VoiceChannel) -> None:
        self.author: discord.Member = author
        self.channel: discord.VoiceChannel = channel
        self.guild: discord.Guild = channel.guild

#-------------- Vocard Functions --------------
def open_json(path: str) -> dict:
    try:
        with open(os.path.join(ROOT_DIR, path), encoding="utf8") as json_file:
            return json.load(json_file)
    except:
        return {}

def update_json(path: str, new_data: dict) -> None:
    data = open_json(path)
    if not data:
        data = new_data
    else:
        data.update(new_data)

    with open(os.path.join(ROOT_DIR, path), "w") as json_file:
        json.dump(data, json_file, indent=4)

def langs_setup() -> None:
    for language in os.listdir(os.path.join(ROOT_DIR, "langs")):
        if language.endswith('.json'):
            LANGS[language[:-5]] = {}
    
    for language in os.listdir(os.path.join(ROOT_DIR, "local_langs")):
        if language.endswith('.json'):
            LOCAL_LANGS[language[:-5]] = open_json(os.path.join("local_langs", language))

    return

def time(millis: int) -> str:
    seconds = (millis // 1000) % 60
    minutes = (millis // (1000 * 60)) % 60
    hours = (millis // (1000 * 60 * 60)) % 24
    days = millis // (1000 * 60 * 60 * 24)

    if days > 0:
        return "%d days, %02d:%02d:%02d" % (days, hours, minutes, seconds)
    elif hours > 0:
        return "%d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)

def format_time(number:str) -> int:
    try:
        try:
            num = strptime(number, '%M:%S')
        except ValueError:
            try:
                num = strptime(number, '%S')
            except ValueError:
                num = strptime(number, '%H:%M:%S')
    except:
        return 0
    
    return (int(num.tm_hour) * 3600 + int(num.tm_min) * 60 + int(num.tm_sec)) * 1000

def get_source(source: str, type: str) -> str:
    source_settings: dict[str, str] = settings.sources_settings.get(source.lower().replace(" ", ""), settings.sources_settings.get("others"))
    return source_settings.get(type)

def cooldown_check(ctx: commands.Context) -> Optional[commands.Cooldown]:
    if ctx.author.id in settings.bot_access_user:
        return None
    cooldown = settings.cooldowns_settings.get(f"{ctx.command.parent.qualified_name} {ctx.command.name}" if ctx.command.parent else ctx.command.name)
    if not cooldown:
        return None
    return commands.Cooldown(cooldown[0], cooldown[1])

def get_aliases(name: str) -> list:
    return settings.aliases_settings.get(name, [])

def check_roles() -> tuple[str, int, int]:
    return 'Normal', 5, 500

def truncate_string(text: str, length: int = 40) -> str:
    return text[:length - 3] + "..." if len(text) > length else text
    
def get_lang_non_async(guild_id: int, *keys) -> Union[list[str], str]:
    settings = SETTINGS_BUFFER.get(guild_id, {})
    lang = settings.get("lang", "EN")
    if lang in LANGS and not LANGS[lang]:
        LANGS[lang] = open_json(os.path.join("langs", f"{lang}.json"))

    if len(keys) == 1:
        return LANGS.get(lang, {}).get(keys[0], "Not found!")
    return [LANGS.get(lang, {}).get(key, "Not found!") for key in keys]

def format_bytes(bytes: int, unit: bool = False):
    if bytes <= 1_000_000_000:
        return f"{bytes / (1024 ** 2):.1f}" + ("MB" if unit else "")
    
    else:
        return f"{bytes / (1024 ** 3):.1f}" + ("GB" if unit else "")

#-------------- Cheems Language Processor --------------
# Word replacements for Cheems speak
CHEEMS_REPLACEMENTS = {
    'the': 'teh', 'you': 'yu', 'your': 'yur', 'are': 'r', 'have': 'hav',
    'with': 'wif', 'this': 'dis', 'that': 'dat', 'what': 'wut', 'when': 'whem',
    'because': 'cuz', 'please': 'pls', 'thanks': 'thamks', 'sorry': 'sowwy',
    'hello': 'hemlo', 'friend': 'fren', 'friends': 'frens', 'brother': 'brudder',
    'something': 'somethimg', 'nothing': 'nothimg', 'everything': 'everythimg',
    'anyone': 'anyome', 'someone': 'someome', 'everyone': 'everyome',
    "don't": 'domt', 'dont': 'domt', "can't": 'camt', 'cant': 'camt',
    "won't": 'womt', 'wont': 'womt', "isn't": 'ismt', "doesn't": 'doesmt',
    'playing': 'playimg', 'loading': 'loadimg', 'adding': 'addimg',
    'song': 'somg', 'music': 'moosic', 'queue': 'queme', 'volume': 'volmume',
    'pause': 'pawse', 'stop': 'stomp', 'skip': 'skimp', 'loop': 'loomp',
}

# Fun Cheems phrases to randomly append
CHEEMS_PHRASES = [
    "🐕", "vro!", "much wow!", "very nice!", "heuhehueuh", "bonk!", 
    "such amaze!", "wow!", "very good!", "much success!", "heckin good!",
    "doge approves!", "🐶", "woof!", "borking intensifies!", "pls no bonk",
    "very impress!", "such skill!", "many thanks!", "so helpful!",
    "cheemsburger time!", "🍔", "doing a heckin good job!", "10/10 would bonk again",
]

# Cheems GIFs (Tenor/Giphy URLs)
CHEEMS_GIFS = [
    "https://media.tenor.com/DSG9ZID25nsAAAAC/cheems-dance.gif",
    "https://media.tenor.com/M35iMzlD5HYAAAAC/cheems-bonk.gif", 
    "https://media.tenor.com/LCPAHb_MvfkAAAAC/bonk-meme.gif",
    "https://media.tenor.com/hKkQvDoJuVoAAAAC/cheems-sad.gif",
    "https://media.tenor.com/gQ_NrH0D6-wAAAAC/cheems-cheemsdog.gif",
    "https://media.tenor.com/IbZEMlVmmF4AAAAC/doge-cheems.gif",
    "https://media.tenor.com/6sNPPbnxC7YAAAAC/cheems-balltze.gif",
    "https://media.tenor.com/pPKOYQpTO8AAAAAC/cheems-bonk.gif",
]

def cheems_transform(text: str, add_phrase: bool = True, chance_gif: float = 0.05) -> tuple[str, Optional[str]]:
    """
    Transform text to Cheems speak!
    
    Args:
        text: The text to transform
        add_phrase: Whether to add a random Cheems phrase
        chance_gif: Chance (0-1) to return a GIF URL
        
    Returns:
        tuple of (transformed_text, gif_url or None)
    """
    if not text:
        return text, None
    
    result = text
    
    # Apply word replacements (case-insensitive, whole words only)
    for original, replacement in CHEEMS_REPLACEMENTS.items():
        pattern = r'\b' + re.escape(original) + r'\b'
        
        def replace_case(match):
            word = match.group(0)
            if word.isupper():
                return replacement.upper()
            elif word[0].isupper():
                return replacement.capitalize()
            return replacement
        
        result = re.sub(pattern, replace_case, result, flags=re.IGNORECASE)
    
    # Insert 'm' sounds in some words ending with 'ing', 'tion', etc.
    result = re.sub(r'(\w)ing\b', r'\1img', result, flags=re.IGNORECASE)
    result = re.sub(r'(\w)tion\b', r'\1tiom', result, flags=re.IGNORECASE)
    result = re.sub(r'(\w)ness\b', r'\1mness', result, flags=re.IGNORECASE)
    
    # Add random Cheems phrase at the end
    if add_phrase and random.random() < 0.6:
        # Remove trailing punctuation, add phrase
        result = result.rstrip('!.?')
        result = f"{result} {random.choice(CHEEMS_PHRASES)}"
    
    # Maybe return a GIF
    gif = None
    if random.random() < chance_gif:
        gif = random.choice(CHEEMS_GIFS)
    
    return result, gif

def cheems_embed(embed: discord.Embed) -> tuple[discord.Embed, Optional[str]]:
    """Transform all text in an embed to Cheems speak."""
    gif = None
    
    if embed.title:
        embed.title, gif = cheems_transform(embed.title, add_phrase=False)
    
    if embed.description:
        embed.description, maybe_gif = cheems_transform(embed.description)
        gif = gif or maybe_gif
    
    if embed.footer and embed.footer.text:
        new_footer, _ = cheems_transform(embed.footer.text, add_phrase=False)
        embed.set_footer(text=new_footer, icon_url=embed.footer.icon_url)
    
    # Transform field values
    new_fields = []
    for field in embed.fields:
        new_name, _ = cheems_transform(field.name, add_phrase=False) if field.name else (field.name, None)
        new_value, _ = cheems_transform(field.value, add_phrase=False) if field.value else (field.value, None)
        new_fields.append((new_name, new_value, field.inline))
    
    embed.clear_fields()
    for name, value, inline in new_fields:
        embed.add_field(name=name, value=value, inline=inline)
    
    return embed, gif

    
async def get_lang(guild_id:int, *keys) -> Optional[Union[list[str], str]]:
    settings = await get_settings(guild_id)
    lang = settings.get("lang", "EN")
    if lang in LANGS and not LANGS[lang]:
        LANGS[lang] = open_json(os.path.join("langs", f"{lang}.json"))

    if len(keys) == 1:
        return LANGS.get(lang, {}).get(keys[0])
    return [LANGS.get(lang, {}).get(key) for key in keys]

async def send(
    ctx: Union[commands.Context, discord.Interaction],
    content: Union[str, discord.Embed] = None,
    *params,
    view: discord.ui.View = None,
    delete_after: float = None,
    ephemeral: bool = False,
    requires_fetch: bool = False
) -> Optional[discord.Message]:
    if content is None:
        content = "No content provided."

    # Get settings first to check language
    settings = await get_settings(ctx.guild.id)
    is_cheems = settings.get("lang", "EN").upper() == "CHEEMS"
    cheems_gif = None

    # Determine the text to send
    if isinstance(content, discord.Embed):
        embed = content
        text = None
        # Apply Cheems transformation to embed if CHEEMS lang
        if is_cheems:
            embed, cheems_gif = cheems_embed(embed)
    else:
        text = await get_lang(ctx.guild.id, content)
        if text:
            text = text.format(*params)
        else:
            text = content.format(*params)
        embed = None
        # Apply Cheems transformation to text if CHEEMS lang
        if is_cheems:
            text, cheems_gif = cheems_transform(text)
        
    # Determine the sending function
    send_func = (
        ctx.send if isinstance(ctx, commands.Context) else
        ctx.channel.send if isinstance(ctx, TempCtx) else
        ctx.followup.send if ctx.response.is_done() else
        ctx.response.send_message
    )

    send_kwargs = {
        "content": text,
        "embed": embed,
        "allowed_mentions": ALLOWED_MENTIONS,
        "silent": settings.get("silent_msg", False),
    }
    
    if "delete_after" in send_func.__code__.co_varnames:
        if settings and ctx.channel.id == settings.get("music_request_channel", {}).get("text_channel_id"):
            delete_after = 10
        send_kwargs["delete_after"] = delete_after
    
    if "ephemeral" in send_func.__code__.co_varnames:
        send_kwargs["ephemeral"] = ephemeral

    if view:
        send_kwargs["view"] = view

    # Send the message or embed
    message = await send_func(**send_kwargs)

    if isinstance(message, discord.InteractionCallbackResponse):
        message = message.resource
    
    if requires_fetch and isinstance(message, (discord.WebhookMessage, discord.InteractionMessage)):
        message = await message.fetch()
    
    # Sometimes send a bonus Cheems GIF (5% chance when CHEEMS mode)
    if cheems_gif and message:
        try:
            channel = ctx.channel if hasattr(ctx, 'channel') else ctx.message.channel if hasattr(ctx, 'message') else None
            if channel:
                await channel.send(cheems_gif, delete_after=15)
        except:
            pass  # Silently ignore if we can't send the GIF

    return message

async def update_db(db: AsyncIOMotorCollection, tempStore: dict, filter: dict, data: dict) -> bool:
    for mode, action in data.items():
        for key, value in action.items():
            cursors = key.split(".")

            nested_data = tempStore
            for c in cursors[:-1]:
                nested_data = nested_data.setdefault(c, {})

            if mode == "$set":
                try:
                    nested_data[cursors[-1]] = value
                except TypeError:
                    nested_data[int(cursors[-1])] = value

            elif mode == "$unset":
                nested_data.pop(cursors[-1], None)

            elif mode == "$inc":
                nested_data[cursors[-1]] = nested_data.get(cursors[-1], 0) + value

            elif mode == "$push":
                if isinstance(value, dict) and "$each" in value:
                    nested_data.setdefault(cursors[-1], []).extend(value["$each"])
                    if "$slice" in value:
                        nested_data[cursors[-1]] = nested_data[cursors[-1]][value["$slice"]:]
                else:
                    nested_data.setdefault(cursors[-1], []).append(value)

            elif mode == "$pull":
                if cursors[-1] in nested_data:
                    value = value.get("$in", []) if isinstance(value, dict) else [value]
                    nested_data[cursors[-1]] = [item for item in nested_data[cursors[-1]] if item not in value]
                    
            else:
                return False

    try:
        result = await db.update_one(filter, data)
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"MongoDB update error: {e}")
        return False

async def get_settings(guild_id:int) -> dict[str, Any]:
    settings = SETTINGS_BUFFER.get(guild_id, None)
    if not settings:
        settings = await SETTINGS_DB.find_one({"_id": guild_id})
        if not settings:
            await SETTINGS_DB.insert_one({"_id": guild_id})
            
        settings = SETTINGS_BUFFER[guild_id] = settings or {}
    return settings

async def update_settings(guild_id: int, data: dict[str, dict[str, Any]]) -> bool:
    settings = await get_settings(guild_id)
    return await update_db(SETTINGS_DB, settings, {"_id": guild_id}, data)
            
async def get_user(user_id: int, d_type: Optional[str] = None, need_copy: bool = True) -> Dict[str, Any]:
    user = USERS_BUFFER.get(user_id)
    if not user:
        user = await USERS_DB.find_one({"_id": user_id})
        if not user:
            user = {"_id": user_id, **USER_BASE}
            await USERS_DB.insert_one(user)
    
        USERS_BUFFER[user_id] = user
        
    if d_type:
        user = user.setdefault(d_type, copy.deepcopy(USER_BASE.get(d_type)))
            
    return copy.deepcopy(user) if need_copy else user

async def update_user(user_id:int, data:dict) -> bool:
    playlist = await get_user(user_id, need_copy=False)
    return await update_db(USERS_DB, playlist, {"_id": user_id}, data)