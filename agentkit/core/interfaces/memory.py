# agentkit/agentkit/core/interfaces/memory.py
"""Abstract Base Class for agent memory modules."""

import abc
from typing import Any, Dict, List, Optional


class BaseMemory(abc.ABC):
    """Abstract base class for agent memory management."""

    @abc.abstractmethod
    async def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to the agent's memory.

        Args:
            role: The role of the message sender (e.g., 'user', 'agent', 'system', 'tool').
            content: The content of the message.
            metadata: Optional dictionary for additional message context.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_context(self, max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve the current conversational context from memory.

        Args:
            max_tokens: Optional limit on the number of tokens for the context.

        Returns:
            A list of message dictionaries representing the context.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self) -> None:
        """Clear the agent's memory."""
        raise NotImplementedError
