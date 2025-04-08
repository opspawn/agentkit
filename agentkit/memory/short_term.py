# agentkit/agentkit/memory/short_term.py
"""Basic short-term memory implementation for agents."""

from typing import Any, Dict, List, Optional

# Use relative import for interfaces within the same package level
from ..core.interfaces.memory import BaseMemory


class ShortTermMemory(BaseMemory):
    """Manages a short-term memory buffer, typically for conversation history."""

    def __init__(self, max_size: int = 100):
        """
        Initializes the short-term memory.

        Args:
            max_size: The maximum number of messages to store.
                      Older messages are discarded if the limit is exceeded.
        """
        self.messages: List[Dict[str, Any]] = []
        self.max_size = max_size

    async def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to the agent's memory.

        If the buffer exceeds max_size, the oldest message is removed.

        Args:
            role: The role of the message sender (e.g., 'user', 'agent', 'system', 'tool').
            content: The content of the message.
            metadata: Optional dictionary for additional message context.
        """
        message = {"role": role, "content": content}
        if metadata:
            message.update(metadata)  # Add metadata if provided

        self.messages.append(message)
        # Only prune if max_size is set (not None) and the limit is exceeded
        if self.max_size is not None and len(self.messages) > self.max_size:
            self.messages.pop(0)  # Remove the oldest message

    async def get_context(self, max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve the current conversational context from memory.

        Args:
            max_tokens: Optional limit on the number of tokens (ignored in this implementation).

        Returns:
            A list of message dictionaries representing the context.
        """
        # Note: max_tokens is ignored in this simple implementation
        return self.messages.copy()  # Return a copy to prevent external modification

    async def clear(self) -> None:
        """Clear the agent's memory."""
        self.messages = []
