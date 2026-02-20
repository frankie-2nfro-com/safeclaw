"""
Base class for agent actions. Each ability extends this and implements execute().
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class BaseAgentAction(ABC):
    """Base for all agent actions. Subclasses implement execute()."""

    def __init__(self, workspace: Path, params: dict):
        self.workspace = workspace
        self.params = params

    @abstractmethod
    def execute(self) -> Optional[dict[str, Any]]:
        """Execute the action. Return result dict or None."""
        pass
