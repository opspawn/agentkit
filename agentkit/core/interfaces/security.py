# agentkit/agentkit/core/interfaces/security.py
"""Abstract Base Class for agent security managers."""

import abc
from typing import Any, Dict


class BaseSecurityManager(abc.ABC):
    """Abstract base class for managing agent security aspects.

    This is a placeholder for future security-related functionalities,
    such as input validation, output filtering, or permission checks.
    """

    @abc.abstractmethod
    async def check_permissions(self, action: str, context: Dict[str, Any]) -> bool:
        """
        Check if the agent has permission to perform a specific action.

        Args:
            action: The action being attempted (e.g., 'execute_tool:tool_name').
            context: Supporting information relevant to the permission check.

        Returns:
            True if the action is permitted, False otherwise.
        """
        # Placeholder implementation
        return True  # Default to permissive for now
