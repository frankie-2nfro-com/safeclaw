#!/usr/bin/env python3
"""
Monitor the Redis command queue. Keeps running and prints commands as chat.py pushes them.
Simulates the router: after receiving a command, waits 1-5s and pushes a test response.
Run in one terminal: python test_queue_sub.py
Run chat.py in another terminal.
"""
import json
import os
import random
import signal
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from redis import Redis

load_dotenv(Path(__file__).parent / ".env")

COMMAND_QUEUE = "safeclaw:command_queue"
RESPONSE_PREFIX = "safeclaw:response:"


def main():
    url = os.getenv("REDIS_URL")
    if not url:
        print("ERROR: REDIS_URL not set in .env")
        return 1

    print("Connecting to Redis...")
    try:
        r = Redis.from_url(url)
        r.ping()
        print("Connected.")
    except Exception as e:
        print(f"ERROR: Cannot connect to Redis: {e}")
        return 1

    print(f"Monitoring {COMMAND_QUEUE} (Ctrl+C to stop)\n")
    running = True

    def stop(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)

    while running:
        result = r.brpop(COMMAND_QUEUE, timeout=1)
        if result:
            _, raw = result
            payload = raw.decode() if isinstance(raw, bytes) else raw
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Received: {payload}")
            try:
                parsed = json.loads(payload)
                message_id = parsed.get("message_id")
                action = parsed.get("action")
                print(f"      action={action} message_id={message_id}")

                delay = random.uniform(1, 5)
                print(f"      Waiting {delay:.1f}s...")
                time.sleep(delay)

                response_key = f"{RESPONSE_PREFIX}{message_id}"
                test_response = {"status": "ok", "test": True, "action": action}
                r.lpush(response_key, json.dumps(test_response))
                print(f"      Pushed test response to {response_key}")
            except json.JSONDecodeError as e:
                print(f"      Invalid JSON: {e}")
            except Exception as e:
                print(f"      Error: {e}")
            print()

    print("\nStopped.")
    return 0


if __name__ == "__main__":
    exit(main())
