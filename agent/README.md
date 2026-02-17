# Agent

Self-contained agent component. Runs separately from the router. Can run on another process or machine on the same network.

## Setup

```bash
cd agent
pip install -r requirements.txt
```

Copy `.env` and set `REDIS_URL`, `REMOTE_BROWSER_SERVER` as needed.

## Run

From agent directory:
```bash
cd agent
python chat.py
```

Or from project root:
```bash
python agent/chat.py
```

## Structure

```
agent/
  chat.py          # Entry point
  .env             # REDIS_URL, REMOTE_BROWSER_SERVER, etc.
  requirements.txt
  libs/
    prompt.py
    action_executor.py
    llm_response.py
    remote_chrome_utils.py
  workspace/
    memory.json
    input_history.json
    PROMPT.md
    ...
```

See agent_design_details.txt for full design documentation.
