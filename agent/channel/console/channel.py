"""
Console channel. stdin/stdout I/O.
"""
from typing import Tuple

from libs.base_channel import BaseChannel


class ConsoleChannel(BaseChannel):
    """Console I/O: input() and print()."""

    @property
    def source_name(self) -> str:
        return "Console"

    def __init__(self):
        super().__init__(config_path=None)

    def receive(self) -> Tuple[str, str]:
        return input("You: ").strip(), self.source_name

    def send(self, message: str) -> None:
        print(f"\nSafeClaw: {message}\n")

    def broadcast_receive(self, user_input: str, from_source: str) -> None:
        """Show messages replicated from other channels (e.g. Telegram)."""
        print(f"[{from_source}] {user_input}", flush=True)

    def broadcast_response(self, response: str, from_source: str) -> None:
        """Show response replicated from another channel (e.g. Telegram)."""
        print(f"\nSafeClaw: {response}\n", flush=True)
        print("You: ", end="", flush=True)

    def run(self, agent) -> None:
        """Blocking loop: receive -> process -> send."""
        agent._ensure_ready()
        while True:
            user_input, source = self.receive()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            agent.broadcast_to_other_channels(user_input, exclude_source=source)
            response = agent.process(user_input, source)
            self.send(response)
            agent.broadcast_response_to_other_channels(response, exclude_source=source)
