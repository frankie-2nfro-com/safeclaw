"""Delete schedule: remove matching items from schedule.json."""
from libs.base_agent_action import BaseAgentAction
from libs.scheduler import remove_schedule_items


class DeleteScheduleAction(BaseAgentAction):
    """Remove schedule items matching datetime and/or message."""

    def execute(self):
        datetime_str = self.params.get("datetime") or ""
        message = self.params.get("message") or ""
        if not datetime_str and not message:
            return {
                "action": "_DELETE_SCHEDULE",
                "text": "No criteria provided. Specify datetime and/or message to remove.",
            }
        removed = remove_schedule_items(
            self.workspace,
            datetime_str=datetime_str if datetime_str else None,
            message=message if message else None,
        )
        if removed == 0:
            return {
                "action": "_DELETE_SCHEDULE",
                "text": "No matching reminders found.",
            }
        return {
            "action": "_DELETE_SCHEDULE",
            "text": f"Removed {removed} reminder(s).",
        }
