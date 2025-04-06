import multiprocessing
import time
import traceback
from typing import Any, Dict, Optional

from .schemas import Tool, ToolResult # Import Tool from schemas now

DEFAULT_TOOL_TIMEOUT = 60.0  # seconds

# Import Connection type correctly
from multiprocessing.connection import Connection

def _tool_execution_wrapper(
    tool: Tool, args: Dict[str, Any], connection: Connection
):
    """
    Internal wrapper function to execute the tool in a separate process.
    Handles both sync and async tool execute methods.
    Sends the result or exception back through the connection.
    """
    import asyncio
    import inspect # Needed for iscoroutinefunction

    try:
        execute_method = tool.execute
        if inspect.iscoroutinefunction(execute_method):
            # Run async function in a new event loop within the process
            result = asyncio.run(execute_method(args))
        else:
            # Execute sync function directly
            result = execute_method(args)

        connection.send(result)
    except Exception as e:
        # Capture the full traceback string
        tb_str = traceback.format_exc()
        # Send back a tuple indicating an exception occurred
        connection.send((e, tb_str))
    finally:
        connection.close()


async def execute_tool_safely(
    tool: Tool,
    args: Dict[str, Any],
    timeout: Optional[float] = DEFAULT_TOOL_TIMEOUT,
) -> ToolResult:
    """
    Executes a tool's `execute` method in a separate process with a timeout.

    Args:
        tool: The Tool instance to execute.
        args: The arguments dictionary to pass to the tool's execute method.
        timeout: Maximum time in seconds to allow the tool to run.
                 Defaults to DEFAULT_TOOL_TIMEOUT.

    Returns:
        A ToolResult containing the output or error information.
    """
    parent_conn, child_conn = multiprocessing.Pipe()
    process = multiprocessing.Process(
        target=_tool_execution_wrapper, args=(tool, args, child_conn)
    )

    start_time = time.monotonic()
    process.start()

    # Wait for the process to finish or timeout
    if timeout is not None:
        process.join(timeout=timeout)
    else:
        process.join() # Wait indefinitely if no timeout

    elapsed_time = time.monotonic() - start_time

    if process.is_alive():
        # Process timed out
        process.terminate()  # Try to terminate gracefully
        time.sleep(0.1) # Give it a moment
        if process.is_alive():
            process.kill() # Force kill if terminate didn't work
        process.join() # Ensure process is cleaned up
        return ToolResult(
            tool_name=tool.spec.name,
            tool_args=args,
            output=None,
            error=f"Tool execution timed out after {timeout:.2f} seconds.",
            status_code=504, # Gateway Timeout
        )

    if process.exitcode != 0:
        # Process exited with an error code (e.g., killed)
        # Check if an exception was sent back before the non-zero exit
        if parent_conn.poll():
            received = parent_conn.recv()
            parent_conn.close()
            if isinstance(received, tuple) and len(received) == 2 and isinstance(received[0], Exception):
                exception, tb_str = received
                return ToolResult(
                    tool_name=tool.spec.name,
                    tool_args=args,
                    output=None,
                    error=f"Tool execution failed with exception: {type(exception).__name__}: {exception}\nTraceback:\n{tb_str}",
                    status_code=500, # Internal Server Error
                )
        # If no specific exception was sent, report the exit code
        return ToolResult(
            tool_name=tool.spec.name,
            tool_args=args,
            output=None,
            error=f"Tool process exited unexpectedly with code {process.exitcode}.",
            status_code=500, # Internal Server Error
        )

    # Process finished normally, check the pipe for results
    if parent_conn.poll():
        received = parent_conn.recv()
        parent_conn.close()

        if isinstance(received, ToolResult):
            # Tool returned a ToolResult directly
            return received
        elif isinstance(received, tuple) and len(received) == 2 and isinstance(received[0], Exception):
                # Tool raised an exception
                exception, tb_str = received
                # Ensure tool_args is a dict, even if original args were None
                error_tool_args = args if args is not None else {}
                return ToolResult(
                    tool_name=tool.spec.name,
                    tool_args=error_tool_args,
                    output=None,
                    error=f"Tool execution failed with exception: {type(exception).__name__}: {exception}\nTraceback:\n{tb_str}",
                status_code=500, # Internal Server Error
            )
        else:
            # Tool returned some other value, wrap it in a ToolResult
            return ToolResult(
                tool_name=tool.spec.name,
                tool_args=args,
                output=received,
                error=None,
                status_code=200, # OK
            )
    else:
        # Should not happen if process exited cleanly, but handle defensively
        parent_conn.close()
        return ToolResult(
            tool_name=tool.spec.name,
            tool_args=args,
            output=None,
            error="Tool process finished but did not return a result.",
            status_code=500, # Internal Server Error
        )
