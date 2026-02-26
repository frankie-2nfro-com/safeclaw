"""Client for sending prompts to Gemini via the SocketQueueBridge."""

import json
import time
from typing import Any, Callable, Optional

import redis


class RequestClient:
    """Sends prompts to a Redis queue. Use send_with_callback or send_and_wait."""

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

    def _validate_and_push(self, request_id: str, prompt: str) -> None:
        if request_id is None or not str(request_id).strip():
            raise ValueError("request_id is required and must be non-empty")
        if not prompt or not str(prompt).strip():
            raise ValueError("prompt is required and must be non-empty")
        payload = {"id": request_id, "prompt": prompt, "timestamp": int(time.time() * 1000)}
        self.redis.lpush(self.queue_in, json.dumps(payload))

    def _wait_for_response(self) -> dict[str, Any]:
        result = self.redis.blpop(self.queue_out, timeout=0)
        if result is None:
            raise TimeoutError("No response received")
        _, raw = result
        return json.loads(raw)

    def send_with_callback(
        self, request_id: str, prompt: str, callback: Callable[[Any], None]
    ) -> None:
        """
        Push a prompt to the queue, wait for response, then call callback with the result.

        Args:
            request_id: Unique ID for this request.
            prompt: Text to send to Gemini.
            callback: Called with the response dict when done. Dict has keys: type, id, response, timestamp.

        Raises:
            ValueError: If request_id, prompt, or callback is invalid.
        """
        if callback is None:
            raise ValueError("callback is required")
        self._validate_and_push(request_id, prompt)
        data = self._wait_for_response()
        callback(data)

    def send_and_wait(self, request_id: str, prompt: str) -> dict[str, Any]:
        """
        Push a prompt to the queue, block until response received, return the result.

        Args:
            request_id: Unique ID for this request.
            prompt: Text to send to Gemini.

        Returns:
            Response dict with keys: type, id, response, timestamp.

        Raises:
            ValueError: If request_id or prompt is invalid.
        """
        self._validate_and_push(request_id, prompt)
        return self._wait_for_response()

    def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            self._redis.close()
            self._redis = None

    def __enter__(self) -> "RequestClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()





""" SAMPLE USAGE 


import sys
import time

from libs import RequestClient

REDIS_URL = "redis://192.168.1.153:6379"
QUEUE_IN = "IN_QUEUE"
QUEUE_OUT = "OUT_QUEUE"


def main():
    send_only = False
    args = sys.argv[1:]
    if args and args[0] == "--send-only":
        send_only = True
        args = args[1:]

    if not args:
        print("Usage: python test.py [--send-only] \"<prompt>\"", file=sys.stderr)
        sys.exit(1)

    prompt = args[0]

    with RequestClient(REDIS_URL, QUEUE_IN, QUEUE_OUT) as req:
        request_id = f"req_{int(time.time() * 1000)}"
        if send_only:
            req._validate_and_push(request_id, prompt)
            print(f"Sent request {request_id}", file=sys.stderr)
        else:
            result = req.send_and_wait(request_id, prompt)
            print(result["response"])


if __name__ == "__main__":
    main()



"""