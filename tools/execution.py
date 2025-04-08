# agentkit/tools/execution.py
import asyncio
import logging
import multiprocessing
from multiprocessing.connection import Connection # Added import
import time
import traceback
from typing import Any, Dict, Optional

from agentkit.tools.schemas import Tool, ToolResult

logger = logging.getLogger(__name__)

# Define a sentinel value for timeout
TIMEOUT_SENTINEL = object()

def _execute_tool_target(
    tool: Tool, tool_input: Dict[str, Any], connection: Connection # Changed type hint
) -> None:
    """
    Target function to be run in a separate process.
    Executes the tool's method and sends the result or exception back through the pipe.
    """
    try:
        # Run the potentially blocking or async tool execution
        # Need to run async execute method in an event loop if it's async
        if asyncio.iscoroutinefunction(tool.execute):
            result = asyncio.run(tool.execute(**tool_input))
        else:
            # Assuming execute can be sync or async, handle sync case directly
            # If execute MUST be async, this branch might need adjustment or removal
            result = tool.execute(**tool_input) # type: ignore

        connection.send(result)
    except Exception as e:
        # Capture the exception and traceback, send it back
        error_info = {
            "exception_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
        }
        connection.send(error_info)
    finally:
        connection.close()


async def execute_tool_safely(
    tool: Tool, tool_input: Dict[str, Any], timeout: Optional[float] = 5.0
) -> ToolResult:
    """
    Executes a tool's `execute` method in a separate process with a timeout.

    Args:
        tool (Tool): The tool instance to execute.
        tool_input (Dict[str, Any]): The input arguments for the tool.
        timeout (Optional[float]): Maximum time in seconds to allow the tool to run.
                                   Defaults to 5.0 seconds. Set to None for no timeout.

    Returns:
        ToolResult: The result of the tool execution, including output or error details.
    """
    tool_name = tool.spec.name
    parent_conn, child_conn = multiprocessing.Pipe()

    process = multiprocessing.Process(
        target=_execute_tool_target, args=(tool, tool_input, child_conn), daemon=True
    )

    start_time = time.monotonic()
    try:
        process.start()
        logger.info(f"Started process {process.pid} for tool '{tool_name}'.")

        # Wait for the process to finish or timeout
        # We need to periodically check the pipe for results without blocking indefinitely
        result_data = TIMEOUT_SENTINEL
        while process.is_alive():
            if timeout is not None and (time.monotonic() - start_time) > timeout:
                logger.warning(f"Tool '{tool_name}' (pid: {process.pid}) timed out after {timeout} seconds.")
                process.terminate() # Try to terminate gracefully
                await asyncio.sleep(0.1) # Give it a moment
                if process.is_alive():
                    logger.warning(f"Tool '{tool_name}' (pid: {process.pid}) did not terminate, killing.")
                    process.kill() # Force kill if terminate didn't work
                process.join(0.1) # Wait briefly for cleanup
                return ToolResult(output=None, error=f"Tool execution timed out after {timeout} seconds.")

            if parent_conn.poll(0.01): # Check if data is available
                try:
                    result_data = parent_conn.recv()
                    break # Exit loop once data is received
                except (EOFError, OSError) as pipe_err:
                    logger.error(f"Pipe error receiving result from tool '{tool_name}': {pipe_err}")
                    return ToolResult(output=None, error=f"Pipe error receiving result: {pipe_err}")

            await asyncio.sleep(0.05) # Small sleep to yield control

        # If process finished but we didn't get data via poll, try one last recv
        if result_data is TIMEOUT_SENTINEL and not process.is_alive():
             if parent_conn.poll():
                 try:
                    result_data = parent_conn.recv()
                 except (EOFError, OSError) as pipe_err:
                    logger.error(f"Pipe error receiving result from tool '{tool_name}' after process exit: {pipe_err}")
                    return ToolResult(output=None, error=f"Pipe error receiving result: {pipe_err}")
             else:
                 # Process finished but sent nothing?
                 exit_code = process.exitcode
                 logger.error(f"Tool '{tool_name}' process {process.pid} finished with exit code {exit_code} but sent no result.")
                 return ToolResult(output=None, error=f"Tool process finished unexpectedly (exit code {exit_code}) without sending result.")


        # Process the received data
        if isinstance(result_data, ToolResult):
            return result_data
        elif isinstance(result_data, dict) and "exception_type" in result_data:
            # It's an error dictionary sent from the target function
            error_msg = (
                f"Tool execution failed with {result_data['exception_type']}: "
                f"{result_data['error_message']}\nTraceback:\n{result_data['traceback']}"
            )
            logger.error(f"Tool '{tool_name}' raised an exception:\n{result_data['traceback']}")
            return ToolResult(output=None, error=error_msg)
        elif result_data is TIMEOUT_SENTINEL:
             # Should have been caught by timeout logic, but as a fallback
             logger.error(f"Tool '{tool_name}' execution ended without result or timeout.")
             return ToolResult(output=None, error="Tool execution finished without providing a result or explicit error.")
        else:
            # Unexpected data type received
            logger.error(f"Received unexpected data type from tool '{tool_name}' process: {type(result_data)}")
            return ToolResult(output=None, error=f"Received unexpected data type from tool process: {type(result_data)}")

    except Exception as e:
        logger.exception(f"Error managing process for tool '{tool_name}': {e}")
        # Ensure process is cleaned up if it's still running
        if process.is_alive():
            process.terminate()
            process.join(0.5)
            if process.is_alive():
                process.kill()
                process.join(0.1)
        return ToolResult(output=None, error=f"Error managing tool process: {e}")
    finally:
        parent_conn.close()
        # Ensure process is joined if it finished normally
        if process.is_alive():
             logger.warning(f"Process {process.pid} for tool {tool_name} still alive after main logic, joining.")
             process.join(timeout) # Attempt to join with remaining timeout
        if process.is_alive():
             logger.error(f"Process {process.pid} for tool {tool_name} could not be joined, killing.")
             process.kill()
             process.join(0.1)
