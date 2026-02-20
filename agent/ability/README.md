# Agent abilities

Self-contained agent actions. Each ability lives in its own folder and extends `BaseAgentAction`.

## Registry

`registry.json` maps action names (as used by the LLM) to ability folders. **You must add an entry here when creating a new ability**—do not edit `__init__.py`.

Example:
```json
{
  "_MEMORY_WRITE": "memory_write",
  "MEMORY_WRITE": "memory_write",
  "_BROWSER_VISION": "browser_vision",
  "BROWSER_VISION": "browser_vision"
}
```

## Adding a new ability

1. Create `ability/{folder}/`:
   - `__init__.py`: `from .action import XxxAction` and `__all__ = ["XxxAction"]`
   - `action.py`: `class XxxAction(BaseAgentAction)` with `execute() -> dict`
2. Add to `workspace/agent_action.json` (tool definition for the LLM).
3. **Add to `ability/registry.json`**:
   ```json
   "_SEND_EMAIL": "send_email",
   "SEND_EMAIL": "send_email"
   ```

Convention: folder `send_email` → class `SendEmailAction` (PascalCase of folder + "Action").
