"""
Defines Pydantic models for specifying agent tools.
"""
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field, create_model

# Using Any for schema definition for now, can be refined later
# e.g., using JSONSchema types or more specific Pydantic fields
ToolInputSchema = Type[BaseModel]
ToolOutputSchema = Type[BaseModel]

# Default empty schema
DEFAULT_SCHEMA = create_model('EmptySchema')

class ToolSpec(BaseModel):
    """
    Specification for a tool that an agent can use.

    Attributes:
        name: Unique identifier for the tool.
        description: Natural language description of what the tool does.
        input_schema: Pydantic model defining the expected input arguments.
                      Defaults to an empty schema if not provided.
        output_schema: Pydantic model defining the expected output structure.
                       Defaults to an empty schema if not provided.
    """
    name: str = Field(..., description="Unique name for the tool.")
    description: str = Field(..., description="Description of the tool's purpose.")
    input_schema: ToolInputSchema = Field(
        default=DEFAULT_SCHEMA,
        description="Pydantic model for input validation."
    )
    output_schema: ToolOutputSchema = Field(
        default=DEFAULT_SCHEMA,
        description="Pydantic model for output validation."
    )

    class Config:
        arbitrary_types_allowed = True # Allow Type[BaseModel]

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
    tool_input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
