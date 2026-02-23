"""
Scheduler: tick thread, fires every minute aligned to minute boundaries.
Agent owns it and controls lifecycle (start/stop). Logs to logs/schedule.log.
No Redis, no external deps. Extensible for future scheduled tasks.
See agent/README.md and agent_design_details.txt.
"""
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

SCHEDULE_LOG = Path(__file__).resolve().parent.parent / "logs" / "schedule.log"


class Scheduler:
    """Tick scheduler. Agent creates, starts, and stops it."""

    def __init__(self, agent: Optional[object] = None):
        self._agent = agent
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _write_tick(self) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} TICK\n"
        try:
            SCHEDULE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULE_LOG, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass

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
            self._write_tick()

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
