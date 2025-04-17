import httpx # Import httpx for async HTTP calls
from fastapi import APIRouter, HTTPException, status, Body, Path
from pydantic import HttpUrl # For endpoint validation
from agentkit.core.models import MessagePayload, ApiResponse, AgentInfo
from agentkit.registration.storage import agent_storage # To get agent details
from agentkit.tools.registry import tool_registry
from agentkit.tools.interface import ToolInterface
import logging # Add logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Placeholder for more sophisticated dispatch logic later
# from agentkit.messaging.dispatcher import dispatch_message

router = APIRouter()

# Define a timeout for external calls
EXTERNAL_CALL_TIMEOUT = 15.0 # seconds

@router.post(
    "/agents/{agent_id}/run",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message or command to an agent",
    description="Sends a structured message payload to the specified agent for processing. Handles internal tool invocations and dispatches other messages to the agent's contact endpoint.",
    tags=["Messaging"]
)
async def run_agent(
    agent_id: str = Path(..., description="The unique ID of the target agent"),
    payload: MessagePayload = Body(...)
) -> ApiResponse:
    """
    Handles incoming messages/commands for a specific agent.

    1. Checks if the target agent is registered.
    2. If messageType is 'tool_invocation':
        - Attempts to execute the tool (external HTTP or local class).
    3. If messageType is anything else:
        - Retrieves the target agent's contact_endpoint.
        - Forwards the message payload to that endpoint via HTTP POST.
    """
    logger.info(f"Received message for agent {agent_id}. Type: {payload.messageType}, Sender: {payload.senderId}")

    # 1. Check if the target agent exists and get details
    target_agent: AgentInfo | None = agent_storage.get_agent(agent_id)
    if not target_agent:
        logger.warning(f"Agent with ID '{agent_id}' not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found."
        )

    # 2. Handle tool invocation
    if payload.messageType == "tool_invocation":
        tool_name = payload.payload.get("tool_name")
        arguments = payload.payload.get("arguments", {})

        if not tool_name:
            logger.error("Tool invocation request missing 'tool_name'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'tool_name' in payload for tool_invocation message type."
            )

        # Check if it's an external tool first
        external_endpoint = tool_registry.get_tool_endpoint(tool_name)
        if external_endpoint:
            logger.info(f"Attempting to invoke external tool '{tool_name}' at {external_endpoint}")
            async with httpx.AsyncClient(timeout=EXTERNAL_CALL_TIMEOUT) as client:
                try:
                    response = await client.post(external_endpoint, json={"arguments": arguments})
                    response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses
                    tool_result = response.json()

                    # Format external tool response
                    if isinstance(tool_result, dict) and tool_result.get("status") == "error":
                         logger.error(f"External tool '{tool_name}' reported execution error: {tool_result.get('error_message')}")
                         return ApiResponse(
                             status="error",
                             message=f"External tool '{tool_name}' execution failed: {tool_result.get('error_message', 'Unknown tool error')}",
                             data=tool_result,
                             error_code="EXTERNAL_TOOL_EXECUTION_FAILED"
                         )
                    else:
                         logger.info(f"External tool '{tool_name}' executed successfully.")
                         return ApiResponse(
                             status="success",
                             message=f"External tool '{tool_name}' executed successfully.",
                             data=tool_result
                         )

                except httpx.TimeoutException:
                     logger.error(f"Request to external tool '{tool_name}' timed out.")
                     raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=f"Request to external tool '{tool_name}' timed out.")
                except httpx.ConnectError:
                     logger.error(f"Could not connect to external tool '{tool_name}' at {external_endpoint}.")
                     raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to external tool '{tool_name}' at {external_endpoint}.")
                except httpx.HTTPStatusError as e:
                     error_detail = f"External tool '{tool_name}' returned error: Status {e.response.status_code}"
                     try:
                         error_data = e.response.json()
                         error_detail += f" - Response: {error_data}"
                     except Exception: # Use broad exception for JSON decode issues
                         error_detail += f" - Response: {e.response.text}"
                     logger.error(error_detail)
                     raise HTTPException(status_code=e.response.status_code, detail=error_detail)
                except Exception as e:
                     logger.exception(f"An unexpected error occurred while calling external tool '{tool_name}'.") # Log stack trace
                     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while calling external tool '{tool_name}': {str(e)}")

        else:
            # Fallback to local tool class execution
            logger.info(f"Attempting to invoke local tool class '{tool_name}'")
            tool_class = tool_registry.get_tool_class(tool_name)
            if not tool_class:
                logger.error(f"Tool '{tool_name}' not found in registry.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tool '{tool_name}' not found in registry (local or external)."
                )

            try:
                tool_instance: ToolInterface = tool_class()
                context = payload.sessionContext.model_dump(mode='json') if payload.sessionContext else None
                tool_result = await tool_instance.execute(parameters=arguments, context=context)

                if isinstance(tool_result, dict) and tool_result.get("status") == "error":
                     logger.error(f"Local tool '{tool_name}' reported execution error: {tool_result.get('error_message')}")
                     return ApiResponse(
                         status="error",
                         message=f"Local tool '{tool_name}' execution failed: {tool_result.get('error_message', 'Unknown tool error')}",
                         data=tool_result,
                         error_code="LOCAL_TOOL_EXECUTION_FAILED"
                     )
                else:
                     logger.info(f"Local tool '{tool_name}' executed successfully.")
                     return ApiResponse(
                         status="success",
                         message=f"Local tool '{tool_name}' executed successfully.",
                         data=tool_result
                     )

            except Exception as e:
                 logger.exception(f"An unexpected error occurred while executing local tool '{tool_name}'.") # Log stack trace
                 raise HTTPException(
                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                     detail=f"An unexpected error occurred while executing local tool '{tool_name}': {str(e)}"
                 )

    # 3. Handle other message types by dispatching to agent's contact_endpoint
    else:
        logger.info(f"Attempting to dispatch message type '{payload.messageType}' to agent {agent_id}")
        contact_endpoint_str = target_agent.contactEndpoint

        if not contact_endpoint_str:
            logger.error(f"Agent {agent_id} has no registered contactEndpoint. Cannot dispatch message.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent '{agent_id}' has no registered contact endpoint. Cannot dispatch message type '{payload.messageType}'."
            )

        # Validate the endpoint URL
        try:
            # Pydantic's HttpUrl can validate - we just need the string form after validation
            HttpUrl(contact_endpoint_str) # This raises ValueError if invalid
            logger.info(f"Validated contact endpoint for agent {agent_id}: {contact_endpoint_str}")
        except ValueError as e: # Catches Pydantic's validation error
            logger.error(f"Agent {agent_id} has an invalid contactEndpoint URL: {contact_endpoint_str}. Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Internal config error
                detail=f"Agent '{agent_id}' has an invalid registered contact endpoint URL."
            )

        # Prepare payload to send (using the original MessagePayload model)
        dispatch_payload = payload.model_dump(mode='json')

        async with httpx.AsyncClient(timeout=EXTERNAL_CALL_TIMEOUT) as client:
            try:
                # Convert HttpUrl to string for httpx and logging
                contact_url_str = str(contact_endpoint_str)
                logger.info(f"Dispatching message to {contact_url_str} for agent {agent_id}")
                response = await client.post(contact_url_str, json=dispatch_payload)
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses

                # Assume target agent responds with JSON containing its result/status
                try:
                    agent_response_data = response.json()
                    logger.info(f"Successfully dispatched message to agent {agent_id}. Received response: {agent_response_data}")
                    # Return success, including the data received from the target agent
                    return ApiResponse(
                        status="success",
                        message=f"Message successfully dispatched to agent {agent_id}.",
                        data=agent_response_data # Include response from target agent
                    )
                except Exception: # Broad exception for JSON decode issues
                    logger.warning(f"Successfully dispatched message to agent {agent_id}, but response was not valid JSON: {response.text}")
                    return ApiResponse(
                        status="success",
                        message=f"Message successfully dispatched to agent {agent_id}, but response from agent was not valid JSON.",
                        data={"raw_response": response.text}
                    )

            except (httpx.TimeoutException, httpx.RemoteProtocolError) as timeout_err:
                 # Catch both explicit timeouts and cases where the server disconnects unexpectedly
                 error_message = f"Dispatch request to agent '{agent_id}' at {contact_url_str} timed out or connection failed unexpectedly: {timeout_err}"
                 logger.error(error_message)
                 raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=f"Dispatch request to agent '{agent_id}' timed out or failed.")
            except httpx.ConnectError:
                 logger.error(f"Could not connect to agent '{agent_id}' at {contact_endpoint_str}.")
                 raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to agent '{agent_id}' contact endpoint.")
            except httpx.HTTPStatusError as e:
                 error_detail = f"Agent '{agent_id}' endpoint returned error: Status {e.response.status_code}"
                 try:
                     error_data = e.response.json()
                     error_detail += f" - Response: {error_data}"
                 except Exception: # Broad exception for JSON decode issues
                     error_detail += f" - Response: {e.response.text}"
                 logger.error(error_detail)
                 # Forward the status code from the target agent if possible
                 raise HTTPException(status_code=e.response.status_code, detail=error_detail)
            except Exception as e:
                 logger.exception(f"An unexpected error occurred while dispatching message to agent '{agent_id}'.") # Log stack trace
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while dispatching message to agent '{agent_id}': {str(e)}")

# Add other messaging-related endpoints if needed