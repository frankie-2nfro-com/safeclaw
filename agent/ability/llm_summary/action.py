"""LLM summary: summarize file content via LLM."""
import json
import os
from pathlib import Path

from libs.base_agent_action import BaseAgentAction
from libs.logger import dialog, log

from llm import get_llm


class LLMSummaryAction(BaseAgentAction):
    """Summarize content file using LLM."""

    def _get_config(self) -> dict:
        """Load config.json. Use same provider/model as main agent."""
        config_path = self.workspace.parent / "config.json"
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding="utf-8").strip())
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def _get_thinking(self) -> bool:
        """Whether to show thinking status (from config.json)."""
        return self._get_config().get("thinking", True)

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
            cfg = self._get_config()
            llm_cfg = cfg.get("llm", {})
            provider = llm_cfg.get("provider") or os.getenv("LLM_PROVIDER", "ollama")
            model = llm_cfg.get("model") or os.getenv("LLM_MODEL", "llama3.1:8B")
            llm = get_llm(workspace=self.workspace, provider=provider, model=model)
            output = llm.chat(summary_prompt)
        except Exception as e:
            output = f"Error: {e}"
            log("(Check LLM_PROVIDER and API key in .env)")

        return {
            "action": "_LLM_SUMMARY",
            "output": output,
        }
