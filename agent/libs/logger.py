"""
System logging. Writes to agent/logs/system.log.
Console shows only user/agent dialog.
"""
import logging
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "system.log"
_configured = False


def logging_setup():
    """Configure logging to logs/system.log. Idempotent."""
    global _configured
    if _configured:
        return
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
        force=True,
    )
    _configured = True


def log(msg: str, level: str = "info") -> None:
    """Log to system.log. Does not print to console."""
    logging_setup()
    getattr(logging, level.lower())(msg)


def dialog(msg: str) -> None:
    """Log to system.log AND print to console (part of chat dialog)."""
    logging_setup()
    logging.info(msg)
    print(msg, flush=True)
