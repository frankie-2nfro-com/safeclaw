"""Add schedule: append a schedule item to schedule.json."""
from datetime import datetime

from libs.base_agent_action import BaseAgentAction
from libs.scheduler import append_schedule_item


def _normalize_datetime(dt_str: str) -> str:
    """Normalize to YYYY-MM-DD HH:MM for scheduler matching. Accepts T or space."""
    if not dt_str or not isinstance(dt_str, str):
        return ""
    s = dt_str.strip().replace("T", " ")
    if len(s) >= 16:
        s = s[:16]
    elif len(s) == 10:
        s = s + " 00:00"
    try:
        parsed = datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return s[:16] if len(s) >= 16 else s


class AddScheduleAction(BaseAgentAction):
    """Append a schedule item to workspace/schedule.json."""

    def execute(self):
        limit_channel = self.params.get("limit_channel")
        if limit_channel is None:
            limit_channel = []
        if not isinstance(limit_channel, list):
            limit_channel = []
        item = {
            "datetime": _normalize_datetime(self.params.get("datetime", "")),
            "type": self.params.get("type", "reminder"),
            "message": self.params.get("message", ""),
            "limit_channel": limit_channel,
        }
        append_schedule_item(self.workspace, item)
        return {
            "action": "_ADD_SCHEDULE",
            "text": f"Scheduled: {item['datetime']} - {item['message']}",
        }
