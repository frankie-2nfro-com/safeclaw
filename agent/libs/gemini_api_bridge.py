"""Utility to send prompts to Gemini via API bridge (Redis queues)."""

import json
import time
import redis

REDIS_URL = "redis://192.168.1.153:6379"
PROMPT_QUEUE_IN = "GEMINI_PROMPT_IN"
PROMPT_QUEUE_OUT = "GEMINI_PROMPT_OUT"


def ask_gemini(prompt: str, redis_url: str = REDIS_URL) -> str:
    """
    Send prompt to GEMINI_PROMPT_IN, wait for response from GEMINI_PROMPT_OUT.
    Returns the response text.
    """
    if not prompt or not str(prompt).strip():
        raise ValueError("Prompt is empty")

    r = redis.from_url(redis_url)
    req_id = f"req_{int(time.time() * 1000)}"
    payload = {"id": req_id, "prompt": prompt}
    r.lpush(PROMPT_QUEUE_IN, json.dumps(payload))

    _, raw = r.blpop(PROMPT_QUEUE_OUT)
    resp = json.loads(raw)
    return resp.get("response", "")
