"""Add schedule: append a schedule item to schedule.json."""
from datetime import datetime, timedelta

from libs.base_agent_action import BaseAgentAction
from libs.scheduler import append_schedule_item, normalize_datetime


class AddScheduleAction(BaseAgentAction):
    """Append a schedule item to workspace/schedule.json."""

    def execute(self):
        limit_channel = self.params.get("limit_channel")
        if limit_channel is None:
            limit_channel = []
        if not isinstance(limit_channel, list):
            limit_channel = []

        # When user says "in X mins", use relative_minutes to compute datetime server-side (avoids LLM errors)
        relative_minutes = self.params.get("relative_minutes")
        if relative_minutes is not None:
            try:
                mins = int(relative_minutes)
                if mins >= 0:
                    target = datetime.now() + timedelta(minutes=mins)
                    dt_str = target.strftime("%Y-%m-%d %H:%M")
                else:
                    dt_str = normalize_datetime(self.params.get("datetime", ""))
            except (TypeError, ValueError):
                dt_str = normalize_datetime(self.params.get("datetime", ""))
        else:
            dt_str = normalize_datetime(self.params.get("datetime", ""))

        item = {
            "datetime": dt_str,
            "type": self.params.get("type", "reminder"),
            "message": self.params.get("message", ""),
            "limit_channel": limit_channel,
        }
        append_schedule_item(self.workspace, item)
        return {
            "action": "_ADD_SCHEDULE",
            "text": f"Scheduled: {item['datetime']} - {item['message']}",
        }
