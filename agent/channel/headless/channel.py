"""
Headless channel. Listens to a Redis queue for requests.
LAN services use RequestClient to push requests; this channel uses ResponseClient
to consume them and return agent responses.
"""
import os
from typing import Tuple

from libs.base_channel import BaseChannel
from libs.logger import log
from libs.response_client import ResponseClient


class HeadlessChannel(BaseChannel):
    """Headless channel: receives from queue_in, processes via agent, pushes to queue_out."""

    SOURCE_NAME = "Headless"

    def __init__(self, channel_cfg: dict = None):
        super().__init__(config_path=None)
        cfg = channel_cfg or {}
        self._enabled = cfg.get("enabled", True)
        self._redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._queue_in = os.getenv(
            "LAN_QUEUE_IN",
            cfg.get("queue_in", "safeclaw:lan_request_queue"),
        )
        self._queue_out = os.getenv(
            "LAN_QUEUE_OUT",
            cfg.get("queue_out", "safeclaw:lan_response_queue"),
        )

    @property
    def source_name(self) -> str:
        return self.SOURCE_NAME

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._redis_url.strip())

    def receive(self) -> Tuple[str, str]:
        """Not used; Headless uses ResponseClient loop instead."""
        return ("", self.source_name)

    def send(self, message: str) -> None:
        """Not used; response is pushed via ResponseClient."""
        pass

    def send_broadcast(self, message: str) -> None:
        """Headless: no broadcast to users."""
        pass

    def run(self, agent) -> None:
        """Run ResponseClient loop: consume from queue_in, process, push to queue_out."""
        if not self.enabled:
            log("[Headless] Channel disabled or REDIS_URL not set. Skipping.")
            return
        agent._ensure_ready()
        log(f"[Headless] Listening on {self._queue_in} -> {self._queue_out}")

        def handler(request: dict) -> dict:
            prompt = (request.get("prompt") or "").strip()
            request_id = request.get("id", "")
            if not prompt:
                return {
                    "id": request_id,
                    "response": "[Error] Empty prompt.",
                    "type": "response",
                }
            try:
                agent.broadcast_to_other_channels(prompt, exclude_source=self.SOURCE_NAME)
                response = agent.process(prompt, source=self.SOURCE_NAME, flush_broadcasts_after=True)
                agent._flush_pending_broadcasts()
                agent.broadcast_response_to_other_channels(response or "", exclude_source=self.SOURCE_NAME)
                return {"id": request_id, "response": response or "", "type": "response"}
            except Exception as e:
                err_msg = f"[Error] {e}"
                agent.broadcast_response_to_other_channels(err_msg, exclude_source=self.SOURCE_NAME)
                return {"id": request_id, "response": err_msg, "type": "response"}

        client = ResponseClient(self._redis_url, self._queue_in, self._queue_out)
        client.run(handler)
