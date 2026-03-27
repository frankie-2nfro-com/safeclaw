#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Ensure skill prints appear immediately in console
os.environ.setdefault("PYTHONUNBUFFERED", "1")
try:
    sys.stdout.reconfigure(line_buffering=True)
except (AttributeError, OSError):
    pass

from libs.router import Router, IN_OUT_LOG
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()

    if len(sys.argv) >= 2 and sys.argv[1].lower() == "clear":
        IN_OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
        IN_OUT_LOG.write_text("")
        print("Cleared in_out.log")

    router = Router()
    exit(router.run())
