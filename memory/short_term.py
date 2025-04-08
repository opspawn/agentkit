# agentkit/memory/short_term.py
from typing import Any, Dict, List

from agentkit.core.interfaces.memory import BaseMemory


class ShortTermMemory(BaseMemory):
    """
    A simple in-memory implementation of the BaseMemory interface.

    Stores the agent's interaction history as a list of dictionaries
    in memory. Suitable for short-term context within a single session.
    """

    def __init__(self) -> None:
        """Initializes an empty short-term memory."""
        self._history: List[Dict[str, Any]] = []

    def add_entry(self, entry: Dict[str, Any]) -> None:
        """
        Adds a new entry to the end of the history list.

        Args:
            entry (Dict[str, Any]): The memory entry to add.
        """
        self._history.append(entry)

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Retrieves the complete interaction history.

        Returns:
            List[Dict[str, Any]]: The list of all memory entries.
        """
        # Return a copy to prevent external modification of the internal list
        return list(self._history)

    def clear(self) -> None:
        """
        Removes all entries from the memory history.
        """
        self._history = []
