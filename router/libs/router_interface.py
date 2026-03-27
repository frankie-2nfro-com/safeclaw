"""
router_interface.py - Client interface for calling the Router via Redis.

Used by backend services (and optionally Agent) to push commands and receive responses
without going through the LLM. Services that know exactly what action they need can
call the router directly.

Usage:
    from router.libs.router_interface import RouterClient

    client = RouterClient({"redis_url": "redis://localhost:6379/0"})
    result = client.sync_call("CREATE_POST", {"platform": "X", "text": "Hello"})
    result = await client.async_call("CREATE_POST", {...})  # asyncio
"""
import asyncio
import json
import os
import threading
import uuid
from typing import Callable, Optional

from redis import Redis


class RouterClient:
    """Client for calling the Router via Redis. Encapsulates queue settings and Redis logic."""

    def __init__(self, config: dict):
        """
        Args:
            config: Queue settings. Keys: redis_url (required), command_queue, response_prefix (optional).
        """
        self._config = config

    def _get_redis(self) -> Redis:
        url = self._config.get("redis_url") or os.getenv("REDIS_URL")
        if not url:
            raise ValueError("redis_url must be in config or REDIS_URL env")
        return Redis.from_url(url)

    def _get_queue_names(self) -> tuple[str, str]:
        command_queue = self._config.get("command_queue") or os.getenv("COMMAND_QUEUE", "safeclaw:command_queue")
        response_prefix = self._config.get("response_prefix") or os.getenv("RESPONSE_PREFIX", "safeclaw:response:")
        return command_queue, response_prefix

    def sync_call(
        self,
        action: str,
        params: dict,
        timeout: int = 10,
    ) -> Optional[dict]:
        """
        Push command to router, block until response received.

        Args:
            action: Skill action name (e.g. "CREATE_POST", "MONGCHOI_UPDATE").
            params: Parameters for the skill.
            timeout: Seconds to wait for response. Returns None on timeout.

        Returns:
            Parsed response dict from router, or None on timeout/error.
        """
        r = self._get_redis()
        command_queue, response_prefix = self._get_queue_names()
        message_id = str(uuid.uuid4())
        payload = {"message_id": message_id, "action": action, "params": params or {}}
        r.lpush(command_queue, json.dumps(payload, ensure_ascii=False))

        response_key = f"{response_prefix}{message_id}"
        try:
            result = r.blpop(response_key, timeout=timeout)
            if result:
                _, raw = result
                return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, Exception):
            pass
        return None

    def call_with_callback(
        self,
        action: str,
        params: dict,
        callback: Callable[[Optional[dict]], None],
        timeout: int = 10,
    ) -> None:
        """
        Push command to router, invoke callback when response received (or timeout).
        Non-blocking: runs in a background thread.

        Args:
            action: Skill action name.
            params: Parameters for the skill.
            callback: Called with (result_dict | None). Result is None on timeout/error.
            timeout: Seconds to wait for response.
        """

        def _run() -> None:
            result = self.sync_call(action, params, timeout)
            callback(result)

        threading.Thread(target=_run, daemon=True).start()

    async def async_call(
        self,
        action: str,
        params: dict,
        timeout: int = 10,
    ) -> Optional[dict]:
        """
        Async version: push command to router, await response.
        Uses asyncio.to_thread to run blocking Redis call without blocking the event loop.

        Args:
            action: Skill action name.
            params: Parameters for the skill.
            timeout: Seconds to wait for response.

        Returns:
            Parsed response dict from router, or None on timeout/error.
        """
        return await asyncio.to_thread(self.sync_call, action, params, timeout)
