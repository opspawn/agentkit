import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Import necessary types from the real library for type hinting if needed
# but the library itself will be mocked during tests.
from anthropic import AnthropicError
from anthropic.types import Message, TextBlock, Usage

# Import the client AFTER potential patches are applied in fixtures/tests
from agentkit.llm_clients.anthropic_client import AnthropicClient
from agentkit.core.interfaces.llm_client import LlmResponse

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_anthropic_api_key_env(monkeypatch):
    """Fixture to provide a mock Anthropic API key environment variable."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key_anthropic_456")

# Use patch for the AsyncAnthropic class where it's imported in the client code
@pytest.fixture
def mock_anthropic():
    """Fixture to mock the AsyncAnthropic class used by AnthropicClient."""
    with patch('agentkit.llm_clients.anthropic_client.AsyncAnthropic') as mock_async_anthropic_class:
        # Configure the mock instance that the mocked class will return
        mock_client_instance = AsyncMock() # Use AsyncMock for the instance
        mock_client_instance.messages = AsyncMock() # Mock the messages attribute
        mock_client_instance.messages.create = AsyncMock() # Mock the create method
        mock_async_anthropic_class.return_value = mock_client_instance
        yield mock_async_anthropic_class # Yield the mocked class

@pytest.fixture
def anthropic_client(mock_anthropic): # Depends on the mocked AsyncAnthropic class
    """Fixture for the AnthropicClient instance, ensuring AsyncAnthropic is mocked."""
    # Reset the mock before creating the client instance for this test
    mock_anthropic.reset_mock()
    client = AnthropicClient()
    # Assert AsyncAnthropic was called (without args, relying on env var)
    mock_anthropic.assert_called_once_with(api_key="test_key_anthropic_456", base_url=None)
    # Ensure the internal client is the mocked one
    assert client.client == mock_anthropic.return_value
    return client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_anthropic_client_generate_success(anthropic_client, mock_anthropic):
    """Tests successful generation using the Anthropic client."""
    # Arrange
    # The mock instance is mock_anthropic.return_value
    mock_client_instance = mock_anthropic.return_value

    mock_response_message = Message(
        id="msg_123",
        content=[TextBlock(text="Generated Anthropic text.", type="text")],
        model="claude-3-test",
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=Usage(input_tokens=8, output_tokens=12),
    )
    # Configure the mock create method on the client instance
    mock_client_instance.messages.create.return_value = mock_response_message

    prompt = "Tell me about Claude."
    model = "claude-3-test"
    temperature = 0.6
    max_tokens = 500 # Anthropic requires this
    system_prompt = "You are a helpful assistant."

    # Act
    response = await anthropic_client.generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=["Human:"],
        system_prompt=system_prompt, # Test system prompt kwarg
        top_k=5 # Test other kwargs passthrough
    )

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "Generated Anthropic text."
    assert response.model_used == "claude-3-test"
    assert response.error is None
    assert response.finish_reason == "stop" # Mapped from "end_turn"
    assert response.usage_metadata == {
        "input_tokens": 8,
        "output_tokens": 12,
    }

    # Verify the mock API call
    mock_client_instance.messages.create.assert_awaited_once()
    call_args, call_kwargs = mock_client_instance.messages.create.call_args
    assert call_kwargs["model"] == model
    # Anthropic expects list of messages, check structure
    assert call_kwargs["messages"] == [{"role": "user", "content": prompt}]
    assert call_kwargs["temperature"] == temperature
    assert call_kwargs["max_tokens"] == max_tokens
    assert call_kwargs["stop_sequences"] == ["Human:"]
    assert call_kwargs["system"] == system_prompt
    assert call_kwargs["top_k"] == 5 # Verify kwargs passthrough

@pytest.mark.asyncio
async def test_anthropic_client_generate_api_error(anthropic_client, mock_anthropic):
    """Tests handling of Anthropic API errors during generation."""
    # Arrange
    mock_client_instance = mock_anthropic.return_value
    mock_client_instance.messages.create.side_effect = AnthropicError("Simulated Anthropic API error")

    prompt = "This prompt will cause an API error."
    model = "claude-3-sonnet-20240229"

    # Act
    response = await anthropic_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "Anthropic API error: Simulated Anthropic API error" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    mock_client_instance.messages.create.assert_awaited_once()

@pytest.mark.asyncio
async def test_anthropic_client_generate_unexpected_error(anthropic_client, mock_anthropic):
    """Tests handling of unexpected errors during generation."""
    # Arrange
    mock_client_instance = mock_anthropic.return_value
    mock_client_instance.messages.create.side_effect = Exception("A different kind of failure")

    prompt = "Trigger unexpected failure."
    model = "claude-3-haiku-20240307"

    # Act
    response = await anthropic_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "An unexpected error occurred: A different kind of failure" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    mock_client_instance.messages.create.assert_awaited_once()

@pytest.mark.asyncio
async def test_anthropic_client_generate_default_max_tokens(anthropic_client, mock_anthropic):
    """Tests that a default max_tokens is used if none is provided."""
    # Arrange
    mock_client_instance = mock_anthropic.return_value

    mock_response_message = Message(
        id="msg_456", content=[TextBlock(text="Default tokens.", type="text")],
        model="claude-3-test", role="assistant", stop_reason="max_tokens",
        type="message", usage=Usage(input_tokens=5, output_tokens=1024)
    )
    mock_client_instance.messages.create.return_value = mock_response_message

    # Act - Call generate without max_tokens argument
    response = await anthropic_client.generate(prompt="Test default tokens", max_tokens=None)

    # Assert
    assert response.finish_reason == "length" # Mapped from "max_tokens"
    # Verify the mock API call used the default
    mock_client_instance.messages.create.assert_awaited_once()
    call_args, call_kwargs = mock_client_instance.messages.create.call_args
    assert call_kwargs["max_tokens"] == 1024 # Check the default was applied

# Use the mock_anthropic fixture which handles patching
def test_anthropic_client_init_missing_key(monkeypatch, mock_anthropic):
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False) # Ensure env var is not set
    mock_anthropic.reset_mock() # Reset mock since it's autoused via env var fixture

    # Act & Assert
    with pytest.raises(ValueError, match="Anthropic API key not provided"):
        AnthropicClient()
    mock_anthropic.assert_not_called() # Ensure constructor wasn't called

# Use the mock_anthropic fixture which handles patching
def test_anthropic_client_init_with_key_arg(mock_anthropic):
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_key_anthropic_789"
    mock_anthropic.reset_mock() # Reset mock before test

    # Act
    client = AnthropicClient(api_key=api_key)

    # Assert
    assert client.api_key == api_key
    # Check that the *mocked* AsyncAnthropic class was called correctly
    mock_anthropic.assert_called_once_with(api_key=api_key, base_url=None)
    assert client.client == mock_anthropic.return_value # Check internal client

# Use the mock_anthropic fixture which handles patching
def test_anthropic_client_init_with_base_url(mock_anthropic):
    """Tests initialization with a custom base URL."""
    # Arrange
    base_url = "http://localhost:8081/anthropic"
    api_key_from_env = "test_key_anthropic_456" # From mock_anthropic_api_key_env
    mock_anthropic.reset_mock() # Reset mock before test

    # Act
    client = AnthropicClient(base_url=base_url) # Relies on env var fixture for key

    # Assert
    assert client.api_key == api_key_from_env # From fixture
    # Check that the *mocked* AsyncAnthropic class was called correctly
    mock_anthropic.assert_called_once_with(api_key=api_key_from_env, base_url=base_url)
    assert client.client == mock_anthropic.return_value # Check internal client
