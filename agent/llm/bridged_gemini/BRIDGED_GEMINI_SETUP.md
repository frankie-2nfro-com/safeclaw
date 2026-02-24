# Bridged Gemini Setup

Uses Gemini via a bridge (e.g. Chrome extension) that communicates through Redis queues.

## Prerequisites

1. **Redis** — Running and reachable (bridge and agent both connect).
2. **Bridge** — Listens on `GEMINI_PROMPT_IN`, pushes responses to `GEMINI_PROMPT_OUT`.

## Config

Set provider in `config.json`:

```json
{
  "llm": {
    "provider": "bridged_gemini",
    "model": "gemini"
  }
}
```

Or via env:

```
LLM_PROVIDER=bridged_gemini
REDIS_URL=redis://192.168.1.153:6379
```

## Redis queues

- **GEMINI_PROMPT_IN** — Agent pushes `{"id": "req_...", "prompt": "..."}`.
- **GEMINI_PROMPT_OUT** — Bridge pushes `{"response": "..."}`.

See `libs/gemini_api_bridge.py` for the protocol.
