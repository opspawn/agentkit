"""
Example tools for simple mathematical operations.
"""
from typing import Dict # Add missing import
from pydantic import BaseModel, Field
from agentkit.tools.schemas import ToolSpec, ToolResult, Tool

# Define Pydantic models for input schemas
class AddInput(BaseModel):
    a: float = Field(..., description="The first number.")
    b: float = Field(..., description="The second number.")

class SubtractInput(BaseModel):
    a: float = Field(..., description="The number to subtract from.")
    b: float = Field(..., description="The number to subtract.")

# Optional: Define output schemas if needed for validation later
# class MathOutput(BaseModel):
#     result: float

class AddTool(Tool):
    """A tool to add two numbers."""
    spec = ToolSpec(
        name="add_numbers",
        description="Adds two numbers (a + b).",
        input_schema=AddInput, # Use the Pydantic model class
        # output_schema=MathOutput # Optional output schema
    )

    def execute(self, args: Dict[str, float]) -> Dict[str, float]:
        """Adds the two numbers provided in args."""
        # Args are already validated floats by Pydantic via ToolRegistry
        a = args["a"]
        b = args["b"]
        result = a + b
        return {"sum": result}


class SubtractTool(Tool):
    """A tool to subtract one number from another."""
    spec = ToolSpec(
        name="subtract_numbers",
        description="Subtracts the second number from the first (a - b).",
        input_schema=SubtractInput, # Use the Pydantic model class
        # output_schema=MathOutput # Optional output schema
    )

    def execute(self, args: Dict[str, float]) -> Dict[str, float]:
        """Subtracts b from a."""
        # Args are already validated floats
        a = args["a"]
        b = args["b"]
        result = a - b
        return {"difference": result}
