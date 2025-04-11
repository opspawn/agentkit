# agentkit/tests/tools/test_execution.py
import asyncio
import time
import pytest
from unittest.mock import MagicMock, PropertyMock

from agentkit.tools.execution import execute_tool_safely
from agentkit.tools.schemas import Tool, ToolSpec, ToolResult


# --- Helper Mock Tools for Execution Tests ---

class SyncTool(Tool):
    """A mock tool with a synchronous execute method."""
    def __init__(self, output=None, error=None, delay=0):
        self._spec = ToolSpec(name="sync_tool", description="Sync test tool.")
        self._output = output
        self._error = error
        self._delay = delay

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, args: dict) -> ToolResult: # Changed from **kwargs to args: dict
        if self._delay > 0:
            time.sleep(self._delay)
        if self._error:
            raise self._error
        # Add required fields for ToolResult and use args
        return ToolResult(
            tool_name=self.spec.name,
            tool_args=args,
            output=self._output or {"sync_result": "ok", **args} # Use args here too
        )


class AsyncTool(Tool):
    """A mock tool with an asynchronous execute method."""
    def __init__(self, output=None, error=None, delay=0):
        self._spec = ToolSpec(name="async_tool", description="Async test tool.")
        self._output = output
        self._error = error
        self._delay = delay

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    async def execute(self, args: dict) -> ToolResult: # Changed from **kwargs to args: dict
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        # Add required fields for ToolResult and use args
        return ToolResult(
            tool_name=self.spec.name,
            tool_args=args,
            output=self._output or {"async_result": "ok", **args} # Use args here too
        )


# --- Test Cases ---

@pytest.mark.asyncio
async def test_execute_sync_tool_success():
    """Tests successful execution of a synchronous tool."""
    tool_input = {"arg": 1}
    expected_output = {"sync_result": "ok", "arg": 1}
    tool = SyncTool(output=expected_output)

    result = await execute_tool_safely(tool=tool, args=tool_input, timeout=1.0)

    assert isinstance(result, ToolResult)
    assert result.output == expected_output
    assert result.error is None


@pytest.mark.asyncio
async def test_execute_async_tool_success():
    """Tests successful execution of an asynchronous tool."""
    tool_input = {"arg": 2}
    expected_output = {"async_result": "ok", "arg": 2}
    tool = AsyncTool(output=expected_output)

    result = await execute_tool_safely(tool=tool, args=tool_input, timeout=1.0)

    assert isinstance(result, ToolResult)
    assert result.output == expected_output
    assert result.error is None


@pytest.mark.asyncio
async def test_execute_sync_tool_raises_exception():
    """Tests execution where the synchronous tool raises an exception."""
    tool_input = {}
    error_message = "Sync tool failed!"
    tool = SyncTool(error=ValueError(error_message))

    result = await execute_tool_safely(tool=tool, args=tool_input, timeout=1.0)

    assert isinstance(result, ToolResult)
    assert result.output is None
    # Check for exception type and message within the error string
    assert "ValueError" in result.error
    assert error_message in result.error
    assert "Traceback" in result.error


@pytest.mark.asyncio
async def test_execute_async_tool_raises_exception():
    """Tests execution where the asynchronous tool raises an exception."""
    tool_input = {}
    error_message = "Async tool failed!"
    tool = AsyncTool(error=RuntimeError(error_message))

    result = await execute_tool_safely(tool=tool, args=tool_input, timeout=1.0)

    assert isinstance(result, ToolResult)
    assert result.output is None
    # Check for exception type and message within the error string
    assert "RuntimeError" in result.error
    assert error_message in result.error
    assert "Traceback" in result.error


@pytest.mark.asyncio
async def test_execute_tool_timeout():
    """Tests tool execution exceeding the timeout."""
    tool_input = {}
    timeout_duration = 0.1
    tool = AsyncTool(delay=timeout_duration + 0.2) # Ensure delay exceeds timeout

    result = await execute_tool_safely(tool=tool, args=tool_input, timeout=timeout_duration)

    assert isinstance(result, ToolResult)
    assert result.output is None
    # Match the formatting used in the actual error message
    assert f"Tool execution timed out after {timeout_duration:.2f} seconds." in result.error


@pytest.mark.asyncio
async def test_execute_tool_no_timeout():
    """Tests tool execution with timeout explicitly set to None."""
    tool_input = {}
    delay_duration = 0.1 # Short delay, should complete
    tool = AsyncTool(delay=delay_duration)

    result = await execute_tool_safely(tool=tool, args=tool_input, timeout=None) # No timeout

    assert isinstance(result, ToolResult)
    assert result.output is not None
    assert result.error is None


# Note: Testing pipe errors directly is complex and platform-dependent.
# The current implementation includes basic error handling for pipe issues.
