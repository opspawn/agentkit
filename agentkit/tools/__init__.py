"""
Agentkit Tools Package.

Provides components for defining, registering, and executing tools.
"""

# Import from schemas first
from .schemas import ToolSpec, ToolResult, DEFAULT_SCHEMA, Tool, ToolError
# Import from registry
from .registry import ToolRegistry, ToolExecutionError, ToolNotFoundError
# Import from execution (optional, maybe not needed for direct export)
# from .execution import execute_tool_safely
# Import the spec from the new module
from .mcp_proxy import mcp_proxy_tool_spec

__all__ = [
    "ToolSpec",
    "ToolResult",
    "mcp_proxy_tool_spec", # Add the spec here
    "ToolInputSchema",
    "ToolOutputSchema",
    "DEFAULT_SCHEMA",
    "Tool",
    "ToolRegistry",
    "ToolExecutionError",
    "ToolNotFoundError",
]
