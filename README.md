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

## Prerequisites

### Redis (LAN)

Redis must be running and reachable on your local network. Agent and Router communicate via Redis queues.

- Install Redis on a machine in your LAN (or use Docker: `docker run -d -p 6379:6379 redis`).
- Ensure the Redis host is accessible from both Agent and Router (e.g. `redis://192.168.1.100:6379/0`).
- Agent and Router can run on different machines as long as they can both connect to the same Redis instance.

---

## Quick Start

### 1. Environment setup

Each component needs a `.env` file. Clone the sample and set your values:

```bash
# Agent
cd agent
cp .env.sample .env
# Edit .env: set REDIS_URL (Redis in LAN), REMOTE_BROWSER_SERVER

# Router (in another terminal or machine)
cd router
cp .env.sample .env
# Edit .env: set REDIS_URL (same Redis as Agent)
```

Use your Redis host's LAN IP (e.g. `redis://192.168.1.100:6379/0`) so both Agent and Router can connect.

### 2. Agent

```bash
cd agent
pip install -r requirements.txt
python chat.py
```

Requires: **Ollama** (ollama serve, ollama pull llama3.1:8B).

### 3. Router

```bash
cd router
pip install -r requirements.txt
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
- **VERSIONING.md** – Version workflow, push_new_version.sh, roll_back_version.sh
- **idea.txt** – Architecture vision, biological-first design

---

## Design Principles

- **Decoupling**: Agent and Router run separately; can be on different machines.
- **Agent-Wall**: Router acts as a firewall; only mapped skills execute.
- **Stateless Agent**: Context (memory, artifact, history) is sent with each prompt.
- **Extensible**: Add agent actions in `action_executor.py`; add router skills in `router/skills/`.
