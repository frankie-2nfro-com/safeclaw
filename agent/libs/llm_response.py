"""
Parse LLM response: extract message body and <tool_code> content.
Handles formatting variations (whitespace, newlines, markdown).
"""

import re
from typing import Optional, Tuple
import json


class LLMResponseError(Exception):
    """Raised when the LLM response cannot be parsed meaningfully."""

    pass



class LLMResponse:
    """Parsed LLM response with message and actions from <tool_code>."""

    def __init__(self, output: str):
        """
        Parse output and extract message + actions.
        Raises LLMResponseError if output cannot be parsed.
        """
        self.message, self.actions = self._extract_response(output)


    def _extract_response(self, output: str) -> Tuple[str, Optional[str]]:
        """
        Extract message body and tool_code from LLM response.

        Returns:
            (message_body, tool_code_content)
            - message_body: text before <tool_code>, or full text if no tag
            - tool_code_content: content inside first <tool_code>...</tool_code>, or None

        Raises:
            LLMResponseError: if response is empty, too short, or doesn't make sense
        """
        if not output or not isinstance(output, str):
            raise LLMResponseError("Response is empty or invalid")

        text = output.strip()
        if len(text) < 2:
            raise LLMResponseError("Response is too short to be meaningful")

        # Reject garbled output: mostly non-printable or repeated junk
        printable_ratio = sum(1 for c in text if c.isprintable() or c in "\n\t") / max(len(text), 1)
        if printable_ratio < 0.8:
            raise LLMResponseError("Response contains too many unprintable characters")

        # Extract tool_code - flexible: allow whitespace, newlines
        pattern = r"<tool_code>\s*([\s\S]*?)\s*</tool_code>"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if match:
            tool_code_content = match.group(1).strip()
            message_text = text[: match.start()].strip()
            message_text = re.sub(r"\s+$", "", message_text)
            actions = json.loads(tool_code_content)
            return (message_text, actions)

        return (text, None)
