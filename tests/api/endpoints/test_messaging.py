import pytest
from fastapi.testclient import TestClient
from main import app # Import the FastAPI app instance
from agentkit.registration.storage import agent_storage
from agentkit.core.models import AgentInfo, MessagePayload
from agentkit.tools.registry import tool_registry # Import tool registry
from agentkit.tools.interface import ToolInterface # Import base interface
from typing import Dict, Any, Optional

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

def test_run_agent_non_tool_message_success(client: TestClient, setup_test_environment_with_tools):
    """Test sending a valid non-tool message to an existing agent."""
    target_agent_id = setup_test_environment_with_tools
    payload = {
        "senderId": "sender-agent-123",
        "messageType": "intent_query",
        "payload": {"query": "What is the weather?"},
        "sessionContext": {"sessionId": "session-abc"}
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert f"Message type 'intent_query' received for agent {target_agent_id}" in response_data["message"]
    assert response_data["data"]["received_payload"]["senderId"] == payload["senderId"]
    assert response_data["data"]["received_payload"]["messageType"] == payload["messageType"]
    assert response_data["data"]["received_payload"]["payload"] == payload["payload"]

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
            "parameters": tool_params
        }
    }
    response = client.post(f"/v1/agents/{target_agent_id}/run", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert "Tool 'mock_success' executed successfully" in response_data["message"]
    assert response_data["data"]["status"] == "success"
    assert response_data["data"]["result"] == f"Executed with {tool_params}"

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
    assert response_data["error_code"] == "TOOL_EXECUTION_FAILED"
    assert "Tool 'mock_handled_error' execution failed" in response_data["message"]
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
    assert "An unexpected error occurred while executing tool 'mock_unexpected_error'" in response_data["detail"]
    assert "Something broke unexpectedly inside the tool!" in response_data["detail"] # Include exception message