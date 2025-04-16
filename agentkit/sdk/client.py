import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from pydantic import HttpUrl # For type hinting contactEndpoint

# Import relevant models if needed for type hinting or data construction,
# though often SDKs redefine simplified versions or just use dicts.
# from agentkit.core.models import AgentMetadata # Example

class AgentKitError(Exception):
    """Custom exception for AgentKit SDK errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class AgentKitClient:
    """
    Client for interacting with the AgentKit API.
    """
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initializes the AgentKit client.

        Args:
            base_url: The base URL of the running AgentKit API service.
        """
        self.base_url = base_url
        self._session = requests.Session() # Use a session for potential connection pooling

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Helper method to make requests and handle common errors."""
        url = urljoin(self.base_url, endpoint)
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e: # Catch HTTPError first
            # Handle HTTP errors (4xx, 5xx)
            status_code = e.response.status_code
            error_data = None # Initialize error_data
            try:
                # Try to get error details from response body
                error_data = e.response.json()
                detail = error_data.get("detail", str(e))
            except requests.exceptions.JSONDecodeError:
                detail = str(e) # Use the base exception string if JSON fails
            raise AgentKitError(f"AgentKit API error (HTTP {status_code}): {detail}", status_code=status_code, response_data=error_data) from e
        except requests.exceptions.RequestException as e: # Catch other network errors last
            # Handle network errors, timeouts, etc.
            raise AgentKitError(f"Network error communicating with AgentKit API: {e}") from e
        except requests.exceptions.JSONDecodeError as e: # Handle JSON decoding errors specifically if needed
             raise AgentKitError(f"Failed to decode JSON response from AgentKit API: {e}") from e


    def register_agent(
        self,
        agent_name: str,
        capabilities: List[str],
        version: str,
        contact_endpoint: HttpUrl, # Use HttpUrl for validation hint
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registers a new agent with the AgentKit service.

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

        response_data = self._make_request("POST", endpoint, json=payload)

        # Check application-level success status from ApiResponse model
        if response_data.get("status") == "success" and "data" in response_data and "agentId" in response_data["data"]:
            return response_data["data"]["agentId"]
        else:
            # If API returned 2xx but status is not success or data format is wrong
            message = response_data.get("message", "Registration failed with unexpected response format.")
            raise AgentKitError(message, response_data=response_data)

    def send_message(
        self,
        target_agent_id: str,
        sender_id: str,
        message_type: str,
        payload: Dict[str, Any],
        session_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends a message to a specific agent via the AgentKit service.

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

        response_data = self._make_request("POST", endpoint, json=message_data)

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

    # --- Other SDK methods to be added later ---
    # def list_agents(...)
    # def get_agent_info(...)