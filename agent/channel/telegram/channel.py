"""
Telegram channel. Pure I/O for Telegram bot.
"""
import asyncio
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Set, Tuple

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from libs.base_channel import BaseChannel
from libs.logger import dialog, log

CHANNEL_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = CHANNEL_DIR.parent


class TelegramChannel(BaseChannel):
    """Telegram I/O. Uses python-telegram-bot polling."""

    @property
    def source_name(self) -> str:
        return "Telegram"

    def __init__(self, channel_cfg: Optional[dict] = None):
        super().__init__(config_path=None)
        cfg = channel_cfg or {}
        self.bot_token = cfg.get("bot_token", "")
        self.enabled = cfg.get("enabled", False)
        self._chat_ids: Set[int] = set()
        self._broadcast_chat_ids: Set[int] = set(
            int(x) for x in cfg.get("broadcast_chat_ids", []) if str(x).lstrip("-").isdigit()
        )
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._application: Optional[Application] = None

    def send(self, message: str) -> None:
        """Sync send (used when not in bot context)."""
        log(f"[Telegram send] {message}")

    def _target_chat_ids(self) -> Set[int]:
        """Chat IDs to receive broadcasts (config + anyone who has messaged)."""
        return self._broadcast_chat_ids | self._chat_ids

    def broadcast_receive(self, user_input: str, from_source: str) -> None:
        """Send replicated message from another channel (e.g. Console) to all known Telegram chats."""
        if not self._loop or not self._application:
            return
        chat_ids = self._target_chat_ids()
        if not chat_ids:
            if not hasattr(self, "_broadcast_skip_logged"):
                self._broadcast_skip_logged = True
                log("Tip: Console messages not sent to Telegram. Message the bot first or add broadcast_chat_ids to config.json (get chat ID from @userinfobot)")
            return
        message = f"[{from_source}] I got your request: {user_input}"
        async def _send():
            for chat_id in list(chat_ids):
                try:
                    await self._application.bot.send_message(chat_id=chat_id, text=message[:4096])
                except Exception as e:
                    log(f"[Telegram broadcast] {e}")
        asyncio.run_coroutine_threadsafe(_send(), self._loop)

    def broadcast_response(self, response: str, from_source: str) -> None:
        """Send replicated response from another channel (e.g. Console) to all known Telegram chats."""
        if not self._loop or not self._application:
            return
        chat_ids = self._target_chat_ids()
        if not chat_ids:
            if not hasattr(self, "_broadcast_skip_logged"):
                self._broadcast_skip_logged = True
                log("Tip: Console responses not sent to Telegram. Message the bot first or add broadcast_chat_ids to config.json (get chat ID from @userinfobot)")
            return
        async def _send():
            for chat_id in list(chat_ids):
                try:
                    await self._application.bot.send_message(chat_id=chat_id, text=response[:4096])
                except Exception as e:
                    log(f"[Telegram broadcast] {e}")
        asyncio.run_coroutine_threadsafe(_send(), self._loop)

    def start_typing(self) -> Optional[Callable[[], None]]:
        """Start typing indicator for all broadcast chats (e.g. when Console is processing).
        Returns a stop() callback to call when done. Typing also stops when a message is sent."""
        if not self._loop or not self._application:
            return None
        chat_ids = self._target_chat_ids()
        if not chat_ids:
            return None
        stop_event = threading.Event()

        async def _keep_typing() -> None:
            while not stop_event.is_set():
                for chat_id in list(chat_ids):
                    try:
                        await self._application.bot.send_chat_action(chat_id=chat_id, action="typing")
                    except Exception:
                        pass
                for _ in range(4):
                    if stop_event.is_set():
                        break
                    await asyncio.sleep(1)

        def stop() -> None:
            stop_event.set()

        asyncio.run_coroutine_threadsafe(_keep_typing(), self._loop)
        return stop

    def receive(self) -> Tuple[str, str]:
        """Blocking receive (fallback). Telegram uses async callback instead."""
        return input("You: ").strip(), self.source_name

    def run(self, agent) -> None:
        """Start the Telegram bot. On each message: agent.process -> send to user."""
        if not self.bot_token:
            log("ERROR: Add telegram to agent/config.json channels with bot_token")
            return
        if not self.enabled:
            log("ERROR: Set enabled: true for telegram in agent/config.json")
            return

        if str(AGENT_DIR) not in sys.path:
            sys.path.insert(0, str(AGENT_DIR))

        # Set event loop for this thread (required when run in threading.Thread)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._application = None  # set after app is built

        agent._ensure_ready()

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if not update.message or not update.message.text:
                return
            # Reject messages older than timeout (e.g. backlog from before agent started)
            timeout = agent.config.get("timeout", 10)
            msg_date = update.message.date
            if msg_date:
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - msg_date).total_seconds()
                if age_seconds > timeout:
                    too_old_msg = f"Received this request, but it's too old to handle (>{timeout}s). Please send again."
                    await update.message.reply_text(too_old_msg)
                    return
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id is not None:
                self._chat_ids.add(chat_id)
            user_input = update.message.text.strip()
            if not user_input:
                return
            source = self.source_name
            agent.broadcast_to_other_channels(user_input, exclude_source=source)
            try:
                loop = asyncio.get_event_loop()
                process_task = loop.run_in_executor(
                    None,
                    lambda: agent.process(user_input, source),
                )
                async def keep_typing():
                    while True:
                        await update.message.chat.send_action("typing")
                        done, _ = await asyncio.wait([process_task], timeout=4)
                        if done:
                            break
                _, response = await asyncio.gather(keep_typing(), process_task)
                text = (response or "(no response)")[:4096]
                await update.message.reply_text(text)
                agent.broadcast_response_to_other_channels(text, exclude_source=source)
            except Exception as e:
                log(f"[Telegram] Error: {e}")
                try:
                    await update.message.reply_text(f"Error: {e}")
                except Exception:
                    pass
            # Typing stops when reply_text is sent; ensure we always resume (success or timeout)

        async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id is not None:
                self._chat_ids.add(chat_id)
            text = f"Your chat ID: {chat_id}" if chat_id is not None else "Could not get chat ID"
            await update.message.reply_text(text)

        async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id is not None:
                self._chat_ids.add(chat_id)
            path = agent.WORKSPACE / "memory.json"
            if not path.exists():
                await update.message.reply_text("(No memory)")
                return
            try:
                raw = path.read_text(encoding="utf-8").strip()
                data = json.loads(raw) if raw else {}
                if not isinstance(data, dict):
                    data = {}
                if not data:
                    await update.message.reply_text("(Empty memory)")
                    return
                lines = [f"• {k}: {v}" for k, v in data.items()]
                text = "Memory:\n" + "\n".join(lines)
                await update.message.reply_text(text[:4096])
            except Exception as e:
                await update.message.reply_text(f"Error reading memory: {e}")

        async def cmd_soul(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id is not None:
                self._chat_ids.add(chat_id)
            path = agent.WORKSPACE / "SOUL.md"
            if not path.exists():
                await update.message.reply_text("(No soul)")
                return
            try:
                text = path.read_text(encoding="utf-8").strip()
                if not text:
                    await update.message.reply_text("(Empty soul)")
                    return
                await update.message.reply_text(text[:4096])
            except Exception as e:
                await update.message.reply_text(f"Error reading soul: {e}")

        async def post_init(app: Application) -> None:
            await app.bot.delete_my_commands()
            await app.bot.set_my_commands([
                BotCommand("whoami", "Show your chat ID"),
                BotCommand("memory", "Show current memory"),
                BotCommand("soul", "Show agent identity and beliefs"),
            ])

        app = (
            Application.builder()
            .token(self.bot_token)
            .post_init(post_init)
            .build()
        )
        self._application = app
        app.add_handler(CommandHandler("whoami", cmd_whoami))
        app.add_handler(CommandHandler("memory", cmd_memory))
        app.add_handler(CommandHandler("soul", cmd_soul))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
