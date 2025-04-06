import pytest
from pydantic import ValidationError

from agentkit.tools.schemas import ToolSpec, ToolResult, Tool
from agentkit.tools.mcp_proxy import MCPProxyToolInput


from pydantic import BaseModel # Add BaseModel import

# --- ToolSpec Tests ---

# Define a dummy BaseModel for schema tests
class DummyInputSchema(BaseModel):
    arg1: str

def test_toolspec_valid():
    """Tests successful creation of a ToolSpec."""
    spec = ToolSpec(
        name="test_tool",
        description="A test tool description.",
        input_schema=DummyInputSchema, # Use the BaseModel subclass
    )
    assert spec.name == "test_tool"
    assert spec.description == "A test tool description."
    # Assert that the stored schema is the class itself
    assert spec.input_schema is DummyInputSchema


def test_toolspec_missing_name():
    """Tests validation error for missing name."""
    with pytest.raises(ValidationError):
        ToolSpec(
            description="A test tool description.",
            input_schema={"type": "object"},
        )


def test_toolspec_missing_description():
    """Tests validation error for missing description."""
    with pytest.raises(ValidationError):
        ToolSpec(
            name="test_tool",
            input_schema={"type": "object"},
        )


def test_toolspec_invalid_schema_type():
    """Tests validation error for invalid input_schema type."""
    with pytest.raises(ValidationError):
        ToolSpec(
            name="test_tool",
            description="A test tool description.",
            input_schema={"not": "a BaseModel subclass"}, # Pass something invalid
        )


# --- ToolResult Tests ---

def test_toolresult_valid_success():
    """Tests successful creation of a ToolResult for success."""
    result = ToolResult(
        tool_name="test_tool",
        tool_args={"input": "value"}, # Add missing tool_args
        status_code=200,
        output={"data": "success"},
        error=None,
    )
    assert result.tool_name == "test_tool"
    assert result.tool_args == {"input": "value"}
    assert result.status_code == 200
    assert result.output == {"data": "success"}
    assert result.error is None


def test_toolresult_valid_error():
    """Tests successful creation of a ToolResult for error."""
    result = ToolResult(
        tool_name="test_tool",
        tool_args={"input": "failed"}, # Add missing tool_args
        status_code=500,
        output=None,
        error="Something went wrong",
    )
    assert result.tool_name == "test_tool"
    assert result.tool_args == {"input": "failed"}
    assert result.status_code == 500
    assert result.output is None
    assert result.error == "Something went wrong"


def test_toolresult_missing_tool_name():
    """Tests validation error for missing tool_name."""
    with pytest.raises(ValidationError):
        ToolResult(status_code=200, output={"data": "success"})


def test_toolresult_missing_status_code():
    """Tests validation error for missing status_code."""
    with pytest.raises(ValidationError):
        ToolResult(tool_name="test_tool", output={"data": "success"})


def test_toolresult_invalid_status_code_type():
    """Tests validation error for invalid status_code type."""
    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="test_tool",
            status_code="not an int",
            output={"data": "success"},
        )


# --- Tool Base Class Tests ---

def test_tool_abc_instantiation_fails():
    """Tests that the abstract Tool class cannot be instantiated directly."""
    # Tool.__init__ raises NotImplementedError if spec is missing
    with pytest.raises(NotImplementedError):
        Tool()


# --- MCPProxyToolInput Tests ---

def test_mcp_proxy_input_valid():
    """Tests successful creation of MCPProxyToolInput."""
    input_data = MCPProxyToolInput(
        server_name="test-server", # Use correct field name
        tool_name="get_data",      # Use correct field name
        arguments={"param1": "value1"}, # Use correct field name
    )
    assert input_data.server_name == "test-server"
    assert input_data.tool_name == "get_data"
    assert input_data.arguments == {"param1": "value1"}


def test_mcp_proxy_input_missing_server_name():
    """Tests validation error for missing server_name."""
    with pytest.raises(ValidationError):
        MCPProxyToolInput(
            tool_name="get_data",
            arguments={"param1": "value1"},
        )


def test_mcp_proxy_input_missing_tool_name():
    """Tests validation error for missing tool_name."""
    with pytest.raises(ValidationError):
        MCPProxyToolInput(
            server_name="test-server",
            arguments={"param1": "value1"},
        )


def test_mcp_proxy_input_missing_arguments():
    """Tests validation error for missing arguments."""
    with pytest.raises(ValidationError):
        MCPProxyToolInput(
            server_name="test-server",
            tool_name="get_data",
        )


def test_mcp_proxy_input_invalid_arguments_type():
    """Tests validation error for invalid arguments type."""
    with pytest.raises(ValidationError):
        MCPProxyToolInput(
            server_name="test-server",
            tool_name="get_data",
            arguments="not a dict",
        )
