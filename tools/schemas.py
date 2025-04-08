# agentkit/tools/schemas.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class ToolResult(BaseModel):
    """
    Represents the outcome of executing a tool.
    """

    model_config = ConfigDict(frozen=True) # Make results immutable

    output: Any = Field(..., description="The primary output data from the tool.")
    error: Optional[str] = Field(None, description="Any error message if execution failed.")


class ToolSpec(BaseModel):
    """
    Defines the specification of a tool, including its name, description,
    and input schema.
    """

    model_config = ConfigDict(frozen=True) # Make specs immutable

    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A description of what the tool does.")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="A JSON Schema describing the expected input arguments for the tool.",
    )


class Tool(ABC):
    """
    Abstract base class for all tools that an agent can use.

    Subclasses must implement the `spec` property and the `execute` method.
    """

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:
        """
        Returns the specification (ToolSpec) of the tool.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Executes the tool's logic with the provided arguments.

        Args:
            **kwargs: The input arguments for the tool, validated against the input_schema.

        Returns:
            ToolResult: The result of the tool execution.
        """
        raise NotImplementedError
