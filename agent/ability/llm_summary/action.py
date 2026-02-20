"""LLM summary: summarize file content via LLM."""
import json
from pathlib import Path

from libs.base_agent_action import BaseAgentAction
from libs.logger import dialog, log

from llm import get_llm


class LLMSummaryAction(BaseAgentAction):
    """Summarize content file using LLM."""

    def _get_thinking(self) -> bool:
        """Whether to show thinking status (from config.json)."""
        config_path = self.workspace.parent / "config.json"
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8").strip())
                return cfg.get("thinking", True)
            except (json.JSONDecodeError, ValueError):
                pass
        return True

    def execute(self):
        content_file = self.params.get("content")
        if not content_file:
            return {
                "action": "_LLM_SUMMARY",
                "error": "Missing 'content' param (path to file). Use artifact content path.",
                "status": "failed",
            }
        path = Path(content_file)
        if not path.is_absolute():
            path = self.workspace / "output" / path.name
        content = path.read_text(encoding="utf-8")

        try:
            summary_prompt = (
                "Summary in 100 words or less to the following content of a website body: \n"
                + content
            )
            if self._get_thinking():
                dialog("Waiting for LLM...")
            llm = get_llm(workspace=self.workspace)
            output = llm.chat(summary_prompt)
        except Exception as e:
            output = f"Error: {e}"
            log("(Check LLM_PROVIDER and API key in .env)")

        return {
            "action": "_LLM_SUMMARY",
            "output": output,
        }
