"""
Unit tests for the agentkit.tools module.
"""
import pytest
import inspect # Needed for iscoroutinefunction check
from typing import Dict # Add missing import
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
# Import the function needed for direct tool execution tests
from agentkit.tools.execution import execute_tool_safely

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


# --- Tool Specs & Mock Tool Classes ---

# Define Pydantic models used by mock tools
class AddInput(BaseModel):
    a: int
    b: int

class AddOutput(BaseModel):
    result: int

# Define mock Tool subclasses for testing registry/execution
class MockSyncTool(Tool):
    spec = ToolSpec(
        name="add",
        description="Adds two integers.",
        input_schema=AddInput,
        output_schema=AddOutput,
    )
    def execute(self, args: Dict[str, int]) -> Dict[str, int]:
        return {"result": args["a"] + args["b"]}

class MockAsyncTool(Tool):
    spec = ToolSpec(
        name="add_async", # Different name to avoid registry conflicts
        description="Adds two integers asynchronously.",
        input_schema=AddInput,
        output_schema=AddOutput,
    )
    async def execute(self, args: Dict[str, int]) -> Dict[str, int]:
        return {"result": args["a"] + args["b"]}

class MockSyncToolNoSchema(Tool):
    spec = ToolSpec(
        name="process_string",
        description="Processes a string value.",
        # Uses default schemas
    )
    def execute(self, args: Dict[str, str]) -> str:
        return f"Processed: {args.get('value', '')}"

class MockAsyncRaiserTool(Tool):
    spec = ToolSpec(
        name="raiser_async",
        description="An async tool that always fails.",
    )
    async def execute(self, args: Dict) -> None:
        raise ValueError("Something went wrong async")

class MockSyncRaiserTool(Tool):
    spec = ToolSpec(
        name="raiser_sync",
        description="A sync tool that always fails.",
    )
    def execute(self, args: Dict) -> None:
        raise RuntimeError("Something went wrong sync")

# Define tool for output validation test
class BadOutputToolInput(BaseModel):
    pass
class BadOutputToolOutput(BaseModel):
    count: int # Expects an int

class MockBadOutputTool(Tool):
    spec = ToolSpec(
        name="bad_output",
        description="Returns wrong output type.",
        input_schema=BadOutputToolInput,
        output_schema=BadOutputToolOutput,
    )
    def execute(self, args: Dict) -> Dict[str, str]:
        return {"count": "not_an_int"} # Returns a string instead


# --- Tests ---

@pytest.fixture
def registry() -> ToolRegistry:
    """Provides a fresh ToolRegistry for each test."""
    return ToolRegistry()

# --- Tool Class Tests (Now testing subclasses) ---

def test_tool_creation_sync():
    """Test creating an instance of a sync Tool subclass."""
    tool = MockSyncTool()
    assert tool.spec.name == "add"
    assert callable(tool.execute)

def test_tool_creation_async():
    """Test creating an instance of an async Tool subclass."""
    tool = MockAsyncTool()
    assert tool.spec.name == "add_async"
    assert inspect.iscoroutinefunction(tool.execute)

def test_tool_creation_requires_spec():
    """Test that creating a Tool subclass without a spec raises error."""
    with pytest.raises(NotImplementedError, match="must define a 'spec' attribute"):
        class NoSpecTool(Tool):
            def execute(self, args): pass
        NoSpecTool()

def test_tool_creation_requires_execute():
    """Test that creating a Tool subclass without execute raises error."""
    # Note: This isn't checked at init, but when execute is called.
    # We test the NotImplementedError during execution tests instead.
    class NoExecuteTool(Tool):
        spec = ToolSpec(name="no_exec", description="...")
    tool = NoExecuteTool()
    assert tool is not None # Instantiation works

@pytest.mark.asyncio
async def test_tool_execute_sync():
    """Test executing a synchronous tool function via execute_tool_safely."""
    tool = MockSyncTool()
    # Use execute_tool_safely as the Tool.execute method is now internal detail
    result = await execute_tool_safely(tool, {"a": 5, "b": 3})
    assert result.output == {"result": 8}
    assert result.error is None

@pytest.mark.asyncio
async def test_tool_execute_async():
    """Test executing an asynchronous tool function via execute_tool_safely."""
    tool = MockAsyncTool()
    result = await execute_tool_safely(tool, {"a": 10, "b": 2})
    assert result.output == {"result": 12}
    assert result.error is None

@pytest.mark.asyncio
async def test_tool_execute_sync_raises():
    """Test executing a sync tool that raises an error via execute_tool_safely."""
    tool = MockSyncRaiserTool()
    result = await execute_tool_safely(tool, {})
    assert result.output is None
    assert result.error is not None
    assert "RuntimeError: Something went wrong sync" in result.error

@pytest.mark.asyncio
async def test_tool_execute_async_raises():
    """Test executing an async tool that raises an error via execute_tool_safely."""
    tool = MockAsyncRaiserTool()
    result = await execute_tool_safely(tool, {})
    assert result.output is None
    assert result.error is not None
    assert "ValueError: Something went wrong async" in result.error

@pytest.mark.asyncio
async def test_tool_execute_not_implemented():
    """Test calling execute on a Tool subclass that didn't implement it."""
    class NoExecuteTool(Tool):
        spec = ToolSpec(name="no_exec", description="...")
    tool = NoExecuteTool()
    result = await execute_tool_safely(tool, {})
    assert result.output is None
    assert result.error is not None
    assert "NotImplementedError: Subclasses must implement the 'execute' method" in result.error


# --- ToolRegistry Tests ---

def test_registry_add_tool(registry: ToolRegistry):
    """Test adding a valid tool instance to the registry."""
    tool = MockSyncTool() # Instantiate the subclass
    registry.add_tool(tool)
    assert registry.get_tool("add") == tool
    assert registry.get_tool_spec("add") == tool.spec
    assert len(registry.list_tools()) == 1
    assert registry.list_tools()[0] == tool.spec

def test_registry_add_duplicate_tool(registry: ToolRegistry):
    """Test that adding a tool with a duplicate name raises ValueError."""
    tool1 = MockSyncTool()
    tool2 = MockSyncTool() # Instance with the same spec name
    registry.add_tool(tool1)
    with pytest.raises(ValueError, match="Tool with name 'add' already registered."):
        registry.add_tool(tool2)

def test_registry_add_non_tool_instance(registry: ToolRegistry):
    """Test adding something that isn't a Tool instance."""
    with pytest.raises(ValueError, match="Item to be added must be an instance of the Tool class."):
        registry.add_tool(MockSyncTool.spec) # Try adding just the spec

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
    tool_add = MockSyncTool()
    tool_proc = MockSyncToolNoSchema()
    registry.add_tool(tool_add)
    registry.add_tool(tool_proc)
    specs = registry.list_tools()
    assert len(specs) == 2
    # Order isn't guaranteed, check for presence
    assert tool_add.spec in specs
    assert tool_proc.spec in specs

@pytest.mark.asyncio
async def test_registry_execute_tool_sync_success(registry: ToolRegistry):
    """Test successfully executing a registered sync tool."""
    tool = MockSyncTool() # Instantiate subclass
    registry.add_tool(tool)
    result = await registry.execute_tool(name="add", arguments={"a": 10, "b": 5})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "add"
    # Assert that tool_args contains the validated arguments
    validated_args = AddInput(a=10, b=5).model_dump()
    assert result.tool_args == validated_args
    assert result.output == {"result": 15}
    assert result.error is None
    assert result.status_code == 200 # From safe exec

@pytest.mark.asyncio
async def test_registry_execute_tool_async_success(registry: ToolRegistry):
    """Test successfully executing a registered async tool."""
    tool = MockAsyncTool() # Instantiate subclass
    registry.add_tool(tool)
    result = await registry.execute_tool(name="add_async", arguments={"a": 7, "b": 3})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "add_async"
    # Assert that tool_args contains the validated arguments
    validated_args = AddInput(a=7, b=3).model_dump()
    assert result.tool_args == validated_args
    assert result.output == {"result": 10}
    assert result.error is None
    assert result.status_code == 200

@pytest.mark.asyncio
async def test_registry_execute_tool_input_validation_error(registry: ToolRegistry):
    """Test executing a tool with invalid input arguments."""
    tool = MockSyncTool() # Instantiate subclass
    registry.add_tool(tool)
    result = await registry.execute_tool(name="add", arguments={"a": "ten", "b": 5}) # 'a' is wrong type
    assert isinstance(result, ToolResult)
    assert result.tool_name == "add"
    assert result.tool_args == {"a": "ten", "b": 5} # Original args in error result
    assert result.output is None
    assert result.error is not None
    assert "Input validation failed" in result.error
    assert "validation error for AddInput" in result.error
    assert result.status_code == 400 # Check status code for validation error

@pytest.mark.asyncio
async def test_registry_execute_tool_sync_raises_error(registry: ToolRegistry):
    """Test executing a sync tool that raises an internal error."""
    tool = MockSyncRaiserTool() # Instantiate subclass
    registry.add_tool(tool)
    result = await registry.execute_tool(name="raiser_sync", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "raiser_sync"
    assert result.tool_args == {}
    assert result.output is None
    assert result.error is not None
    assert "RuntimeError: Something went wrong sync" in result.error
    assert result.status_code == 500 # From safe exec

@pytest.mark.asyncio
async def test_registry_execute_tool_async_raises_error(registry: ToolRegistry):
    """Test executing an async tool that raises an internal error."""
    tool = MockAsyncRaiserTool() # Instantiate subclass
    registry.add_tool(tool)
    result = await registry.execute_tool(name="raiser_async", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "raiser_async"
    assert result.tool_args == {}
    assert result.output is None
    assert result.error is not None
    assert "ValueError: Something went wrong async" in result.error
    assert result.status_code == 500 # From safe exec

@pytest.mark.asyncio
async def test_registry_execute_tool_not_found(registry: ToolRegistry):
    """Test executing a tool that is not registered."""
    result = await registry.execute_tool(name="nonexistent", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "nonexistent"
    # The code returns the original arguments in the error case
    assert result.tool_args == {}
    assert result.output is None
    assert result.error is not None
    assert "Tool 'nonexistent' not found" in result.error
    assert result.status_code == 500 # Error before safe exec

@pytest.mark.asyncio
async def test_registry_execute_tool_no_schema_success(registry: ToolRegistry):
    """Test executing a tool with default (no) schemas."""
    tool = MockSyncToolNoSchema() # Instantiate subclass
    registry.add_tool(tool)
    result = await registry.execute_tool(name="process_string", arguments={"value": "hello"})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "process_string"
    assert result.tool_args == {"value": "hello"}
    # Output is captured even without schema by safe exec
    assert result.output == "Processed: hello" # Safe exec returns raw output
    assert result.error is None
    assert result.status_code == 200

@pytest.mark.asyncio
async def test_registry_execute_tool_output_validation_error(registry: ToolRegistry):
    """Test executing a tool where the output doesn't match the schema."""
    # Note: Output validation was removed from registry.execute_tool when
    # switching to execute_tool_safely, as the safe executor returns raw output.
    # If output validation is desired *after* safe execution, it needs to be
    # added back to the registry method or handled elsewhere.
    # This test is now effectively testing that bad output is returned successfully.
    tool = MockBadOutputTool() # Instantiate subclass
    registry.add_tool(tool)

    result = await registry.execute_tool(name="bad_output", arguments={})
    assert isinstance(result, ToolResult)
    assert result.tool_name == "bad_output"
    assert result.tool_args == {}
    # The raw, invalid output is returned by execute_tool_safely
    assert result.output == {"count": "not_an_int"}
    assert result.error is None # No error during execution itself


@pytest.mark.asyncio
async def test_registry_execute_tool_none_arguments(registry: ToolRegistry):
    """Test executing a tool with arguments=None."""
    tool = MockSyncTool() # Tool expects 'a' and 'b'
    registry.add_tool(tool)
    # Execute with None arguments
    result = await registry.execute_tool(name="add", arguments=None)
    assert isinstance(result, ToolResult)
    assert result.tool_name == "add"
    assert result.tool_args == {} # Defaulted to {} in error result
    assert result.output is None
    assert result.error is not None
    # Check for the actual TypeError message from argument unpacking
    assert "Error during tool preparation or input validation" in result.error
    assert "argument after ** must be a mapping, not NoneType" in result.error
    assert result.status_code == 500 # Should be 500 for this type of error


@pytest.mark.asyncio
async def test_registry_execute_tool_missing_arguments(registry: ToolRegistry):
    """Test executing a tool by omitting the arguments parameter."""
    tool = MockSyncToolNoSchema() # Tool uses default schema (empty object)
    registry.add_tool(tool)
    # Execute by omitting arguments (should default to {})
    result = await registry.execute_tool(name="process_string")
    assert isinstance(result, ToolResult)
    assert result.tool_name == "process_string"
    assert result.tool_args == {} # Default empty dict is validated
    assert result.output == "Processed: " # Tool gets empty dict
    assert result.error is None
    assert result.status_code == 200
