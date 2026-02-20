"""LLM summary: summarize file content via LLM."""
from pathlib import Path

from libs.base_agent_action import BaseAgentAction
from libs.logger import log

from llm import get_llm


class LLMSummaryAction(BaseAgentAction):
    """Summarize content file using LLM."""

    def execute(self):
        content_file = self.params["content"]
        path = Path(content_file)
        if not path.is_absolute():
            path = self.workspace / "output" / path.name
        content = path.read_text(encoding="utf-8")

        try:
            summary_prompt = (
                "Summary in 100 words or less to the following content of a website body: \n"
                + content
            )
            llm = get_llm(workspace=self.workspace)
            output = llm.chat(summary_prompt)
        except Exception as e:
            output = f"Error: {e}"
            log("(Check LLM_PROVIDER and API key in .env)")

        return {
            "action": "_LLM_SUMMARY",
            "output": output,
        }
