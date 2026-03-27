"""Client for the gateway side: consumes requests from queue_in, calls handler, pushes results to queue_out."""

import json
import time
from typing import Any, Callable, Optional

import redis

from libs.debug_log import debug_log, truncate_debug


class ResponseClient:
    """
    Gateway-side client. Consumes requests from queue_in, passes each to the handler,
    and pushes the handler's return value to queue_out.

    The application (gateway) provides a handler and never touches Redis.
    """

    def __init__(self, redis_url: str, queue_in: str, queue_out: str):
        if not redis_url or not str(redis_url).strip():
            raise ValueError("redis_url is required and must be non-empty")
        if queue_in is None or not str(queue_in).strip():
            raise ValueError("queue_in is required and must be non-empty")
        if queue_out is None or not str(queue_out).strip():
            raise ValueError("queue_out is required and must be non-empty")
        self.redis_url = redis_url.strip()
        self.queue_in = queue_in.strip()
        self.queue_out = queue_out.strip()
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url)
        return self._redis

    def run(self, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        """
        Run the gateway loop. For each request from queue_in:
        - Call handler(request)
        - Push handler's return value to queue_out

        The handler receives the request dict (e.g. id, prompt, timestamp) and must return
        a result dict (e.g. id, response, type, timestamp) to be pushed to queue_out.

        Args:
            handler: Callable that receives request dict and returns result dict.
        """
        if handler is None:
            raise ValueError("handler is required")

        while True:
            result = self.redis.blpop(self.queue_in, timeout=0)
            if result is None:
                continue
            _, raw = result
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            request = json.loads(raw)
            rid = request.get("id", "")
            prompt_preview = truncate_debug((request.get("prompt") or "").strip(), 200)
            debug_log(f"LAN queue: BLPOP {self.queue_in} ok id={rid!r} prompt_preview={prompt_preview}")
            try:
                response = handler(request)
                if response is not None:
                    if "timestamp" not in response:
                        response = {**response, "timestamp": int(time.time() * 1000)}
                    out_raw = json.dumps(response, ensure_ascii=False)
                    self.redis.rpush(self.queue_out, out_raw)
                    debug_log(
                        f"LAN queue: RPUSH {self.queue_out} ok id={response.get('id', rid)!r} "
                        f"bytes={len(out_raw.encode('utf-8'))}"
                    )
            except Exception as e:
                # Push error response so RequestClient doesn't block forever
                err_response = {
                    "id": request.get("id", ""),
                    "response": f"[Error] {e}",
                    "type": "response",
                    "timestamp": int(time.time() * 1000),
                }
                self.redis.rpush(self.queue_out, json.dumps(err_response))
                debug_log(f"LAN queue: RPUSH {self.queue_out} error_response id={rid!r} exc={e!r}")

    def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            self._redis.close()
            self._redis = None

    def __enter__(self) -> "ResponseClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
