"""
Chrome Extension Gemini LLM. Sends prompts via Redis to a Chrome extension that uses Gemini.
"""
import os
from pathlib import Path
from typing import Optional

from libs.base_llm import BaseLLM
from libs.gemini_api_bridge import ask_gemini


class ChromeExtensionGeminiLLM(BaseLLM):
    """LLM via Gemini Chrome extension bridge. Uses Redis queues (GEMINI_PROMPT_IN / GEMINI_PROMPT_OUT)."""

    def __init__(self, workspace: Path, provider: str = "chrome_extension_gemini", model: Optional[str] = None):
        super().__init__(workspace=workspace, provider=provider, model=model)
        self._redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    def chat(self, prompt: str) -> str:
        return ask_gemini(prompt, redis_url=self._redis_url)

    def _format_chat_error(self, e: Exception) -> str:
        return f"Error: {e}\n(Ensure Chrome extension is running and Redis is reachable at REDIS_URL)"
