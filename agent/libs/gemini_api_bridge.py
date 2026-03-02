"""Utility to send prompts to Gemini via API bridge (Redis queues)."""

import json
import time
from pathlib import Path
from typing import Optional

import redis

REDIS_URL = "redis://192.168.1.153:6379"
PROMPT_QUEUE_IN = "GEMINI_PROMPT_IN"
PROMPT_QUEUE_OUT = "GEMINI_PROMPT_OUT"


def ask_gemini(
    prompt: str,
    redis_url: str = REDIS_URL,
    options: Optional[list] = None,
    workspace: Optional[Path] = None,
) -> str:
    """
    Send prompt to GEMINI_PROMPT_IN, wait for response from GEMINI_PROMPT_OUT.
    options: optional list of special instructions for the bridge.
    workspace: if provided, store full response JSON to workspace/artifact.json.
    Returns the response text (parses {"type":"text","content":"..."} and returns content).
    """
    if not prompt or not str(prompt).strip():
        raise ValueError("Prompt is empty")

    try:
        r = redis.from_url(redis_url)
        req_id = f"req_{int(time.time() * 1000)}"
        payload = {"id": req_id, "prompt": prompt}
        if options and "RENEW_SESSION" in options:
            payload["option"] = "RENEW_SESSION"
        r.lpush(PROMPT_QUEUE_IN, json.dumps(payload))

        _, raw = r.blpop(PROMPT_QUEUE_OUT)
        resp = json.loads(raw)
        raw_response = resp.get("response", "")

        # Parse JSON-encoded response: {"type":"text","content":"..."}
        content = raw_response
        parsed = None
        try:
            if isinstance(raw_response, str):
                parsed = json.loads(raw_response)
            else:
                parsed = raw_response
            if isinstance(parsed, dict) and "content" in parsed:
                content = parsed.get("content", raw_response)
        except (json.JSONDecodeError, TypeError):
            pass

        # Store full response to workspace/artifact.json
        # Skip overwrite when content contains <tool_code> - LLM is delegating to tools, not final result.
        # Preserve previous artifact so USE_ARTIFACT can access the last meaningful result.
        if workspace:
            content_str = content if isinstance(content, str) else json.dumps(content)
            if "<tool_code>" not in content_str.lower():
                artifact_path = workspace / "artifact.json"
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                to_store = parsed if parsed is not None and isinstance(parsed, dict) else resp
                artifact_path.write_text(json.dumps(to_store, indent=2, ensure_ascii=False), encoding="utf-8")

        return content if isinstance(content, str) else json.dumps(content)
    except Exception as e:
        print(f"Error: {e}")
        return ""
