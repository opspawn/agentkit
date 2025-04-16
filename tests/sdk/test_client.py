import pytest
import requests
import requests_mock
from agentkit.sdk.client import AgentKitClient, AgentKitError
from pydantic import HttpUrl

BASE_URL = "http://test-agentkit.local"
REGISTER_ENDPOINT = f"{BASE_URL}/v1/agents/register"
RUN_ENDPOINT_TPL = f"{BASE_URL}/v1/agents/{{agent_id}}/run"

@pytest.fixture
def client():
    """Provides an AgentKitClient instance for testing."""
    return AgentKitClient(base_url=BASE_URL)

# --- register_agent Tests ---

def test_register_agent_success(client: AgentKitClient, requests_mock):
    """Test successful agent registration via SDK."""
    mock_agent_id = "agent-sdk-test-123"
    mock_response = {
        "status": "success",
        "message": "Agent registered.",
        "data": {"agentId": mock_agent_id}
    }
    requests_mock.post(REGISTER_ENDPOINT, json=mock_response, status_code=201)

    agent_id = client.register_agent(
        agent_name="SDKTestAgent",
        capabilities=["sdk"],
        version="0.1",
        contact_endpoint=HttpUrl("http://sdk-agent.test/"),
        metadata={"desc": "test"}
    )

    assert agent_id == mock_agent_id
    history = requests_mock.request_history
    assert len(history) == 1
    assert history[0].method == "POST"
    assert history[0].url == REGISTER_ENDPOINT
    assert history[0].json()["agentName"] == "SDKTestAgent"
    assert history[0].json()["contactEndpoint"] == "http://sdk-agent.test/"
    assert "metadata" in history[0].json()

def test_register_agent_api_error(client: AgentKitClient, requests_mock):
    """Test handling of API error (e.g., 409 Conflict) during registration."""
    error_detail = "Agent with name 'SDKTestAgent' already registered."
    requests_mock.post(REGISTER_ENDPOINT, json={"detail": error_detail}, status_code=409)

    with pytest.raises(AgentKitError) as excinfo:
        client.register_agent(
            agent_name="SDKTestAgent",
            capabilities=["sdk"],
            version="0.1",
            contact_endpoint=HttpUrl("http://sdk-agent.test/")
        )

    assert excinfo.value.status_code == 409
    assert error_detail in str(excinfo.value)

def test_register_agent_network_error(client: AgentKitClient, requests_mock):
    """Test handling of network errors during registration."""
    requests_mock.post(REGISTER_ENDPOINT, exc=requests.exceptions.ConnectionError("Failed to connect")) # Use requests.exceptions

    with pytest.raises(AgentKitError, match="Network error"):
        client.register_agent(
            agent_name="SDKTestAgent",
            capabilities=["sdk"],
            version="0.1",
            contact_endpoint=HttpUrl("http://sdk-agent.test/")
        )

def test_register_agent_unexpected_response(client: AgentKitClient, requests_mock):
    """Test handling unexpected success response format."""
    mock_response = {"status": "success", "data": {}} # Missing agentId in data
    requests_mock.post(REGISTER_ENDPOINT, json=mock_response, status_code=201)

    with pytest.raises(AgentKitError, match="unexpected response format"):
         client.register_agent(
            agent_name="SDKTestAgent",
            capabilities=["sdk"],
            version="0.1",
            contact_endpoint=HttpUrl("http://sdk-agent.test/")
        )

# --- send_message Tests ---

def test_send_message_success(client: AgentKitClient, requests_mock):
    """Test successful message sending via SDK."""
    target_agent_id = "receiver-agent-456"
    run_endpoint = RUN_ENDPOINT_TPL.format(agent_id=target_agent_id)
    mock_response_data = {"tool_result": "calculation complete", "value": 100}
    mock_api_response = {
        "status": "success",
        "message": "Tool executed.",
        "data": mock_response_data
    }
    requests_mock.post(run_endpoint, json=mock_api_response, status_code=200)

    sender_id = "caller-789"
    message_type = "tool_invocation"
    payload = {"tool_name": "calculator", "parameters": {"op": "add", "a": 50, "b": 50}}

    response_data = client.send_message(
        target_agent_id=target_agent_id,
        sender_id=sender_id,
        message_type=message_type,
        payload=payload
    )

    assert response_data == mock_response_data # Should return the 'data' part
    history = requests_mock.request_history
    assert len(history) == 1
    assert history[0].method == "POST"
    assert history[0].url == run_endpoint
    assert history[0].json()["senderId"] == sender_id
    assert history[0].json()["messageType"] == message_type
    assert history[0].json()["payload"] == payload

def test_send_message_api_error_404(client: AgentKitClient, requests_mock):
    """Test sending message to non-existent agent (404)."""
    target_agent_id = "ghost-agent"
    run_endpoint = RUN_ENDPOINT_TPL.format(agent_id=target_agent_id)
    error_detail = f"Agent with ID '{target_agent_id}' not found."
    requests_mock.post(run_endpoint, json={"detail": error_detail}, status_code=404)

    with pytest.raises(AgentKitError) as excinfo:
        client.send_message(
            target_agent_id=target_agent_id,
            sender_id="caller-1",
            message_type="query",
            payload={"q": "hello?"}
        )

    assert excinfo.value.status_code == 404
    assert error_detail in str(excinfo.value)

def test_send_message_tool_execution_error(client: AgentKitClient, requests_mock):
    """Test handling application-level error reported by API (e.g., tool failed)."""
    target_agent_id = "receiver-agent-456"
    run_endpoint = RUN_ENDPOINT_TPL.format(agent_id=target_agent_id)
    mock_api_response = {
        "status": "error",
        "message": "Tool 'calculator' execution failed: Division by zero",
        "data": {"status": "error", "error_message": "Division by zero"},
        "error_code": "TOOL_EXECUTION_FAILED"
    }
    requests_mock.post(run_endpoint, json=mock_api_response, status_code=200) # API call is 200 OK

    with pytest.raises(AgentKitError) as excinfo:
         client.send_message(
            target_agent_id=target_agent_id,
            sender_id="caller-2",
            message_type="tool_invocation",
            payload={"tool_name": "calculator", "parameters": {"op": "div", "a": 1, "b": 0}}
        )

    assert excinfo.value.status_code is None # Application level error, not HTTP
    assert "Tool 'calculator' execution failed" in str(excinfo.value)
    assert "(Code: TOOL_EXECUTION_FAILED)" in str(excinfo.value)
    assert excinfo.value.response_data == mock_api_response

def test_send_message_network_error(client: AgentKitClient, requests_mock):
    """Test handling network error during message sending."""
    target_agent_id = "receiver-agent-456"
    run_endpoint = RUN_ENDPOINT_TPL.format(agent_id=target_agent_id)
    requests_mock.post(run_endpoint, exc=requests.exceptions.Timeout("Request timed out")) # Use requests.exceptions

    with pytest.raises(AgentKitError, match="Network error"):
        client.send_message(
            target_agent_id=target_agent_id,
            sender_id="caller-3",
            message_type="ping",
            payload={}
        )