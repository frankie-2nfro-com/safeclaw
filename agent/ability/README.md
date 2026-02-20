# Agent abilities

Self-contained agent actions. Each ability lives in its own folder and extends `BaseAgentAction`.

## Registry

`registry.json` maps action names (as used by the LLM) to ability folders. **You must add an entry here when creating a new ability**—do not edit `__init__.py`.

Example:
```json
{
  "_MEMORY_WRITE": {"ability": "memory_write", "class": "MemoryWriteAction"},
  "MEMORY_WRITE": {"ability": "memory_write", "class": "MemoryWriteAction"},
  "_SEND_EMAIL": {"ability": "send_email", "class": "SendEmailAction"},
  "SEND_EMAIL": {"ability": "send_email", "class": "SendEmailAction"}
}
```

Every entry uses `{"ability": "folder_name", "class": "ClassName"}`.

## Adding a new ability

1. Create `ability/{folder}/`:
   - `__init__.py`: `from .action import XxxAction` and `__all__ = ["XxxAction"]`
   - `action.py`: `class XxxAction(BaseAgentAction)` with `execute() -> dict`
2. Add to `workspace/agent_action.json` (tool definition for the LLM).
3. **Add to `ability/registry.json`**:
   ```json
   "_SEND_EMAIL": {"ability": "send_email", "class": "SendEmailAction"},
   "SEND_EMAIL": {"ability": "send_email", "class": "SendEmailAction"}
   ```
