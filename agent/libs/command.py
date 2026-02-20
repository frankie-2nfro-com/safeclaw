"""
Channel commands: whoami, memory, soul, restart.
Logic lives here; channels call these and send the response to the user.
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

COMMANDS: List[Tuple[str, str]] = [
    ("whoami", "Show your chat ID"),
    ("memory", "Show current memory"),
    ("soul", "Show agent identity and beliefs"),
    ("restart", "Restart the agent"),
]


def usage() -> str:
    """Return the command list for usage/help."""
    lines = [f"/{name} - {desc}" for name, desc in COMMANDS]
    return "Available commands:\n" + "\n".join(lines)


def whoami(source: str, chat_id: Optional[int] = None) -> str:
    """Return whoami response. source is channel name (Console, Telegram, WhatsApp, etc.)."""
    base = f"You are using {source.lower()}."
    if chat_id is not None:
        return f"{base} [Chat ID: {chat_id}]"
    return base


def memory(workspace: Path) -> str:
    """Return formatted memory content from workspace/memory.json."""
    path = workspace / "memory.json"
    if not path.exists():
        return "(No memory)"
    try:
        raw = path.read_text(encoding="utf-8").strip()
        data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            data = {}
        if not data:
            return "(Empty memory)"
        lines = [f"• {k}: {v}" for k, v in data.items()]
        return "Memory:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error reading memory: {e}"


def soul(workspace: Path) -> str:
    """Return soul content from workspace/SOUL.md."""
    path = workspace / "SOUL.md"
    if not path.exists():
        return "(No soul)"
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return "(Empty soul)"
        return text
    except Exception as e:
        return f"Error reading soul: {e}"


def restart(workspace: Path) -> str:
    """Return restart message. Call perform_restart() after sending to user."""
    return "Restarting agent..."


def perform_restart(workspace: Path) -> None:
    """
    Restart the agent by re-execing. Replaces current process in-place,
    preserving stdin/stdout - avoids keystroke splitting.
    Never returns.
    """
    agent_dir = workspace.parent
    script = agent_dir / "start_agent.py"
    if not script.exists():
        script = agent_dir.parent / "agent" / "start_agent.py"
        agent_dir = script.parent
    os.chdir(agent_dir)
    os.execv(sys.executable, [sys.executable, str(script)] + sys.argv[1:])


def run_command(
    name: str, workspace: Path, source: str, chat_id: Optional[int] = None
) -> Optional[str]:
    """
    Run a command by name. Returns response string or None if unknown.
    Channels call this and send the result to the user.
    source: channel name (Console, Telegram, WhatsApp, etc.)
    """
    if name == "whoami":
        return whoami(source, chat_id)
    if name == "memory":
        return memory(workspace)
    if name == "soul":
        return soul(workspace)
    if name == "restart":
        return restart(workspace)
    return None
