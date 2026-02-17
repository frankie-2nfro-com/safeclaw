from pathlib import Path
from typing import Optional
import json
import sys


class Prompt:
    def __init__(self, workspace: Optional[Path] = None, output_file: Optional[Path] = None):
        self._root = Path(__file__).parent.parent
        self.workspace = workspace or (self._root / "workspace")
        self.output_file = output_file or (self.workspace / "output" / "prompt_cache.txt")  

    def _load_file(self, path: Path, default: str = "") -> str:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return default

    def _load_memory(self) -> str:
        """Load memory.json. Returns formatted JSON for <memory> block."""
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
        """Load agent_action.json. Returns formatted JSON for <agent_action> block."""
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
        """Load router_actions.json. Returns formatted JSON for <router_action> block."""
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
        """Load input_history.json. Returns formatted JSON for <user_input_history> block."""
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
        """Load artifact.json. Returns formatted JSON or placeholder if empty/invalid."""
        artifact_path = self.workspace / "artifact.json"
        if not artifact_path.exists():
            return "(No artifact)"
        raw = artifact_path.read_text(encoding="utf-8").strip()
        if not raw:
            return "{}"
        try:
            data = json.loads(raw)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return raw

    def _escape_user_input(self, text: str) -> str:
        """Escape closing tags: </user_input> -> [REDACTED TAG], </ -> <\\/"""
        if not text:
            return ""
        escaped = text.replace("</user_input>", "[REDACTED TAG]")
        escaped = escaped.replace("</", "<\\/")
        return escaped

    def create_prompt(self, user_input: str) -> str:
        """
        Build prompt from PROMPT.md template.
        Escapes user_input to prevent tag injection, merges SOUL, MEMORY, AGENT_ACTION,
        ROUTER_ACTION, and writes result to workspace/output/prompt_cache.txt.
        Returns the merged prompt string.
        """
        clear_escaped_text = self._escape_user_input(user_input.strip())
        if not clear_escaped_text:
            return None

        prompt = self._load_file(self.workspace / "PROMPT.md", "{{USER_MESSAGE}}")
    
        memory = self._load_memory()
        prompt = prompt.replace("{{MEMORY_CONTENT}}", memory)

        artifact = self._load_artifact()
        prompt = prompt.replace("{{ARTIFACT}}", artifact)

        input_history = self._load_input_history()
        prompt = prompt.replace("{{USER_INPUT_HISTORY}}", input_history)

        soul = self._load_file(self.workspace / "SOUL.md", "You are SafeClaw.")
        prompt = prompt.replace("{{SOUL_CONTENT}}", soul)

        agent_actions = self._load_agent_actions()
        prompt = prompt.replace("{{AGENT_ACTIONS}}", agent_actions, 1)

        router_actions = self._load_router_actions()
        prompt = prompt.replace("{{ROUTER_ACTIONS}}", router_actions, 1)

        prompt = prompt.replace("{{USER_MESSAGE}}", clear_escaped_text)

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(prompt, encoding="utf-8")
        return prompt


if __name__ == "__main__":
    print("Don't run this file directly. Use the prompt.py script instead.")
    sys.exit(1)
