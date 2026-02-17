from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """Base class for router skills. Subclasses must implement execute()."""

    @abstractmethod
    def execute(self, params: dict):
        """Execute the skill. Returns result to send as response."""
        pass
