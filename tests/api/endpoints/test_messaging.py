import pytest
from fastapi.testclient import TestClient
from main import app # Import the FastAPI app instance
from agentkit.registration.storage import agent_storage
from agentkit.core.models import AgentInfo, MessagePayload
from agentkit.tools.registry import tool_registry # Import tool registry
from agentkit.tools.interface import ToolInterface # Import base interface
from typing import Dict, Any, Optional
import httpx # Import httpx for mocking
from unittest.mock import AsyncMock, patch # Add patch
from pydantic import HttpUrl
from fastapi import HTTPException, BackgroundTasks # Import HTTPException and BackgroundTasks

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

def test_run_agent_dispatch_accepted(client: TestClient, setup_test_environment_with_tools, mocker):
    """Test successful acceptance of a non-tool message (202 Accepted)."""
    target_agent_id = setup_test_environment_with_tools
    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")

    payload = {
        "senderId": "dispatch-tester",
        "messageType": "custom_instruction",
        "payload": {"do": "something"}
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "Task accepted" in response_data["message"]
    assert response_data["data"]["dispatch_status"] == "scheduled"
    assert response_data["data"]["agentId"] == target_agent_id

    # Verify background task was scheduled
    mock_add_task.assert_called_once()
    assert mock_add_task.call_args[0][0].__name__ == "dispatch_to_agent_endpoint"
    # Check args passed to background task
    call_kwargs = mock_add_task.call_args[1] # Keyword args passed to add_task
    assert call_kwargs["agent_id"] == target_agent_id
    # Compare string representation of HttpUrl, expecting trailing slash
    assert str(call_kwargs["contact_endpoint"]) == "http://test-receiver.local/" # From fixture
    assert call_kwargs["payload"].senderId == payload["senderId"]
    assert call_kwargs["payload"].messageType == payload["messageType"]
    assert call_kwargs["payload"].payload == payload["payload"]


def test_run_agent_dispatch_with_opscore_fields(client: TestClient, setup_test_environment_with_tools, mocker):
    """Test dispatch acceptance with Ops-Core fields in the payload."""
    target_agent_id = setup_test_environment_with_tools
    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")

    payload = {
        "senderId": "opscore-sim",
        "messageType": "opscore_task",
        "payload": {"some_param": "value"},
        "task_name": "opscore_defined_task",
        "opscore_session_id": "sess_123",
        "opscore_task_id": "task_456"
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["status"] == "success"

    # Verify background task was scheduled with correct payload including opscore fields
    mock_add_task.assert_called_once()
    call_kwargs = mock_add_task.call_args[1]
    assert call_kwargs["payload"].senderId == payload["senderId"]
    assert call_kwargs["payload"].messageType == payload["messageType"]
    assert call_kwargs["payload"].payload == payload["payload"]
    assert call_kwargs["payload"].task_name == payload["task_name"]
    assert call_kwargs["payload"].opscore_session_id == payload["opscore_session_id"]
    assert call_kwargs["payload"].opscore_task_id == payload["opscore_task_id"]


def test_run_agent_dispatch_agent_no_endpoint(client: TestClient, setup_test_environment_with_tools, mocker):
    """Test dispatch attempt when the target agent has no contact endpoint."""
    target_agent_id = setup_test_environment_with_tools
    # Modify the agent directly in storage to remove the endpoint
    agent = agent_storage.get_agent(target_agent_id)
    assert agent is not None # Ensure agent was found
    agent.contactEndpoint = None
    # No need to call add_agent again, modification is in-place for dict storage

    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")

    payload = {
        "senderId": "dispatch-tester",
        "messageType": "custom_instruction",
        "payload": {"do": "something"}
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    # Should fail because no endpoint exists to schedule dispatch
    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "has no registered contact endpoint" in response_data["detail"]
    mock_add_task.assert_not_called() # Background task should not be scheduled


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

    assert response.status_code == 202 # Endpoint default is 202, even for sync tool calls
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

    assert response.status_code == 202 # Endpoint default is 202, even for sync tool calls
    response_data = response.json()
    assert response_data["status"] == "error" # But the tool reported an error
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
async def test_unit_dispatch_accepted_and_schedules_task(mocker):
    """Unit test successful acceptance and background task scheduling."""
    # Mock dependencies
    mock_agent_storage = mocker.patch('agentkit.api.endpoints.messaging.agent_storage')
    mock_background_tasks = mocker.MagicMock(spec=BackgroundTasks) # Use MagicMock for BackgroundTasks

    # Setup mock return values
    target_agent_id = "unit-target-01"
    contact_url = "http://mock-agent.test/receive"
    mock_agent = AgentInfo(
        agentId=target_agent_id, agentName="UnitTarget", version="1.0",
        capabilities=["test"], contactEndpoint=HttpUrl(contact_url)
    )
    mock_agent_storage.get_agent.return_value = mock_agent

    # Prepare input payload
    message = MessagePayload(
        senderId="unit-sender-01",
        messageType="custom_instruction",
        payload={"instruction": "unit test dispatch"}
    )

    # Call the function directly, passing the mocked BackgroundTasks
    api_response = await run_agent(
        agent_id=target_agent_id,
        payload=message,
        background_tasks=mock_background_tasks # Pass mock
    )

    # Assertions
    mock_agent_storage.get_agent.assert_called_once_with(target_agent_id)
    # Verify background task was scheduled
    mock_background_tasks.add_task.assert_called_once()
    # Check function and args passed to add_task
    assert mock_background_tasks.add_task.call_args.args[0].__name__ == "dispatch_to_agent_endpoint"
    assert len(mock_background_tasks.add_task.call_args.args) == 1 # Only the function itself as positional arg
    assert mock_background_tasks.add_task.call_args.kwargs is not None # Ensure kwargs exist
    call_kwargs = mock_background_tasks.add_task.call_args.kwargs # Check keyword args
    assert call_kwargs["agent_id"] == target_agent_id
    assert str(call_kwargs["contact_endpoint"]) == contact_url # Compare string representation
    # Compare dictionary representations for robustness
    assert call_kwargs["payload"].model_dump() == message.model_dump()

    # Assert the immediate response (202 Accepted structure)
    assert api_response.status == "success"
    assert api_response.message == f"Task accepted for agent {target_agent_id}. Dispatch scheduled."
    assert api_response.data == {"agentId": target_agent_id, "dispatch_status": "scheduled"}


# --- Removed Unit Tests for Synchronous Dispatch Error Handling ---
# The following unit tests were removed because the dispatch logic is now asynchronous (background task):
# - test_unit_dispatch_httpx_timeout
# - test_unit_dispatch_httpx_connect_error
# - test_unit_dispatch_httpx_target_error
# The main run_agent function now returns 202 Accepted immediately if dispatch is possible.
# Error handling for the actual dispatch happens within the background task (`dispatch_to_agent_endpoint`),
# which should ideally be tested via integration tests or separate unit tests focusing on that specific function
# (though testing background tasks in isolation can be complex).