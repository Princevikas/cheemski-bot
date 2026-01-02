"""
Custom HTTP-based Akinator client - backup for when the akinator library fails.
Based on the Akinator API endpoints used by zennn08/akinator-api.
"""
import aiohttp
import asyncio
from typing import Optional
import function as func


class AkinatorHTTP:
    """
    Simple HTTP-based Akinator client as a backup.
    Uses direct API calls instead of cloudscraper.
    """
    
    # API Endpoints by region
    SERVERS = {
        "en": "https://srv2.akinator.com:9162",
        "en_animals": "https://srv2.akinator.com:9163",
        "en_objects": "https://srv2.akinator.com:9164",
    }
    
    def __init__(self, region: str = "en", child_mode: bool = True):
        self.region = region
        self.child_mode = child_mode
        self.server = self.SERVERS.get(region, self.SERVERS["en"])
        
        # Game state
        self.session_id: Optional[str] = None
        self.signature: Optional[str] = None
        self.step: int = 0
        self.question: Optional[str] = None
        self.progression: float = 0.0
        self.win: bool = False
        
        # Guess data
        self.name_proposition: Optional[str] = None
        self.description_proposition: Optional[str] = None
        self.photo: Optional[str] = None
        
        self._http_session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._http_session = aiohttp.ClientSession(timeout=timeout)
        return self._http_session
    
    async def close(self):
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
    
    async def start_game(self) -> str:
        """Start a new Akinator game session."""
        session = await self._get_session()
        
        # Parameters for starting game
        params = {
            "partner": "1",
            "player": "website-desktop",
            "uid_ext_session": "",
            "frontaddr": "NDYuMTA1LjExMC4yNDk=",  # Base64 encoded address
            "childMod": "true" if self.child_mode else "false",
            "constraint": "ETAT\u003c\u003e'AV'",
            "soft_constraint": "",
            "question_filter": ""
        }
        
        url = f"{self.server}/ws/new_session"
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to start game: HTTP {resp.status}")
                
                data = await resp.json()
                
                # Check for errors
                completion = data.get("completion", "")
                if completion != "OK":
                    raise Exception(f"API Error: {data.get('completion', 'Unknown error')}")
                
                # Parse response
                parameters = data.get("parameters", {})
                identification = parameters.get("identification", {})
                step_info = parameters.get("step_information", {})
                
                self.session_id = identification.get("session")
                self.signature = identification.get("signature")
                self.step = int(step_info.get("step", 0))
                self.question = step_info.get("question", "")
                self.progression = float(step_info.get("progression", 0))
                
                func.logger.info(f"[AkinatorHTTP] Started session: {self.session_id}")
                return self.question
                
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {e}")
        except Exception as e:
            raise Exception(f"Failed to start game: {e}")
    
    async def answer(self, answer: str) -> str:
        """Submit an answer and get the next question."""
        session = await self._get_session()
        
        # Map answer strings to numbers
        answer_map = {
            "yes": 0, "y": 0, "0": 0,
            "no": 1, "n": 1, "1": 1,
            "i don't know": 2, "idk": 2, "2": 2,
            "probably": 3, "p": 3, "3": 3,
            "probably not": 4, "pn": 4, "4": 4,
        }
        
        answer_num = answer_map.get(answer.lower(), 2)  # Default to "don't know"
        
        params = {
            "session": self.session_id,
            "signature": self.signature,
            "step": str(self.step),
            "answer": str(answer_num),
            "question_filter": ""
        }
        
        url = f"{self.server}/ws/answer"
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to answer: HTTP {resp.status}")
                
                data = await resp.json()
                completion = data.get("completion", "")
                
                if completion != "OK":
                    # Check if we have a guess
                    if completion == "WARN - Loss of 1 questions remaining":
                        # Akinator wants to guess
                        await self._fetch_guess()
                        self.win = True
                        return self.question or "Ready to guess!"
                    raise Exception(f"API Error: {completion}")
                
                # Parse next question
                parameters = data.get("parameters", {})
                self.step = int(parameters.get("step", self.step + 1))
                self.question = parameters.get("question", "")
                self.progression = float(parameters.get("progression", 0))
                
                # Check if Akinator is ready to guess (high progression)
                if self.progression >= 80:
                    await self._fetch_guess()
                    self.win = True
                
                return self.question
                
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {e}")
    
    async def _fetch_guess(self):
        """Fetch the character guess from Akinator."""
        session = await self._get_session()
        
        params = {
            "session": self.session_id,
            "signature": self.signature,
            "step": str(self.step),
        }
        
        url = f"{self.server}/ws/list"
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return
                
                data = await resp.json()
                parameters = data.get("parameters", {})
                elements = parameters.get("elements", [])
                
                if elements:
                    first = elements[0].get("element", {})
                    self.name_proposition = first.get("name", "Unknown")
                    self.description_proposition = first.get("description", "")
                    self.photo = first.get("absolute_picture_path", None)
                    func.logger.info(f"[AkinatorHTTP] Guess: {self.name_proposition}")
                    
        except Exception as e:
            func.logger.error(f"[AkinatorHTTP] Error fetching guess: {e}")
    
    async def back(self):
        """Go back to the previous question."""
        if self.step == 0:
            raise Exception("Cannot go back from first question")
        
        session = await self._get_session()
        
        params = {
            "session": self.session_id,
            "signature": self.signature,
            "step": str(self.step),
            "answer": "-1"  # -1 means back
        }
        
        url = f"{self.server}/ws/cancel_answer"
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to go back: HTTP {resp.status}")
                
                data = await resp.json()
                parameters = data.get("parameters", {})
                self.step = int(parameters.get("step", max(0, self.step - 1)))
                self.question = parameters.get("question", self.question)
                self.progression = float(parameters.get("progression", self.progression))
                
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {e}")
