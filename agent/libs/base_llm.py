"""
BaseLLM: prompt building, response parsing, process_turn.
Provider-specific chat() is implemented by subclasses (OllamaLLM, GeminiLLM, etc.).
"""
import json
import os
import re
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from libs.debug_log import debug_log
from libs.logger import dialog


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
        path = self.workspace / "router_action.json"
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

    MAX_HISTORY_CHARS = 8000

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
            out = json.dumps(data, indent=2)
            if len(out) <= self.MAX_HISTORY_CHARS:
                return out
            # Truncate: keep last 4 entries, shorten each response to ~150 chars
            kept = data[-4:] if len(data) > 4 else data
            for e in kept:
                r = e.get("response", "")
                if isinstance(r, str) and len(r) > 150:
                    e["response"] = r[:147] + "..."
            return json.dumps(kept, indent=2)
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

        prompt_path = self._root / "llm" / self.provider / "PROMPT.md"
        if not prompt_path.exists():
            prompt_path = self._root / "llm" / "ollama" / "PROMPT.md"
        prompt = self._load_file(prompt_path, "{{USER_MESSAGE}}")
        now = datetime.now()
        prompt = prompt.replace("{{CURRENT_DAY}}", now.strftime("%a"))
        prompt = prompt.replace("{{CURRENT_DATETIME}}", now.strftime("%Y-%m-%d %H:%M:%S"))
        prompt = prompt.replace("{{MEMORY_CONTENT}}", self._load_memory())
        prompt = prompt.replace("{{USER_INPUT_HISTORY}}", self._load_input_history())
        prompt = prompt.replace("{{SOUL_CONTENT}}", self._load_file(self.workspace / "SOUL.md", "You are SafeClaw."))
        prompt = prompt.replace("{{AGENT_ACTIONS}}", self._load_agent_actions(), 1)
        prompt = prompt.replace("{{ROUTER_ACTIONS}}", self._load_router_actions(), 1)
        prompt = prompt.replace("{{USER_MESSAGE}}", clear_escaped_text)

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(prompt, encoding="utf-8")
        return prompt

    @abstractmethod
    def chat(self, prompt: str, options: Optional[list[str]] = None) -> str:
        """Send prompt to LLM and return response. options: optional list of special instructions per provider."""
        pass

    def _get_llm_timeout(self) -> int:
        """Timeout in seconds for LLM chat (from config.json llm_timeout, default 120). Applies to all providers."""
        cfg_path = self.workspace.parent / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8").strip())
                return int(cfg.get("llm_timeout", 120))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        return 120

    def _chat_with_timeout(self, prompt: str, options: Optional[list[str]] = None) -> str:
        """Run chat() with timeout. Returns error string if LLM does not respond in time."""
        timeout_s = self._get_llm_timeout()
        debug_log(
            f"LLM: chat start provider={self.provider} timeout_s={timeout_s} "
            f"prompt_len={len(prompt)} options={options!r}"
        )
        result = [None]
        exc = [None]

        def run():
            try:
                result[0] = self.chat(prompt, options=options)
            except Exception as e:
                exc[0] = e

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=timeout_s)
        if exc[0]:
            debug_log(f"LLM: chat failed exception={exc[0]!r}")
            raise exc[0]
        if t.is_alive():
            debug_log(f"LLM: chat TIMEOUT after {timeout_s}s (thread still running)")
            return "[Timeout] Response did not complete in time."
        out = result[0] or ""
        debug_log(f"LLM: chat ok output_len={len(out)}")
        return out

    def _generic_llm_request(self, instruction: str, data=None) -> Optional[str]:
        """Send instruction (and optionally data) to LLM. Use for summarize, generate, etc. Returns response or None."""
        if not instruction:
            return None
        if data is None:
            prompt = instruction
        else:
            if isinstance(data, list):
                data_str = "\n".join(str(x) for x in data)
            elif isinstance(data, dict):
                data_str = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                data_str = str(data)
            prompt = f"{instruction}\n\n{data_str}" if data_str.strip() else instruction
        try:
            return self._chat_with_timeout(prompt, options=["RENEW_SESSION"]).strip()
        except Exception:
            return None

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
    def process_turn(self, user_input: str, thinking: bool = True) -> str:
        input_history = json.loads((self.workspace / "input_history.json").read_text(encoding="utf-8"))

        prompt = self.create_prompt(user_input)
        if not prompt:
            return ("(Empty prompt, skipping)", False)

        # Log Q immediately (when user asked)
        llm_log_path = self._root / "logs" / "llm.log"
        llm_log_path.parent.mkdir(parents=True, exist_ok=True)
        ts_q = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(llm_log_path, "a", encoding="utf-8") as f:
            f.write(f"{ts_q} Q: {user_input}\n")

        if thinking:
            dialog("Waiting for LLM...")
        debug_log(f"process_turn: built prompt len={len(prompt)}")
        try:
            output = self._chat_with_timeout(prompt)
        except Exception as e:
            debug_log(f"process_turn: LLM error {e!r}")
            return (self._format_chat_error(e), False)

        # Log A when LLM responds (collapse newlines between text and <tool_code>)
        ts_a = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output_for_log = re.sub(r"\s+<tool_code>", " <tool_code>", output)
        with open(llm_log_path, "a", encoding="utf-8") as f:
            f.write(f"{ts_a} A: {output_for_log}\n")
            f.write("\n")

        try:
            message, actions = self._parse_response(output)
            if actions:
                names = [a.get("name", "?") for a in actions if isinstance(a, dict)]
                debug_log(f"process_turn: tool_code actions count={len(actions)} names={names}")
            else:
                debug_log("process_turn: no tool_code; text-only reply")
            response_parts = [message]
            follow_up_results = []

            if actions:
                from libs.action_executor import ActionExecutor
                follow_up_results = []
                digests = []  # Q/A pairs for input_history: [{Q: instruction, A: summary}]
                PARAM_KEYS = {"full_page", "headless", "width", "height"}

                def _strip_params(d):
                    if isinstance(d, dict):
                        return {k: _strip_params(v) for k, v in d.items() if k not in PARAM_KEYS}
                    if isinstance(d, list):
                        return [_strip_params(x) for x in d]
                    return d

                for action in actions:
                    prev_len = len(response_parts)
                    try:
                        try:
                            executor = ActionExecutor(action["name"], action["params"], workspace=self.workspace)
                            executed_result = executor.execute()
                            data = _strip_params(executed_result) if executed_result is not None else None
                        except Exception as e:
                            response_parts.append(f"Error: {e}")
                            continue
                        if executed_result is None:
                            response_parts.append("Action failed: No response from router (timeout or error).")
                            continue
                        if not data or not isinstance(data, dict):
                            continue
                        # Process result immediately so artifact/state is updated before next action
                        if "follow_up" in data:
                            try:
                                fu = data["follow_up"]
                                executor = ActionExecutor(fu["name"], fu["params"], workspace=self.workspace)
                                result = executor.execute()
                                output = result.get("output", str(result))
                                response_parts.append(output)
                                follow_up_results.append({"action": fu["name"], "output": output})
                            except Exception:
                                pass
                        status = (data.get("status") or "").strip()
                        if status == "Failed":
                            err_msg = data.get("text") or data.get("error") or "Something went wrong."
                            response_parts.append(f"Action failed: {err_msg}")
                        elif status == "Executed" or not status:
                            if data.get("text"):
                                response_parts.append(data["text"])
                            if data.get("instruction") and data.get("data"):
                                raw_data = data["data"]
                                if raw_data is not None and raw_data != [] and raw_data != {}:
                                    summary = self._generic_llm_request(
                                        data["instruction"],
                                        raw_data,
                                    )
                                    if summary:
                                        response_parts.append(summary)
                                        digests.append({"Q": data["instruction"], "A": summary})
                    finally:
                        # Flush new content before next action so QUERY result appears before UPDATE
                        if len(response_parts) > prev_len:
                            to_flush = "\n\n".join(response_parts[prev_len:])
                            if to_flush.strip():
                                dialog(to_flush)

            if actions and digests:
                response_for_history = "\n\n".join(d["A"] for d in digests)
            else:
                response_for_history = message
            entry = {"user_input": user_input, "response": response_for_history}
            input_history.append(entry)
            for fu in follow_up_results:
                input_history.append({"follow_up_action": fu["action"], "response": fu["output"]})
            if len(input_history) > 10:
                input_history = input_history[-10:]
            (self.workspace / "input_history.json").write_text(
                json.dumps(input_history, indent=2), encoding="utf-8"
            )

            response = "\n\n".join(response_parts)
            # When we had actions and flushed incrementally, skip duplicate send to Console
            streamed_to_console = bool(actions)
            return (response, streamed_to_console)

        except LLMResponseError as e:
            return (f"(Parse error: {e})", False)

    def _format_chat_error(self, e: Exception) -> str:
        """Override in subclasses for provider-specific error messages."""
        return f"Error: {e}\n(Check API key in .env)"
