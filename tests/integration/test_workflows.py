import pytest
import time
from agentkit.sdk.client import AgentKitClient, AgentKitError
from agentkit.core.models import MessagePayload # Assuming models are accessible

# --- Constants ---
# TODO: Make API URL configurable, potentially via environment variable or fixture
API_BASE_URL = "http://localhost:8000" # Default assumption

# --- Fixtures ---

@pytest.fixture(scope="module")
def agent_kit_client():
    """Provides an AgentKitClient instance configured for the integration test API."""
    # TODO: Add logic to wait for the API service (in Docker) to be ready
    # For now, assume it's running at API_BASE_URL
    print(f"\nInitializing AgentKitClient for {API_BASE_URL}...")
    client = AgentKitClient(base_url=API_BASE_URL)
    # Simple readiness check (optional but recommended)
    # Add a small delay or a loop with health check if needed
    # time.sleep(2) # Basic delay
    return client

# TODO: Add fixture to manage Docker Compose environment (start/stop)
# This might involve using pytest-docker or subprocess calls.
# @pytest.fixture(scope="session", autouse=True)
# def docker_environment():
#     print("\nStarting Docker Compose environment...")
#     # Command to start docker-compose up -d
#     yield
#     print("\nStopping Docker Compose environment...")
#     # Command to stop docker-compose down

# --- Test Scenarios ---

@pytest.mark.integration
def test_scenario_1_basic_registration_and_messaging(agent_kit_client: AgentKitClient):
    """
    Tests Scenario 1:
    - Register Agent A
    - Register Agent B
    - Agent A sends a message to Agent B
    """
    client = agent_kit_client
    agent_a_name = f"integ-agent-a-{int(time.time())}"
    agent_b_name = f"integ-agent-b-{int(time.time())}"
    agent_a_endpoint = "http://mock-agent-a.test/endpoint"
    agent_b_endpoint = "http://mock-agent-b.test/endpoint"

    print(f"Registering {agent_a_name}...")
    agent_a_id = client.register_agent(
        agent_name=agent_a_name,
        version="1.0",
        contact_endpoint=agent_a_endpoint,
        capabilities=["test"]
    )
    assert isinstance(agent_a_id, str)
    print(f"Registered {agent_a_name} with ID: {agent_a_id}")

    print(f"Registering {agent_b_name}...")
    agent_b_id = client.register_agent(
        agent_name=agent_b_name,
        version="1.0",
        contact_endpoint=agent_b_endpoint,
        capabilities=["test"]
    )
    assert isinstance(agent_b_id, str)
    print(f"Registered {agent_b_name} with ID: {agent_b_id}")

    # Agent A sends message to Agent B
    message_payload = {"content": "ping"}
    message_type = "ping_request"
    print(f"Agent {agent_a_id} sending '{message_type}' to {agent_b_id}...")

    response = client.send_message(
        target_agent_id=agent_b_id,
        sender_id=agent_a_id,
        message_type=message_type,
        payload=message_payload
    )

    print(f"Received response: {response}")
    # Basic assertion: API accepted the message (actual processing depends on agent B)
    # The default API likely returns a simple acknowledgement.
    # Adjust assertion based on actual API behavior.
    assert response is not None
    assert isinstance(response, dict)
    # Example assertion if API returns a status:
    # assert response.get("status") == "message_received" or response.get("status") == "processing_started"

# --- Scenario 2 ---

@pytest.mark.integration
def test_scenario_2_simple_tool_invocation(agent_kit_client: AgentKitClient):
    """
    Tests Scenario 2: Agent invokes a registered (mock) tool.
    Assumes the API service is configured with 'mock_tool_adder' pointing to
    the mock_tool service at http://mock_tool:9001/invoke
    """
    client = agent_kit_client
    agent_name = f"integ-agent-tool-user-{int(time.time())}"
    agent_endpoint = "http://mock-agent-tool-user.test/endpoint"
    tool_name = "mock_tool_adder" # Name API service knows

    print(f"\nRegistering {agent_name} for Scenario 2...")
    agent_id = client.register_agent(
        agent_name=agent_name,
        version="1.0",
        contact_endpoint=agent_endpoint,
        capabilities=["calculator_user"]
    )
    assert isinstance(agent_id, str)
    print(f"Registered {agent_name} with ID: {agent_id}")

    # Agent attempts to invoke the mock tool
    tool_arguments = {"x": 5, "y": 3}
    message_payload = {
        "tool_name": tool_name,
        "arguments": tool_arguments
    }
    message_type = "tool_invocation"
    print(f"Agent {agent_id} attempting to invoke '{message_type}' for tool '{tool_name}'...")

    response = client.send_message(
        target_agent_id=agent_id, # Target doesn't matter for tool invocation via API
        sender_id="system", # Assume system triggers tool use
        message_type=message_type,
        payload=message_payload
    )

    print(f"Received response from tool invocation: {response}")

    # Assert that the response indicates success and contains expected data from the mock tool
    assert isinstance(response, dict)
    assert response.get("status") == "success" # From mock_tool.py response
    assert response.get("message") == "Mock tool executed successfully."
    # Assert that the echoed input matches only the arguments sent to the mock tool
    assert response.get("input_received") == {"arguments": tool_arguments}
    assert response.get("output") == f"Processed arguments: {tool_arguments}"


# --- Scenario 3 ---

@pytest.mark.integration
def test_scenario_3_invoke_nonexistent_tool(agent_kit_client: AgentKitClient):
    """Tests Scenario 3: Agent tries to invoke a tool that doesn't exist."""
    client = agent_kit_client
    agent_name = f"integ-agent-tool-test-{int(time.time())}"
    agent_endpoint = "http://mock-agent-tool.test/endpoint"

    print(f"\nRegistering {agent_name} for Scenario 3...")
    agent_id = client.register_agent(
        agent_name=agent_name,
        version="1.0",
        contact_endpoint=agent_endpoint,
        capabilities=["tool_user"]
    )
    assert isinstance(agent_id, str)
    print(f"Registered {agent_name} with ID: {agent_id}")

    # Attempt to invoke a tool that is not registered
    message_payload = {
        "tool_name": "non_existent_tool",
        "arguments": {"param": "value"}
    }
    message_type = "tool_invocation"
    print(f"Agent {agent_id} attempting to invoke '{message_type}' for non_existent_tool...")

    with pytest.raises(AgentKitError) as excinfo:
        client.send_message(
            target_agent_id=agent_id, # Sending to self for simplicity, target doesn't matter here
            sender_id="system", # Assume system triggers tool use
            message_type=message_type,
            payload=message_payload
        )

    print(f"Caught expected error: {excinfo.value}")
    # Check for a specific error message or status code if the API provides one
    # Example: Check if the error message contains "Tool not found" or similar
    assert excinfo.value.status_code == 404 # Assuming API returns 404 for not found tool
    assert "Tool 'non_existent_tool' not found" in str(excinfo.value.response_data) # Check detail message


# --- Scenario 4 ---

@pytest.mark.integration
def test_scenario_4_message_nonexistent_agent(agent_kit_client: AgentKitClient):
    """Tests Scenario 4: Agent sends a message to an agent that doesn't exist."""
    client = agent_kit_client
    sender_agent_name = f"integ-agent-sender-{int(time.time())}"
    sender_endpoint = "http://mock-agent-sender.test/endpoint"

    print(f"\nRegistering {sender_agent_name} for Scenario 4...")
    sender_id = client.register_agent(
        agent_name=sender_agent_name,
        version="1.0",
        contact_endpoint=sender_endpoint,
        capabilities=["sender"]
    )
    assert isinstance(sender_id, str)
    print(f"Registered {sender_agent_name} with ID: {sender_id}")

    # Attempt to send message to a non-existent agent ID
    target_id = "agent-does-not-exist-12345"
    message_payload = {"content": "hello?"}
    message_type = "query"
    print(f"Agent {sender_id} attempting to send '{message_type}' to non-existent agent {target_id}...")

    with pytest.raises(AgentKitError) as excinfo:
        client.send_message(
            target_agent_id=target_id,
            sender_id=sender_id,
            message_type=message_type,
            payload=message_payload
        )

    print(f"Caught expected error: {excinfo.value}")
    # Check for a specific error message or status code
    assert excinfo.value.status_code == 404 # Assuming API returns 404 for not found agent
    assert f"Agent with ID '{target_id}' not found" in str(excinfo.value.response_data) # Check detail message