"""
ActionExecutor: runs agent actions (via ability registry) and router actions (via Redis).
"""
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from redis import Redis

from libs.logger import dialog, log

COMMAND_QUEUE = "safeclaw:command_queue"
RESPONSE_PREFIX = "safeclaw:response:"


class ActionExecutor:
    """Execute agent actions (dynamic from ability registry) or router actions (Redis queue)."""

    def __init__(self, action: str, params: dict, workspace: Optional[Path] = None):
        self.action = action
        self.params = params
        self.workspace = workspace or (Path(__file__).resolve().parent.parent / "workspace")

    def _get_config(self) -> dict:
        """Load config.json for timeout, thinking, etc."""
        config_path = self.workspace.parent / "config.json"
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding="utf-8").strip())
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def _get_timeout(self) -> int:
        """Timeout in seconds from config.json (response queue, message age)."""
        return int(self._get_config().get("timeout", 10))

    def _get_thinking(self) -> bool:
        """Whether to show thinking status (waiting for LLM, router, etc.)."""
        return self._get_config().get("thinking", True)

    def execute(self):
        from ability import get_action_class

        action_class = get_action_class(self.action)
        result = None
        execution_message = "\n--- Executing Action ---\n"
        executed_successfully = False

        if action_class is not None:
            # AGENT ACTION: instantiate from registry and execute
            execution_message += f"Agent Action: {self.action}\n"
            execution_message += f"Params: {self.params}\n"
            if self._get_thinking():
                dialog(f"Executing agent action ({self.action})...")
            action_instance = action_class(workspace=self.workspace, params=self.params)
            result = action_instance.execute()
            executed_successfully = True
        else:
            # ROUTER ACTION: push to Redis, wait for response
            execution_message += f"Router Action: {self.action}\n"
            execution_message += f"Params: {self.params}\n"

            if self._get_thinking():
                dialog(f"Waiting for router ({self.action})...")

            message_id = str(uuid.uuid4())
            result_holder = [None]

            runner_thread = threading.Thread(
                target=self._subscribe_to_response_queue,
                args=(result_holder, message_id),
            )
            runner_thread.start()

            self._push_to_command_queue(message_id, self.action, self.params)

            timeout = self._get_timeout()
            start = time.time()
            runner_thread.join(timeout=timeout)
            elapsed = time.time() - start
            if elapsed < timeout and result_holder[0] is None:
                time.sleep(timeout - elapsed)
            result = result_holder[0]
            execution_message += f"PUSH ROUTER ACTION TO QUEUE: {self.action}\n"
            executed_successfully = True
            if result is None:
                log(f"Timeout {timeout} seconds without any response!")

        execution_message += "--- Action Finished ---\n"

        if executed_successfully and result is not None:
            execution_message += f"Execution Artifact: {result}\n"
            log(execution_message.strip())

        return result

    def _get_redis(self):
        url = os.getenv("REDIS_URL")
        if url is None:
            raise ValueError("REDIS_URL is not set")
        return Redis.from_url(url)

    def _push_to_command_queue(self, message_id: str, action: str, params: dict) -> None:
        """Push command to Redis queue. Router will process and push to response:{message_id}."""
        payload = json.dumps({"message_id": message_id, "action": action, "params": params})
        try:
            r = self._get_redis()
            r.lpush(COMMAND_QUEUE, payload)
            log(f"PUSH ROUTER ACTION TO QUEUE: {payload}")
        except Exception as e:
            log(f"Redis push error: {e}")

    def _subscribe_to_response_queue(self, result_holder: list, message_id: str) -> None:
        """
        Block on response queue (BLPOP safeclaw:response:{message_id}, timeout from config).
        On response: set result_holder[0] = parsed result.
        On timeout/error: result_holder[0] stays None.
        """
        response_key = f"{RESPONSE_PREFIX}{message_id}"
        timeout = self._get_timeout()
        try:
            r = self._get_redis()
            log(f"Waiting for response for {timeout} seconds...")
            blpop_result = r.blpop(response_key, timeout=timeout)
            if blpop_result:
                log("RESPONSE_FOUND")
                _, raw = blpop_result
                result_holder[0] = json.loads(raw)
        except Exception as e:
            log(f"Redis subscribe error: {e}")
