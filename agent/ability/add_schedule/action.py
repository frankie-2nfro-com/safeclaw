"""Add schedule: append a schedule item to schedule.json."""
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
        item = {
            "datetime": normalize_datetime(self.params.get("datetime", "")),
            "type": self.params.get("type", "reminder"),
            "message": self.params.get("message", ""),
            "limit_channel": limit_channel,
        }
        append_schedule_item(self.workspace, item)
        return {
            "action": "_ADD_SCHEDULE",
            "text": f"Scheduled: {item['datetime']} - {item['message']}",
        }
