from fastapi import APIRouter, HTTPException, status, Body, Path
from agentkit.core.models import MessagePayload, ApiResponse
from agentkit.registration.storage import agent_storage # To check if agent exists
from agentkit.tools.registry import tool_registry # Import tool registry
from agentkit.tools.interface import ToolInterface # Import base interface

# Placeholder for more sophisticated dispatch logic later
# from agentkit.messaging.dispatcher import dispatch_message

router = APIRouter()

@router.post(
    "/agents/{agent_id}/run",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message or command to an agent",
    description="Sends a structured message payload to the specified agent for processing.",
    tags=["Messaging"]
)
async def run_agent(
    agent_id: str = Path(..., description="The unique ID of the target agent"),
    payload: MessagePayload = Body(...)
) -> ApiResponse:
    """
    Handles incoming messages/commands for a specific agent.

    1. Checks if the target agent is registered.
    2. Checks message type. If 'tool_invocation', attempts to execute the tool.
    3. Otherwise, acknowledges receipt (placeholder for other message types).
    """
    # 1. Check if the target agent exists
    target_agent = agent_storage.get_agent(agent_id)
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found."
        )

    # 2. Check message type and handle tool invocation
    if payload.messageType == "tool_invocation":
        tool_name = payload.payload.get("tool_name")
        parameters = payload.payload.get("parameters", {})

        if not tool_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'tool_name' in payload for tool_invocation message type."
            )

        tool_class = tool_registry.get_tool_class(tool_name)
        if not tool_class:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found in registry."
            )

        try:
            # Instantiate the tool - assumes constructor doesn't need args for now
            tool_instance: ToolInterface = tool_class()
            # Pass session context if available
            context = payload.sessionContext.model_dump(mode='json') if payload.sessionContext else None
            # Execute the tool
            tool_result = await tool_instance.execute(parameters=parameters, context=context)

            # Return the tool's result wrapped in ApiResponse
            # We assume the tool returns a dict with at least a 'status' key
            if tool_result.get("status") == "error":
                 # If tool execution resulted in a handled error
                 return ApiResponse(
                     status="error",
                     message=f"Tool '{tool_name}' execution failed: {tool_result.get('error_message', 'Unknown tool error')}",
                     data=tool_result,
                     error_code="TOOL_EXECUTION_FAILED"
                 )
            else:
                 # Assume success if status is not 'error'
                 return ApiResponse(
                     status="success",
                     message=f"Tool '{tool_name}' executed successfully.",
                     data=tool_result # Include the full tool result
                 )

        except Exception as e:
            # Catch unexpected errors during tool instantiation or execution
            # Log the error: logger.error(f"Tool execution error for {tool_name}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred while executing tool '{tool_name}': {e}"
            )

    else:
        # 3. Handle other message types (Placeholder)
        print(f"Received message type '{payload.messageType}' for agent {agent_id} from {payload.senderId}. Processing TBD.") # Basic logging
        return ApiResponse(
            status="success",
            message=f"Message type '{payload.messageType}' received for agent {agent_id}. Processing TBD.",
            data={"received_payload": payload.model_dump(mode='json')} # Echo payload for confirmation
        )

# Add other messaging-related endpoints if needed