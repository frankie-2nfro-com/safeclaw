# Telegram Channel Setup

## 1. Get a Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts: choose a name and username for your bot
4. BotFather will reply with a token like `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
5. **Keep this token secret** – do not commit it to git

## 2. Configure the Channel

Copy the config and edit the Telegram channel. Config files live in `agent/` (same folder as config.json), not in workspace:

```bash
cd agent
cp config_initial.json config.json
```

Edit `config.json`:

1. Set `"enabled": true`
2. Set `"bot_token": "YOUR_TOKEN_FROM_BOTFATHER"`
3. Add your chat ID to `"broadcast_chat_ids": [123456789]` — get it via `/whoami` in your bot or [@userinfobot](https://t.me/userinfobot). This lets you receive Console messages and responses in Telegram.

```json
{
  "channels": [
    {
      "name": "telegram",
      "enabled": true,
      "bot_token": "YOUR_TOKEN_HERE",
      "broadcast_chat_ids": [123456789]
    }
  ],
  "timeout": 10
}
```

- **timeout** (optional, default 10): Seconds. Messages older than this when the agent starts are ignored with "too old to handle". Also used for response queue timeout.

Console is always available (no config needed). Add other channels as needed.

## 3. Install Dependencies

```bash
cd agent
pip install python-telegram-bot
```

## 4. Run the Agent with Telegram

```bash
cd agent
python start_agent.py
```

The bot will start polling. Open Telegram, find your bot, send a message. SafeClaw will reply.

## 5. Commands

Type `/` in the chat to see available commands:

| Command   | Description                          |
|-----------|--------------------------------------|
| `/whoami` | Show your chat ID (for broadcast_chat_ids) |
| `/memory` | Show current memory content          |
| `/soul`   | Show agent identity and beliefs      |

Use `/whoami` to get your chat ID instead of @userinfobot if you prefer.

## 6. Flow

```
You (Telegram)  →  Bot receives message  →  Agent (LLM + actions)  →  Bot sends reply
```

Same logic as console, but input/output goes through Telegram.
