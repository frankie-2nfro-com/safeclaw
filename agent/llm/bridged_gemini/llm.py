"""
Bridged Gemini LLM. Sends prompts via Redis to a bridge (e.g. Chrome extension) that uses Gemini.
"""
import os
from pathlib import Path
from typing import Optional

from libs.base_llm import BaseLLM
from libs.gemini_api_bridge import ask_gemini


class BridgedGeminiLLM(BaseLLM):
    """LLM via Gemini API bridge. Uses Redis queues (GEMINI_PROMPT_IN / GEMINI_PROMPT_OUT)."""

    def __init__(self, workspace: Path, provider: str = "bridged_gemini", model: Optional[str] = None):
        super().__init__(workspace=workspace, provider=provider, model=model)
        self._redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    def chat(self, prompt: str, options: Optional[list[str]] = None) -> str:
        return ask_gemini(prompt, redis_url=self._redis_url, options=options, workspace=self.workspace)

    def _format_chat_error(self, e: Exception) -> str:
        return f"Error: {e}\n(Ensure bridge is running and Redis is reachable at REDIS_URL)"
