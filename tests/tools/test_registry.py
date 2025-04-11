# agentkit/tests/tools/test_registry.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from agentkit.tools.registry import ToolRegistry, ToolNotFoundError, ToolRegistrationError # Added commas
from agentkit.tools.schemas import Tool, ToolSpec, ToolResult


# --- Helper Mock Tool ---

class MockTool(Tool):
    def __init__(self, name="mock_tool", description="A mock tool.", schema=None):
        self._spec = ToolSpec(
            name=name,
            description=description,
            input_schema=schema or {},
        )
        # Allow mocking the execute method easily
        self.execute = AsyncMock()

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    # execute is mocked via AsyncMock


# --- Fixtures ---

@pytest.fixture
def tool_registry():
    """Fixture for an empty ToolRegistry."""
    return ToolRegistry()

@pytest.fixture
def mock_tool_instance():
    """Fixture for a basic MockTool instance."""
    return MockTool()

@pytest.fixture
def mock_tool_instance_alt():
    """Fixture for another MockTool instance with a different name."""
    return MockTool(name="alt_mock_tool", description="Another mock tool.")


# --- Test Cases ---

def test_registry_initialization(tool_registry):
    """Tests that the registry initializes empty."""
    assert tool_registry.list_tools() == []
    # Test that get_tool raises ToolNotFoundError for a nonexistent tool
    with pytest.raises(ToolNotFoundError):
        tool_registry.get_tool("nonexistent")


def test_registry_register_tool_success(tool_registry, mock_tool_instance):
    """Tests successful registration of a tool."""
    tool_registry.add_tool(mock_tool_instance) # Use add_tool
    assert tool_registry.list_tools() == [mock_tool_instance.spec]
    assert tool_registry.get_tool(mock_tool_instance.spec.name) is mock_tool_instance


def test_registry_register_multiple_tools(tool_registry, mock_tool_instance, mock_tool_instance_alt):
    """Tests registering multiple different tools."""
    tool_registry.add_tool(mock_tool_instance) # Use add_tool
    tool_registry.add_tool(mock_tool_instance_alt) # Use add_tool

    registered_specs = tool_registry.list_tools()
    assert len(registered_specs) == 2
    assert mock_tool_instance.spec in registered_specs
    assert mock_tool_instance_alt.spec in registered_specs

    assert tool_registry.get_tool(mock_tool_instance.spec.name) is mock_tool_instance
    assert tool_registry.get_tool(mock_tool_instance_alt.spec.name) is mock_tool_instance_alt


def test_registry_register_tool_duplicate_name(tool_registry, mock_tool_instance):
    """Tests that registering a tool with a duplicate name raises an error."""
    tool_registry.add_tool(mock_tool_instance) # Use add_tool
    duplicate_tool = MockTool(name=mock_tool_instance.spec.name) # Same name

    with pytest.raises(ToolRegistrationError, match="already registered"):
        tool_registry.add_tool(duplicate_tool) # Use add_tool

    # Ensure only the first tool remains
    assert tool_registry.list_tools() == [mock_tool_instance.spec]


def test_registry_get_tool_not_found(tool_registry):
    """Tests getting a tool that hasn't been registered."""
    # Test that get_tool raises ToolNotFoundError
    with pytest.raises(ToolNotFoundError):
        tool_registry.get_tool("not_registered_tool")


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", new_callable=AsyncMock)
async def test_registry_execute_tool_success(mock_safe_execute, tool_registry, mock_tool_instance):
    """Tests successful execution of a registered tool via the registry."""
    tool_name = mock_tool_instance.spec.name
    tool_args_dict = {"arg1": "value1"} # Use a different name to avoid confusion
    # Add missing fields to ToolResult
    expected_result = ToolResult(tool_name=tool_name, tool_args=tool_args_dict, output={"success": True}, error=None)

    # Configure the mock execute_tool_safely to return the expected result
    mock_safe_execute.return_value = expected_result

    # Register the tool
    tool_registry.add_tool(mock_tool_instance) # Use add_tool

    # Execute the tool via the registry - use arguments=
    actual_result = await tool_registry.execute_tool(name=tool_name, arguments=tool_args_dict)

    # Assert that execute_tool_safely was called correctly using positional arguments
    # Note: execute_tool validates input first, then calls execute_tool_safely with validated args
    # For this test, assume validation passes and validated_input == tool_args_dict
    mock_safe_execute.assert_awaited_once_with(mock_tool_instance, tool_args_dict)

    # Assert the final result matches what execute_tool_safely returned
    assert actual_result == expected_result


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", new_callable=AsyncMock)
async def test_registry_execute_tool_not_found(mock_safe_execute, tool_registry):
    """Tests executing a tool that is not registered."""
    tool_name = "nonexistent_tool"
    tool_args_dict = {"arg": "val"} # Use a different name

    # Expect execute_tool to return an error ToolResult, not raise ToolNotFoundError
    actual_result = await tool_registry.execute_tool(name=tool_name, arguments=tool_args_dict)

    assert actual_result.error is not None
    assert f"Tool '{tool_name}' not found" in actual_result.error
    assert actual_result.status_code == 500 # Check status code based on registry.py logic
    mock_safe_execute.assert_not_awaited()


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", new_callable=AsyncMock)
async def test_registry_execute_tool_safe_execution_error(mock_safe_execute, tool_registry, mock_tool_instance):
    """Tests when execute_tool_safely itself returns an error result."""
    tool_name = mock_tool_instance.spec.name
    tool_args_dict = {"arg1": "value1"} # Use a different name
    # Add missing fields to ToolResult
    error_result = ToolResult(tool_name=tool_name, tool_args=tool_args_dict, output=None, error="Safe execution failed")

    mock_safe_execute.return_value = error_result
    tool_registry.add_tool(mock_tool_instance) # Use add_tool

    # Use arguments=
    actual_result = await tool_registry.execute_tool(name=tool_name, arguments=tool_args_dict)

    # Use positional arguments in assertion
    mock_safe_execute.assert_awaited_once_with(mock_tool_instance, tool_args_dict)
    assert actual_result == error_result


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", side_effect=Exception("Wrapper error"))
async def test_registry_execute_tool_unexpected_wrapper_error(mock_safe_execute, tool_registry, mock_tool_instance):
    """Tests when the call to execute_tool_safely raises an unexpected exception."""
    tool_name = mock_tool_instance.spec.name
    tool_args_dict = {"arg1": "value1"} # Use a different name

    tool_registry.add_tool(mock_tool_instance) # Use add_tool

    # Use arguments=
    actual_result = await tool_registry.execute_tool(name=tool_name, arguments=tool_args_dict)

    # Use positional arguments in assertion
    mock_safe_execute.assert_awaited_once_with(mock_tool_instance, tool_args_dict)
    assert actual_result.output is None
    # Check the actual error message format from registry.py
    assert "Error during tool preparation or input validation: Wrapper error" in actual_result.error
