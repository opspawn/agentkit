"""
Specification for the MCP Proxy Tool.

This tool is not implemented within agentkit itself but is injected by ops-core.
This spec defines the interface that agentkit agents use to interact with it.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field

from agentkit.tools.schemas import ToolSpec


class MCPProxyToolInput(BaseModel):
    """Input schema for the MCP Proxy Tool."""
    server_name: str = Field(..., description="The name/identifier of the target MCP server.")
    tool_name: str = Field(..., description="The name of the tool to execute on the target MCP server.")
    arguments: Dict[str, Any] = Field(..., description="The arguments to pass to the external MCP tool.")


# ToolSpec instance defining the proxy tool's interface for agentkit agents
mcp_proxy_tool_spec = ToolSpec(
    name="mcp_proxy_tool",
    description=(
        "Proxies calls to external MCP tools managed by ops-core. "
        "Use this to interact with external services or data sources via the Model Context Protocol."
    ),
    input_schema=MCPProxyToolInput.model_json_schema(), # Pass the JSON schema dict
)
