import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from libs.llm_client import chat as llm_chat
from libs.remote_chrome_utils import dismiss_consent
import threading
from redis import Redis

COMMAND_QUEUE = "safeclaw:command_queue"
RESPONSE_PREFIX = "safeclaw:response:"





class ActionExecutor:

    def __init__(self, action: str, params: dict, workspace: Optional[Path] = None):
        self.action = action
        self.params = params
        self.workspace = workspace or (Path(__file__).resolve().parent.parent / "workspace")


    def execute(self):
        # Agent actions: methods are _MEMORY_WRITE, _BROWSER_VISION (underscore prefix)
        # Incoming action names: MEMORY_WRITE (no underscore)
        inner_method_name = self.action if hasattr(self, self.action) else f"_{self.action}"
        result = None

        execution_message = f"\n--- Executing Action ---\n"
        executed_successfully = False

        if hasattr(self, inner_method_name):
            # AGENT ACTION
            execution_message += f"Agent Action: {self.action}\n"
            execution_message += f"Params: {self.params}\n"

            # dynamic bind a function by the self.action and call the function and get the result
            self.function = getattr(self, inner_method_name)
            result = self.function(params=self.params)
            executed_successfully = True
        else:
            # ROUTER ACTION
            execution_message += f"Router Action: {self.action}\n"
            execution_message += f"Params: {self.params}\n"

            # Generate message_id, start listener thread, then push command
            message_id = str(uuid.uuid4())
            result_holder = [None]

            runner_thread = threading.Thread(
                target=self._subscribe_to_response_queue,
                args=(result_holder, message_id),
            )
            runner_thread.start()

            # Push the action to command queue (router will pick it up and push to response:{message_id})
            self._push_to_command_queue(message_id, self.action, self.params)

            # Wait for runner thread (timeout 10 seconds)
            # If thread exits early (e.g. Redis error), join returns immediately.
            # Sleep remainder so we always wait full 10s before next "You:" prompt.
            start = time.time()
            runner_thread.join(timeout=10)
            elapsed = time.time() - start
            if elapsed < 10 and result_holder[0] is None:
                time.sleep(10 - elapsed)
            result = result_holder[0]
            execution_message += f"PUSH ROUTER ACTION TO QUEUE: {self.action}\n"
            executed_successfully = True
            if result is None:
                print("Timeout 10 seconds without any response!", flush=True)

        execution_message += f"--- Action Finished ---\n"

        if executed_successfully and result is not None: 
            execution_message += f"Execution Artifact: {result}\n"
            print(execution_message)

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
            print(f"PUSH ROUTER ACTION TO QUEUE: {payload}")
        except Exception as e:
            print(f"Redis push error: {e}")

    def _subscribe_to_response_queue(self, result_holder: list, message_id: str) -> None:
        """
        Block on response queue (BLPOP safeclaw:response:{message_id}, timeout 10s).
        On response: set result_holder[0] = parsed result.
        On timeout/error: result_holder[0] stays None. Ignores errors.
        """
        response_key = f"{RESPONSE_PREFIX}{message_id}"
        try:
            r = self._get_redis()
            print(f"Waiting for response for 10 seconds...")
            # BLPOP blocks for up to 10 seconds
            blpop_result = r.blpop(response_key, timeout=10)
            if blpop_result:
                print("*********RESPONSE_FOUND*************")
                _, raw = blpop_result
                result_holder[0] = json.loads(raw)
        except Exception as e:
            print(f"Redis subscribe error: {e}")

    # dynamic function : MEMORY_WRITE
    def _MEMORY_WRITE(self, params: dict):
        memory_path = self.workspace / "memory.json"
        old_memory = json.loads(memory_path.read_text(encoding="utf-8")) if memory_path.exists() else {}
        new_memory = params["new_memory"]

        # merge old_memory and new_memory
        merged_memory = {**old_memory, **new_memory}

        # write the merged memory to the memory.json
        with open(memory_path, "w") as f:
            json.dump(merged_memory, f, indent=2)

        return {
            "action": "_MEMORY_WRITE",
            "text": f"Memory updated: {merged_memory}"
        }


    # dynamic function : BROWSER_VISION
    def _BROWSER_VISION(self, params: dict):
        url = params["url"]

        # use remote chrome to take a screenshot of the url  
        REMOTE_DRIVER = os.getenv("REMOTE_BROWSER_SERVER")
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1080,1650")
        driver = webdriver.Remote(
            command_executor=REMOTE_DRIVER,
            options=options,
        )
        try:
            driver.get(url)
            dismiss_consent(driver)
            time.sleep(3)  # Let the page stabilize before screenshot

            output_dir = self.workspace / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            html = driver.page_source
            html_path = output_dir / "browser_vision.html"
            html_path.write_text(html, encoding="utf-8")

            screenshot = driver.get_screenshot_as_png()
            png_path = output_dir / "browser_vision.png"
            png_path.write_bytes(screenshot)

            content = driver.find_element(By.TAG_NAME, "body").text
            txt_path = output_dir / "browser_vision.txt"
            txt_path.write_text(content, encoding="utf-8")
        finally:
            driver.quit()

        return {
          "action": "_BROWSER_VISION",
          "url": url,
          "html": str(html_path),
          "screenshot": str(png_path),
          "content": str(txt_path),
          "follow_up": {
            "name": "_LLM_SUMMARY",
            "params": {"content": str(txt_path)}
          }
        }



    # generic LLM function (no prompt and memory and running context)
    def _LLM_SUMMARY(self, params: dict):
        content_file = params["content"]
        path = Path(content_file)
        if not path.is_absolute():
            path = self.workspace / "output" / path.name
        content = path.read_text(encoding="utf-8")

        # use llm to summarize the content
        try:
            summary_prompt = "Summary in 100 words or less to the following content of a website body: \n" + content
            output = llm_chat(summary_prompt)
        except Exception as e:
            output = f"Error: {e}"
            print("(Check LLM_PROVIDER and API key in .env)")

        return {
          "action": "_LLM_SUMMARY",
          "output": output
        }