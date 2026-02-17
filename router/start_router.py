#!/usr/bin/env python3

from libs.router import Router
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()

    router = Router()
    exit(router.run())
