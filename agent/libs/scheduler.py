"""
Scheduler: tick thread, fires every minute aligned to minute boundaries.
Agent owns it and controls lifecycle (start/stop). Loads workspace/schedule.json.
Logs to logs/schedule.log. No Redis, no external deps.
See agent/README.md and agent_design_details.txt.
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

SCHEDULE_JSON = "schedule.json"
SCHEDULE_LOG = Path(__file__).resolve().parent.parent / "logs" / "schedule.log"


def normalize_datetime(dt_str: str) -> str:
    """Normalize to YYYY-MM-DD HH:MM for storage and matching. Accepts T or space.
    Handles date-only (YYYY-MM-DD) by appending 00:00. Validates format.
    """
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


def append_schedule_item(workspace: Path, item: dict) -> None:
    """Append item to schedule.json. Used by ADD_SCHEDULE action."""
    path = Path(workspace) / SCHEDULE_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
    try:
        raw = path.read_text(encoding="utf-8").strip()
        data = json.loads(raw) if raw else []
        schedule = data if isinstance(data, list) else []
        schedule.append(item)
        path.write_text(json.dumps(schedule, indent=2), encoding="utf-8")
    except (json.JSONDecodeError, OSError):
        path.write_text(json.dumps([item], indent=2), encoding="utf-8")


def remove_schedule_items(
    workspace: Path,
    datetime_str: Optional[str] = None,
    message: Optional[str] = None,
) -> int:
    """Remove schedule items matching datetime and/or message. Returns count removed.
    At least one of datetime_str or message must be provided.
    datetime: YYYY-MM-DD HH:MM (exact match). message: substring match (case-insensitive).
    """
    if not datetime_str and not message:
        return 0
    path = Path(workspace) / SCHEDULE_JSON
    if not path.exists():
        return 0
    try:
        raw = path.read_text(encoding="utf-8").strip()
        data = json.loads(raw) if raw else []
        schedule = data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return 0

    dt_norm = normalize_datetime(datetime_str) if datetime_str else ""
    msg_lower = message.lower().strip() if message else ""

    def matches(item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        if dt_norm:
            item_dt = item.get("datetime", "")
            if normalize_datetime(item_dt) != dt_norm:
                return False
        if msg_lower:
            data = item.get("data")
            item_msg = (data.get("message", "") if isinstance(data, dict) else "") or item.get("message", "") or ""
            if msg_lower not in item_msg.lower():
                return False
        return True

    original_len = len(schedule)
    schedule = [i for i in schedule if not matches(i)]
    removed = original_len - len(schedule)
    if removed > 0:
        path.write_text(json.dumps(schedule, indent=2), encoding="utf-8")
    return removed


class Scheduler:
    """Tick scheduler. Agent creates, starts, and stops it. Loads schedule.json."""

    def __init__(self, agent: Optional[object] = None):
        self._agent = agent
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._schedule: List[Any] = []
        self._load_schedule()

    def _get_workspace(self) -> Path:
        if self._agent is not None and hasattr(self._agent, "WORKSPACE"):
            return Path(self._agent.WORKSPACE)
        return Path(__file__).resolve().parent.parent / "workspace"

    def _get_schedule_path(self) -> Path:
        return self._get_workspace() / SCHEDULE_JSON

    def _load_schedule(self) -> None:
        """Load schedule.json. Create with [] if missing."""
        path = self._get_schedule_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("[]", encoding="utf-8")
            self._schedule = []
            return
        try:
            raw = path.read_text(encoding="utf-8").strip()
            data = json.loads(raw) if raw else []
            self._schedule = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            self._schedule = []

    def _save_schedule(self) -> None:
        """Write schedule to schedule.json."""
        try:
            self._get_schedule_path().write_text(
                json.dumps(self._schedule, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    @property
    def schedule(self) -> List[Any]:
        """Loaded schedule from schedule.json (read-only)."""
        return self._schedule

    def _log(self, msg: str) -> None:
        """Append to logs/schedule.log."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} {msg}\n"
        try:
            SCHEDULE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULE_LOG, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass

    def _get_item_message(self, item: dict) -> str:
        """Get message from item: data.message (new format) or message (legacy)."""
        data = item.get("data")
        if isinstance(data, dict) and data.get("message"):
            return str(data.get("message", ""))
        return item.get("message") or ""

    def _run_schedule(self, item: dict) -> None:
        """Execute a matched schedule item. Type determines behavior.
        'reminder' -> broadcast to channels.
        'action' -> run via ActionExecutor (agent or router based on action code).
        'prompt' -> run data.message as user input through agent (LLM + tools), broadcast response.
        """
        item_type = (item.get("type") or "reminder").strip().lower()

        if item_type == "reminder":
            message = self._get_item_message(item)
            if message and self._agent and hasattr(self._agent, "broadcast_message"):
                channels = item.get("limit_channel")
                channels = channels if (channels and isinstance(channels, list)) else None
                self._agent.broadcast_message(f"Reminder: {message}", channels)

        elif item_type == "prompt":
            message = self._get_item_message(item)
            if message and self._agent and hasattr(self._agent, "process"):
                try:
                    # Pass as normal user request (_ADD_SCHEDULE excluded when source=Schedule)
                    prompt_input = message
                    result = self._agent.process(prompt_input, source="Schedule", flush_broadcasts_after=True)
                    response, _ = result if isinstance(result, tuple) else (result, False)
                    # Send broadcast content first (tool output), then [Scheduled] response
                    if hasattr(self._agent, "_flush_pending_broadcasts"):
                        self._agent._flush_pending_broadcasts()
                    if response and hasattr(self._agent, "broadcast_message"):
                        channels = item.get("limit_channel")
                        channels = channels if (channels and isinstance(channels, list)) else None
                        self._agent.broadcast_message(f"[Scheduled] {response}", channels)
                    self._log(f"[Schedule] prompt executed: {message[:50]}...")
                except Exception as e:
                    self._log(f"[Schedule] prompt error: {e}")

        elif item_type == "action":
            data = item.get("data")
            if isinstance(data, dict):
                action_name = data.get("action", "").strip()
                param = data.get("param")
                if action_name and isinstance(param, dict):
                    try:
                        from libs.action_executor import ActionExecutor

                        workspace = self._get_workspace()
                        executor = ActionExecutor(action_name, param, workspace=workspace)
                        result = executor.execute()
                        self._log(f"[Schedule] action={action_name} result={result}")
                    except Exception as e:
                        self._log(f"[Schedule] action={action_name} error={e}")

        self._log(f"[Schedule] type={item_type} {item}")

    def _clean_up_schedules(self) -> int:
        """Remove invalid and expired records from schedule. Returns count removed."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        original_len = len(self._schedule)
        kept: List[Any] = []

        for item in self._schedule:
            if not isinstance(item, dict):
                continue
            dt = item.get("datetime", "")
            if not dt or not isinstance(dt, str):
                continue
            dt_norm = normalize_datetime(dt)
            if not dt_norm:
                continue
            if dt_norm < now_str:
                continue
            kept.append(item)

        removed = original_len - len(kept)
        if removed > 0:
            self._schedule[:] = kept
            self._log(f"[Cleanup] removed {removed} invalid/expired record(s)")
        return removed

    def _check_schedule(self) -> None:
        """Reload schedule.json, find records matching current minute, run action, remove from schedule, then clean up."""
        self._load_schedule()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        to_remove: List[int] = []
        for i, item in enumerate(self._schedule):
            if not isinstance(item, dict):
                continue
            dt = item.get("datetime", "")
            dt_norm = dt.replace("T", " ")[:16] if isinstance(dt, str) else ""
            if dt_norm.strip() == now_str:
                self._run_schedule(item)
                to_remove.append(i)
        if to_remove:
            for i in reversed(to_remove):
                self._schedule.pop(i)
        cleanup_removed = self._clean_up_schedules()
        if to_remove or cleanup_removed > 0:
            self._save_schedule()
        if not to_remove:
            self._log("No Action")

    def _tick_loop(self) -> None:
        """Wait until next minute boundary, then tick every 60s. Stops when _stop_event is set."""
        while not self._stop_event.is_set():
            now = datetime.now()
            secs_until_next = 60 - (now.second + now.microsecond / 1_000_000)
            if secs_until_next < 59:
                if self._stop_event.wait(timeout=secs_until_next):
                    return

            if self._stop_event.is_set():
                return
            self._check_schedule()

            now = datetime.now()
            secs_until_next = 60 - (now.second + now.microsecond / 1_000_000)
            timeout = secs_until_next if secs_until_next >= 1 else 60
            if self._stop_event.wait(timeout=timeout):
                return

    def start(self) -> None:
        """Start the tick thread. Call when agent starts."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the tick thread to stop. Call when agent shuts down."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
