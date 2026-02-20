"""
BaseLLM: prompt building, response parsing, process_turn.
Provider-specific chat() is implemented by subclasses (OllamaLLM, GeminiLLM, etc.).
"""
import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


class LLMResponseError(Exception):
    """Raised when the LLM response cannot be parsed meaningfully."""
    pass


class BaseLLM(ABC):
    """Base LLM: prompt, parse, process_turn. Subclasses implement chat() for provider-specific connection."""

    def __init__(self, workspace: Path, provider: str = "ollama", model: Optional[str] = None):
        self.workspace = workspace
        self.provider = provider or os.getenv("LLM_PROVIDER", "ollama")
        self.model = model or os.getenv("LLM_MODEL", "llama3.1:8B")
        self._root = Path(__file__).resolve().parent.parent
        self.output_file = workspace / "output" / "prompt_cache.txt"

    # --- Prompt (from prompt.py) ---
    def _load_file(self, path: Path, default: str = "") -> str:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return default

    def _load_memory(self) -> str:
        path = self.workspace / "memory.json"
        if not path.exists():
            return "{}"
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return "{}"
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return json.dumps(dict(data) if hasattr(data, "__iter__") else {}, indent=2)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return raw

    def _load_agent_actions(self) -> str:
        path = self.workspace / "agent_action.json"
        if not path.exists():
            return "[]"
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return "[]"
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                return json.dumps([data], indent=2)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return raw

    def _load_router_actions(self) -> str:
        path = self.workspace / "router_actions.json"
        if not path.exists():
            return "[]"
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return "[]"
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                return json.dumps([data], indent=2)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return raw

    def _load_input_history(self) -> str:
        path = self.workspace / "input_history.json"
        if not path.exists():
            return "[]"
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return "[]"
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                return json.dumps([data], indent=2)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return raw

    def _load_artifact(self) -> str:
        path = self.workspace / "artifact.json"
        if not path.exists():
            return "(No artifact)"
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return "{}"
        try:
            data = json.loads(raw)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return raw

    def _escape_user_input(self, text: str) -> str:
        if not text:
            return ""
        escaped = text.replace("</user_input>", "[REDACTED TAG]")
        escaped = escaped.replace("</", "<\\/")
        return escaped

    def create_prompt(self, user_input: str) -> Optional[str]:
        clear_escaped_text = self._escape_user_input(user_input.strip())
        if not clear_escaped_text:
            return None

        prompt = self._load_file(self.workspace / "PROMPT.md", "{{USER_MESSAGE}}")
        prompt = prompt.replace("{{MEMORY_CONTENT}}", self._load_memory())
        prompt = prompt.replace("{{ARTIFACT}}", self._load_artifact())
        prompt = prompt.replace("{{USER_INPUT_HISTORY}}", self._load_input_history())
        prompt = prompt.replace("{{SOUL_CONTENT}}", self._load_file(self.workspace / "SOUL.md", "You are SafeClaw."))
        prompt = prompt.replace("{{AGENT_ACTIONS}}", self._load_agent_actions(), 1)
        prompt = prompt.replace("{{ROUTER_ACTIONS}}", self._load_router_actions(), 1)
        prompt = prompt.replace("{{USER_MESSAGE}}", clear_escaped_text)

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(prompt, encoding="utf-8")
        return prompt

    @abstractmethod
    def chat(self, prompt: str) -> str:
        """Send prompt to LLM and return response. Implemented by provider subclasses."""
        pass

    # --- Response parsing (from llm_response.py) ---
    def _parse_response(self, output: str) -> Tuple[str, Optional[list]]:
        if not output or not isinstance(output, str):
            raise LLMResponseError("Response is empty or invalid")

        text = output.strip()
        if len(text) < 2:
            raise LLMResponseError("Response is too short to be meaningful")

        printable_ratio = sum(1 for c in text if c.isprintable() or c in "\n\t") / max(len(text), 1)
        if printable_ratio < 0.8:
            raise LLMResponseError("Response contains too many unprintable characters")

        pattern = r"<tool_code>\s*([\s\S]*?)\s*</tool_code>"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if match:
            tool_code_content = match.group(1).strip()
            message_text = text[: match.start()].strip()
            message_text = re.sub(r"\s+$", "", message_text)
            actions = json.loads(tool_code_content)
            return (message_text, actions)

        return (text, None)

    # --- Process turn (from chat_core.py) ---
    def process_turn(self, user_input: str) -> str:
        input_history = json.loads((self.workspace / "input_history.json").read_text(encoding="utf-8"))

        prompt = self.create_prompt(user_input)
        if not prompt:
            return "(Empty prompt, skipping)"

        try:
            output = self.chat(prompt)
        except Exception as e:
            return self._format_chat_error(e)

        try:
            message, actions = self._parse_response(output)
            response_parts = [message]
            follow_up_results = []

            if actions:
                from libs.action_executor import ActionExecutor
                artifact = {"timestamp": datetime.now().isoformat(), "data": []}
                for action in actions:
                    try:
                        executor = ActionExecutor(action["name"], action["params"], workspace=self.workspace)
                        executed_result = executor.execute()
                        artifact["data"].append({"data": executed_result})
                    except Exception as e:
                        response_parts.append(f"Error: {e}")

                follow_up_results = []
                for follow_info in artifact["data"]:
                    if (
                        follow_info.get("data")
                        and isinstance(follow_info["data"], dict)
                        and "follow_up" in follow_info["data"]
                    ):
                        try:
                            fu = follow_info["data"]["follow_up"]
                            executor = ActionExecutor(fu["name"], fu["params"], workspace=self.workspace)
                            result = executor.execute()
                            output = result.get("output", str(result))
                            response_parts.append(output)
                            follow_up_results.append({"action": fu["name"], "output": output})
                        except Exception:
                            pass

                artifact["follow_up_results"] = follow_up_results
                (self.workspace / "artifact.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")

            input_history.append({"user_input": user_input, "response": message})
            for fu in follow_up_results:
                input_history.append({"follow_up_action": fu["action"], "response": fu["output"]})
            if len(input_history) > 10:
                input_history = input_history[-10:]
            (self.workspace / "input_history.json").write_text(
                json.dumps(input_history, indent=2), encoding="utf-8"
            )

            return "\n\n".join(response_parts)

        except LLMResponseError as e:
            return f"(Parse error: {e})"

    def _format_chat_error(self, e: Exception) -> str:
        """Override in subclasses for provider-specific error messages."""
        return f"Error: {e}\n(Check API key in .env)"
