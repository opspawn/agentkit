import httpx # Import httpx for async HTTP calls
from fastapi import APIRouter, HTTPException, status, Body, Path, BackgroundTasks # Add BackgroundTasks
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
    response_model=ApiResponse, # Response model remains ApiResponse for structure
    status_code=status.HTTP_202_ACCEPTED, # Change status code to 202 Accepted
    summary="Accept a task for an agent",
    description="Accepts a task payload for the specified agent. If the agent has a contact endpoint, the task is dispatched asynchronously in the background. Tool invocations are handled synchronously before responding.",
    tags=["Messaging"]
)
async def run_agent(
    background_tasks: BackgroundTasks, # Dependency Injection (no default) - MUST COME FIRST
    agent_id: str = Path(..., description="The unique ID of the target agent"), # Default from Path
    payload: MessagePayload = Body(...) # Default from Body
) -> ApiResponse:
    """
    Accepts incoming tasks/messages for a specific agent.

    1. Checks if the target agent is registered.
    2. If messageType is 'tool_invocation':
        - Attempts to execute the tool synchronously (external HTTP or local class).
        - Returns the tool execution result with 200 OK (overrides 202).
    3. If messageType is anything else:
        - Retrieves the target agent's contact_endpoint.
        - If an endpoint exists, schedules asynchronous dispatch via background task.
        - Returns 202 Accepted immediately.

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
                         # Tool errors should still return 200 OK with error status in payload
                         # Overriding the default 202 for synchronous tool calls
                         return ApiResponse(
                             status="error",
                             message=f"External tool '{tool_name}' execution failed: {tool_result.get('error_message', 'Unknown tool error')}",
                             data=tool_result,
                             error_code="EXTERNAL_TOOL_EXECUTION_FAILED"
                         )
                    else:
                         logger.info(f"External tool '{tool_name}' executed successfully.")
                         # Tool success should return 200 OK
                         # Overriding the default 202 for synchronous tool calls
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
                     # Tool errors should still return 200 OK with error status in payload
                     # Overriding the default 202 for synchronous tool calls
                     return ApiResponse(
                         status="error",
                         message=f"Local tool '{tool_name}' execution failed: {tool_result.get('error_message', 'Unknown tool error')}",
                         data=tool_result,
                         error_code="LOCAL_TOOL_EXECUTION_FAILED"
                     )
                else:
                     logger.info(f"Local tool '{tool_name}' executed successfully.")
                     # Tool success should return 200 OK
                     # Overriding the default 202 for synchronous tool calls
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

        # Schedule the dispatch to the agent's endpoint as a background task
        logger.info(f"Scheduling background dispatch to agent {agent_id} at {contact_endpoint_str}")
        background_tasks.add_task(
            dispatch_to_agent_endpoint,
            agent_id=agent_id,
            contact_endpoint=contact_endpoint_str, # Pass validated string URL
            payload=payload
        )

        # Return 202 Accepted immediately
        return ApiResponse(
            status="success",
            message=f"Task accepted for agent {agent_id}. Dispatch scheduled.",
            data={"agentId": agent_id, "dispatch_status": "scheduled"}
        )


async def dispatch_to_agent_endpoint(agent_id: str, contact_endpoint: str, payload: MessagePayload):
    """
    Background task to dispatch a message payload to the agent's contact endpoint.
    Handles HTTP calls and logging.
    """
    dispatch_payload = payload.model_dump(mode='json')
    logger.info(f"[Background Task] Dispatching message type '{payload.messageType}' to {contact_endpoint} for agent {agent_id}")

    async with httpx.AsyncClient(timeout=EXTERNAL_CALL_TIMEOUT) as client:
        try:
            response = await client.post(contact_endpoint, json=dispatch_payload)
            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses

            # Log success, but don't process response body in background task
            logger.info(f"[Background Task] Successfully dispatched message to agent {agent_id} at {contact_endpoint}. Status: {response.status_code}")
            # Optionally log response snippet if needed for debugging:
            # response_text_snippet = response.text[:100] + "..." if len(response.text) > 100 else response.text
            # logger.debug(f"[Background Task] Agent {agent_id} response snippet: {response_text_snippet}")

        except (httpx.TimeoutException, httpx.RemoteProtocolError) as timeout_err:
             error_message = f"[Background Task] Dispatch request to agent '{agent_id}' at {contact_endpoint} timed out or connection failed unexpectedly: {timeout_err}"
             logger.error(error_message)
        except httpx.ConnectError:
             logger.error(f"[Background Task] Could not connect to agent '{agent_id}' at {contact_endpoint}.")
        except httpx.HTTPStatusError as e:
             error_detail = f"[Background Task] Agent '{agent_id}' endpoint ({contact_endpoint}) returned error: Status {e.response.status_code}"
             try:
                 error_data = e.response.json()
                 error_detail += f" - Response: {error_data}"
             except Exception:
                 error_detail += f" - Response: {e.response.text}"
             logger.error(error_detail)
        except Exception as e:
             logger.exception(f"[Background Task] An unexpected error occurred while dispatching message to agent '{agent_id}' at {contact_endpoint}.")

# Add other messaging-related endpoints if needed