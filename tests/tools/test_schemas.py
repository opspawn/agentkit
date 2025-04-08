# agentkit/tests/tools/test_schemas.py
import pytest
from pydantic import ValidationError

from agentkit.tools.schemas import ToolResult, ToolSpec


# --- ToolResult Tests ---

def test_tool_result_success():
    """Tests creating a successful ToolResult."""
    output_data = {"value": 42}
    result = ToolResult(output=output_data)
    assert result.output == output_data
    assert result.error is None
    # Check immutability
    with pytest.raises(ValidationError):
        result.error = "New error"


def test_tool_result_error():
    """Tests creating a ToolResult with an error."""
    error_msg = "Something went wrong"
    result = ToolResult(output=None, error=error_msg)
    assert result.output is None
    assert result.error == error_msg
    # Check immutability
    with pytest.raises(ValidationError):
        result.output = "New output"


def test_tool_result_requires_output():
    """Tests that output field is required."""
    with pytest.raises(ValidationError, match="Field required"):
        ToolResult(error="An error occurred") # Missing output


# --- ToolSpec Tests ---

def test_tool_spec_creation():
    """Tests creating a valid ToolSpec."""
    name = "calculator"
    description = "Performs calculations."
    schema = {"type": "object", "properties": {"expression": {"type": "string"}}}
    spec = ToolSpec(name=name, description=description, input_schema=schema)
    assert spec.name == name
    assert spec.description == description
    assert spec.input_schema == schema
    # Check immutability
    with pytest.raises(ValidationError):
        spec.name = "new_calculator"


def test_tool_spec_default_schema():
    """Tests that input_schema defaults to an empty dict."""
    name = "simple_tool"
    description = "A tool with no input."
    spec = ToolSpec(name=name, description=description)
    assert spec.name == name
    assert spec.description == description
    assert spec.input_schema == {}


def test_tool_spec_missing_required_fields():
    """Tests validation errors for missing required fields."""
    with pytest.raises(ValidationError, match="Field required"):
        ToolSpec(description="Missing name")

    with pytest.raises(ValidationError, match="Field required"):
        ToolSpec(name="Missing description")


# --- Tool ABC Tests ---
# (No direct tests for the ABC itself, but ensure subclasses can be defined)

def test_tool_abc_definition():
    """Placeholder test to ensure Tool ABC is defined correctly."""
    from agentkit.tools.schemas import Tool # Re-import locally if needed
    assert Tool is not None
    # Further tests would involve creating a concrete subclass
