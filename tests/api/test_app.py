import pytest
from fastapi.testclient import TestClient
from main import app  # Import the FastAPI app instance from main.py

# Fixture to create a TestClient instance
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Test for the /health endpoint
def test_health_check(client: TestClient):
    """
    Test the GET /health endpoint.
    It should return a 200 OK status and the expected JSON body.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

# Test for the root endpoint (optional, but good practice)
def test_read_root(client: TestClient):
    """
    Test the GET / endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to AgentKit API"}