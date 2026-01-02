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

import os

from dotenv import load_dotenv
from typing import (
    Dict,
    List,
    Any,
    Union
)

load_dotenv()

def _get_int(value, env_key: str, default: int = 0) -> int:
    """Safely get an integer value from settings or environment variable."""
    if value and str(value).strip():
        try:
            return int(value)
        except (ValueError, TypeError):
            pass
    env_val = os.getenv(env_key)
    if env_val and env_val.strip():
        try:
            return int(env_val)
        except (ValueError, TypeError):
            pass
    return default

def _get_str(value, env_key: str, default: str = "") -> str:
    """Safely get a string value from settings or environment variable."""
    if value and str(value).strip():
        return str(value)
    env_val = os.getenv(env_key)
    if env_val and env_val.strip():
        return env_val
    return default

class Settings:
    def __init__(self, settings: Dict) -> None:
        self.token: str = _get_str(settings.get("token"), "TOKEN")
        self.client_id: int = _get_int(settings.get("client_id"), "CLIENT_ID")
        self.genius_token: str = _get_str(settings.get("genius_token"), "GENIUS_TOKEN")
        self.tenor_apikey: str = _get_str(settings.get("tenor_apikey"), "TENOR_APIKEY")
        self.mongodb_url: str = _get_str(settings.get("mongodb_url"), "MONGODB_URL")
        self.mongodb_name: str = _get_str(settings.get("mongodb_name"), "MONGODB_NAME")
        
        self.invite_link: str = ""  # Removed - ping @cheemkas for support
        # Load nodes from separate nodes.json file (tracked in Git) or fallback to settings
        self.nodes: Dict[str, Dict[str, Union[str, int, bool]]] = self._load_nodes(settings.get("nodes", {}))
        self.max_queue: int = settings.get("default_max_queue", 1000)
        self.bot_prefix: str = settings.get("prefix", "")
        self.activity: List[Dict[str, str]] = settings.get("activity", [{"listen": "/help"}])
        self.logging: Dict[Union[str, Dict[str, Union[str, bool]]]] = settings.get("logging", {})
        self.embed_color: str = int(settings.get("embed_color", "0xb3b3b3"), 16)
        # Support BOT_ACCESS_USER env var (comma-separated IDs) or settings file
        env_access = os.getenv("BOT_ACCESS_USER", "")
        if env_access:
            self.bot_access_user: List[int] = [int(x.strip()) for x in env_access.split(",") if x.strip()]
        else:
            self.bot_access_user: List[int] = settings.get("bot_access_user", [])
        self.sources_settings: Dict[Dict[str, str]] = settings.get("sources_settings", {})
        self.cooldowns_settings: Dict[str, List[int]] = settings.get("cooldowns", {})
        self.aliases_settings: Dict[str, List[str]] = settings.get("aliases", {})
        self.controller: Dict[str, Dict[str, Any]] = settings.get("default_controller", {})
        self.voice_status_template: str = settings.get("default_voice_status_template", "")
        self.lyrics_platform: str = settings.get("lyrics_platform", "A_ZLyrics").lower()
        self.ipc_client: Dict[str, Union[str, bool, int]] = settings.get("ipc_client", {})
        self.version: str = settings.get("version", "")

    def _load_nodes(self, fallback_nodes: Dict) -> Dict[str, Dict[str, Union[str, int, bool]]]:
        """Load nodes from nodes.json file (tracked in Git) or fallback to settings.json nodes."""
        import json
        nodes_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nodes.json")
        try:
            if os.path.exists(nodes_file):
                with open(nodes_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load nodes.json: {e}")
        return fallback_nodes