"""
Agent abilities: self-contained agent actions.
Each ability lives in its own folder and extends BaseAgentAction.
Registry (ability/registry.json) maps action codes to ability folders.
"""
import importlib
import json
from pathlib import Path
from typing import Optional, Type

from libs.base_agent_action import BaseAgentAction

ABILITY_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = ABILITY_DIR / "registry.json"


def _load_registry() -> dict[str, str]:
    """Load action name -> ability_key mapping from registry.json."""
    if not REGISTRY_PATH.exists():
        return {}
    raw = REGISTRY_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _ability_key_to_class_name(ability_key: str) -> str:
    """Convert ability_key (e.g. memory_write) to class name (e.g. MemoryWriteAction)."""
    parts = ability_key.split("_")
    return "".join(p.capitalize() for p in parts) + "Action"


def get_action_class(action: str) -> Optional[Type[BaseAgentAction]]:
    """Return the action class for the given action code, or None if not an agent action."""
    registry = _load_registry()
    ability_key = registry.get(action)
    if not ability_key:
        return None
    try:
        module = importlib.import_module(f"ability.{ability_key}")
        class_name = _ability_key_to_class_name(ability_key)
        cls = getattr(module, class_name)
        if issubclass(cls, BaseAgentAction):
            return cls
    except (ImportError, AttributeError):
        pass
    return None
