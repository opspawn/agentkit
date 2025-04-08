# agentkit/tools/registry.py
import logging
from typing import Any, Dict, List, Optional

from agentkit.core.interfaces.tool_manager import BaseToolManager
from agentkit.tools.schemas import Tool, ToolResult, ToolSpec

# Import execute_tool_safely - will be defined in execution.py
# Use a forward reference style initially if needed, or import directly
# assuming execution.py will exist when this module is fully used.
from .execution import execute_tool_safely

logger = logging.getLogger(__name__)


class ToolNotFoundError(Exception):
    """Exception raised when a requested tool is not found in the registry."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' not found in registry.")


class ToolRegistrationError(Exception):
    """Exception raised when there's an error registering a tool (e.g., duplicate name)."""

    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"Error registering tool '{tool_name}': {message}")


class ToolRegistry(BaseToolManager):
    """
    Manages the registration and execution of tools available to an agent.

    Implements the BaseToolManager interface using an in-memory dictionary
    to store registered tools.
    """

    def __init__(self) -> None:
        """Initializes an empty tool registry."""
        self._tools: Dict[str, Tool] = {}
        logger.info("ToolRegistry initialized.")

    def register_tool(self, tool: Tool) -> None:
        """
        Registers a new tool.

        Args:
            tool (Tool): The tool instance to register.

        Raises:
            ToolRegistrationError: If a tool with the same name is already registered.
        """
        tool_name = tool.spec.name
        if tool_name in self._tools:
            raise ToolRegistrationError(
                tool_name, "A tool with this name is already registered."
            )
        self._tools[tool_name] = tool
        logger.info(f"Tool '{tool_name}' registered successfully.")

    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Retrieves a tool by its name.

        Args:
            name (str): The name of the tool.

        Returns:
            Optional[Tool]: The tool instance if found, otherwise None.
        """
        return self._tools.get(name)

    def list_tools(self) -> List[ToolSpec]:
        """
        Lists the specifications of all registered tools.

        Returns:
            List[ToolSpec]: A list of ToolSpec objects.
        """
        return [tool.spec for tool in self._tools.values()]

    async def execute_tool(self, name: str, tool_input: Dict[str, Any]) -> ToolResult:
        """
        Executes a registered tool safely using multiprocessing.

        Args:
            name (str): The name of the tool to execute.
            tool_input (Dict[str, Any]): The input arguments for the tool.

        Returns:
            ToolResult: The result of the tool execution.

        Raises:
            ToolNotFoundError: If the tool with the given name is not registered.
        """
        tool = self.get_tool(name)
        if not tool:
            logger.error(f"Attempted to execute non-existent tool: {name}")
            raise ToolNotFoundError(name)

        logger.info(f"Executing tool '{name}' with input: {tool_input}")

        # Input validation against schema could be added here using jsonschema
        # For now, assume input is valid or handled within the tool's execute method

        try:
            # Delegate to the safe execution function
            result = await execute_tool_safely(tool=tool, tool_input=tool_input)
            logger.info(f"Tool '{name}' execution completed. Result: {result}")
            return result
        except Exception as e:
            # Catch unexpected errors during the safe execution call itself
            logger.exception(f"Unexpected error during safe execution wrapper for tool '{name}': {e}")
            return ToolResult(output=None, error=f"Unexpected execution wrapper error: {e}")
