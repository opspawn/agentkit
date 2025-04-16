import requests # Import requests for HTTP calls
from fastapi import APIRouter, HTTPException, status, Body, Path
from agentkit.core.models import MessagePayload, ApiResponse
from agentkit.registration.storage import agent_storage # To check if agent exists
from agentkit.tools.registry import tool_registry # Import updated tool registry
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
        arguments = payload.payload.get("arguments", {}) # Match test payload key

        if not tool_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'tool_name' in payload for tool_invocation message type."
            )

        # Check if it's an external tool first
        external_endpoint = tool_registry.get_tool_endpoint(tool_name)
        if external_endpoint:
            print(f"Attempting to invoke external tool '{tool_name}' at {external_endpoint}")
            try:
                # Make HTTP POST request to the external tool endpoint
                # TODO: Add timeout, headers (e.g., Content-Type), error handling
                response = requests.post(external_endpoint, json={"arguments": arguments}, timeout=10) # Send arguments
                response.raise_for_status() # Raise HTTPError for bad responses
                tool_result = response.json()

                # Format external tool response into ApiResponse
                # Assuming external tool returns a similar structure as local ones
                if isinstance(tool_result, dict) and tool_result.get("status") == "error":
                     return ApiResponse(
                         status="error",
                         message=f"External tool '{tool_name}' execution failed: {tool_result.get('error_message', 'Unknown tool error')}",
                         data=tool_result,
                         error_code="EXTERNAL_TOOL_EXECUTION_FAILED"
                     )
                else:
                     return ApiResponse(
                         status="success",
                         message=f"External tool '{tool_name}' executed successfully.",
                         data=tool_result # Include the full tool result
                     )

            except requests.exceptions.Timeout:
                 raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=f"Request to external tool '{tool_name}' timed out.")
            except requests.exceptions.ConnectionError:
                 raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to external tool '{tool_name}' at {external_endpoint}.")
            except requests.exceptions.HTTPError as e:
                 # Handle 4xx/5xx errors from the external tool itself
                 error_detail = f"External tool '{tool_name}' returned error: {e}"
                 try:
                     error_data = e.response.json()
                     error_detail += f" - Response: {error_data}"
                 except requests.exceptions.JSONDecodeError:
                     error_detail += f" - Response: {e.response.text}"
                 raise HTTPException(status_code=e.response.status_code, detail=error_detail)
            except Exception as e:
                 # Catch other unexpected errors during external call
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while calling external tool '{tool_name}': {e}")

        else:
            # Fallback to local tool class execution
            print(f"Attempting to invoke local tool class '{tool_name}'")
            tool_class = tool_registry.get_tool_class(tool_name)
            if not tool_class:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tool '{tool_name}' not found in registry (local or external)." # Updated error message
                )

            try:
                # Instantiate the tool
                tool_instance: ToolInterface = tool_class()
                # Pass session context if available
                context = payload.sessionContext.model_dump(mode='json') if payload.sessionContext else None
                # Execute the tool (using 'arguments' key now)
                tool_result = await tool_instance.execute(parameters=arguments, context=context)

                # Return the tool's result wrapped in ApiResponse
                if isinstance(tool_result, dict) and tool_result.get("status") == "error":
                     return ApiResponse(
                         status="error",
                         message=f"Local tool '{tool_name}' execution failed: {tool_result.get('error_message', 'Unknown tool error')}",
                         data=tool_result,
                         error_code="LOCAL_TOOL_EXECUTION_FAILED"
                     )
                else:
                     return ApiResponse(
                         status="success",
                         message=f"Local tool '{tool_name}' executed successfully.",
                         data=tool_result
                     )

            except Exception as e:
                # Catch unexpected errors during local tool instantiation or execution
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred while executing local tool '{tool_name}': {e}"
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