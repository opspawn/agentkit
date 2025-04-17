import pytest
from fastapi.testclient import TestClient
from main import app # Import the FastAPI app instance
from agentkit.registration.storage import agent_storage
from agentkit.core.models import AgentInfo, MessagePayload
from agentkit.tools.registry import tool_registry # Import tool registry
from agentkit.tools.interface import ToolInterface # Import base interface
from typing import Dict, Any, Optional
import httpx # Import httpx for mocking
from unittest.mock import AsyncMock # For mocking async functions/methods
from pydantic import HttpUrl
from fastapi import HTTPException # Import HTTPException

# Fixture to provide a TestClient instance
@pytest.fixture(scope="module")
def client():
    # Manually include routers for testing if not already included in main app setup
    from agentkit.api.endpoints import registration, messaging
    if registration.router not in app.routes:
         app.include_router(registration.router, prefix="/v1")
    if messaging.router not in app.routes:
         app.include_router(messaging.router, prefix="/v1")

    with TestClient(app) as c:
        yield c

# Fixture to ensure clean storage and register a sample agent for tests
# --- Dummy Tool for Testing Tool Invocation ---
class MockSuccessTool(ToolInterface):
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "success", "result": f"Executed with {parameters}"}
    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        return {"name": "mock_success", "description": "Always succeeds", "parameters": {}}

class MockHandledErrorTool(ToolInterface):
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "error", "error_message": "Tool failed as expected"}
    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        return {"name": "mock_handled_error", "description": "Always returns error status", "parameters": {}}

class MockUnexpectedErrorTool(ToolInterface):
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise ValueError("Something broke unexpectedly inside the tool!")
    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        return {"name": "mock_unexpected_error", "description": "Always raises ValueError", "parameters": {}}


# Fixture to setup agent and register tools
@pytest.fixture(autouse=True)
def setup_test_environment_with_tools():
    agent_storage.clear_all()
    tool_registry.clear_all() # Clear tool registry too

    # Register a sample agent
    test_agent = AgentInfo(
        agentName="MessagingTestAgent",
        capabilities=["receive"],
        version="1.0",
        contactEndpoint="http://test-receiver.local"
    )
    agent_storage.add_agent(test_agent)
    # Removed duplicate add_agent call here

    # Register mock tools
    tool_registry.register_tool(MockSuccessTool)
    tool_registry.register_tool(MockHandledErrorTool)
    tool_registry.register_tool(MockUnexpectedErrorTool)

    yield test_agent.agentId # Provide agentId to tests

    agent_storage.clear_all()
    tool_registry.clear_all() # Clean up tools

# --- Test Cases ---

# Removed test_run_agent_non_tool_message_success as non-tool messages are now dispatched
# and success is tested via unit/integration tests for dispatch logic.

def test_run_agent_not_found(client: TestClient):
    """Test sending a message to a non-existent agent ID."""
    non_existent_agent_id = "agent-does-not-exist"
    payload = {
        "senderId": "sender-agent-123",
        "messageType": "data_response",
        "payload": {"result": 42}
    }
    response = client.post(f"/v1/agents/{non_existent_agent_id}/run", json=payload)

    assert response.status_code == 404
    response_data = response.json()
    assert "detail" in response_data
    assert f"Agent with ID '{non_existent_agent_id}' not found" in response_data["detail"]

def test_run_agent_invalid_payload(client: TestClient, setup_test_environment_with_tools):
    """Test sending a message with missing required fields in the payload."""
    target_agent_id = setup_test_environment_with_tools
    invalid_payload = {
        # Missing senderId
        "messageType": "error_notification",
        "payload": {"error": "Something went wrong"}
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=invalid_payload)

    # FastAPI/Pydantic validation error
    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    assert any("senderId" in error["loc"] for error in response_data["detail"])
    assert any("Field required" in error["msg"] for error in response_data["detail"])

def test_run_agent_missing_payload_field(client: TestClient, setup_test_environment_with_tools):
    """Test sending a message with the 'payload' field itself missing."""
    target_agent_id = setup_test_environment_with_tools
    invalid_payload = {
        "senderId": "sender-agent-123",
        "messageType": "intent_query",
        # Missing payload field
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=invalid_payload)

    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    assert any("payload" in error["loc"] for error in response_data["detail"])
    assert any("Field required" in error["msg"] for error in response_data["detail"])


# --- Tool Invocation Tests ---

def test_run_agent_tool_invocation_success(client: TestClient, setup_test_environment_with_tools):
    """Test successfully invoking a registered tool."""
    target_agent_id = setup_test_environment_with_tools
    tool_params = {"input": "data"}
    payload = {
        "senderId": "tool-caller-agent",
        "messageType": "tool_invocation",
        "payload": {
            "tool_name": "mock_success",
            "arguments": tool_params # Use 'arguments' key to match API endpoint logic
        }
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "Local tool 'mock_success' executed successfully" in response_data["message"] # Updated message
    assert response_data["data"]["status"] == "success"
    # Correct assertion to match the tool's actual output format
    # Correct assertion: Compare against the expected string output of the mock tool
    expected_result_string = f"Executed with {tool_params}"
    assert response_data["data"]["result"] == expected_result_string

def test_run_agent_tool_invocation_tool_not_found(client: TestClient, setup_test_environment_with_tools):
    """Test invoking a tool that is not registered."""
    target_agent_id = setup_test_environment_with_tools
    payload = {
        "senderId": "tool-caller-agent",
        "messageType": "tool_invocation",
        "payload": {
            "tool_name": "non_existent_tool",
            "parameters": {}
        }
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 404
    response_data = response.json()
    assert "detail" in response_data
    assert "Tool 'non_existent_tool' not found" in response_data["detail"]

def test_run_agent_tool_invocation_missing_tool_name(client: TestClient, setup_test_environment_with_tools):
    """Test invoking a tool without specifying 'tool_name' in the payload."""
    target_agent_id = setup_test_environment_with_tools
    payload = {
        "senderId": "tool-caller-agent",
        "messageType": "tool_invocation",
        "payload": {
            # Missing tool_name
            "parameters": {}
        }
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "Missing 'tool_name' in payload" in response_data["detail"]

def test_run_agent_tool_invocation_handled_error(client: TestClient, setup_test_environment_with_tools):
    """Test invoking a tool that returns a handled error status."""
    target_agent_id = setup_test_environment_with_tools
    payload = {
        "senderId": "tool-caller-agent",
        "messageType": "tool_invocation",
        "payload": {
            "tool_name": "mock_handled_error",
            "parameters": {}
        }
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 200 # API call itself is successful
    response_data = response.json()
    assert response_data["status"] == "error"
    assert response_data["error_code"] == "LOCAL_TOOL_EXECUTION_FAILED" # Updated error code
    assert "Local tool 'mock_handled_error' execution failed" in response_data["message"] # Updated message
    assert response_data["data"]["status"] == "error"
    assert response_data["data"]["error_message"] == "Tool failed as expected"

def test_run_agent_tool_invocation_unexpected_error(client: TestClient, setup_test_environment_with_tools):
    """Test invoking a tool that raises an unexpected exception during execution."""
    target_agent_id = setup_test_environment_with_tools
    payload = {
        "senderId": "tool-caller-agent",
        "messageType": "tool_invocation",
        "payload": {
            "tool_name": "mock_unexpected_error",
            "parameters": {}
        }
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 500 # Internal Server Error
    response_data = response.json()
    assert "detail" in response_data
    assert "An unexpected error occurred while executing local tool 'mock_unexpected_error'" in response_data["detail"] # Updated message
    assert "Something broke unexpectedly inside the tool!" in response_data["detail"] # Include exception message


# --- Unit Tests for Dispatch Logic (using mocker) ---

# We need to test the run_agent function directly, mocking its dependencies
from agentkit.api.endpoints.messaging import run_agent

@pytest.mark.asyncio
async def test_unit_dispatch_success(mocker):
    """Unit test successful dispatch logic, mocking dependencies."""
    # Mock dependencies
    mock_agent_storage = mocker.patch('agentkit.api.endpoints.messaging.agent_storage')
    mock_httpx_client = mocker.patch('httpx.AsyncClient')

    # Setup mock return values
    target_agent_id = "unit-target-01"
    contact_url = "http://mock-agent.test/receive"
    mock_agent = AgentInfo(
        agentId=target_agent_id, agentName="UnitTarget", version="1.0",
        capabilities=["test"], contactEndpoint=HttpUrl(contact_url)
    )
    mock_agent_storage.get_agent.return_value = mock_agent

    # Mock httpx response
    mock_response = httpx.Response(
        200,
        json={"status": "received", "result": "mock agent processed"},
        request=httpx.Request("POST", contact_url) # Need a request object for the response
    )
    # Configure the AsyncClient context manager and the post method
    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.post = AsyncMock(return_value=mock_response)
    # Make the AsyncClient context manager return our mock instance
    mock_httpx_client.return_value.__aenter__.return_value = mock_async_client_instance


    # Prepare input payload
    message = MessagePayload(
        senderId="unit-sender-01",
        messageType="custom_instruction",
        payload={"instruction": "unit test dispatch"}
    )

    # Call the function directly
    api_response = await run_agent(agent_id=target_agent_id, payload=message)

    # Assertions
    mock_agent_storage.get_agent.assert_called_once_with(target_agent_id)
    mock_httpx_client.assert_called_once() # Check AsyncClient was instantiated
    mock_async_client_instance.post.assert_awaited_once_with(
        contact_url, json=message.model_dump(mode='json')
    )
    assert api_response.status == "success"
    assert api_response.message == f"Message successfully dispatched to agent {target_agent_id}."
    assert api_response.data == {"status": "received", "result": "mock agent processed"}

# Removed test_unit_dispatch_no_endpoint and test_unit_dispatch_invalid_endpoint
# as AgentInfo model requires a valid HttpUrl for contactEndpoint, making these states unreachable
# if registration validation is working correctly.

@pytest.mark.asyncio
async def test_unit_dispatch_httpx_timeout(mocker):
    """Unit test dispatch logic when httpx call times out."""
    mock_agent_storage = mocker.patch('agentkit.api.endpoints.messaging.agent_storage')
    mock_httpx_client = mocker.patch('httpx.AsyncClient')

    target_agent_id = "unit-timeout-01"
    contact_url = "http://mock-timeout.test/receive"
    mock_agent = AgentInfo(
        agentId=target_agent_id, agentName="UnitTimeout", version="1.0",
        capabilities=["test"], contactEndpoint=HttpUrl(contact_url)
    )
    mock_agent_storage.get_agent.return_value = mock_agent

    # Mock httpx to raise TimeoutException
    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
    mock_httpx_client.return_value.__aenter__.return_value = mock_async_client_instance

    message = MessagePayload(senderId="unit-sender-04", messageType="process", payload={})

    with pytest.raises(HTTPException) as exc_info:
        await run_agent(agent_id=target_agent_id, payload=message)

    assert exc_info.value.status_code == 504 # Gateway Timeout
    assert "timed out" in exc_info.value.detail
    mock_agent_storage.get_agent.assert_called_once_with(target_agent_id)
    mock_async_client_instance.post.assert_awaited_once()

@pytest.mark.asyncio
async def test_unit_dispatch_httpx_connect_error(mocker):
    """Unit test dispatch logic when httpx call has connection error."""
    mock_agent_storage = mocker.patch('agentkit.api.endpoints.messaging.agent_storage')
    mock_httpx_client = mocker.patch('httpx.AsyncClient')

    target_agent_id = "unit-connect-error-01"
    contact_url = "http://mock-unreachable.test/receive"
    mock_agent = AgentInfo(
        agentId=target_agent_id, agentName="UnitConnectError", version="1.0",
        capabilities=["test"], contactEndpoint=HttpUrl(contact_url)
    )
    mock_agent_storage.get_agent.return_value = mock_agent

    # Mock httpx to raise ConnectError
    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
    mock_httpx_client.return_value.__aenter__.return_value = mock_async_client_instance

    message = MessagePayload(senderId="unit-sender-05", messageType="ping", payload={})

    with pytest.raises(HTTPException) as exc_info:
        await run_agent(agent_id=target_agent_id, payload=message)

    assert exc_info.value.status_code == 503 # Service Unavailable
    assert "Could not connect" in exc_info.value.detail
    mock_agent_storage.get_agent.assert_called_once_with(target_agent_id)
    mock_async_client_instance.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_dispatch_httpx_target_error(mocker):
    """Unit test dispatch logic when target agent returns an HTTP error."""
    mock_agent_storage = mocker.patch('agentkit.api.endpoints.messaging.agent_storage')
    mock_httpx_client = mocker.patch('httpx.AsyncClient')

    target_agent_id = "unit-target-error-01"
    contact_url = "http://mock-error-agent.test/receive"
    mock_agent = AgentInfo(
        agentId=target_agent_id, agentName="UnitTargetError", version="1.0",
        capabilities=["test"], contactEndpoint=HttpUrl(contact_url)
    )
    mock_agent_storage.get_agent.return_value = mock_agent

    # Mock httpx response with an error status code
    mock_request = httpx.Request("POST", contact_url)
    mock_error_response = httpx.Response(
        400,
        json={"error": "Target agent rejected request"},
        request=mock_request
    )
    # Raise HTTPStatusError when raise_for_status is called
    mock_async_client_instance = AsyncMock()
    mock_async_client_instance.post = AsyncMock(return_value=mock_error_response)
    # Make raise_for_status raise the appropriate error
    mock_error_response.raise_for_status = mocker.Mock(side_effect=httpx.HTTPStatusError(
        "Client Error", request=mock_request, response=mock_error_response
    ))
    mock_httpx_client.return_value.__aenter__.return_value = mock_async_client_instance


    message = MessagePayload(senderId="unit-sender-06", messageType="process", payload={"data": "bad"})

    with pytest.raises(HTTPException) as exc_info:
        await run_agent(agent_id=target_agent_id, payload=message)

    assert exc_info.value.status_code == 400 # Should forward the target's error code
    assert "endpoint returned error" in exc_info.value.detail
    assert "Status 400" in exc_info.value.detail
    assert str({"error": "Target agent rejected request"}) in exc_info.value.detail
    mock_agent_storage.get_agent.assert_called_once_with(target_agent_id)
    mock_async_client_instance.post.assert_awaited_once()