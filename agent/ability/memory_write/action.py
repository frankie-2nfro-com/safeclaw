"""Memory write: merge new_memory into memory.json."""
import json
from pathlib import Path

from libs.base_agent_action import BaseAgentAction


class MemoryWriteAction(BaseAgentAction):
    """Write/merge memory to workspace/memory.json."""

    def execute(self):
        memory_path = self.workspace / "memory.json"
        old_memory = json.loads(memory_path.read_text(encoding="utf-8")) if memory_path.exists() else {}
        new_memory = self.params["new_memory"]

        merged_memory = {**old_memory, **new_memory}

        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(merged_memory, f, indent=2)

        return {
            "action": "_MEMORY_WRITE",
            "text": f"Memory updated: {merged_memory}",
        }
