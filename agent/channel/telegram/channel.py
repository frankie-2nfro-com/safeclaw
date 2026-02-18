"""
Telegram channel. Pure I/O for Telegram bot.
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set, Tuple

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

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

        app = Application.builder().token(self.bot_token).build()
        self._application = app
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
