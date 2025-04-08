import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

from anthropic import AnthropicError
from anthropic.types import Message, TextBlock, Usage

from agentkit.llm_clients.anthropic_client import AnthropicClient
from agentkit.core.interfaces.llm_client import LlmResponse

# Fixture to provide a mock API key
@pytest.fixture(autouse=True)
def mock_anthropic_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key_anthropic_456")

# Fixture for the AnthropicClient instance
@pytest.fixture
def anthropic_client():
    return AnthropicClient()

# --- Test Cases ---

@pytest.mark.asyncio
@patch("anthropic.AsyncAnthropic", new_callable=MagicMock)
async def test_anthropic_client_generate_success(mock_async_anthropic_class, anthropic_client):
    """Tests successful generation using the Anthropic client."""
    # Arrange
    mock_client_instance = AsyncMock()
    mock_async_anthropic_class.return_value = mock_client_instance

    mock_response_message = Message(
        id="msg_123",
        content=[TextBlock(text="Generated Anthropic text.", type="text")],
        model="claude-3-test",
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=Usage(input_tokens=8, output_tokens=12),
    )
    mock_client_instance.messages.create = AsyncMock(return_value=mock_response_message)

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
    assert call_kwargs["messages"] == [{"role": "user", "content": prompt}]
    assert call_kwargs["temperature"] == temperature
    assert call_kwargs["max_tokens"] == max_tokens
    assert call_kwargs["stop_sequences"] == ["Human:"]
    assert call_kwargs["system"] == system_prompt
    assert call_kwargs["top_k"] == 5 # Verify kwargs passthrough

@pytest.mark.asyncio
@patch("anthropic.AsyncAnthropic", new_callable=MagicMock)
async def test_anthropic_client_generate_api_error(mock_async_anthropic_class, anthropic_client):
    """Tests handling of Anthropic API errors during generation."""
    # Arrange
    mock_client_instance = AsyncMock()
    mock_async_anthropic_class.return_value = mock_client_instance
    mock_client_instance.messages.create = AsyncMock(
        side_effect=AnthropicError("Simulated Anthropic API error")
    )

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
@patch("anthropic.AsyncAnthropic", new_callable=MagicMock)
async def test_anthropic_client_generate_unexpected_error(mock_async_anthropic_class, anthropic_client):
    """Tests handling of unexpected errors during generation."""
    # Arrange
    mock_client_instance = AsyncMock()
    mock_async_anthropic_class.return_value = mock_client_instance
    mock_client_instance.messages.create = AsyncMock(
        side_effect=Exception("A different kind of failure")
    )

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
@patch("anthropic.AsyncAnthropic", new_callable=MagicMock)
async def test_anthropic_client_generate_default_max_tokens(mock_async_anthropic_class, anthropic_client):
    """Tests that a default max_tokens is used if none is provided."""
    # Arrange
    mock_client_instance = AsyncMock()
    mock_async_anthropic_class.return_value = mock_client_instance

    mock_response_message = Message(
        id="msg_456", content=[TextBlock(text="Default tokens.", type="text")],
        model="claude-3-test", role="assistant", stop_reason="max_tokens",
        type="message", usage=Usage(input_tokens=5, output_tokens=1024)
    )
    mock_client_instance.messages.create = AsyncMock(return_value=mock_response_message)

    # Act - Call generate without max_tokens argument
    response = await anthropic_client.generate(prompt="Test default tokens", max_tokens=None)

    # Assert
    assert response.finish_reason == "length" # Mapped from "max_tokens"
    # Verify the mock API call used the default
    mock_client_instance.messages.create.assert_awaited_once()
    call_args, call_kwargs = mock_client_instance.messages.create.call_args
    assert call_kwargs["max_tokens"] == 1024 # Check the default was applied

def test_anthropic_client_init_missing_key(monkeypatch):
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False) # Ensure env var is not set

    # Act & Assert
    with pytest.raises(ValueError, match="Anthropic API key not provided"):
        AnthropicClient()

def test_anthropic_client_init_with_key_arg():
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_key_anthropic_789"

    # Act
    with patch("anthropic.AsyncAnthropic") as mock_async_anthropic_class:
        client = AnthropicClient(api_key=api_key)

    # Assert
    assert client.api_key == api_key
    mock_async_anthropic_class.assert_called_once_with(api_key=api_key, base_url=None)

def test_anthropic_client_init_with_base_url():
    """Tests initialization with a custom base URL."""
    # Arrange
    base_url = "http://localhost:8081/anthropic"

    # Act
    with patch("anthropic.AsyncAnthropic") as mock_async_anthropic_class:
        client = AnthropicClient(base_url=base_url) # Relies on mock_anthropic_api_key fixture

    # Assert
    assert client.api_key == "test_key_anthropic_456" # From fixture
    mock_async_anthropic_class.assert_called_once_with(api_key="test_key_anthropic_456", base_url=base_url)
