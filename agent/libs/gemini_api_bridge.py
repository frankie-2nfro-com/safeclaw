"""Utility to send prompts to Gemini via API bridge (Redis queues)."""

import json
import time
from typing import Optional

import redis

REDIS_URL = "redis://192.168.1.153:6379"
PROMPT_QUEUE_IN = "GEMINI_PROMPT_IN"
PROMPT_QUEUE_OUT = "GEMINI_PROMPT_OUT"


def ask_gemini(prompt: str, redis_url: str = REDIS_URL, options: Optional[list] = None) -> str:
    """
    Send prompt to GEMINI_PROMPT_IN, wait for response from GEMINI_PROMPT_OUT.
    options: optional list of special instructions for the bridge.
    Returns the response text.
    """
    if not prompt or not str(prompt).strip():
        raise ValueError("Prompt is empty")

    try:
        r = redis.from_url(redis_url)
        req_id = f"req_{int(time.time() * 1000)}"
        payload = {"id": req_id, "prompt": prompt}
        # check if options contains RENEW_SESSION
        if options and "RENEW_SESSION" in options:
            # request to renew gemini session 
            payload["option"] = "RENEW_SESSION"
        r.lpush(PROMPT_QUEUE_IN, json.dumps(payload))

        _, raw = r.blpop(PROMPT_QUEUE_OUT)
        resp = json.loads(raw)
        return resp.get("response", "")
    except Exception as e:
        print(f"Error: {e}")
        return ""
