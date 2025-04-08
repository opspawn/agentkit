# agentkit/core/interfaces/memory.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseMemory(ABC):
    """
    Abstract base class for agent memory modules.

    Defines the standard interface for adding entries to memory,
    retrieving the history, and clearing the memory.
    """

    @abstractmethod
    def add_entry(self, entry: Dict[str, Any]) -> None:
        """
        Adds a new entry to the agent's memory.

        Args:
            entry (Dict[str, Any]): The dictionary representing the memory entry.
                                     The structure can vary depending on the
                                     memory type (e.g., observation, thought, action).
        """
        raise NotImplementedError

    @abstractmethod
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Retrieves the entire history stored in the memory.

        Returns:
            List[Dict[str, Any]]: A list of memory entries.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """
        Clears all entries from the memory.
        """
        raise NotImplementedError
