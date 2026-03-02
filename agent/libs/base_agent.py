"""
Base agent: workspace, process_turn logic, and channels.
Channels are I/O (ConsoleChannel, TelegramChannel, etc.) - parts of the agent.
On startup: load config.json (clone from config_initial.json if missing), use llm settings to select LLM class.
"""
import atexit
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from channel.console.channel import ConsoleChannel
from channel.headless.channel import HeadlessChannel
from libs.agent_config import AgentConfig
from libs.logger import dialog, log, logging_setup
from libs.scheduler import Scheduler
from channel.telegram.channel import TelegramChannel
from llm import get_llm


class BaseAgent:
    """Agent with channels. Console is always loaded; others from config."""

    # Agent variables
    AGENT_DIR = Path(__file__).resolve().parent.parent
    WORKSPACE = AGENT_DIR / "workspace"

    WORKSPACE_DEFAULTS = {
        "memory.json": {},
        "input_history.json": [],
        "schedule.json": [],
    }

    WORKSPACE_INITIAL_TEMPLATES = {
        "agent_action.json": "agent_action_initial.json",
        "router_action.json": "router_action_initial.json",
        "SOUL.md": "SOUL_initial.md",
    }

    CONFIG_PATH = AGENT_DIR / "config.json"
    CONFIG_INITIAL_PATH = AGENT_DIR / "config_initial.json"


    # Constructor
    def __init__(self, config: Optional[dict] = None, console_monitor: bool = True):
        """
        Read argv, load config, build channels. If argv has 'clear', clear workspace and set _exit_clear.
        config: optional override; if None, load from config.json (cloned from config_initial.json if missing).
        """
        load_dotenv()
        logging_setup()
        self._exit_clear = False
        if len(sys.argv) > 1 and sys.argv[1].lower() == "clear":
            self.clear_workspace()
            print("Run without 'clear' to start the agent.", flush=True)
            self._exit_clear = True
            self.config = {}
            self.channels = []
            self.console_monitor = console_monitor
            self._llm = None
            self._provider = None
            self._scheduler = Scheduler(agent=self)
            return
        self.config = config or self.load_config()
        self.console_monitor = console_monitor
        self.channels = self._build_channels()
        self._llm = None
        self._provider = None
        self._scheduler = Scheduler(agent=self)



    @classmethod
    def load_config(cls) -> dict:
        """Load config.json. If missing, clone from config_initial.json first."""
        return AgentConfig.load_config()

    
    def _build_channels(self) -> List:
        """Build channels: ConsoleChannel (always) + others from config."""
        channels = [ConsoleChannel()]
        for c in self.config.get("channels", []):
            if c.get("name") == "telegram" and c.get("enabled"):
                ch = TelegramChannel(channel_cfg=c)
                if ch.bot_token:
                    channels.append(ch)
            elif c.get("name") == "headless" and c.get("enabled", True):
                ch = HeadlessChannel(channel_cfg=c)
                if ch.enabled:
                    channels.append(ch)
        return channels

    def _ensure_ready(self) -> None:
        if self._llm is None:
            self.ensure_workspace_files()
            # LLM settings from config.json (config first, env fallback)
            llm_cfg = self.config.get("llm", {})
            self._provider = llm_cfg.get("provider") or os.getenv("LLM_PROVIDER", "ollama")
            self._model = llm_cfg.get("model") or os.getenv("LLM_MODEL", "llama3.1:8B")
            self._llm = get_llm(workspace=self.WORKSPACE, provider=self._provider, model=self._model)

    def print_banner(self) -> None:
        """Show startup banner in console dialog and log."""
        llm_cfg = self.config.get("llm", {})
        provider = llm_cfg.get("provider") or os.getenv("LLM_PROVIDER", "ollama")
        model = llm_cfg.get("model") or os.getenv("LLM_MODEL", "llama3.1:8B")
        channel_names = [c.source_name for c in self.channels]
        router_actions = []
        try:
            raw = (self.WORKSPACE / "router_action.json").read_text(encoding="utf-8").strip()
            if raw:
                actions = json.loads(raw)
                router_actions = [a.get("name", "") for a in actions if isinstance(a, dict) and a.get("name")]
        except (json.JSONDecodeError, OSError):
            pass
        dialog(f"SafeClaw Agent ({provider} + {model})")
        dialog("")
        dialog(f"Channels: {', '.join(channel_names)}")
        dialog(f"Router Actions: {', '.join(router_actions)}" if router_actions else "Router Actions: (none)")
        dialog("Tip: /restart to restart the agent.")
        dialog("")

    def run(self) -> None:
        """Run all channels. Telegram needs main thread (signal handlers); Console runs in thread."""
        if self._exit_clear:
            return
        self.ensure_workspace_files()
        self.print_banner()
        self._scheduler.start()
        atexit.register(self._scheduler.stop)
        try:
            # Headless channel: runs in background thread
            headless_ch = next((c for c in self.channels if c.source_name == "Headless"), None)
            if headless_ch:
                t_lan = threading.Thread(target=headless_ch.run, args=(self,))
                t_lan.daemon = True
                t_lan.start()
            # Telegram (and similar) must run in main thread - run_polling uses signal handlers
            telegram_ch = next((c for c in self.channels if c.source_name == "Telegram"), None)
            console_ch = next((c for c in self.channels if c.source_name == "Console"), None)
            if telegram_ch:
                log("Telegram bot running.")
                dialog("Send a message to your bot.")
                dialog("")
                if not getattr(telegram_ch, "_broadcast_chat_ids", set()):
                    dialog("Tip: To receive Console messages in Telegram, message the bot first or add broadcast_chat_ids to config.json (get chat ID from @userinfobot)")
                # Run Console in background thread, Telegram in main
                if console_ch:
                    t = threading.Thread(target=console_ch.run, args=(self,))
                    t.daemon = True
                    t.start()
                telegram_ch.run(self)
            else:
                # No Telegram: run Console in main thread
                if console_ch:
                    console_ch.run(self)
        finally:
            self._scheduler.stop()

    def broadcast_to_other_channels(self, user_input: str, exclude_source: str) -> None:
        """Replicate user input to all channels except the source."""
        for ch in self.channels:
            if ch.source_name != exclude_source:
                ch.broadcast_receive(user_input, exclude_source)

    def broadcast_response_to_other_channels(self, response: str, exclude_source: str) -> None:
        """Replicate a response to all channels except the source."""
        for ch in self.channels:
            if ch.source_name != exclude_source:
                ch.broadcast_response(response, exclude_source)

    def broadcast_message(self, message: str, channels: Optional[List[str]] = None) -> None:
        """Send message to specified channels. channels=None or [] = all channels."""
        target_names = {c.strip() for c in channels} if channels else None
        for ch in self.channels:
            if target_names is None or ch.source_name in target_names:
                if hasattr(ch, "send_broadcast") and callable(getattr(ch, "send_broadcast")):
                    ch.send_broadcast(message)

    def _flush_pending_broadcasts(self) -> None:
        """Read workspace/broadcast_pending.json, send to channels, delete file."""
        path = self.WORKSPACE / "broadcast_pending.json"
        if not path.exists():
            return
        try:
            raw = path.read_text(encoding="utf-8").strip()
            data = json.loads(raw) if raw else {}
            pending = data.get("pending", [])
            if isinstance(pending, dict):
                pending = [pending]
            if not isinstance(pending, list):
                pending = []
            for item in pending:
                if isinstance(item, dict) and item.get("message"):
                    msg = item.get("message", "")
                    ch_list = item.get("channels")
                    self.broadcast_message(msg, ch_list if ch_list else None)
        except (json.JSONDecodeError, OSError):
            pass
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def start_typing_except(self, source: str):
        """Start typing on channels that support it (e.g. Telegram) when another channel is processing.
        Returns a stop() callback to call when done."""
        stop_callbacks = []
        for ch in self.channels:
            if ch.source_name != source and hasattr(ch, "start_typing"):
                stop = ch.start_typing()
                if stop:
                    stop_callbacks.append(stop)

        def stop() -> None:
            for cb in stop_callbacks:
                cb()

        return stop

    def process(self, user_input: str, source: str = "Console", flush_broadcasts_after: bool = False) -> str:
        """Process one turn. Returns response text. flush_broadcasts_after: if True, caller flushes (for correct order)."""
        self._ensure_ready()
        thinking = self.config.get("thinking", True)
        response = self._llm.process_turn(user_input, thinking=thinking)
        if not flush_broadcasts_after:
            self._flush_pending_broadcasts()
        return response

    @classmethod
    def ensure_workspace_files(cls) -> None:
        """Create workspace files if missing."""
        cls.WORKSPACE.mkdir(parents=True, exist_ok=True)
        for filename, default in cls.WORKSPACE_DEFAULTS.items():
            path = cls.WORKSPACE / filename
            if not path.exists():
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(default, f, indent=2)
        for target, source in cls.WORKSPACE_INITIAL_TEMPLATES.items():
            target_path = cls.WORKSPACE / target
            source_path = cls.WORKSPACE / source
            if target_path.exists() or not source_path.exists():
                continue
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    @classmethod
    def clear_workspace(cls) -> None:
        """Reset input_history.json, delete schedule.json, clear logs, and workspace/output/."""
        cls.WORKSPACE.mkdir(parents=True, exist_ok=True)
        artifact_path = cls.WORKSPACE / "artifact.json"
        if artifact_path.exists():
            artifact_path.unlink()
        with open(cls.WORKSPACE / "input_history.json", "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        schedule_path = cls.WORKSPACE / "schedule.json"
        if schedule_path.exists():
            schedule_path.unlink()
        logs_dir = (cls.AGENT_DIR / "logs").resolve()
        logs_dir.mkdir(parents=True, exist_ok=True)
        for log_name in ("system.log", "llm.log", "schedule.log"):
            log_path = logs_dir / log_name
            if log_path.exists():
                log_path.unlink()
        # Recreate empty log files so agent can append; unlink leaves dir without them
        for log_name in ("system.log", "llm.log", "schedule.log"):
            (logs_dir / log_name).touch()
        output_dir = cls.WORKSPACE / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print("Cleared input_history.json, schedule.json (deleted), artifact.json (deleted), system.log, llm.log, schedule.log, and workspace/output/", flush=True)
