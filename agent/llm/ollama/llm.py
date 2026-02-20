"""
Ollama LLM. Connects to local Ollama server (ollama serve).
"""
from pathlib import Path
from typing import Optional

import ollama

from libs.base_llm import BaseLLM


class OllamaLLM(BaseLLM):
    """LLM for local Ollama. Handles connection to ollama serve on the network."""

    def __init__(self, workspace: Path, provider: str = "ollama", model: Optional[str] = None):
        super().__init__(workspace=workspace, provider=provider, model=model)

    def chat(self, prompt: str) -> str:
        response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response.message.content

    def _format_chat_error(self, e: Exception) -> str:
        return f"Error: {e}\n(Make sure Ollama is running: ollama serve, ollama pull <model>)"
