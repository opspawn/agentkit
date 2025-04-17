import pytest
import httpx
from pytest_httpx import HTTPXMock
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from agentkit.sdk.client import AgentKitClient, AgentKitError
from pydantic import HttpUrl

# Use pytest mark for async tests
pytestmark = pytest.mark.asyncio

BASE_URL = "http://test-agentkit.local"
# Endpoints relative to base_url used by httpx.AsyncClient
REGISTER_ENDPOINT_REL = "/v1/agents/register"
RUN_ENDPOINT_TPL_REL = "/v1/agents/{agent_id}/run"

# Ops-Core related constants for testing
OPSCORE_BASE_URL = "http://test-opscore.local"
OPSCORE_STATE_ENDPOINT_TPL = f"{OPSCORE_BASE_URL}/v1/opscore/agent/{{agent_id}}/state"
OPSCORE_API_KEY = "test-opscore-key-123"

@pytest.fixture
async def client():
    """Provides an async AgentKitClient instance for testing."""
    client_instance = AgentKitClient(base_url=BASE_URL)
    yield client_instance
    # Clean up the client session after tests
    await client_instance.close()

# --- register_agent Tests (Async) ---

async def test_register_agent_success(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test successful agent registration via async SDK."""
    mock_agent_id = "agent-sdk-test-123"
    mock_response = {
        "status": "success",
        "message": "Agent registered.",
        "data": {"agentId": mock_agent_id}
    }
    httpx_mock.add_response(method="POST", url=f"{BASE_URL}{REGISTER_ENDPOINT_REL}", json=mock_response, status_code=201)

    agent_id = await client.register_agent(
        agent_name="SDKTestAgent",
        capabilities=["sdk"],
        version="0.1",
        contact_endpoint=HttpUrl("http://sdk-agent.test/"),
        metadata={"desc": "test"}
    )

    assert agent_id == mock_agent_id
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == f"{BASE_URL}{REGISTER_ENDPOINT_REL}"
    request_json = request.read().decode()
    assert '"agentName": "SDKTestAgent"' in request_json
    assert '"contactEndpoint": "http://sdk-agent.test/"' in request_json
    assert '"metadata": {' in request_json

async def test_register_agent_api_error(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test handling of API error (e.g., 409 Conflict) during async registration."""
    error_detail = "Agent with name 'SDKTestAgent' already registered."
    httpx_mock.add_response(method="POST", url=f"{BASE_URL}{REGISTER_ENDPOINT_REL}", json={"detail": error_detail}, status_code=409)

    with pytest.raises(AgentKitError) as excinfo:
        await client.register_agent(
            agent_name="SDKTestAgent",
            capabilities=["sdk"],
            version="0.1",
            contact_endpoint=HttpUrl("http://sdk-agent.test/")
        )

    assert excinfo.value.status_code == 409
    assert error_detail in str(excinfo.value)

async def test_register_agent_network_error(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test handling of network errors during async registration."""
    httpx_mock.add_exception(httpx.ConnectError("Failed to connect"))

    with pytest.raises(AgentKitError, match="Network error"):
        await client.register_agent(
            agent_name="SDKTestAgent",
            capabilities=["sdk"],
            version="0.1",
            contact_endpoint=HttpUrl("http://sdk-agent.test/")
        )

async def test_register_agent_unexpected_response(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test handling unexpected success response format during async registration."""
    mock_response = {"status": "success", "data": {}} # Missing agentId in data
    httpx_mock.add_response(method="POST", url=f"{BASE_URL}{REGISTER_ENDPOINT_REL}", json=mock_response, status_code=201)

    with pytest.raises(AgentKitError, match="unexpected response format"):
         await client.register_agent(
            agent_name="SDKTestAgent",
            capabilities=["sdk"],
            version="0.1",
            contact_endpoint=HttpUrl("http://sdk-agent.test/")
        )

# --- send_message Tests (Async) ---

async def test_send_message_success(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test successful async message sending via SDK."""
    target_agent_id = "receiver-agent-456"
    run_endpoint_rel = RUN_ENDPOINT_TPL_REL.format(agent_id=target_agent_id)
    run_endpoint_abs = f"{BASE_URL}{run_endpoint_rel}"
    mock_response_data = {"tool_result": "calculation complete", "value": 100}
    mock_api_response = {
        "status": "success",
        "message": "Tool executed.",
        "data": mock_response_data
    }
    httpx_mock.add_response(method="POST", url=run_endpoint_abs, json=mock_api_response, status_code=200)

    sender_id = "caller-789"
    message_type = "tool_invocation"
    payload = {"tool_name": "calculator", "parameters": {"op": "add", "a": 50, "b": 50}}

    response_data = await client.send_message(
        target_agent_id=target_agent_id,
        sender_id=sender_id,
        message_type=message_type,
        payload=payload
    )

    assert response_data == mock_response_data # Should return the 'data' part
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == run_endpoint_abs
    request_json = request.read().decode()
    assert f'"senderId": "{sender_id}"' in request_json
    assert f'"messageType": "{message_type}"' in request_json
    assert '"payload": {' in request_json

async def test_send_message_api_error_404(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test sending async message to non-existent agent (404)."""
    target_agent_id = "ghost-agent"
    run_endpoint_rel = RUN_ENDPOINT_TPL_REL.format(agent_id=target_agent_id)
    run_endpoint_abs = f"{BASE_URL}{run_endpoint_rel}"
    error_detail = f"Agent with ID '{target_agent_id}' not found."
    httpx_mock.add_response(method="POST", url=run_endpoint_abs, json={"detail": error_detail}, status_code=404)

    with pytest.raises(AgentKitError) as excinfo:
        await client.send_message(
            target_agent_id=target_agent_id,
            sender_id="caller-1",
            message_type="query",
            payload={"q": "hello?"}
        )

    assert excinfo.value.status_code == 404
    assert error_detail in str(excinfo.value)

async def test_send_message_tool_execution_error(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test handling application-level error reported by API during async send."""
    target_agent_id = "receiver-agent-456"
    run_endpoint_rel = RUN_ENDPOINT_TPL_REL.format(agent_id=target_agent_id)
    run_endpoint_abs = f"{BASE_URL}{run_endpoint_rel}"
    mock_api_response = {
        "status": "error",
        "message": "Tool 'calculator' execution failed: Division by zero",
        "data": {"status": "error", "error_message": "Division by zero"},
        "error_code": "TOOL_EXECUTION_FAILED"
    }
    httpx_mock.add_response(method="POST", url=run_endpoint_abs, json=mock_api_response, status_code=200) # API call is 200 OK

    with pytest.raises(AgentKitError) as excinfo:
         await client.send_message(
            target_agent_id=target_agent_id,
            sender_id="caller-2",
            message_type="tool_invocation",
            payload={"tool_name": "calculator", "parameters": {"op": "div", "a": 1, "b": 0}}
        )

    assert excinfo.value.status_code is None # Application level error, not HTTP
    assert "Tool 'calculator' execution failed" in str(excinfo.value)
    assert "(Code: TOOL_EXECUTION_FAILED)" in str(excinfo.value)
    assert excinfo.value.response_data == mock_api_response

async def test_send_message_network_error(client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test handling network error during async message sending."""
    target_agent_id = "receiver-agent-456"
    run_endpoint_rel = RUN_ENDPOINT_TPL_REL.format(agent_id=target_agent_id)
    run_endpoint_abs = f"{BASE_URL}{run_endpoint_rel}"
    httpx_mock.add_exception(httpx.TimeoutException("Request timed out"))

    with pytest.raises(AgentKitError, match="Network error"):
        await client.send_message(
            target_agent_id=target_agent_id,
            sender_id="caller-3",
            message_type="ping",
            payload={}
        )

# --- report_state_to_opscore Tests (New Async Tests) ---

@patch('agentkit.sdk.client.os.getenv')
@patch('agentkit.sdk.client.datetime')
async def test_report_state_success(mock_dt, mock_getenv, client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test successful state reporting to Ops-Core."""
    mock_getenv.side_effect = lambda key, default=None: OPSCORE_BASE_URL if key == "OPSCORE_API_URL" else OPSCORE_API_KEY if key == "OPSCORE_API_KEY" else default
    mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_dt.now.return_value = mock_now

    agent_id = "opscore-agent-1"
    state = "active"
    details = {"task": "processing data"}
    target_url = OPSCORE_STATE_ENDPOINT_TPL.format(agent_id=agent_id)

    httpx_mock.add_response(method="POST", url=target_url, status_code=200)

    await client.report_state_to_opscore(agent_id=agent_id, state=state, details=details)

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == target_url
    assert request.headers["Authorization"] == f"Bearer {OPSCORE_API_KEY}"
    assert request.headers["Content-Type"] == "application/json"

    request_json = request.read().decode()
    assert f'"agentId": "{agent_id}"' in request_json
    assert f'"state": "{state}"' in request_json
    assert f'"timestamp": "{mock_now.isoformat()}"' in request_json
    assert '"details": {"task": "processing data"}' in request_json

@patch('agentkit.sdk.client.os.getenv')
async def test_report_state_missing_config_url(mock_getenv, client: AgentKitClient):
    """Test error handling when OPSCORE_API_URL is not set."""
    mock_getenv.side_effect = lambda key, default=None: None if key == "OPSCORE_API_URL" else OPSCORE_API_KEY if key == "OPSCORE_API_KEY" else default

    with pytest.raises(AgentKitError, match="Configuration error: OPSCORE_API_URL not set"):
        await client.report_state_to_opscore(agent_id="test-agent", state="idle")

@patch('agentkit.sdk.client.os.getenv')
async def test_report_state_missing_config_key(mock_getenv, client: AgentKitClient):
    """Test error handling when OPSCORE_API_KEY is not set."""
    mock_getenv.side_effect = lambda key, default=None: OPSCORE_BASE_URL if key == "OPSCORE_API_URL" else None if key == "OPSCORE_API_KEY" else default

    with pytest.raises(AgentKitError, match="Configuration error: OPSCORE_API_KEY not set"):
        await client.report_state_to_opscore(agent_id="test-agent", state="idle")

@patch('agentkit.sdk.client.os.getenv')
async def test_report_state_opscore_api_error(mock_getenv, client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test handling API error from Ops-Core during state reporting."""
    mock_getenv.side_effect = lambda key, default=None: OPSCORE_BASE_URL if key == "OPSCORE_API_URL" else OPSCORE_API_KEY if key == "OPSCORE_API_KEY" else default

    agent_id = "opscore-agent-2"
    state = "error"
    target_url = OPSCORE_STATE_ENDPOINT_TPL.format(agent_id=agent_id)
    error_detail = "Invalid state transition"
    httpx_mock.add_response(method="POST", url=target_url, status_code=400, json={"detail": error_detail})

    with pytest.raises(AgentKitError) as excinfo:
        await client.report_state_to_opscore(agent_id=agent_id, state=state)

    assert excinfo.value.status_code == 400
    assert "Ops-Core API error" in str(excinfo.value)
    assert error_detail in str(excinfo.value)

@patch('agentkit.sdk.client.os.getenv')
async def test_report_state_network_error(mock_getenv, client: AgentKitClient, httpx_mock: HTTPXMock):
    """Test handling network error during state reporting."""
    mock_getenv.side_effect = lambda key, default=None: OPSCORE_BASE_URL if key == "OPSCORE_API_URL" else OPSCORE_API_KEY if key == "OPSCORE_API_KEY" else default

    agent_id = "opscore-agent-3"
    state = "idle"
    target_url = OPSCORE_STATE_ENDPOINT_TPL.format(agent_id=agent_id)
    httpx_mock.add_exception(httpx.ConnectError("Failed to connect to Ops-Core"))

    with pytest.raises(AgentKitError, match="Network error communicating with Ops-Core API"):
        await client.report_state_to_opscore(agent_id=agent_id, state=state)