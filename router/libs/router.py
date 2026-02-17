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
from pathlib import Path
from typing import Optional
from redis import Redis

ROUTER_DIR = Path(__file__).resolve().parent.parent


class Router:
    def __init__(self, redis_url: Optional[str] = None, config_path: Optional[Path] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis: Optional[Redis] = None
        self._running = False
        self.config_path = config_path or (ROUTER_DIR / "config.json")
        self.config = self._load_config()

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
        Route the command. Check config for allow-list/enabled, then load skill and execute().
        Returns result from skill.execute().
        """
        skills_config = self.config.get("skills", {})
        skill_config = skills_config.get(action, {})
        if skill_config.get("enabled", True) is False:
            return {"status": "skipped", "reason": f"Skill {action} is disabled in config"}
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
