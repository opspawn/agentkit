import asyncio
import time
import pytest
from pydantic import Field, BaseModel
from typing import Optional, Dict # Add missing imports

# Import Tool base class from schemas
from agentkit.tools.schemas import ToolSpec, ToolResult, Tool, DEFAULT_SCHEMA
from agentkit.tools.execution import execute_tool_safely, DEFAULT_TOOL_TIMEOUT

# --- Pydantic Models for Mock Tools ---
class SuccessToolInput(BaseModel):
    value: int = 0

class SuccessToolOutput(BaseModel):
    result: int

class TimeoutToolInput(BaseModel):
    duration: Optional[float] = None # Now Optional is defined

# --- Mock Tools for Testing ---

class SuccessTool(Tool):
    spec = ToolSpec(
        name="success_tool",
        description="A tool that always succeeds.",
        input_schema=SuccessToolInput, # Use Pydantic model
        output_schema=SuccessToolOutput, # Optional output schema
    )

    def execute(self, args: Dict[str, int]) -> Dict[str, int]:
        # Args are validated ints
        return {"result": args["value"] * 2}

class SuccessToolReturnsResult(Tool):
    spec = ToolSpec(
        name="success_tool_returns_result",
        description="A tool that succeeds and returns a ToolResult.",
        input_schema=DEFAULT_SCHEMA, # No specific input needed
    )

    def execute(self, args: Dict) -> ToolResult:
        return ToolResult(tool_name=self.spec.name, tool_args=args, output="Success!", status_code=201)


class ErrorTool(Tool):
    spec = ToolSpec(
        name="error_tool",
        description="A tool that always raises an exception.",
        input_schema=DEFAULT_SCHEMA, # No specific input needed
    )

    def execute(self, args: Dict):
        raise ValueError("This tool intentionally failed.")


class TimeoutTool(Tool):
    spec = ToolSpec(
        name="timeout_tool",
        description="A tool that sleeps longer than the default timeout.",
        input_schema=TimeoutToolInput, # Use Pydantic model
    )

    def execute(self, args: Dict):
        sleep_duration = args.get("duration", DEFAULT_TOOL_TIMEOUT + 1)
        print(f"TimeoutTool sleeping for {sleep_duration}s...") # Add print for debugging in tests
        time.sleep(sleep_duration)
        print("TimeoutTool finished sleeping.")
        return "Slept successfully" # Should not be reached if timeout works

# --- Tests ---

@pytest.mark.asyncio
async def test_execute_tool_safely_success():
    """Test successful execution returning a value."""
    tool = SuccessTool()
    args = {"value": 5}
    result = await execute_tool_safely(tool, args)

    assert isinstance(result, ToolResult)
    assert result.tool_name == "success_tool"
    assert result.tool_args == args
    assert result.output == {"result": 10}
    assert result.error is None
    assert result.status_code == 200

@pytest.mark.asyncio
async def test_execute_tool_safely_success_returns_result():
    """Test successful execution where the tool returns a ToolResult."""
    tool = SuccessToolReturnsResult()
    args = {}
    result = await execute_tool_safely(tool, args)

    assert isinstance(result, ToolResult)
    assert result.tool_name == "success_tool_returns_result"
    assert result.tool_args == args
    assert result.output == "Success!"
    assert result.error is None
    assert result.status_code == 201 # Check custom status code

@pytest.mark.asyncio
async def test_execute_tool_safely_exception():
    """Test execution where the tool raises an exception."""
    tool = ErrorTool()
    args = {}
    result = await execute_tool_safely(tool, args)

    assert isinstance(result, ToolResult)
    assert result.tool_name == "error_tool"
    assert result.tool_args == args
    assert result.output is None
    assert "Tool execution failed with exception: ValueError: This tool intentionally failed." in result.error
    assert "Traceback" in result.error # Check if traceback is included
    assert result.status_code == 500

@pytest.mark.asyncio
async def test_execute_tool_safely_timeout():
    """Test execution that exceeds the timeout."""
    tool = TimeoutTool()
    args = {} # Use default sleep duration > timeout
    timeout_duration = 0.1 # Set a very short timeout for the test

    start_time = time.monotonic()
    result = await execute_tool_safely(tool, args, timeout=timeout_duration)
    end_time = time.monotonic()

    assert isinstance(result, ToolResult)
    assert result.tool_name == "timeout_tool"
    assert result.tool_args == args
    assert result.output is None
    assert f"Tool execution timed out after {timeout_duration:.2f} seconds." in result.error
    assert result.status_code == 504
    # Check that the execution actually took roughly the timeout duration, not the tool's sleep time
    assert (end_time - start_time) < (DEFAULT_TOOL_TIMEOUT / 2) # Should be much less than the tool's sleep

@pytest.mark.asyncio
async def test_execute_tool_safely_no_timeout():
    """Test execution with timeout explicitly set to None."""
    tool = SuccessTool()
    args = {"value": 3}
    # Execute with no timeout, should succeed normally
    result = await execute_tool_safely(tool, args, timeout=None)

    assert isinstance(result, ToolResult)
    assert result.tool_name == "success_tool"
    assert result.output == {"result": 6}
    assert result.error is None
    assert result.status_code == 200
