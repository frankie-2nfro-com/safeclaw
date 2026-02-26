"""Client for the gateway side: consumes requests from queue_in, calls handler, pushes results to queue_out."""

import json
import time
from typing import Any, Callable, Optional

import redis


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
            request = json.loads(raw)
            try:
                response = handler(request)
                if response is not None:
                    if "timestamp" not in response:
                        response = {**response, "timestamp": int(time.time() * 1000)}
                    self.redis.rpush(self.queue_out, json.dumps(response))
            except Exception as e:
                # Push error response so RequestClient doesn't block forever
                err_response = {
                    "id": request.get("id", ""),
                    "response": f"[Error] {e}",
                    "type": "response",
                    "timestamp": int(time.time() * 1000),
                }
                self.redis.rpush(self.queue_out, json.dumps(err_response))

    def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            self._redis.close()
            self._redis = None

    def __enter__(self) -> "ResponseClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()




""" SAMPLE USAGE 


from libs import ResponseClient

REDIS_URL = "redis://192.168.1.153:6379"
QUEUE_IN = "IN_QUEUE"
QUEUE_OUT = "OUT_QUEUE"


def handler(request: dict) -> dict:
    #Application logic: receives request, returns result. No Redis/queue knowledge.
    prompt = request.get("prompt", "")
    request_id = request.get("id", "")
    # Example: echo back (replace with real logic, e.g. call extension)
    return {
        "id": request_id,
        "response": f"You said: {prompt} (I've handled this request #{request_id})",
        "type": "response",
    }


def main():
    print("Gateway listening on queue_in, pushing results to queue_out...")
    with ResponseClient(REDIS_URL, QUEUE_IN, QUEUE_OUT) as client:
        client.run(handler)


if __name__ == "__main__":
    main()


"""