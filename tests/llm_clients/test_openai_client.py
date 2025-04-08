import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

from openai import OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from agentkit.llm_clients.openai_client import OpenAiClient
from agentkit.core.interfaces.llm_client import LlmResponse

# Fixture to provide a mock API key
@pytest.fixture(autouse=True)
def mock_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_123")

# Fixture for the OpenAiClient instance
@pytest.fixture
def openai_client():
    return OpenAiClient()

# --- Test Cases ---

@pytest.mark.asyncio
@patch("openai.AsyncOpenAI", new_callable=MagicMock) # Use MagicMock for sync/async flexibility if needed later
async def test_openai_client_generate_success(mock_async_openai_class, openai_client):
    """Tests successful generation using the OpenAI client."""
    # Arrange
    mock_client_instance = AsyncMock()
    mock_async_openai_class.return_value = mock_client_instance # Mock the instance created in __init__

    mock_completion = ChatCompletion(
        id="chatcmpl-123",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="This is the generated text.",
                    role="assistant",
                ),
            )
        ],
        created=1677652288,
        model="gpt-4-test",
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=10, prompt_tokens=5, total_tokens=15),
    )
    mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

    prompt = "Tell me a story."
    model = "gpt-4-test"
    temperature = 0.5
    max_tokens = 100

    # Act
    response = await openai_client.generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=["\n"],
        custom_arg="test_value" # Test kwargs passthrough
    )

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "This is the generated text."
    assert response.model_used == "gpt-4-test"
    assert response.error is None
    assert response.finish_reason == "stop"
    assert response.usage_metadata == {
        "prompt_tokens": 5,
        "completion_tokens": 10,
        "total_tokens": 15,
    }

    # Verify the mock API call
    mock_client_instance.chat.completions.create.assert_awaited_once()
    call_args, call_kwargs = mock_client_instance.chat.completions.create.call_args
    assert call_kwargs["model"] == model
    assert call_kwargs["messages"] == [{"role": "user", "content": prompt}]
    assert call_kwargs["temperature"] == temperature
    assert call_kwargs["max_tokens"] == max_tokens
    assert call_kwargs["stop"] == ["\n"]
    assert call_kwargs["custom_arg"] == "test_value" # Verify kwargs passthrough

@pytest.mark.asyncio
@patch("openai.AsyncOpenAI", new_callable=MagicMock)
async def test_openai_client_generate_api_error(mock_async_openai_class, openai_client):
    """Tests handling of OpenAI API errors during generation."""
    # Arrange
    mock_client_instance = AsyncMock()
    mock_async_openai_class.return_value = mock_client_instance
    mock_client_instance.chat.completions.create = AsyncMock(
        side_effect=OpenAIError("Simulated API error")
    )

    prompt = "This will fail."
    model = "gpt-4"

    # Act
    response = await openai_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "OpenAI API error: Simulated API error" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    mock_client_instance.chat.completions.create.assert_awaited_once()

@pytest.mark.asyncio
@patch("openai.AsyncOpenAI", new_callable=MagicMock)
async def test_openai_client_generate_unexpected_error(mock_async_openai_class, openai_client):
    """Tests handling of unexpected errors during generation."""
    # Arrange
    mock_client_instance = AsyncMock()
    mock_async_openai_class.return_value = mock_client_instance
    mock_client_instance.chat.completions.create = AsyncMock(
        side_effect=Exception("Something went wrong unexpectedly")
    )

    prompt = "Another failure."
    model = "gpt-3.5-turbo"

    # Act
    response = await openai_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "An unexpected error occurred: Something went wrong unexpectedly" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    mock_client_instance.chat.completions.create.assert_awaited_once()


def test_openai_client_init_missing_key(monkeypatch):
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("OPENAI_API_KEY", raising=False) # Ensure env var is not set

    # Act & Assert
    with pytest.raises(ValueError, match="OpenAI API key not provided"):
        OpenAiClient()

def test_openai_client_init_with_key_arg():
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_key_456"

    # Act
    # Use patch here to avoid actual client instantiation during test
    with patch("openai.AsyncOpenAI") as mock_async_openai_class:
        client = OpenAiClient(api_key=api_key)

    # Assert
    assert client.api_key == api_key
    mock_async_openai_class.assert_called_once_with(api_key=api_key, base_url=None)

def test_openai_client_init_with_base_url():
    """Tests initialization with a custom base URL."""
    # Arrange
    base_url = "http://localhost:8080/v1"

    # Act
    with patch("openai.AsyncOpenAI") as mock_async_openai_class:
        client = OpenAiClient(base_url=base_url) # Relies on mock_openai_api_key fixture

    # Assert
    assert client.api_key == "test_key_123" # From fixture
    mock_async_openai_class.assert_called_once_with(api_key="test_key_123", base_url=base_url)
