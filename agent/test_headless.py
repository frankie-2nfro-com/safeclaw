#!/usr/bin/env python3
"""
Test the headless channel. Sends argv[1] to the agent via RequestClient.
Run from agent/: python test_headless.py "your prompt"
"""
import os
import sys
import time

from dotenv import load_dotenv

from libs.request_client import RequestClient

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_IN = os.getenv("LAN_QUEUE_IN", "safeclaw:lan_request_queue")
QUEUE_OUT = os.getenv("LAN_QUEUE_OUT", "safeclaw:lan_response_queue")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_headless.py \"<prompt>\"", file=sys.stderr)
        sys.exit(1)
    prompt = sys.argv[1]
    request_id = f"req_{int(time.time() * 1000)}"
    with RequestClient(REDIS_URL, QUEUE_IN, QUEUE_OUT) as client:
        result = client.send_and_wait(request_id, prompt)
        print(result.get("response", ""))


if __name__ == "__main__":
    main()
