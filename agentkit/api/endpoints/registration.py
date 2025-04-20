import os
import time
import json
import hmac
import hashlib
import logging
import httpx
from fastapi import APIRouter, HTTPException, status, Body, BackgroundTasks
from agentkit.core.models import AgentRegistrationPayload, AgentInfo, ApiResponse
from agentkit.registration.storage import agent_storage

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

# --- Webhook Notification Logic ---

async def notify_opscore_webhook(agent_info: AgentInfo):
    """
    Sends a webhook notification to Ops-Core upon agent registration.
    Uses HMAC-SHA256 signature for authentication.
    """
    webhook_url = os.getenv("OPSCORE_WEBHOOK_URL")
    webhook_secret = os.getenv("OPSCORE_WEBHOOK_SECRET")

    if not webhook_url or not webhook_secret:
        logger.info("Ops-Core webhook URL or secret not configured. Skipping notification.")
        return

    try:
        # Ensure agent_details matches the expected Ops-Core structure
        # Assuming AgentInfo fields map directly for now, adjust if needed based on Ops-Core spec
        agent_details = {
            "agentId": agent_info.agentId,
            "agentName": agent_info.agentName,
            "version": agent_info.version,
            "capabilities": agent_info.capabilities,
            "contactEndpoint": str(agent_info.contactEndpoint), # Ensure URL is string
            "metadata": agent_info.metadata or {} # Ensure metadata is at least an empty dict
        }
        payload = {
            "event_type": "REGISTER",
            "agent_details": agent_details
        }
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

        timestamp = str(int(time.time()))
        # Construct signature string consistently
        sig_string = timestamp.encode('utf-8') + b'.' + payload_bytes
        signature = hmac.new(webhook_secret.encode('utf-8'), sig_string, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-AgentKit-Timestamp": timestamp,
            "X-AgentKit-Signature": signature
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, content=payload_bytes, headers=headers, timeout=10.0) # Add timeout
            response.raise_for_status() # Raise exception for 4xx/5xx responses
            logger.info(f"Successfully sent webhook notification for agent {agent_info.agentId} to {webhook_url}. Status: {response.status_code}")

    except httpx.RequestError as exc:
        logger.error(f"Error sending Ops-Core webhook for agent {agent_info.agentId}: Request failed {exc.request.url!r} - {exc}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"Error sending Ops-Core webhook for agent {agent_info.agentId}: Status error {exc.response.status_code} while requesting {exc.request.url!r}. Response: {exc.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Ops-Core webhook notification for agent {agent_info.agentId}: {e}", exc_info=True)


# --- API Endpoint ---

@router.post(
    "/agents/register",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Registers a new agent with the system, assigning a unique ID.",
    tags=["Registration"] # Add tag for grouping in Swagger UI
)
async def register_agent(
    background_tasks: BackgroundTasks, # Non-default first
    payload: AgentRegistrationPayload = Body(...) # Default argument second
) -> ApiResponse:
    """
    Handles the registration of a new agent and triggers a background task
    to notify Ops-Core via webhook if configured.

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

        # Trigger webhook notification in the background
        background_tasks.add_task(notify_opscore_webhook, agent_info)

        # Return success response immediately
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