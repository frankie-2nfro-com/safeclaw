"""
Router: self-contained component. Waits for commands on Redis, routes by action, pushes responses.
Run from router/: python router.py
Or from project root: python router/router.py
Can be moved to another machine - ensure .env has REDIS_URL.
"""
import importlib
import json
import os
import signal
import sys
from typing import Optional
from redis import Redis

class Router:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis: Optional[Redis] = None
        self._running = False

    def _get_redis(self) -> Redis:
        if self._redis is None:
            if not self.redis_url:
                raise ValueError("REDIS_URL not set")
            self._redis = Redis.from_url(self.redis_url)
        return self._redis

    def _get_skill_class(self, action: str):
        """Dynamically load skill class: CREATE_POST -> skills.create_post.skill.CreatePostSkill"""
        module_name = action.lower()
        class_name = "".join(w.capitalize() for w in module_name.split("_")) + "Skill"
        module_path = f"skills.{module_name}.skill"
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)

    def route_command(self, action: str, params: dict):
        """
        Route the command. Load skill class dynamically and call execute().
        Returns result from skill.execute().
        """
        SkillClass = self._get_skill_class(action)
        skill = SkillClass()
        return skill.execute(params)

    def run(self) -> int:
        if not self.redis_url:
            print("ERROR: REDIS_URL not set in .env")
            return 1

        print("Connecting to Redis...")
        try:
            r = self._get_redis()
            r.ping()
            print("Connected.")
        except Exception as e:
            print(f"ERROR: Cannot connect to Redis: {e}")
            return 1

        command_queue = os.getenv("COMMAND_QUEUE", "safeclaw:command_queue")
        response_prefix = os.getenv("RESPONSE_PREFIX", "safeclaw:response:")

        print(f"Router listening on {command_queue} (Ctrl+C to stop)\n")
        self._running = True

        def stop(sig, frame):
            self._running = False

        signal.signal(signal.SIGINT, stop)

        while self._running:
            result = r.brpop(command_queue, timeout=1)
            if result:
                _, raw = result
                payload = raw.decode() if isinstance(raw, bytes) else raw
                try:
                    parsed = json.loads(payload)
                    message_id = parsed.get("message_id")
                    action = parsed.get("action")
                    params = parsed.get("params", {})

                    result = self.route_command(action, params)

                    response_key = f"{response_prefix}{message_id}"
                    response = {"status": "ok", "action": action, **(result or {})}
                    r.lpush(response_key, json.dumps(response))
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON: {e}")
                except Exception as e:
                    print(f"Error: {e}")

        print("\nStopped.")
        return 0


if __name__ == "__main__":
    print("Don't run this file directly. Use the router.py script instead.")
    sys.exit(1)
