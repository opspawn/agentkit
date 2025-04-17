import pytest
import os
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response # Required by httpserver handler
from urllib.parse import urljoin
import json
from datetime import datetime, timezone

from agentkit.sdk.client import AgentKitClient, AgentKitError

# Use pytest mark for async tests
pytestmark = pytest.mark.asyncio

# Constants for the test
MOCK_AGENT_ID = "int-test-agent-opscore-1"
MOCK_OPSCORE_API_KEY = "int-test-opscore-key"

@pytest.fixture
async def sdk_client(httpserver: HTTPServer):
    """Fixture to provide an SDK client configured for the test HTTP server."""
    # Configure AgentKit base URL (not strictly needed for this test, but good practice)
    agentkit_base_url = f"http://{httpserver.host}:{httpserver.port}/agentkit"
    client = AgentKitClient(base_url=agentkit_base_url)

    # Set environment variables for Ops-Core URL pointing to the mock server
    opscore_base_url = f"http://{httpserver.host}:{httpserver.port}"
    os.environ["OPSCORE_API_URL"] = opscore_base_url
    os.environ["OPSCORE_API_KEY"] = MOCK_OPSCORE_API_KEY

    yield client

    # Clean up environment variables and client
    await client.close()
    del os.environ["OPSCORE_API_URL"]
    del os.environ["OPSCORE_API_KEY"]


async def test_report_state_integration_success(httpserver: HTTPServer, sdk_client: AgentKitClient):
    """
    Integration test verifying report_state_to_opscore sends correct request
    to a mock Ops-Core endpoint.
    """
    state_to_report = "active"
    details_to_report = {"current_task": "integration_test"}
    expected_endpoint = f"/v1/opscore/agent/{MOCK_AGENT_ID}/state"
    expected_url = urljoin(os.environ["OPSCORE_API_URL"], expected_endpoint)

    # Configure the mock Ops-Core server endpoint
    httpserver.expect_request(
        uri=expected_endpoint,
        method="POST",
        headers={
            "Authorization": f"Bearer {MOCK_OPSCORE_API_KEY}",
            "Content-Type": "application/json",
        },
        # Use a handler function for more complex JSON validation if needed
        # json=expected_payload # Simple check might fail due to timestamp
    ).respond_with_json({"status": "success", "message": "State updated"}, status=200)

    # Call the SDK method
    await sdk_client.report_state_to_opscore(
        agent_id=MOCK_AGENT_ID,
        state=state_to_report,
        details=details_to_report
    )

    # Assert that the expected request was received by the mock server
    # httpserver automatically asserts if the expected request wasn't made.
    # We can add more specific assertions on the received request data if needed.
    recorded_requests = httpserver.log # Get recorded requests
    assert len(recorded_requests) == 1
    req, _ = recorded_requests[0] # req is werkzeug.Request

    # Validate specific parts of the received request
    assert req.method == "POST"
    assert req.url == expected_endpoint # URI path
    assert req.headers.get("Authorization") == f"Bearer {MOCK_OPSCORE_API_KEY}"
    assert req.headers.get("Content-Type") == "application/json"

    # Validate JSON payload (handle timestamp carefully)
    received_payload = json.loads(req.get_data(as_text=True))
    assert received_payload["agentId"] == MOCK_AGENT_ID
    assert received_payload["state"] == state_to_report
    assert received_payload["details"] == details_to_report
    # Check timestamp format and that it's recent
    received_timestamp = datetime.fromisoformat(received_payload["timestamp"])
    assert received_timestamp.tzinfo == timezone.utc
    time_diff = datetime.now(timezone.utc) - received_timestamp
    assert abs(time_diff.total_seconds()) < 5 # Allow 5 seconds difference


async def test_report_state_integration_opscore_error(httpserver: HTTPServer, sdk_client: AgentKitClient):
    """
    Integration test verifying error handling when mock Ops-Core returns an error.
    """
    state_to_report = "error"
    expected_endpoint = f"/v1/opscore/agent/{MOCK_AGENT_ID}/state"
    error_detail = "Invalid state provided"

    # Configure the mock Ops-Core server endpoint to return an error
    httpserver.expect_request(
        uri=expected_endpoint,
        method="POST",
    ).respond_with_json({"detail": error_detail}, status=400)

    # Call the SDK method and expect an AgentKitError
    with pytest.raises(AgentKitError) as excinfo:
        await sdk_client.report_state_to_opscore(
            agent_id=MOCK_AGENT_ID,
            state=state_to_report
        )

    # Assert details about the raised exception
    assert excinfo.value.status_code == 400
    assert "Ops-Core API error" in str(excinfo.value)
    assert error_detail in str(excinfo.value)

    # Assert the request was still made
    recorded_requests = httpserver.log
    assert len(recorded_requests) == 1
    req, _ = recorded_requests[0]
    assert req.method == "POST"
    assert req.url == expected_endpoint