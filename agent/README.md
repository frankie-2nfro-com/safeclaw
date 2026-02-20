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

## Config

Interactive config prompts:
```bash
./start_agent.py config timeout   # Set request timeout
./start_agent.py config llm       # Set provider and model
./start_agent.py config           # List available keys
```

## Structure

```
agent/
  start_agent.py   # Entry point (run, clear, config)
  config.json      # Runtime config (llm, timeout, channels). Edit or use config command.
  .env             # REDIS_URL, REMOTE_BROWSER_SERVER, API keys
  requirements.txt
  libs/
    agent_config.py    # AgentConfig: load config, interactive prompts
    base_llm.py        # BaseLLM: prompt, parse, process_turn
    action_executor.py
    command.py         # Channel commands: /whoami, /memory, /soul (Console, Telegram)
    remote_chrome_utils.py
  ability/            # Agent actions (memory_write, browser_vision, llm_summary)
    registry.json     # Maps action name -> ability folder (edit when adding abilities)
  llm/             # LLM providers (ollama, openai, gemini)
    ollama/llm.py
    ...
  channel/        # I/O channels (console, telegram)
  workspace/
    memory.json
    input_history.json
    PROMPT.md
    ...
```

## Adding a new ability

1. Add entry to `workspace/agent_action.json` (name, instruction, params).
2. Create `ability/{folder}/` with `__init__.py` and `action.py` extending `BaseAgentAction`.
3. **Add mapping to `ability/registry.json`** (required):
   ```json
   "_MY_ACTION": {"ability": "my_action", "class": "MyActionAction"},
   "MY_ACTION": {"ability": "my_action", "class": "MyActionAction"}
   ```

## Channel commands

In Console or Telegram, type `/` for system commands:

- `/whoami` — Show channel and chat ID
- `/memory` — Show current memory
- `/soul` — Show agent identity (SOUL.md)

Command logic lives in `libs/command.py`; channels call `run_command()`. See agent_design_details.txt for full design documentation.
