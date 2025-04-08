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
    assert tool_registry.get_tool("nonexistent") is None


def test_registry_register_tool_success(tool_registry, mock_tool_instance):
    """Tests successful registration of a tool."""
    tool_registry.register_tool(mock_tool_instance)
    assert tool_registry.list_tools() == [mock_tool_instance.spec]
    assert tool_registry.get_tool(mock_tool_instance.spec.name) is mock_tool_instance


def test_registry_register_multiple_tools(tool_registry, mock_tool_instance, mock_tool_instance_alt):
    """Tests registering multiple different tools."""
    tool_registry.register_tool(mock_tool_instance)
    tool_registry.register_tool(mock_tool_instance_alt)

    registered_specs = tool_registry.list_tools()
    assert len(registered_specs) == 2
    assert mock_tool_instance.spec in registered_specs
    assert mock_tool_instance_alt.spec in registered_specs

    assert tool_registry.get_tool(mock_tool_instance.spec.name) is mock_tool_instance
    assert tool_registry.get_tool(mock_tool_instance_alt.spec.name) is mock_tool_instance_alt


def test_registry_register_tool_duplicate_name(tool_registry, mock_tool_instance):
    """Tests that registering a tool with a duplicate name raises an error."""
    tool_registry.register_tool(mock_tool_instance)
    duplicate_tool = MockTool(name=mock_tool_instance.spec.name) # Same name

    with pytest.raises(ToolRegistrationError, match="already registered"):
        tool_registry.register_tool(duplicate_tool)

    # Ensure only the first tool remains
    assert tool_registry.list_tools() == [mock_tool_instance.spec]


def test_registry_get_tool_not_found(tool_registry):
    """Tests getting a tool that hasn't been registered."""
    assert tool_registry.get_tool("not_registered_tool") is None


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", new_callable=AsyncMock)
async def test_registry_execute_tool_success(mock_safe_execute, tool_registry, mock_tool_instance):
    """Tests successful execution of a registered tool via the registry."""
    tool_name = mock_tool_instance.spec.name
    tool_input = {"arg1": "value1"}
    expected_result = ToolResult(output={"success": True}, error=None)

    # Configure the mock execute_tool_safely to return the expected result
    mock_safe_execute.return_value = expected_result

    # Register the tool
    tool_registry.register_tool(mock_tool_instance)

    # Execute the tool via the registry
    actual_result = await tool_registry.execute_tool(name=tool_name, tool_input=tool_input)

    # Assert that execute_tool_safely was called correctly
    mock_safe_execute.assert_awaited_once_with(tool=mock_tool_instance, tool_input=tool_input)

    # Assert the final result matches what execute_tool_safely returned
    assert actual_result == expected_result


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", new_callable=AsyncMock)
async def test_registry_execute_tool_not_found(mock_safe_execute, tool_registry):
    """Tests executing a tool that is not registered."""
    tool_name = "nonexistent_tool"
    tool_input = {"arg": "val"}

    with pytest.raises(ToolNotFoundError, match=f"Tool '{tool_name}' not found"):
        await tool_registry.execute_tool(name=tool_name, tool_input=tool_input)

    mock_safe_execute.assert_not_awaited()


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", new_callable=AsyncMock)
async def test_registry_execute_tool_safe_execution_error(mock_safe_execute, tool_registry, mock_tool_instance):
    """Tests when execute_tool_safely itself returns an error result."""
    tool_name = mock_tool_instance.spec.name
    tool_input = {"arg1": "value1"}
    error_result = ToolResult(output=None, error="Safe execution failed")

    mock_safe_execute.return_value = error_result
    tool_registry.register_tool(mock_tool_instance)

    actual_result = await tool_registry.execute_tool(name=tool_name, tool_input=tool_input)

    mock_safe_execute.assert_awaited_once_with(tool=mock_tool_instance, tool_input=tool_input)
    assert actual_result == error_result


@pytest.mark.asyncio
@patch("agentkit.tools.registry.execute_tool_safely", side_effect=Exception("Wrapper error"))
async def test_registry_execute_tool_unexpected_wrapper_error(mock_safe_execute, tool_registry, mock_tool_instance):
    """Tests when the call to execute_tool_safely raises an unexpected exception."""
    tool_name = mock_tool_instance.spec.name
    tool_input = {"arg1": "value1"}

    tool_registry.register_tool(mock_tool_instance)

    actual_result = await tool_registry.execute_tool(name=tool_name, tool_input=tool_input)

    mock_safe_execute.assert_awaited_once_with(tool=mock_tool_instance, tool_input=tool_input)
    assert actual_result.output is None
    assert "Unexpected execution wrapper error: Wrapper error" in actual_result.error
