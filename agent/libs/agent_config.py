"""
AgentConfig: load config.json and interactive config prompts.
Usage: AgentConfig(key) to run interactive prompts for that key.
"""
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from libs.logger import logging_setup

AGENT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = AGENT_DIR / "config.json"
CONFIG_INITIAL_PATH = AGENT_DIR / "config_initial.json"

CONFIG_PROMPTS = {
    "timeout": {
        "prompt": "What is the timeout for each request?",
        "type": "int",
        "default": 10,
    },
    "llm": {
        "provider": {
            "prompt": "What is the provider [e.g. ollama]?",
            "default": "ollama",
        },
        "model": {
            "prompt": "What model you are target to use [e.g. llama3.1:8B]?",
            "default": "llama3.1:8B",
        },
    },
}


class AgentConfig:
    """Load and interactively configure agent config.json."""

    @classmethod
    def load_config(cls) -> dict:
        """Load config.json. If missing, clone from config_initial.json first."""
        if not CONFIG_PATH.exists() and CONFIG_INITIAL_PATH.exists():
            CONFIG_PATH.write_text(CONFIG_INITIAL_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        if CONFIG_PATH.exists():
            try:
                raw = CONFIG_PATH.read_text(encoding="utf-8").strip()
                if raw:
                    return json.loads(raw)
            except json.JSONDecodeError:
                pass
            if CONFIG_INITIAL_PATH.exists():
                CONFIG_PATH.write_text(CONFIG_INITIAL_PATH.read_text(encoding="utf-8"), encoding="utf-8")
                return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {"channels": []}

    def __init__(self, config_key: Optional[str] = None):
        """
        If config_key is passed, run interactive prompts for that key and save to config.json.
        """
        if not config_key:
            return
        load_dotenv()
        logging_setup()
        config = self.load_config()
        key = config_key.lower()
        if key not in CONFIG_PROMPTS:
            print(f"Unknown key: {key}. Available:", ", ".join(CONFIG_PROMPTS))
            return
        schema = CONFIG_PROMPTS[key]
        if "prompt" in schema:
            current = config.get(key, schema.get("default", ""))
            prompt = f"{schema['prompt']} [{current}]: "
            raw = input(prompt).strip() or str(current)
            if schema.get("type") == "int":
                try:
                    config[key] = int(raw)
                except ValueError:
                    config[key] = schema.get("default", 10)
            else:
                config[key] = raw
        else:
            if key not in config:
                config[key] = {}
            for subkey, sub_schema in schema.items():
                if isinstance(sub_schema, dict) and "prompt" in sub_schema:
                    current = config[key].get(subkey, sub_schema.get("default", ""))
                    prompt = f"{sub_schema['prompt']} [{current}]: "
                    raw = input(prompt).strip() or str(current)
                    config[key][subkey] = raw
        CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(f"Updated config.json: {key}")

    @classmethod
    def run_interactive(cls, key: Optional[str] = None) -> None:
        """Run interactive config. If no key, print usage."""
        if not key:
            print("Usage: ./start_agent.py config <key>")
            print("Keys:", ", ".join(CONFIG_PROMPTS))
            return
        cls(config_key=key)
