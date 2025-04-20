import pytest
import os
import uuid
import asyncio # Import asyncio
from agentkit.sdk.client import AgentKitClient, AgentKitError
from pydantic import HttpUrl

# --- Test Configuration ---
AGENTKIT_API_BASE_URL = os.getenv("AGENTKIT_URL", "http://127.0.0.1:8000")
LIVE_LLM_MODEL = "gpt-4.1-mini-2025-04-14" # Model specified by user

# Define a custom marker for live tests that require external services and API keys
live_llm_test = pytest.mark.live_llm

# Apply the asyncio marker to all tests in this module
pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="module")
def live_agent_client(): # Make this fixture synchronous
    """Fixture to provide an AgentKitClient instance for the module."""
    # Ensure API is running and .env is loaded before running these tests
    # (Typically handled by running the API via docker-compose up)
    client = AgentKitClient(base_url=AGENTKIT_API_BASE_URL)
    # Optional: Add a check here to see if the API is reachable
    # try:
    #     # A simple check, maybe list agents or a health check endpoint if available
    #     pass
    # except AgentKitError:
    #     pytest.skip("AgentKit API not reachable, skipping live tests.")
    return client

@pytest.fixture(scope="module")
async def registered_dummy_agent_id(live_agent_client: AgentKitClient): # Take the client instance
    """Fixture to register a dummy agent once per module for API calls."""
    # Use the provided client instance directly
    client = live_agent_client

    dummy_agent_name = f"live-test-dummy-{uuid.uuid4()}"
    dummy_endpoint = HttpUrl("http://localhost:9999/dummy-live")
    try:
        # Directly await the async SDK method
        agent_id = await client.register_agent(
            agent_name=dummy_agent_name,
            capabilities=["live_test"],
            version="1.0",
            contact_endpoint=dummy_endpoint
        )
        print(f"\nRegistered dummy agent {dummy_agent_name} with ID: {agent_id} for live test")
        return agent_id
    except AgentKitError as e:
        pytest.skip(f"Failed to register dummy agent for live test: {e}")


@live_llm_test # Mark this test as a live LLM test
async def test_generic_llm_tool_live_call(live_agent_client: AgentKitClient, registered_dummy_agent_id: str):
    """
    Performs a live integration test of the generic_llm_completion tool
    by sending a request through the AgentKit API.

    Requires:
    1. AgentKit API running (e.g., via `docker-compose up api`).
    2. A valid .env file in the project root with OPENAI_API_KEY.
    """
    # Get the client instance
    client = live_agent_client
    # The fixture already returns the awaited ID
    dummy_agent_id: str = registered_dummy_agent_id

    tool_payload = {
        "tool_name": "generic_llm_completion",
        "arguments": {
            "model": LIVE_LLM_MODEL,
            "messages": [
                {"role": "user", "content": "What is the capital of France? Respond with only the name."}
            ],
            "max_tokens": 10,
            "temperature": 0.1 # Low temperature for predictable answer
        }
    }

    print(f"\nAttempting live call to model '{LIVE_LLM_MODEL}' via tool...")
    try:
        # Directly await the async SDK method
        response_data = await client.send_message(
            target_agent_id=dummy_agent_id,
            sender_id="live_test_runner",
            message_type="tool_invocation",
            payload=tool_payload
        )

        print("Live call response data:", response_data)

        assert response_data is not None, "API response data should not be None"
        assert isinstance(response_data, dict), "API response data should be a dictionary"

        # Check the structure returned by the messaging endpoint
        assert "status" in response_data, "Response should have a 'status' field"
        assert response_data["status"] == "success", f"API call status was not success: {response_data.get('message')}"
        assert "result" in response_data, "Successful response should contain 'result' from the tool"

        # Check the structure of the tool's result (which is litellm's response dict)
        llm_result = response_data["result"]
        assert isinstance(llm_result, dict), "Tool result should be a dictionary"
        assert llm_result.get("model") == LIVE_LLM_MODEL, "Model in result should match requested model"
        assert "choices" in llm_result, "LLM result should have 'choices'"
        assert len(llm_result["choices"]) > 0, "LLM result should have at least one choice"
        message = llm_result["choices"][0].get("message")
        assert message is not None, "First choice should have a 'message'"
        content = message.get("content")
        assert content is not None, "Message should have 'content'"
        assert "Paris" in content, f"Expected 'Paris' in LLM response, got: {content}"

    except AgentKitError as e:
        pytest.fail(f"Live LLM tool invocation failed: {e} - Response: {e.response_data}")
    except Exception as e:
         pytest.fail(f"An unexpected error occurred during the live test: {e}")