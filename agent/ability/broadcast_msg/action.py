"""Broadcast message: write to broadcast_pending.json for agent to flush to channels."""
import json
from pathlib import Path

from libs.base_agent_action import BaseAgentAction

BROADCAST_PENDING = "broadcast_pending.json"


def _append_broadcast_pending(workspace: Path, message: str, channels: list) -> None:
    """Append a broadcast request to workspace/broadcast_pending.json."""
    path = workspace / BROADCAST_PENDING
    path.parent.mkdir(parents=True, exist_ok=True)
    item = {"message": message, "channels": channels if channels else []}
    existing = {"pending": []}
    if path.exists():
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                data = json.loads(raw)
                existing["pending"] = data.get("pending", [])
                if not isinstance(existing["pending"], list):
                    existing["pending"] = []
        except (json.JSONDecodeError, OSError):
            pass
    existing["pending"].append(item)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


class BroadcastMsgAction(BaseAgentAction):
    """Queue a broadcast message. Agent flushes to channels after process_turn."""

    def execute(self):
        message = self.params.get("message") or ""
        channels = self.params.get("channels")
        if channels is None:
            channels = []
        if not isinstance(channels, list):
            channels = []
        channels = [str(c).strip() for c in channels if c]
        _append_broadcast_pending(self.workspace, message, channels)
        ch_str = "all channels" if not channels else ", ".join(channels)
        return {
            "action": "_BROADCAST_MSG",
            "text": f"Broadcast queued to {ch_str}.",
        }
