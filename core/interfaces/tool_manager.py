# agentkit/core/interfaces/tool_manager.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Forward references to avoid circular imports if Tool/ToolSpec are defined elsewhere
# and imported conditionally or via typing.TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentkit.tools.schemas import Tool, ToolResult, ToolSpec


class BaseToolManager(ABC):
    """
    Abstract base class for managing agent tools.

    Defines the standard interface for registering, retrieving, listing,
    and executing tools available to an agent.
    """

    @abstractmethod
    def register_tool(self, tool: "Tool") -> None:
        """
        Registers a new tool with the manager.

        Args:
            tool (Tool): The tool instance to register.
        """
        raise NotImplementedError

    @abstractmethod
    def get_tool(self, name: str) -> Optional["Tool"]:
        """
        Retrieves a tool by its name.

        Args:
            name (str): The name of the tool to retrieve.

        Returns:
            Optional[Tool]: The tool instance if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def list_tools(self) -> List["ToolSpec"]:
        """
        Lists the specifications of all registered tools.

        Returns:
            List[ToolSpec]: A list of tool specifications.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute_tool(self, name: str, tool_input: Dict[str, Any]) -> "ToolResult":
        """
        Executes a registered tool with the given input.

        Args:
            name (str): The name of the tool to execute.
            tool_input (Dict[str, Any]): The input arguments for the tool,
                                         matching its input schema.

        Returns:
            ToolResult: An object containing the output or error from the tool execution.
        """
        raise NotImplementedError
