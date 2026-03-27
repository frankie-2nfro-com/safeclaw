#!/usr/bin/env python3
"""
Test RouterClient: init and send actions to the router directly.

Prerequisites:
  - Router must be running: python start_router.py
  - REDIS_URL in .env (or set in config)
"""
import asyncio
import sys
from pathlib import Path

# Ensure router/ is on path when run from project root
ROUTER_DIR = Path(__file__).resolve().parent
if str(ROUTER_DIR) not in sys.path:
    sys.path.insert(0, str(ROUTER_DIR))

from dotenv import load_dotenv

load_dotenv(ROUTER_DIR / ".env")

from libs.router_interface import RouterClient


async def main():
    # Config can be empty; falls back to REDIS_URL, COMMAND_QUEUE, RESPONSE_PREFIX from .env
    config = {}
    client = RouterClient(config)

    print("RouterClient initialized.")
    print("Sending HELLO_WORLD (sync)...")

    result = client.sync_call("HELLO_WORLD", {}, timeout=5)
    if result:
        print(f"Response: {result}")
    else:
        print("No response (timeout or router not running).")

    print("\nSending HELLO_WORLD (async with asyncio)...")
    result = await client.async_call("HELLO_WORLD", {}, timeout=5)
    if result:
        print(f"Async response: {result}")
    else:
        print("No async response (timeout or router not running).")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
