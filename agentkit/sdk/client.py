import httpx
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from pydantic import HttpUrl # For type hinting contactEndpoint

# Import relevant models if needed for type hinting or data construction,
# though often SDKs redefine simplified versions or just use dicts.
# from agentkit.core.models import AgentMetadata # Example

logger = logging.getLogger(__name__)

class AgentKitError(Exception):
    """Custom exception for AgentKit SDK errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class AgentKitClient:
    """
    Asynchronous client for interacting with the AgentKit API.
    Requires methods to be awaited.
    """
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initializes the AgentKit client.

        Args:
            base_url: The base URL of the running AgentKit API service.
        """
        self.base_url = base_url
        # Use httpx.AsyncClient for async requests
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Helper method to make async requests and handle common errors."""
        # urljoin is not needed if base_url is set in AsyncClient
        # url = urljoin(self.base_url, endpoint)
        try:
            response = await self._client.request(method, endpoint, **kwargs)
            response.raise_for_status() # Raise HTTPStatusError for bad responses (4xx or 5xx)
            return response.json()
        except httpx.HTTPStatusError as e: # Catch HTTPStatusError first
            # Handle HTTP errors (4xx, 5xx)
            status_code = e.response.status_code
            error_data = None # Initialize error_data
            try:
                # Try to get error details from response body
                error_data = e.response.json()
                detail = error_data.get("detail", str(e))
            except httpx.DecodingError: # Use httpx specific decoding error
                detail = str(e) # Use the base exception string if JSON fails
            raise AgentKitError(f"AgentKit API error (HTTP {status_code}): {detail}", status_code=status_code, response_data=error_data) from e
        except httpx.RequestError as e: # Catch other network errors last (ConnectError, Timeout, etc.)
            # Handle network errors, timeouts, etc.
            raise AgentKitError(f"Network error communicating with AgentKit API: {e}") from e
        except httpx.DecodingError as e: # Handle JSON decoding errors specifically if needed
             raise AgentKitError(f"Failed to decode JSON response from AgentKit API: {e}") from e

    async def close(self):
        """Closes the underlying httpx client."""
        await self._client.aclose()

    async def register_agent(
        self,
        agent_name: str,
        capabilities: List[str],
        version: str,
        contact_endpoint: HttpUrl, # Use HttpUrl for validation hint
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registers a new agent with the AgentKit service (asynchronously).

        Args:
            agent_name: Unique name for the agent.
            capabilities: List of capabilities the agent possesses.
            version: Version string for the agent.
            contact_endpoint: URL endpoint where the agent can be reached.
            metadata: Optional structured metadata (e.g., {"description": "...", "config": {...}}).

        Returns:
            The unique agent ID assigned by the service.

        Raises:
            AgentKitError: If registration fails due to API errors or network issues.
        """
        endpoint = "/v1/agents/register"
        payload = {
            "agentName": agent_name,
            "capabilities": capabilities,
            "version": version,
            "contactEndpoint": str(contact_endpoint), # Convert HttpUrl to string for JSON
            "metadata": metadata
        }
        # Filter out None metadata before sending
        if payload["metadata"] is None:
            del payload["metadata"]

        response_data = await self._make_request("POST", endpoint, json=payload)

        # Check application-level success status from ApiResponse model
        if response_data.get("status") == "success" and "data" in response_data and "agentId" in response_data["data"]:
            return response_data["data"]["agentId"]
        else:
            # If API returned 2xx but status is not success or data format is wrong
            message = response_data.get("message", "Registration failed with unexpected response format.")
            raise AgentKitError(message, response_data=response_data)

    async def send_message(
        self,
        target_agent_id: str,
        sender_id: str,
        message_type: str,
        payload: Dict[str, Any],
        session_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends a message to a specific agent via the AgentKit service (asynchronously).

        Args:
            target_agent_id: The ID of the agent to send the message to.
            sender_id: The ID of the agent sending the message.
            message_type: Type of message (e.g., 'intent_query', 'data_response', 'tool_invocation').
            payload: The actual content/data of the message. For 'tool_invocation',
                     this should include 'tool_name' and 'parameters'.
            session_context: Optional session context (e.g., {"sessionId": "..."}).

        Returns:
            The data part of the successful API response (structure depends on
            how the receiving agent/API handles the message, includes tool results).

        Raises:
            AgentKitError: If sending the message fails due to API errors or network issues.
        """
        endpoint = f"/v1/agents/{target_agent_id}/run"
        message_data = {
            "senderId": sender_id,
            "messageType": message_type,
            "payload": payload,
            "sessionContext": session_context
        }
        # Filter out None context before sending
        if message_data["sessionContext"] is None:
            del message_data["sessionContext"]

        response_data = await self._make_request("POST", endpoint, json=message_data)

        # Check application-level success status
        if response_data.get("status") == "success":
            # Return the 'data' part of the response, which might contain
            # results from tool execution or acknowledgement data.
            return response_data.get("data", {})
        else:
            # Handle application-level errors (e.g., tool execution failure reported by API)
            message = response_data.get("message", "Sending message failed with unexpected response format.")
            error_code = response_data.get("error_code")
            # Include error code in exception if available
            full_message = f"{message} (Code: {error_code})" if error_code else message
            raise AgentKitError(full_message, response_data=response_data)

    async def report_state_to_opscore(
        self,
        agent_id: str,
        state: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Reports the agent's current state to the Ops-Core service (asynchronously).

        Requires OPSCORE_API_URL and OPSCORE_API_KEY environment variables to be set.

        Args:
            agent_id: The ID of the agent reporting its state.
            state: The current state (e.g., "idle", "active", "error").
            details: Optional dictionary with additional context (e.g., error message).

        Raises:
            AgentKitError: If reporting state fails due to configuration issues,
                           API errors, or network problems.
        """
        opscore_url = os.getenv("OPSCORE_API_URL")
        opscore_api_key = os.getenv("OPSCORE_API_KEY")

        if not opscore_url:
            logger.error("OPSCORE_API_URL environment variable not set. Cannot report state.")
            raise AgentKitError("Configuration error: OPSCORE_API_URL not set.")
        if not opscore_api_key:
            # Log warning but allow attempt if URL is set, maybe auth is optional/different?
            # Or raise error immediately depending on Ops-Core requirements.
            # Let's raise for now assuming key is mandatory.
            logger.error("OPSCORE_API_KEY environment variable not set. Cannot report state.")
            raise AgentKitError("Configuration error: OPSCORE_API_KEY not set.")


        endpoint = f"/v1/opscore/agent/{agent_id}/state"
        # Construct URL relative to Ops-Core base URL
        full_url = urljoin(opscore_url, endpoint)

        payload = {
            "agentId": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": state,
            "details": details if details is not None else {} # Ensure details is always a dict
        }

        headers = {
            # Assuming Bearer token auth for Ops-Core, adjust if different
            "Authorization": f"Bearer {opscore_api_key}",
            "Content-Type": "application/json"
        }

        try:
            # Use the client directly for external URL, not _make_request which uses base_url
            response = await self._client.post(full_url, json=payload, headers=headers)
            response.raise_for_status() # Raise HTTPStatusError for bad responses (4xx or 5xx)
            logger.info(f"Successfully reported state '{state}' for agent {agent_id} to Ops-Core.")
            # Optionally return response data if Ops-Core sends anything meaningful back
            # return response.json()
            return None # Indicate success
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_data = None
            try:
                error_data = e.response.json()
                detail = error_data.get("detail", str(e))
            except httpx.DecodingError:
                detail = str(e)
            logger.error(f"Failed to report state to Ops-Core (HTTP {status_code}): {detail}", exc_info=True)
            raise AgentKitError(f"Ops-Core API error (HTTP {status_code}): {detail}", status_code=status_code, response_data=error_data) from e
        except httpx.RequestError as e:
            logger.error(f"Network error reporting state to Ops-Core: {e}", exc_info=True)
            raise AgentKitError(f"Network error communicating with Ops-Core API: {e}") from e
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error reporting state to Ops-Core: {e}", exc_info=True)
            raise AgentKitError(f"Unexpected error: {e}") from e


    # --- Other SDK methods to be added later ---
    # async def list_agents(...)
    # async def get_agent_info(...)