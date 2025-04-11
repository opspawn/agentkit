# agentkit/agentkit/tools/registry.py
"""Manages the registration and execution of agent tools."""

from typing import Any, Dict, List, Optional

from pydantic import ValidationError

# Use relative import for interfaces
from ..core.interfaces.tool_manager import BaseToolManager
from .execution import execute_tool_safely
from .schemas import DEFAULT_SCHEMA, Tool, ToolError, ToolResult, ToolSpec


class ToolExecutionError(ToolError):
    """Custom exception for errors during tool execution."""

    pass


class ToolRegistrationError(ToolError):
    """Custom exception for errors during tool registration."""
    pass


class ToolNotFoundError(ToolError):
    """Custom exception when a tool is not found in the registry."""

    pass


# Tool class definition removed from here


class ToolRegistry(BaseToolManager):
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
            ToolRegistrationError: If a tool with the same name already exists or if the provided object is not a Tool instance.
        """
        if not isinstance(tool, Tool):
             # Reason: Ensure only valid Tool instances are added.
             raise ToolRegistrationError("Item to be added must be an instance of the Tool class.")
        if tool.spec.name in self._tools:
            raise ToolRegistrationError(f"Tool with name '{tool.spec.name}' already registered.")
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

    def lookup_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Find a tool by its name.

        Args:
            tool_name: The name of the tool to look up.

        Returns:
            The Tool instance if found, otherwise None.
        """
        return self._tools.get(tool_name)

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
        # Use lookup_tool internally now
        tool = self.lookup_tool(name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{name}' not found.")
        return tool.spec

    def list_tools(self) -> List[ToolSpec]:
        """
        Lists the specifications of all registered tools.

        Returns:
            A list of ToolSpec objects for all registered tools.
        """
        return [tool.spec for tool in self._tools.values()]

    async def execute_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
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
            # Use lookup_tool internally now
            tool = self.lookup_tool(name)
            if not tool:
                raise ToolNotFoundError(f"Tool '{name}' not found.")

            # 1. Validate Input
            try:
                # Check if the schema is the default empty one by comparing with its dumped version
                if tool.spec.input_schema != DEFAULT_SCHEMA.model_dump(mode='json'):
                    # Dynamically create a model from the schema dict for validation
                    InputModel = create_model(
                        f"{tool.spec.name}Input",
                        **{field: (details.get('type', Any), ...) for field, details in tool.spec.input_schema.get('properties', {}).items()},
                        __config__=ConfigDict(extra='ignore') # Allow extra fields but ignore them
                    )
                    validated_input_model = InputModel(**arguments)
                    validated_input = validated_input_model.model_dump()
                else:
                    # If default schema, no validation needed, pass arguments if any
                    validated_input = arguments if arguments else {}

            except ValidationError as e:
                raise ToolExecutionError(f"Input validation failed for tool '{name}': {e}") from e
            except Exception as e: # Catch other potential errors during model creation/validation
                raise ToolExecutionError(f"Unexpected error during input validation for tool '{name}': {e}") from e

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
            # Ensure tool_args is a dict, even if original arguments were None
            error_tool_args = arguments if arguments is not None else {}
            return ToolResult(
                tool_name=name,
                tool_args=error_tool_args, # Use the potentially defaulted dict
                output=None,
                error=error_message,
                status_code=status_code
            )
