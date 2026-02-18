"""
Base channel: pure I/O for different interfaces (Telegram, WhatsApp, etc.).
Channels receive input, pass to agent for processing, send response.
"""
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from libs.base_agent import BaseAgent


class BaseChannel(ABC):
    """Pure I/O layer. Subclasses implement receive/send for their medium."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.config = self._load_config() if config_path else {}

    def _load_config(self) -> dict:
        """Load config.json. If missing or invalid, copy from config_initial.json first."""
        config_file = self.config_path
        initial_file = config_file.parent / "config_initial.json"
        if not config_file.exists() and initial_file.exists():
            config_file.write_text(initial_file.read_text(encoding="utf-8"), encoding="utf-8")
        if config_file.exists():
            try:
                raw = config_file.read_text(encoding="utf-8").strip()
                if raw:
                    return json.loads(raw)
            except json.JSONDecodeError:
                pass
            if initial_file.exists():
                config_file.write_text(initial_file.read_text(encoding="utf-8"), encoding="utf-8")
                return json.loads(config_file.read_text(encoding="utf-8"))
        return {}

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this channel, e.g. 'Console', 'Telegram'."""
        pass

    @abstractmethod
    def send(self, message: str) -> None:
        """Send a message to the user."""
        pass

    @abstractmethod
    def receive(self) -> Tuple[str, str]:
        """Block until user sends. Return (message_text, source_name)."""
        pass

    @abstractmethod
    def run(self, agent: "BaseAgent") -> None:
        """Start the channel loop: receive -> agent.process -> send."""
        pass

    def broadcast_receive(self, user_input: str, from_source: str) -> None:
        """Display user input replicated from another channel. Override to support cross-channel replication."""
        pass

    def broadcast_response(self, response: str, from_source: str) -> None:
        """Display a response replicated from another channel. Override to support cross-channel replication."""
        pass
