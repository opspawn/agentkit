"""
Manages the registration and execution of agent tools.
"""
import inspect
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from .schemas import ToolSpec, ToolResult, DEFAULT_SCHEMA


class ToolExecutionError(Exception):
    """Custom exception for errors during tool execution."""
    pass


class ToolNotFoundError(Exception):
    """Custom exception when a tool is not found in the registry."""
    pass


class Tool:
    """
    Represents a callable tool with its specification.

    Attributes:
        spec: The ToolSpec defining the tool's metadata and schemas.
        function: The actual callable function implementing the tool's logic.
        is_async: Boolean indicating if the tool function is asynchronous.
    """
    def __init__(self, spec: ToolSpec, function: Callable[..., Any]):
        """
        Initializes a Tool instance.

        Args:
            spec: The specification for the tool.
            function: The callable function for the tool.

        Raises:
            ValueError: If the function is not callable.
        """
        if not callable(function):
            raise ValueError("Provided function must be callable.")
        self.spec = spec
        self.function = function
        self.is_async = inspect.iscoroutinefunction(function)

    async def execute(self, **kwargs: Any) -> Any:
        """
        Executes the tool's function with validated arguments.

        Handles both synchronous and asynchronous functions. Input arguments
        are automatically validated against the tool's input schema.

        Args:
            **kwargs: Keyword arguments to pass to the tool function.

        Returns:
            The result returned by the tool function.

        Raises:
            ToolExecutionError: If the function execution fails.
        """
        try:
            if self.is_async:
                return await self.function(**kwargs)
            else:
                # Consider running sync functions in a thread pool executor
                # for non-blocking behavior in async contexts if needed later.
                return self.function(**kwargs)
        except Exception as e:
            # Reason: Catching broad Exception to handle any failure within the tool code.
            raise ToolExecutionError(f"Error executing tool '{self.spec.name}': {e}") from e


class ToolRegistry:
    """
    Manages a collection of tools available to an agent.
    """
    def __init__(self):
        """Initializes an empty ToolRegistry."""
        self._tools: Dict[str, Tool] = {}

    def add_tool(self, tool: Tool):
        """
        Registers a tool in the registry.

        Args:
            tool: The Tool instance to register.

        Raises:
            ValueError: If a tool with the same name already exists.
        """
        if tool.spec.name in self._tools:
            raise ValueError(f"Tool with name '{tool.spec.name}' already registered.")
        self._tools[tool.spec.name] = tool

    def get_tool(self, name: str) -> Tool:
        """
        Retrieves a tool by its name.

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

            # 2. Execute Tool
            raw_output = await tool.execute(**validated_input)

            # 3. Validate Output
            try:
                if tool.spec.output_schema != DEFAULT_SCHEMA:
                    if not isinstance(raw_output, dict):
                         # Attempt to convert if it's a simple type expected by a single-field model
                         # This might need refinement based on common tool return patterns
                         if len(tool.spec.output_schema.model_fields) == 1:
                             field_name = list(tool.spec.output_schema.model_fields.keys())[0]
                             raw_output = {field_name: raw_output}
                         else:
                             raise ToolExecutionError(f"Output validation failed: Expected a dictionary-like structure for schema {tool.spec.output_schema.__name__}, got {type(raw_output)}")

                    validated_output_model = tool.spec.output_schema(**raw_output)
                    output_data = validated_output_model.model_dump()
                elif raw_output is not None:
                     # If default schema, but tool returned something (unexpected?)
                     # For now, just record it as a dict if possible, else stringify
                     output_data = raw_output if isinstance(raw_output, dict) else {"result": str(raw_output)}


            except ValidationError as e:
                raise ToolExecutionError(f"Output validation failed: {e}") from e

        except (ToolNotFoundError, ToolExecutionError, Exception) as e:
            # Reason: Catching known execution errors and general exceptions
            error_message = str(e)

        return ToolResult(
            tool_name=name,
            tool_input=validated_input, # Use validated input
            output=output_data,
            error=error_message
        )
