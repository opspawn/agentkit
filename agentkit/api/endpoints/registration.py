from fastapi import APIRouter, HTTPException, status, Body
from agentkit.core.models import AgentRegistrationPayload, AgentInfo, ApiResponse
from agentkit.registration.storage import agent_storage

router = APIRouter()

@router.post(
    "/agents/register",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Registers a new agent with the system, assigning a unique ID.",
    tags=["Registration"] # Add tag for grouping in Swagger UI
)
async def register_agent(
    payload: AgentRegistrationPayload = Body(...)
) -> ApiResponse:
    """
    Handles the registration of a new agent.

    Validates the incoming payload, creates an AgentInfo record,
    stores it using the agent_storage, and returns the assigned agent ID.
    """
    try:
        # Create AgentInfo instance from payload, generating a new UUID
        agent_info = AgentInfo(
            agentName=payload.agentName,
            capabilities=payload.capabilities,
            version=payload.version,
            contactEndpoint=payload.contactEndpoint,
            metadata=payload.metadata
            # agentId and registration_time are set by default factory
        )

        # Attempt to add the agent to storage
        agent_storage.add_agent(agent_info)

        # Return success response
        return ApiResponse(
            status="success",
            message=f"Agent '{agent_info.agentName}' registered successfully.",
            data={"agentId": agent_info.agentId}
        )

    except ValueError as e:
        # Handle potential duplicate agent errors from storage
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        # Catch any other unexpected errors during registration
        # Log the error in a real application: logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during agent registration: {e}"
        )

# Add other registration-related endpoints here later if needed
# (e.g., GET /agents/{agentId}, GET /agents, DELETE /agents/{agentId})