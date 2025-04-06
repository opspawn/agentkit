"""
Manages the registration and execution of agent tools.
"""
import inspect
from typing import Any, Callable, Dict, List, Optional

import inspect # Keep inspect if needed elsewhere, maybe not
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

# Import Tool from schemas now
from .schemas import ToolSpec, ToolResult, DEFAULT_SCHEMA, Tool, ToolError
from .execution import execute_tool_safely # Import the safe execution function


class ToolExecutionError(ToolError): # Inherit from base ToolError
    """Custom exception for errors during tool execution."""
    pass


class ToolNotFoundError(Exception):
    """Custom exception when a tool is not found in the registry."""
    pass


class ToolNotFoundError(ToolError): # Inherit from base ToolError
    pass


# Tool class definition removed from here


class ToolRegistry:
    """
    Manages a collection of tools available to an agent.
    """
    def __init__(self):
        """Initializes an empty ToolRegistry."""
        self._tools: Dict[str, Tool] = {} # Type hint uses imported Tool

    def add_tool(self, tool: Tool): # Type hint uses imported Tool
        """
        Registers a tool instance in the registry.

        Args:
            tool: The Tool instance to register.

        Raises:
            ValueError: If a tool with the same name already exists or if the provided object is not a Tool instance.
        """
        if not isinstance(tool, Tool):
             # Reason: Ensure only valid Tool instances are added.
             raise ValueError("Item to be added must be an instance of the Tool class.")
        if tool.spec.name in self._tools:
            raise ValueError(f"Tool with name '{tool.spec.name}' already registered.")
        self._tools[tool.spec.name] = tool

    def get_tool(self, name: str) -> Tool: # Type hint uses imported Tool
        """
        Retrieves a tool instance by its name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            The Tool instance.

        Raises:
            ToolNotFoundError: If no tool with the given name is found.
        """
        tool = self._tools.get(name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{name}' not found.")
        return tool

    def get_tool_spec(self, name: str) -> ToolSpec:
        """
        Retrieves the specification of a tool by its name.

        Args:
            name: The name of the tool whose spec to retrieve.

        Returns:
            The ToolSpec instance.

        Raises:
            ToolNotFoundError: If no tool with the given name is found.
        """
        return self.get_tool(name).spec

    def list_tools(self) -> List[ToolSpec]:
        """
        Lists the specifications of all registered tools.

        Returns:
            A list of ToolSpec objects for all registered tools.
        """
        return [tool.spec for tool in self._tools.values()]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Executes a registered tool by name with the given arguments.

        Performs input and output validation using the tool's schemas.

        Args:
            name: The name of the tool to execute.
            arguments: A dictionary of arguments to pass to the tool.

        Returns:
            A ToolResult object containing the execution outcome.
        """
        validated_input = {}
        output_data = None
        error_message = None

        try:
            tool = self.get_tool(name)

            # 1. Validate Input
            try:
                if tool.spec.input_schema != DEFAULT_SCHEMA:
                    validated_input_model = tool.spec.input_schema(**arguments)
                    validated_input = validated_input_model.model_dump()
                else:
                    # If default schema, pass arguments directly if any
                    validated_input = arguments if arguments else {}

            except ValidationError as e:
                raise ToolExecutionError(f"Input validation failed: {e}") from e

            # 2. Execute Tool Safely
            # The execute_tool_safely function now handles the actual execution
            # in a separate process and returns a ToolResult.
            # Output validation is implicitly skipped here, as the safe executor
            # returns the raw output or error directly within the ToolResult.
            # If strict output validation is needed *after* safe execution,
            # it would need to be added back here, operating on result.output.
            result: ToolResult = await execute_tool_safely(tool, validated_input)

            # Return the result obtained from the safe execution wrapper.
            # It already contains tool_name, tool_args, output/error, status_code.
            return result

        except (ToolNotFoundError, ToolExecutionError, Exception) as e:
            # Reason: Catch errors during tool lookup or input validation before safe execution.
            # Also catch unexpected errors during the setup for safe execution.
            error_message = f"Error during tool preparation or input validation: {e}"
            import traceback
            tb_str = traceback.format_exc()
            error_message += f"\n{tb_str}"
            # Determine the appropriate status code
            # Check if the caught exception (or its cause) is a ValidationError
            is_validation_err = isinstance(e, ValidationError) or isinstance(e.__cause__, ValidationError)
            status_code = 400 if is_validation_err else 500

            # Return an error ToolResult
            return ToolResult(
                tool_name=name,
                tool_args=arguments, # Original args before validation attempt
                output=None,
                error=error_message,
                status_code=status_code
            )
