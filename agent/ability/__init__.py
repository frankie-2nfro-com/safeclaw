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


def _load_registry() -> dict:
    """Load action name -> ability_key or {ability, class} from registry.json."""
    if not REGISTRY_PATH.exists():
        return {}
    raw = REGISTRY_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _parse_registry_entry(entry) -> tuple:
    """Return (ability_key, class_name). Entry must be {ability, class}."""
    if isinstance(entry, dict) and "ability" in entry and "class" in entry:
        return (entry["ability"], entry["class"])
    return (None, None)


def get_action_class(action: str) -> Optional[Type[BaseAgentAction]]:
    """Return the action class for the given action code, or None if not an agent action."""
    registry = _load_registry()
    entry = registry.get(action)
    if entry is None:
        return None
    ability_key, class_name = _parse_registry_entry(entry)
    if not ability_key:
        return None
    try:
        module = importlib.import_module(f"ability.{ability_key}")
        cls = getattr(module, class_name)
        if issubclass(cls, BaseAgentAction):
            return cls
    except (ImportError, AttributeError):
        pass
    return None
