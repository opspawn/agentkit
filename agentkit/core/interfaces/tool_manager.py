# agentkit/agentkit/core/interfaces/tool_manager.py
"""Abstract Base Class for agent tool managers."""

import abc
from typing import TYPE_CHECKING, Any, Dict, Optional

# Use relative import and TYPE_CHECKING to avoid circular dependency issues
if TYPE_CHECKING:
    from ...tools.schemas import Tool, ToolResult


class BaseToolManager(abc.ABC):
    """Abstract base class for managing and executing agent tools."""

    @abc.abstractmethod
    def lookup_tool(self, tool_name: str) -> Optional["Tool"]:
        """
        Find a tool by its name.

        Args:
            tool_name: The name of the tool to look up.

        Returns:
            The Tool instance if found, otherwise None.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> "ToolResult":
        """
        Execute a registered tool with the given arguments.

        Args:
            tool_name: The name of the tool to execute.
            args: A dictionary of arguments for the tool.

        Returns:
            A ToolResult object containing the execution outcome.
        """
        raise NotImplementedError
