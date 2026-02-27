# Schedule Feature

Schedule reminders and actions to run at a specific time. The scheduler ticks every minute and executes matching items from `workspace/schedule.json`.

---

## Overview

| Component | Role |
|-----------|------|
| **schedule.json** | Stores scheduled items (reminders, actions) |
| **Scheduler** | Tick thread, checks every minute, runs matching items |
| **_ADD_SCHEDULE** | Agent action to add items |
| **_DELETE_SCHEDULE** | Agent action to remove items |
| **/schedule** | Command to list all scheduled items |

---

## Schedule Item Format

```json
{
  "datetime": "2026-02-24 15:00",
  "type": "reminder | action | prompt",
  "data": {
    "message": "string",
    "action": "string (only when type is action)",
    "param": {} 
  },
  "limit_channel": []
}
```

- **datetime** — `YYYY-MM-DD HH:MM`. Required.
- **type** — `reminder` (broadcast message), `action` (run agent/router action), or `prompt` (run instruction through agent).
- **data.message** — Description or reminder text.
- **data.action** — Agent/router action name (e.g. `_MEMORY_WRITE`, `_BROADCAST_MSG`). Only when `type` is `action`.
- **data.param** — Params for that action. Only when `type` is `action`.
- **limit_channel** — `[]` = all channels; `["Telegram"]` = Telegram only.

---

## Types

### reminder

Broadcasts a message to channels at the scheduled time.

- Uses `data.message`.
- `limit_channel` controls which channels receive it.

**Example:**
```json
{
  "datetime": "2026-02-24 15:00",
  "type": "reminder",
  "data": { "message": "Check your email" },
  "limit_channel": []
}
```

### action

Runs an agent or router action at the scheduled time.

- Uses `data.action` and `data.param`.
- ActionExecutor decides agent vs router (registry lookup).
- Agent actions run locally; router actions push to Redis.

**Example — set memory in 3 mins:**
```json
{
  "datetime": "2026-02-24 14:55",
  "type": "action",
  "data": {
    "message": "Update Task to Done",
    "action": "_MEMORY_WRITE",
    "param": { "new_memory": { "Task": "Done" } }
  },
  "limit_channel": []
}
```

**Example — broadcast in 5 mins:**
```json
{
  "datetime": "2026-02-24 15:00",
  "type": "action",
  "data": {
    "message": "Hello",
    "action": "_BROADCAST_MSG",
    "param": { "message": "Hello", "channels": [] }
  },
  "limit_channel": []
}
```

### prompt

Runs a free-form instruction through the agent (LLM + tools) at the scheduled time. Use when the task needs values computed at runtime (e.g. current datetime) or when the instruction is open-ended.

- Uses `data.message` as the instruction.
- At the scheduled time, the agent runs it as a user prompt (with `_ADD_SCHEDULE` excluded).
- Message order: `[Scheduled]` response first, then tool output (e.g. `_BROADCAST_MSG`).

**Example — get current datetime and broadcast after 3 mins:**

User says:
```
Schedule to run a prompt after 3 mins. Prompt: get current date and time and broadcast
```

This creates:
```json
{
  "datetime": "2026-02-24 18:05",
  "type": "prompt",
  "data": { "message": "get current date and time and broadcast" },
  "limit_channel": []
}
```

At the scheduled time:
1. Agent runs the instruction as a user prompt.
2. LLM calls `_BROADCAST_MSG` with the current datetime.
3. Output order: `[Scheduled]` response first, then the broadcast content (e.g. "The current date and time is 2026-02-24 18:05:00.").

**Other phrasings that work:**
- `Schedule this prompt after 2 mins: Check current datetime and broadcast to telegram`
- `Set this prompt and schedule to run after 3 mins: get current datetime and send it to telegram`

---

## Adding Schedules

Use `_ADD_SCHEDULE` via natural language:

**Reminders:**
- `Remind me to check my email at 3pm tomorrow`
- `Remind me to send postcards at 4pm tomorrow by TELEGRAM`
- `Remind me 1+1=2 in 5 mins`

**Scheduled actions:**
- `Set memory Task to Done after 3 mins`
- `Please help set memory value "Task" to "Done" after 3 mins`
- `Broadcast Hello in 5 mins`

**Scheduled prompts (run instruction at time):**
- `Schedule to run a prompt after 2 mins. Prompt: get current date and time and broadcast`
- `Schedule this prompt after 2 mins: Check current datetime and broadcast to telegram`

For "in X mins", use `relative_minutes` (server computes datetime). For specific times, use `datetime` in `YYYY-MM-DD HH:MM`.

---

## Deleting Schedules

Use `_DELETE_SCHEDULE`:

- `Cancel the 3pm reminder` → match by datetime
- `Remove the email reminder` → match by message (substring)
- `Delete the postcards reminder at 4pm` → match by both

---

## Commands

- **/schedule** — List all scheduled items, sorted by datetime.

---

## Cleanup

The scheduler removes invalid and expired records each tick:

- Invalid: missing datetime, unparseable format, not a dict.
- Expired: datetime before current minute.

---

## Logs

- `logs/schedule.log` — Tick activity, executed items, cleanup.
