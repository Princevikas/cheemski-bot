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

import re
import random
from discord.ext import commands


class CheemsProcessor:
    """
    Cheems Language Processor - Converts normal text to Cheems speak!
    
    Usage:
        processor = CheemsProcessor()
        cheems_text = processor.cheemify("Hello, my friend!")
        # Output: "Hemllo, my friemd! 🐕"
    """
    
    # Letter replacements (before consonant clusters)
    REPLACEMENTS = {
        # Common word endings
        'ing': 'img',
        'tion': 'tiom',
        'ness': 'mness',
        'ment': 'memt',
        'ble': 'mble',
        'ple': 'mple',
        'cle': 'mcle',
        
        # Common words (full replacements)
        'the': 'teh',
        'you': 'yu',
        'your': 'yur',
        'are': 'r',
        'have': 'hav',
        'with': 'wif',
        'this': 'dis',
        'that': 'dat',
        'what': 'wut',
        'when': 'whem',
        'where': 'wher',
        'which': 'wich',
        'would': 'wuld',
        'could': 'culd',
        'should': 'shuld',
        'because': 'cuz',
        'please': 'pls',
        'thanks': 'thamks',
        'sorry': 'sowwy',
        'hello': 'hemlo',
        'friend': 'fren',
        'friends': 'frens',
        'brother': 'brudder',
        'something': 'somethimg',
        'nothing': 'nothimg',
        'everything': 'everythimg',
        'anyone': 'anyome',
        'someone': 'someome',
        'everyone': 'everyome',
        'myself': 'mysemlf',
        'yourself': 'yoursemlf',
        'don\'t': 'domt',
        'dont': 'domt',
        'can\'t': 'camt',
        'cant': 'camt',
        'won\'t': 'womt',
        'wont': 'womt',
        'isn\'t': 'ismt',
        'isnt': 'ismt',
        'wasn\'t': 'wasmt',
        'wasnt': 'wasmt',
        'doesn\'t': 'doesmt',
        'doesnt': 'doesmt',
        'didn\'t': 'didmt',
        'didnt': 'didmt',
        'couldn\'t': 'couldmt',
        'couldnt': 'couldmt',
        'wouldn\'t': 'wouldmt',
        'wouldnt': 'wouldmt',
        'shouldn\'t': 'shouldmt',
        'shouldnt': 'shouldmt',
    }
    
    # Consonant patterns to insert 'm' before
    CONSONANT_CLUSTERS = ['nd', 'ng', 'nk', 'nt', 'nc', 'ns', 'nz']
    
    # Random Cheems phrases to occasionally append
    CHEEMS_PHRASES = [
        "🐕",
        "vro",
        "much wow",
        "very nice",
        "heuhehueuh",
    ]
    
    def __init__(self, intensity: int = 2):
        """
        Initialize Cheems Processor.
        
        Args:
            intensity: 1 = light, 2 = medium, 3 = heavy cheemification
        """
        self.intensity = min(max(intensity, 1), 3)
    
    def cheemify(self, text: str, add_emoji: bool = True) -> str:
        """
        Convert text to Cheems language.
        
        Args:
            text: The text to convert
            add_emoji: Whether to add a random Cheems emoji/phrase at the end
            
        Returns:
            Cheemified text
        """
        if not text:
            return text
        
        result = text
        
        # Apply word replacements (case-insensitive)
        for original, replacement in self.REPLACEMENTS.items():
            # Match whole words only
            pattern = r'\b' + re.escape(original) + r'\b'
            
            # Handle case preservation
            def replace_with_case(match):
                word = match.group(0)
                if word.isupper():
                    return replacement.upper()
                elif word[0].isupper():
                    return replacement.capitalize()
                return replacement
            
            result = re.sub(pattern, replace_with_case, result, flags=re.IGNORECASE)
        
        # Insert 'm' in words (based on intensity)
        if self.intensity >= 2:
            result = self._insert_m_sounds(result)
        
        # Add random Cheems touch at the end
        if add_emoji and random.random() < 0.7:
            result = result.rstrip('!.?') + ' ' + random.choice(self.CHEEMS_PHRASES)
        
        return result
    
    def _insert_m_sounds(self, text: str) -> str:
        """Insert 'm' sounds into words for that classic Cheems feel."""
        words = text.split()
        result = []
        
        for word in words:
            # Skip short words and already processed words
            if len(word) <= 3 or 'm' in word.lower():
                result.append(word)
                continue
            
            # Check if word ends with consonant cluster that can have 'm' inserted
            modified = False
            for cluster in self.CONSONANT_CLUSTERS:
                if cluster in word.lower():
                    # Insert 'm' before the cluster (simple approach)
                    idx = word.lower().find(cluster)
                    if idx > 0 and word[idx-1].lower() not in 'aeiou':
                        new_word = word[:idx] + 'm' + word[idx:]
                        result.append(new_word)
                        modified = True
                        break
            
            if not modified:
                # Random 'm' insertion for longer words (intensity 3)
                if self.intensity >= 3 and len(word) > 5 and random.random() < 0.3:
                    mid = len(word) // 2
                    word = word[:mid] + 'm' + word[mid:]
                result.append(word)
        
        return ' '.join(result)
    
    def light(self, text: str) -> str:
        """Light cheemification - just word replacements."""
        old_intensity = self.intensity
        self.intensity = 1
        result = self.cheemify(text)
        self.intensity = old_intensity
        return result
    
    def heavy(self, text: str) -> str:
        """Heavy cheemification - maximum Cheems energy."""
        old_intensity = self.intensity
        self.intensity = 3
        result = self.cheemify(text)
        self.intensity = old_intensity
        return result


class CheemsLanguage(commands.Cog):
    """Cheems Language Processor Cog - Provides cheemification services to other cogs!"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.processor = CheemsProcessor(intensity=2)
    
    async def is_cheems_enabled(self, guild_id: int) -> bool:
        """Check if CHEEMS language pack is selected for this guild."""
        import function as func
        settings = await func.get_settings(guild_id)
        return settings.get('lang', 'EN').upper() == 'CHEEMS'
    
    async def cheemify(self, text: str, guild_id: int = None, add_emoji: bool = True) -> str:
        """
        Convert text to Cheems language IF CHEEMS pack is enabled.
        
        Args:
            text: The text to convert
            guild_id: Guild ID to check settings (if None, always cheemify)
            add_emoji: Whether to add a random Cheems emoji/phrase at the end
            
        Usage from other cogs:
            cheems_cog = self.bot.get_cog("CheemsLanguage")
            if cheems_cog:
                text = await cheems_cog.cheemify("Hello friend!", ctx.guild.id)
        """
        # If guild_id provided, check if CHEEMS is enabled
        if guild_id is not None:
            if not await self.is_cheems_enabled(guild_id):
                return text  # Return original text if CHEEMS not enabled
        
        return self.processor.cheemify(text, add_emoji)
    
    def cheemify_always(self, text: str, add_emoji: bool = True) -> str:
        """Always cheemify text regardless of settings."""
        return self.processor.cheemify(text, add_emoji)
    
    async def light(self, text: str, guild_id: int = None) -> str:
        """Light cheemification (only if CHEEMS enabled)."""
        if guild_id is not None:
            if not await self.is_cheems_enabled(guild_id):
                return text
        return self.processor.light(text)
    
    async def heavy(self, text: str, guild_id: int = None) -> str:
        """Heavy cheemification (only if CHEEMS enabled)."""
        if guild_id is not None:
            if not await self.is_cheems_enabled(guild_id):
                return text
        return self.processor.heavy(text)


async def setup(bot: commands.Bot):
    await bot.add_cog(CheemsLanguage(bot))
