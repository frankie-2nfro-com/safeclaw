# SafeClaw

A production-ready agentic system with a **Think-Act-Observe** loop, an **Agent-Wall** (Router), and Redis queues for decoupled execution. The Agent reasons and decides; the Router guards and executes external actions.

---

## Architecture

```
┌─────────────────┐     Redis      ┌─────────────────┐
│     Agent       │ ─────────────► │     Router      │
│  (The Mind)     │  command_queue │  (Agent-Wall)   │
│                 │ ◄───────────── │                 │
│  Think-Act-     │  response:{id} │  Skills         │
│  Observe loop   │                │  (CREATE_POST,  │
└─────────────────┘                │   etc.)         │
        │                          └─────────────────┘
        │
        ▼
   Ollama / LLM
```

- **Agent**: Reads input, builds prompt (SOUL, memory, artifact), sends to LLM, parses `<tool_code>` actions. Runs agent actions locally; pushes router actions to Redis and waits for response.
- **Router**: Consumes commands from Redis, routes by action name to skills, executes, pushes result back. Runs as a separate process (or on another machine).
- **Queues**: `COMMAND_QUEUE` (agent → router), `RESPONSE_PREFIX` + message_id (router → agent).

---

## Project Structure

```
SafeClaw/
├── README.md              # This file – whole project overview
├── idea.txt               # Architecture notes, vision
├── todo.txt
│
├── agent/                 # Self-contained "Mind" component
│   ├── chat.py            # Entry point
│   ├── libs/              # prompt, action_executor, llm_response, remote_chrome_utils
│   ├── workspace/         # PROMPT.md, SOUL.md, memory, artifacts
│   ├── README.md
│   └── agent_design_details.txt
│
├── router/                # Self-contained "Agent-Wall" component
│   ├── start_router.py    # Entry point
│   ├── libs/              # Router class, BaseSkill
│   ├── skills/            # create_post, etc.
│   ├── README.md
│   └── router_design_details.txt
│
├── test_queue_sub.py      # Monitor/simulate Redis queue (testing)
└── test_prompt.py         # Test prompt generation
```

---

## Quick Start

### 1. Redis

Ensure Redis is running. Agent and Router both need `REDIS_URL` in their `.env`.

### 2. Agent

```bash
cd agent
pip install -r requirements.txt
# Copy .env, set REDIS_URL, REMOTE_BROWSER_SERVER
python chat.py
```

Requires: **Ollama** (ollama serve, ollama pull llama3.1:8B).

### 3. Router

```bash
cd router
pip install -r requirements.txt
# Copy .env, set REDIS_URL
python start_router.py
```

### 4. Run both

- Terminal 1: `cd router && python start_router.py`
- Terminal 2: `cd agent && python chat.py`

---

## Components

| Component | Role | Runs |
|-----------|------|------|
| **Agent** | Think-Act-Observe loop, LLM calls, local actions, queue push | `agent/chat.py` |
| **Router** | Consume queue, route to skills, execute, push response | `router/start_router.py` |
| **Redis** | Command queue, response queues | External |

---

## Agent Actions (local)

- `_MEMORY_WRITE` – Update memory.json
- `_BROWSER_VISION` – Screenshot/HTML via remote Chrome
- `_LLM_SUMMARY` – Summarize content via Ollama

## Router Actions (via queue)

- `CREATE_POST` – Social post (stub; extend in `router/skills/create_post/`)

---

## Documentation

- **agent/agent_design_details.txt** – Agent structure, components, actions, config
- **router/router_design_details.txt** – Router structure, skills, Redis flow, adding skills
- **idea.txt** – Architecture vision, biological-first design

---

## Design Principles

- **Decoupling**: Agent and Router run separately; can be on different machines.
- **Agent-Wall**: Router acts as a firewall; only mapped skills execute.
- **Stateless Agent**: Context (memory, artifact, history) is sent with each prompt.
- **Extensible**: Add agent actions in `action_executor.py`; add router skills in `router/skills/`.
