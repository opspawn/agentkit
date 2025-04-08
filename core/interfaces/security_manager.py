# agentkit/core/interfaces/security_manager.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseSecurityManager(ABC):
    """
    Abstract base class for agent security modules.

    Defines the standard interface for checking if an action,
    particularly tool execution, is permitted.
    """

    @abstractmethod
    def check_execution(self, action_type: str, details: Dict[str, Any]) -> bool:
        """
        Checks if a given action is permitted based on security policies.

        Args:
            action_type (str): The type of action being considered (e.g., 'tool_call').
            details (Dict[str, Any]): Specifics of the action (e.g., tool name, input).

        Returns:
            bool: True if the action is permitted, False otherwise.
        """
        # Default implementation allows everything for MVP, can be overridden
        return True
