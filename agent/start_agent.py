#!/usr/bin/env python3
"""
Start the agent. Run from agent/: python start_agent.py  or  ./start_agent.py
BaseAgent constructor loads config, handles argv (e.g. clear), builds channels.
"""
import warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
warnings.filterwarnings("ignore", module="urllib3")

from libs.base_agent import BaseAgent

if __name__ == "__main__":
    BaseAgent().run()
