"""
Unit tests for the agentkit.tools module.
"""
import pytest
from pydantic import BaseModel, Field, ValidationError

from agentkit.tools import (
    ToolSpec,
    ToolResult,
    Tool,
    ToolRegistry,
    ToolExecutionError,
    ToolNotFoundError,
    DEFAULT_SCHEMA,
)

# --- Test Data ---

class AddInput(BaseModel):
    a: int
    b: int

class AddOutput(BaseModel):
    result: int

def add_sync(a: int, b: int) -> dict:
    """Sync tool function for testing."""
    return {"result": a + b}

async def add_async(a: int, b: int) -> dict:
    """Async tool function for testing."""
    return {"result": a + b}

def sync_tool_no_schema(value: str) -> str:
    """Sync tool with no specific input/output schema."""
    return f"Processed: {value}"

async def async_tool_raises() -> None:
    """Async tool that always raises an error."""
    raise ValueError("Something went wrong async")

def sync_tool_raises() -> None:
    """Sync tool that always raises an error."""
    raise RuntimeError("Something went wrong sync")


# --- Tool Specs ---

add_spec = ToolSpec(
    name="add",
    description="Adds two integers.",
    input_schema=AddInput,
    output_schema=AddOutput,
)

no_schema_spec = ToolSpec(
    name="process_string",
    description="Processes a string value.",
    # Uses default schemas
)

raiser_spec = ToolSpec(
    name="raiser",
    description="A tool that always fails.",
)

# --- Tests ---

@pytest.fixture
def registry() -> ToolRegistry:
    """Provides a fresh ToolRegistry for each test."""
    return ToolRegistry()

# --- Tool Class Tests ---

def test_tool_creation_sync():
    """Test creating a Tool instance with a sync function."""
    tool = Tool(spec=add_spec, function=add_sync)
    assert tool.spec == add_spec
    assert tool.function == add_sync
    assert not tool.is_async

def test_tool_creation_async():
    """Test creating a Tool instance with an async function."""
    tool = Tool(spec=add_spec, function=add_async)
    assert tool.spec == add_spec
    assert tool.function == add_async
    assert tool.is_async

def test_tool_creation_not_callable():
    """Test that creating a Tool with a non-callable raises ValueError."""
    with pytest.raises(ValueError, match="Provided function must be callable"):
        Tool(spec=add_spec, function=123) # type: ignore

@pytest.mark.asyncio
async def test_tool_execute_sync():
    """Test executing a synchronous tool function."""
    tool = Tool(spec=add_spec, function=add_sync)
    result = await tool.execute(a=5, b=3)
    assert result == {"result": 8}

@pytest.mark.asyncio
async def test_tool_execute_async():
    """Test executing an asynchronous tool function."""
    tool = Tool(spec=add_spec, function=add_async)
    result = await tool.execute(a=10, b=2)
    assert result == {"result": 12}

@pytest.mark.asyncio
async def test_tool_execute_sync_raises():
    """Test executing a sync tool that raises an error."""
    tool = Tool(spec=raiser_spec, function=sync_tool_raises)
    with pytest.raises(ToolExecutionError, match="Error executing tool 'raiser'"):
        await tool.execute()

@pytest.mark.asyncio
async def test_tool_execute_async_raises():
    """Test executing an async tool that raises an error."""
    tool = Tool(spec=raiser_spec, function=async_tool_raises)
    with pytest.raises(ToolExecutionError, match="Error executing tool 'raiser'"):
        await tool.execute()


# --- ToolRegistry Tests ---

def test_registry_add_tool(registry: ToolRegistry):
    """Test adding a valid tool to the registry."""
    tool = Tool(spec=add_spec, function=add_sync)
    registry.add_tool(tool)
    assert registry.get_tool("add") == tool
    assert registry.get_tool_spec("add") == add_spec
    assert len(registry.list_tools()) == 1
    assert registry.list_tools()[0] == add_spec

def test_registry_add_duplicate_tool(registry: ToolRegistry):
    """Test that adding a tool with a duplicate name raises ValueError."""
    tool1 = Tool(spec=add_spec, function=add_sync)
    tool2 = Tool(spec=add_spec, function=add_async) # Same name
    registry.add_tool(tool1)
    with pytest.raises(ValueError, match="Tool with name 'add' already registered."):
        registry.add_tool(tool2)

def test_registry_get_tool_not_found(registry: ToolRegistry):
    """Test that getting a non-existent tool raises ToolNotFoundError."""
    with pytest.raises(ToolNotFoundError, match="Tool 'nonexistent' not found."):
        registry.get_tool("nonexistent")

def test_registry_get_tool_spec_not_found(registry: ToolRegistry):
    """Test getting spec for a non-existent tool raises ToolNotFoundError."""
    with pytest.raises(ToolNotFoundError, match="Tool 'nonexistent' not found."):
        registry.get_tool_spec("nonexistent")

def test_registry_list_tools_empty(registry: ToolRegistry):
    """Test listing tools from an empty registry."""
    assert registry.list_tools() == []

def test_registry_list_tools_multiple(registry: ToolRegistry):
    """Test listing tools from a registry with multiple tools."""
    tool_add = Tool(spec=add_spec, function=add_sync)
    tool_proc = Tool(spec=no_schema_spec, function=sync_tool_no_schema)
    registry.add_tool(tool_add)
    registry.add_tool(tool_proc)
    specs = registry.list_tools()
    assert len(specs) == 2
    assert add_spec in specs
    assert no_schema_spec in specs

@pytest.mark.asyncio
async def test_registry_execute_tool_sync_success(registry: ToolRegistry):
    """Test successfully executing a registered sync tool."""
    tool = Tool(spec=add_spec, function=add_sync)
    registry.add_tool(tool)
    result = await registry.execute_tool(name="add", arguments={"a": 10, "b": 5})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "add"
    assert result.tool_input == {"a": 10, "b": 5}
    assert result.output == {"result": 15}
    assert result.error is None

@pytest.mark.asyncio
async def test_registry_execute_tool_async_success(registry: ToolRegistry):
    """Test successfully executing a registered async tool."""
    tool = Tool(spec=add_spec, function=add_async)
    registry.add_tool(tool)
    result = await registry.execute_tool(name="add", arguments={"a": 7, "b": 3})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "add"
    assert result.tool_input == {"a": 7, "b": 3}
    assert result.output == {"result": 10}
    assert result.error is None

@pytest.mark.asyncio
async def test_registry_execute_tool_input_validation_error(registry: ToolRegistry):
    """Test executing a tool with invalid input arguments."""
    tool = Tool(spec=add_spec, function=add_sync)
    registry.add_tool(tool)
    result = await registry.execute_tool(name="add", arguments={"a": "ten", "b": 5}) # 'a' is wrong type
    assert isinstance(result, ToolResult)
    assert result.tool_name == "add"
    assert result.tool_input == {} # Validation failed before assignment
    assert result.output is None
    assert result.error is not None
    assert "Input validation failed" in result.error
    assert "validation error for AddInput" in result.error

@pytest.mark.asyncio
async def test_registry_execute_tool_sync_raises_error(registry: ToolRegistry):
    """Test executing a sync tool that raises an internal error."""
    tool = Tool(spec=raiser_spec, function=sync_tool_raises)
    registry.add_tool(tool)
    result = await registry.execute_tool(name="raiser", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "raiser"
    assert result.tool_input == {}
    assert result.output is None
    assert result.error is not None
    assert "Error executing tool 'raiser': Something went wrong sync" in result.error

@pytest.mark.asyncio
async def test_registry_execute_tool_async_raises_error(registry: ToolRegistry):
    """Test executing an async tool that raises an internal error."""
    tool = Tool(spec=raiser_spec, function=async_tool_raises)
    registry.add_tool(tool)
    result = await registry.execute_tool(name="raiser", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "raiser"
    assert result.tool_input == {}
    assert result.output is None
    assert result.error is not None
    assert "Error executing tool 'raiser': Something went wrong async" in result.error

@pytest.mark.asyncio
async def test_registry_execute_tool_not_found(registry: ToolRegistry):
    """Test executing a tool that is not registered."""
    result = await registry.execute_tool(name="nonexistent", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "nonexistent"
    assert result.tool_input == {}
    assert result.output is None
    assert result.error is not None
    assert "Tool 'nonexistent' not found" in result.error

@pytest.mark.asyncio
async def test_registry_execute_tool_no_schema_success(registry: ToolRegistry):
    """Test executing a tool with default (no) schemas."""
    tool = Tool(spec=no_schema_spec, function=sync_tool_no_schema)
    registry.add_tool(tool)
    result = await registry.execute_tool(name="process_string", arguments={"value": "hello"})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "process_string"
    assert result.tool_input == {"value": "hello"}
    # Output is captured even without schema
    assert result.output == {"result": "Processed: hello"}
    assert result.error is None

@pytest.mark.asyncio
async def test_registry_execute_tool_output_validation_error(registry: ToolRegistry):
    """Test executing a tool where the output doesn't match the schema."""
    # Define a tool that returns the wrong type
    class BadOutputToolInput(BaseModel):
        pass
    class BadOutputToolOutput(BaseModel):
        count: int # Expects an int

    def bad_output_func() -> dict:
        return {"count": "not_an_int"} # Returns a string instead

    bad_spec = ToolSpec(
        name="bad_output",
        description="Returns wrong output type.",
        input_schema=BadOutputToolInput,
        output_schema=BadOutputToolOutput,
    )
    tool = Tool(spec=bad_spec, function=bad_output_func)
    registry.add_tool(tool)

    result = await registry.execute_tool(name="bad_output", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "bad_output"
    assert result.tool_input == {}
    assert result.output is None # Validation failed
    assert result.error is not None
    assert "Output validation failed" in result.error
    assert "validation error for BadOutputToolOutput" in result.error
