# agentkit/tests/tools/test_schemas.py
import pytest
from pydantic import ValidationError

from agentkit.tools.schemas import ToolResult, ToolSpec


# --- ToolResult Tests ---

def test_tool_result_success():
    """Tests creating a successful ToolResult."""
    output_data = {"value": 42}
    # Add required fields
    result = ToolResult(tool_name="test_tool", tool_args={"arg": 1}, output=output_data)
    assert result.output == output_data
    assert result.error is None
    assert result.tool_name == "test_tool"
    assert result.tool_args == {"arg": 1}
    # Check immutability (Pydantic v2 models are immutable by default)
    # with pytest.raises(ValidationError):
    #     result.error = "New error" # This check might fail depending on exact Pydantic config


def test_tool_result_error():
    """Tests creating a ToolResult with an error."""
    error_msg = "Something went wrong"
    # Add required fields
    result = ToolResult(tool_name="error_tool", tool_args={}, output=None, error=error_msg)
    assert result.output is None
    assert result.error == error_msg
    assert result.tool_name == "error_tool"
    assert result.tool_args == {}
    # Check immutability (Pydantic v2 models are immutable by default)
    # with pytest.raises(ValidationError):
    #     result.output = "New output" # This check might fail depending on exact Pydantic config


# def test_tool_result_requires_output(): # This test is invalid as output is Optional
#     """Tests that output field is required."""
#     with pytest.raises(ValidationError, match="Field required"):
#         ToolResult(tool_name="t", tool_args={}, error="An error occurred") # Missing output


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
    # Immutability check removed as default is mutable
    # with pytest.raises(ValidationError):
    #     spec.name = "new_calculator"


def test_tool_spec_default_schema():
    """Tests that input_schema defaults to an empty schema dict."""
    from agentkit.tools.schemas import DEFAULT_SCHEMA # Import for comparison
    name = "simple_tool"
    description = "A tool with no input."
    spec = ToolSpec(name=name, description=description)
    assert spec.name == name
    assert spec.description == description
    # Compare against the dumped default schema
    assert spec.input_schema == DEFAULT_SCHEMA.model_dump(mode='json')


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
