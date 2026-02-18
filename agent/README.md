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
python start_agent.py
```

Or from project root:
```bash
python agent/start_agent.py
```

## Structure

```
agent/
  start_agent.py   # Entry point
  .env             # REDIS_URL, REMOTE_BROWSER_SERVER, LLM_PROVIDER, etc.
  requirements.txt
  libs/
    action_executor.py
    remote_chrome_utils.py
  llm/             # LLM providers (ollama, openai, gemini)
    base_llm.py
    ollama/llm.py
    ...
  channel/        # I/O channels (console, telegram)
  workspace/
    memory.json
    input_history.json
    PROMPT.md
    ...
```

See agent_design_details.txt for full design documentation.
