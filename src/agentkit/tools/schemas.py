"""
Defines Pydantic models and base classes for agent tools.
"""
import inspect
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel, Field, create_model, ConfigDict

# Default empty schema
DEFAULT_SCHEMA = create_model('EmptySchema')() # Instantiate the model for default value comparison

class ToolSpec(BaseModel):
    """
    Specification for a tool that an agent can use.

    Attributes:
        name: Unique identifier for the tool.
        description: Natural language description of what the tool does.
        input_schema: Dictionary representing the JSON schema for input arguments.
                      Defaults to an empty schema if not provided.
        output_schema: Dictionary representing the JSON schema for the output structure.
                       Defaults to an empty schema if not provided.
    """
    name: str = Field(..., description="Unique name for the tool.")
    description: str = Field(..., description="Description of the tool's purpose.")
    input_schema: Dict[str, Any] = Field(
        default_factory=lambda: DEFAULT_SCHEMA.model_dump(mode='json'), # Use factory for mutable default
        description="JSON schema for input validation."
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=lambda: DEFAULT_SCHEMA.model_dump(mode='json'), # Use factory for mutable default
        description="JSON schema for output validation."
    )

    # Pydantic v2 configuration
    # model_config = ConfigDict(
    #     arbitrary_types_allowed=True # No longer needed
    # )

class ToolResult(BaseModel):
    """
    Represents the result of executing a tool.

    Attributes:
        tool_name: The name of the tool that was executed.
        tool_input: The validated input arguments passed to the tool.
        output: The validated output produced by the tool.
        error: An error message if the tool execution failed, None otherwise.
    """
    tool_name: str
    tool_args: Dict[str, Any] # Renamed from tool_input for consistency
    output: Optional[Any] = None # Allow non-dict output before potential validation
    error: Optional[str] = None
    status_code: int = Field(default=200, description="HTTP-like status code (e.g., 200 OK, 400 Bad Request, 500 Error).")


# --- Base Tool Error ---

class ToolError(Exception):
    """Base class for tool-related errors."""
    pass


# --- Tool Class Definition ---
# Moved from registry.py to avoid circular imports

class Tool:
    """
    Base class for representing a callable tool with its specification.
    Subclasses should define the `spec` attribute and implement `execute`.

    Attributes:
        spec: The ToolSpec defining the tool's metadata and schemas.
        is_async: Boolean indicating if the tool's execute method is asynchronous.
                  (Note: This is determined by the subclass implementation)
    """
    spec: ToolSpec # Subclasses must define this

    def __init__(self):
        """Initializes the Tool instance and checks for spec."""
        if not hasattr(self, 'spec') or not isinstance(self.spec, ToolSpec):
            raise NotImplementedError(f"Subclasses of Tool must define a 'spec' attribute of type ToolSpec.")
        # is_async check might be better done on the instance's execute method if needed
        # self.is_async = inspect.iscoroutinefunction(self.execute) # This check is complex here

    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Executes the tool's logic with validated arguments.
        Subclasses MUST implement this method.
        It can be synchronous or asynchronous (use `async def` if needed).

        Args:
            args: A dictionary containing validated input arguments based on spec.input_schema.

        Returns:
            The result of the tool's execution. This could be a dictionary,
            a primitive type, or a ToolResult instance directly.

        Raises:
            NotImplementedError: If the subclass does not implement execute.
            Exception: Any exception raised during tool execution.
        """
        raise NotImplementedError("Subclasses must implement the 'execute' method.")

    # Optional: Add an async execute placeholder if needed, but subclasses define sync/async
    # async def execute_async(self, args: Dict[str, Any]) -> Any:
    #     raise NotImplementedError("Subclasses must implement 'execute' or 'execute_async'.")
