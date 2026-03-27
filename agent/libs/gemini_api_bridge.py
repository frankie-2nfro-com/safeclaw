"""Utility to send prompts to Gemini via API bridge (Redis queues)."""

import base64
import binascii
import json
import time
from pathlib import Path
from typing import Any, Optional

import redis

from libs.debug_log import debug_log

REDIS_URL = "redis://192.168.1.153:6379"
PROMPT_QUEUE_IN = "GEMINI_PROMPT_IN"
PROMPT_QUEUE_OUT = "GEMINI_PROMPT_OUT"


def _save_first_multimodal_image(workspace: Path, images: list[Any]) -> Optional[Path]:
    """Write the first base64 image from the bridge to workspace/output/images/download_<ms>.png."""
    if not images:
        return None
    first = images[0]
    if not isinstance(first, str) or not first.strip():
        return None
    try:
        data = base64.standard_b64decode(first.strip())
    except (ValueError, binascii.Error):
        return None
    if not data:
        return None
    out_dir = workspace / "output" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    path = out_dir / f"download_{ts}.png"
    path.write_bytes(data)
    return path


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
    Returns the response text. Parses extension JSON: for text/json/xml/yaml/csv/html code-blocks,
    returns the structured content string only. For multimodal with images, if workspace is set,
    decodes the first image to workspace/output/images/download_<timestamp>.png and returns the
    text content plus a short [Image saved: …] line (no embedded base64). If workspace is omitted,
    multimodal still returns the full JSON string so nothing is dropped.
    Timeout is enforced by BaseLLM._chat_with_timeout for all providers.
    """
    if not prompt or not str(prompt).strip():
        raise ValueError("Prompt is empty")

    try:
        r = redis.from_url(redis_url)
        debug_log(
            f"GEMINI bridge: connected queue_in={PROMPT_QUEUE_IN} queue_out={PROMPT_QUEUE_OUT} "
            f"redis_hint={_redis_log_hint(redis_url)}"
        )
        # Drain stale responses from previous requests (e.g. timeouts) so we get our response
        drained = 0
        while r.llen(PROMPT_QUEUE_OUT) > 0:
            r.lpop(PROMPT_QUEUE_OUT)
            drained += 1
        if drained:
            debug_log(f"GEMINI bridge: drained {drained} stale item(s) from {PROMPT_QUEUE_OUT}")
        req_id = f"req_{int(time.time() * 1000)}"
        payload = {"id": req_id, "prompt": prompt}
        if options and "RENEW_SESSION" in options:
            payload["option"] = "RENEW_SESSION"
        payload_json = json.dumps(payload, ensure_ascii=False)
        r.lpush(PROMPT_QUEUE_IN, payload_json)
        debug_log(
            f"GEMINI bridge: LPUSH {PROMPT_QUEUE_IN} ok id={req_id} prompt_len={len(prompt)} "
            f"payload_bytes={len(payload_json.encode('utf-8'))}"
        )

        _, raw = r.blpop(PROMPT_QUEUE_OUT)
        s = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        resp = json.loads(s)
        raw_response = resp.get("response", "")
        debug_log(f"GEMINI bridge: BLPOP {PROMPT_QUEUE_OUT} ok id={resp.get('id', req_id)} response_len={len(str(raw_response))}")

        # Parse JSON-encoded response from extension (text, json, xml, yaml, multimodal, …)
        content = raw_response
        parsed = None
        try:
            if isinstance(raw_response, str):
                parsed = json.loads(raw_response)
            else:
                parsed = raw_response
            if isinstance(parsed, dict) and "content" in parsed:
                if parsed.get("type") == "multimodal" and parsed.get("images"):
                    if workspace:
                        saved = _save_first_multimodal_image(workspace, parsed["images"])
                        if saved:
                            rel = saved.relative_to(workspace).as_posix()
                            text_part = (parsed.get("content") or "").strip()
                            content = (
                                f"{text_part}\n\n[Image saved: {rel}]"
                                if text_part
                                else f"[Image saved: {rel}]"
                            )
                            parsed = {
                                **parsed,
                                "images": [rel],
                                "images_note": "first image written to workspace path above; base64 omitted",
                            }
                        else:
                            content = json.dumps(parsed, ensure_ascii=False)
                    else:
                        content = json.dumps(parsed, ensure_ascii=False)
                else:
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
        debug_log(f"GEMINI bridge: ERROR {type(e).__name__}: {e}")
        print(f"Error: {e}")
        return ""


def _redis_log_hint(url: str) -> str:
    """Safe one-line hint for logs (no password)."""
    if not url:
        return "(empty)"
    try:
        from urllib.parse import urlparse

        p = urlparse(url)
        host = p.hostname or "?"
        port = f":{p.port}" if p.port else ""
        db = p.path or ""
        return f"{host}{port}{db}"
    except Exception:
        return "(unparsed)"
