import pytest
from fastapi.testclient import TestClient
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

# Note: Testing the 500 Internal Server Error case typically requires mocking
# the storage layer to raise an unexpected Exception, which adds complexity.
# We'll skip that specific test for now but acknowledge its importance in robust testing.