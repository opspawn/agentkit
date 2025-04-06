"""
Basic short-term memory implementation for agents.
Stores conversation history or context in memory.
"""

from typing import List, Dict, Any

# Define a type alias for clarity, representing a message/context item
Message = Dict[str, Any]


class ShortTermMemory:
    """
    Manages a short-term memory buffer, typically for conversation history.
    """

    def __init__(self, max_size: int = 100):
        """
        Initializes the short-term memory.

        Args:
            max_size: The maximum number of messages to store.
                      Older messages are discarded if the limit is exceeded.
        """
        self.messages: List[Message] = []
        self.max_size = max_size

    def add_message(self, message: Message):
        """
        Adds a message to the memory buffer.

        If the buffer exceeds max_size, the oldest message is removed.

        Args:
            message: The message dictionary to add.
        """
        self.messages.append(message)
        if len(self.messages) > self.max_size:
            self.messages.pop(0)  # Remove the oldest message

    def get_messages(self) -> List[Message]:
        """
        Retrieves all messages currently in the memory buffer.

        Returns:
            A list of message dictionaries.
        """
        return self.messages.copy()  # Return a copy to prevent external modification

    def clear(self):
        """
        Clears all messages from the memory buffer.
        """
        self.messages = []

    def __len__(self) -> int:
        """
        Returns the current number of messages in the buffer.
        """
        return len(self.messages)
