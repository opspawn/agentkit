import pytest
import os
import json
import time
import hmac
import hashlib
from unittest.mock import patch, MagicMock, ANY # Import patch and MagicMock
from fastapi import BackgroundTasks # Import BackgroundTasks
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock # Import HTTPXMock
from main import app # Import the FastAPI app instance from main.py
from agentkit.registration.storage import agent_storage
from agentkit.core.models import AgentRegistrationPayload, AgentInfo

# Fixture to provide a TestClient instance for making API requests
@pytest.fixture(scope="module")
def client():
    # Need to include the router in the app for testing
    # This is a bit tricky as main.py doesn't include it by default yet.
    # We'll manually add it here for the test client.
    # In a more structured app, this might be handled differently (e.g., app factory).
    from agentkit.api.endpoints import registration
    if registration.router not in app.routes:
         app.include_router(registration.router, prefix="/v1")

    with TestClient(app) as c:
        yield c

# Fixture to ensure clean storage for each test function
@pytest.fixture(autouse=True)
def clear_storage_before_each_test():
    agent_storage.clear_all()
    yield
    agent_storage.clear_all()

# --- Test Cases ---

def test_register_agent_success(client: TestClient):
    """Test successful agent registration via the API."""
    payload = {
        "agentName": "APITestAgent",
        "capabilities": ["api_test", "crud"],
        "version": "1.0.1",
        "contactEndpoint": "http://api-test-agent.local:8080/invoke",
        "metadata": {
            "description": "Agent created via API test"
        }
    }
    response = client.post("/v1/agents/register", json=payload)

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["message"] == "Agent 'APITestAgent' registered successfully."
    assert "agentId" in response_data["data"]
    agent_id = response_data["data"]["agentId"]

    # Verify agent is actually in storage
    stored_agent = agent_storage.get_agent(agent_id)
    assert stored_agent is not None
    assert stored_agent.agentName == payload["agentName"]
    assert stored_agent.version == payload["version"]
    assert str(stored_agent.contactEndpoint) == payload["contactEndpoint"] # Compare as string
    assert stored_agent.metadata.description == payload["metadata"]["description"]

def test_register_agent_missing_required_field(client: TestClient):
    """Test registration failure when a required field (e.g., agentName) is missing."""
    payload = {
        # "agentName": "MissingNameAgent", # Missing agentName
        "capabilities": ["test"],
        "version": "1.0",
        "contactEndpoint": "http://missing.name:8000"
    }
    response = client.post("/v1/agents/register", json=payload)
    # FastAPI/Pydantic handles validation errors with 422
    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    # Check if the error message mentions the missing field
    assert any("agentName" in error["loc"] for error in response_data["detail"])
    assert any("Field required" in error["msg"] for error in response_data["detail"])


def test_register_agent_invalid_url(client: TestClient):
    """Test registration failure with an invalid contactEndpoint URL."""
    payload = {
        "agentName": "InvalidURLAgent",
        "capabilities": ["test"],
        "version": "1.0",
        "contactEndpoint": "not-a-valid-url" # Invalid URL
    }
    response = client.post("/v1/agents/register", json=payload)
    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    assert any("contactEndpoint" in error["loc"] for error in response_data["detail"])
    # Make assertion more general for URL validation errors
    assert any("URL" in error["msg"].upper() for error in response_data["detail"]), f"Expected URL validation error, got: {response_data['detail']}"


def test_register_agent_duplicate_name_conflict(client: TestClient):
    """Test registration failure when agent name already exists (409 Conflict)."""
    # First registration (should succeed)
    payload1 = {
        "agentName": "DuplicateAPIName",
        "capabilities": ["test1"],
        "version": "1.0",
        "contactEndpoint": "http://dup1.test"
    }
    response1 = client.post("/v1/agents/register", json=payload1)
    assert response1.status_code == 201

    # Second registration with the same name (should fail)
    payload2 = {
        "agentName": "DuplicateAPIName", # Same name
        "capabilities": ["test2"],
        "version": "1.1",
        "contactEndpoint": "http://dup2.test"
    }
    response2 = client.post("/v1/agents/register", json=payload2)
    assert response2.status_code == 409 # Conflict
    response_data = response2.json()
    assert "detail" in response_data
    assert "Agent with name 'DuplicateAPIName' already registered" in response_data["detail"]

    # Ensure only the first agent is stored
    assert len(agent_storage.list_agents()) == 1
    assert agent_storage.get_agent_by_name("DuplicateAPIName").version == "1.0"

# --- Webhook Notification Tests ---

# Common payload for webhook tests
WEBHOOK_TEST_PAYLOAD = {
    "agentName": "WebhookTestAgent",
    "capabilities": ["webhook_test"],
    "version": "1.0.0",
    "contactEndpoint": "http://webhook.test:8000",
}
WEBHOOK_URL = "http://mock-opscore.test/webhook"
WEBHOOK_SECRET = "test-secret"

@pytest.mark.asyncio # Mark test as async if the tested function is async
async def test_register_agent_triggers_webhook_success(
    client: TestClient, httpx_mock: HTTPXMock, monkeypatch, mocker # Add mocks
):
    """Test that successful registration triggers the Ops-Core webhook via background task."""
    monkeypatch.setenv("OPSCORE_WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setenv("OPSCORE_WEBHOOK_SECRET", WEBHOOK_SECRET)

    # Mock BackgroundTasks.add_task
    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")

    # Mock the webhook endpoint
    httpx_mock.add_response(url=WEBHOOK_URL, method="POST", status_code=200)

    # Mock time.time for predictable signature
    fixed_time = int(time.time())
    mocker.patch("time.time", return_value=fixed_time)

    # Perform registration
    response = client.post("/v1/agents/register", json=WEBHOOK_TEST_PAYLOAD)
    assert response.status_code == 201
    agent_id = response.json()["data"]["agentId"]

    # Verify BackgroundTasks.add_task was called correctly
    mock_add_task.assert_called_once()
    # Check the function passed to add_task (it's the webhook function)
    assert mock_add_task.call_args[0][0].__name__ == "notify_opscore_webhook"
    # Check the agent_info argument passed to the webhook function
    agent_info_arg = mock_add_task.call_args[0][1]
    assert isinstance(agent_info_arg, AgentInfo)
    assert agent_info_arg.agentId == agent_id
    assert agent_info_arg.agentName == WEBHOOK_TEST_PAYLOAD["agentName"]

    # --- Now, let's simulate the background task execution to test the webhook call itself ---
    # Get the actual function and arguments passed to add_task
    webhook_func = mock_add_task.call_args[0][0]
    webhook_args = mock_add_task.call_args[0][1:]
    webhook_kwargs = mock_add_task.call_args[1]

    # Execute the background task function directly (since it's hard to test background tasks otherwise)
    await webhook_func(*webhook_args, **webhook_kwargs)

    # Verify the HTTP request made by the webhook function
    requests = httpx_mock.get_requests(url=WEBHOOK_URL, method="POST")
    assert len(requests) == 1
    request = requests[0]

    # Verify headers
    assert request.headers["content-type"] == "application/json"
    assert request.headers["x-agentkit-timestamp"] == str(fixed_time)

    # Verify signature
    # Construct the expected payload *using the agent_info object passed to the task*
    # This ensures consistency with how the actual webhook function builds it.
    agent_info_for_payload = agent_info_arg # From line 170
    expected_agent_details = {
        "agentId": agent_info_for_payload.agentId,
        "agentName": agent_info_for_payload.agentName,
        "version": agent_info_for_payload.version,
        "capabilities": agent_info_for_payload.capabilities,
        "contactEndpoint": str(agent_info_for_payload.contactEndpoint), # Use string form
        "metadata": agent_info_for_payload.metadata or {} # Handle potential None
    }
    expected_payload_dict = {
        "event_type": "REGISTER",
        "agent_details": expected_agent_details
    }
    payload_bytes = json.dumps(expected_payload_dict, separators=(',', ':')).encode('utf-8')
    # Construct signature string consistently with the main code
    sig_string = str(fixed_time).encode('utf-8') + b'.' + payload_bytes
    expected_signature = hmac.new(WEBHOOK_SECRET.encode('utf-8'), sig_string, hashlib.sha256).hexdigest()
    assert request.headers["x-agentkit-signature"] == expected_signature

    # Verify payload
    assert json.loads(request.content) == expected_payload_dict


@pytest.mark.asyncio
async def test_register_agent_webhook_skipped_if_not_configured(
    client: TestClient, httpx_mock: HTTPXMock, monkeypatch, mocker
):
    """Test that the webhook is not called if URL or secret is missing."""
    # Ensure env vars are NOT set
    monkeypatch.delenv("OPSCORE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OPSCORE_WEBHOOK_SECRET", raising=False)

    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")
    mock_logger_info = mocker.patch("agentkit.api.endpoints.registration.logger.info") # Mock logger

    # Perform registration
    response = client.post("/v1/agents/register", json=WEBHOOK_TEST_PAYLOAD)
    assert response.status_code == 201

    # Verify add_task was still called
    mock_add_task.assert_called_once()

    # Simulate background task execution
    webhook_func = mock_add_task.call_args[0][0]
    webhook_args = mock_add_task.call_args[0][1:]
    webhook_kwargs = mock_add_task.call_args[1]
    await webhook_func(*webhook_args, **webhook_kwargs)

    # Verify NO HTTP request was made
    requests = httpx_mock.get_requests(url=WEBHOOK_URL, method="POST")
    assert len(requests) == 0
    # Verify log message indicating skip
    mock_logger_info.assert_any_call("Ops-Core webhook URL or secret not configured. Skipping notification.")


@pytest.mark.asyncio
async def test_register_agent_webhook_handles_http_error(
    client: TestClient, httpx_mock: HTTPXMock, monkeypatch, mocker
):
    """Test that webhook HTTP errors are logged but registration succeeds."""
    monkeypatch.setenv("OPSCORE_WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setenv("OPSCORE_WEBHOOK_SECRET", WEBHOOK_SECRET)

    mock_add_task = mocker.patch("fastapi.BackgroundTasks.add_task")
    mock_logger_error = mocker.patch("agentkit.api.endpoints.registration.logger.error") # Mock logger

    # Mock the webhook endpoint to return an error
    httpx_mock.add_response(url=WEBHOOK_URL, method="POST", status_code=500, text="Internal Server Error")

    # Perform registration - should still succeed
    response = client.post("/v1/agents/register", json=WEBHOOK_TEST_PAYLOAD)
    assert response.status_code == 201

    # Simulate background task execution
    webhook_func = mock_add_task.call_args[0][0]
    webhook_args = mock_add_task.call_args[0][1:]
    webhook_kwargs = mock_add_task.call_args[1]
    await webhook_func(*webhook_args, **webhook_kwargs)

    # Verify HTTP request was made
    requests = httpx_mock.get_requests(url=WEBHOOK_URL, method="POST")
    assert len(requests) == 1

    # Verify error was logged
    mock_logger_error.assert_called_once()
    assert "Status error 500" in mock_logger_error.call_args[0][0]


# Note: Testing the 500 Internal Server Error case for registration itself
# typically requires mocking the storage layer to raise an unexpected Exception,
# which adds complexity. We'll skip that specific test for now but acknowledge
# its importance in robust testing.