"""
Optional debug trace to agent/logs/debug.log.
Enable with: ./start_agent.py DEBUG  (or any argv token DEBUG, case-insensitive)
Cleared with: ./start_agent.py clear  (same as other logs)
"""
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

_lock = threading.Lock()
AGENT_DEBUG = False

AGENT_DIR = Path(__file__).resolve().parent.parent
DEBUG_LOG_PATH = AGENT_DIR / "logs" / "debug.log"


def init_from_argv(argv: list) -> None:
    """Set AGENT_DEBUG if argv contains DEBUG (excluding config subcommand)."""
    global AGENT_DEBUG
    if not argv or len(argv) < 2:
        AGENT_DEBUG = False
        return
    if argv[1].lower() == "config":
        AGENT_DEBUG = False
        return
    AGENT_DEBUG = any(str(a).lower() == "debug" for a in argv[1:])


def is_debug() -> bool:
    return AGENT_DEBUG


def truncate_debug(s: Any, max_len: int = 800) -> str:
    t = s if isinstance(s, str) else repr(s)
    if len(t) <= max_len:
        return t
    return t[:max_len] + f"... ({len(t)} chars total)"


def debug_log(msg: str) -> None:
    """Append one line to logs/debug.log if DEBUG mode is on."""
    if not AGENT_DEBUG:
        return
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with _lock:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
