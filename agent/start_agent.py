#!/usr/bin/env python3
"""
Start the agent. Run from agent/: python start_agent.py  or  ./start_agent.py
BaseAgent constructor loads config, handles argv (e.g. clear), builds channels.

Interactive config: ./start_agent.py config [key]
  e.g. ./start_agent.py config timeout
  e.g. ./start_agent.py config llm
"""
import sys
import warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
warnings.filterwarnings("ignore", module="urllib3")

from libs.agent_config import AgentConfig
from libs.base_agent import BaseAgent

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1].lower() == "config":
        key = sys.argv[2].lower() if len(sys.argv) > 2 else None
        AgentConfig.run_interactive(key)
    else:
        BaseAgent().run()
