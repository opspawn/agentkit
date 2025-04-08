import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Need OpenAI types and errors as OpenRouter uses the OpenAI SDK format
from openai import OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from agentkit.llm_clients.openrouter_client import OpenRouterClient
from agentkit.core.interfaces.llm_client import LlmResponse

# Fixture to provide a mock API key
@pytest.fixture(autouse=True)
def mock_openrouter_api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_or_111")

# Fixture for the OpenRouterClient instance
@pytest.fixture
def openrouter_client():
    # Patch AsyncOpenAI during client instantiation for tests
    with patch("openai.AsyncOpenAI") as mock_async_openai_class:
        client = OpenRouterClient()
        # Verify it was called with OpenRouter defaults during init
        mock_async_openai_class.assert_called_once_with(
            api_key="test_key_or_111",
            base_url=OpenRouterClient.DEFAULT_BASE_URL
        )
    return client

# --- Test Cases ---

@pytest.mark.asyncio
@patch("openai.AsyncOpenAI", new_callable=MagicMock) # Mock the class used internally
async def test_openrouter_client_generate_success(mock_async_openai_class_for_test, openrouter_client):
    """Tests successful generation using the OpenRouter client."""
    # Arrange
    # We need to mock the instance *returned* by the patched class during generate
    mock_client_instance = AsyncMock()
    # Configure the client instance used within the generate method
    openrouter_client.client = mock_client_instance # Replace the client instance created in __init__

    mock_completion = ChatCompletion(
        id="or-chatcmpl-123",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="Generated text via OpenRouter.",
                    role="assistant",
                ),
            )
        ],
        created=1677652300,
        model="anthropic/claude-3-haiku-20240307", # Example OpenRouter model ID
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=12, prompt_tokens=6, total_tokens=18),
    )
    mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

    prompt = "Summarize this article."
    model = "anthropic/claude-3-haiku-20240307"
    temperature = 0.9
    max_tokens = 150

    # Act
    response = await openrouter_client.generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=["\n"],
        extra_param="or_value" # Test kwargs passthrough
    )

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "Generated text via OpenRouter."
    assert response.model_used == model
    assert response.error is None
    assert response.finish_reason == "stop"
    assert response.usage_metadata == {
        "prompt_tokens": 6,
        "completion_tokens": 12,
        "total_tokens": 18,
    }

    # Verify the mock API call
    mock_client_instance.chat.completions.create.assert_awaited_once()
    call_args, call_kwargs = mock_client_instance.chat.completions.create.call_args
    assert call_kwargs["model"] == model
    assert call_kwargs["messages"] == [{"role": "user", "content": prompt}]
    assert call_kwargs["temperature"] == temperature
    assert call_kwargs["max_tokens"] == max_tokens
    assert call_kwargs["stop"] == ["\n"]
    assert call_kwargs["extra_param"] == "or_value" # Verify kwargs passthrough

@pytest.mark.asyncio
@patch("openai.AsyncOpenAI", new_callable=MagicMock)
async def test_openrouter_client_generate_api_error(mock_async_openai_class_for_test, openrouter_client):
    """Tests handling of API errors (via OpenAI SDK) during generation."""
    # Arrange
    mock_client_instance = AsyncMock()
    openrouter_client.client = mock_client_instance
    mock_client_instance.chat.completions.create = AsyncMock(
        side_effect=OpenAIError("Simulated OpenRouter API error")
    )

    prompt = "This will fail on OpenRouter."
    model = "google/gemini-pro" # Required model

    # Act
    response = await openrouter_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "OpenRouter API error (via OpenAI SDK): Simulated OpenRouter API error" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    mock_client_instance.chat.completions.create.assert_awaited_once()

@pytest.mark.asyncio
@patch("openai.AsyncOpenAI", new_callable=MagicMock)
async def test_openrouter_client_generate_no_model(mock_async_openai_class_for_test, openrouter_client):
    """Tests that generate fails if no model is provided."""
    # Act & Assert
    with pytest.raises(ValueError, match="Model identifier is required"):
        await openrouter_client.generate(prompt="Test prompt without model", model=None)

def test_openrouter_client_init_missing_key(monkeypatch):
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False) # Ensure env var is not set

    # Act & Assert
    with pytest.raises(ValueError, match="OpenRouter API key not provided"):
        OpenRouterClient()

def test_openrouter_client_init_with_key_arg():
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_or_key_222"

    # Act
    with patch("openai.AsyncOpenAI") as mock_async_openai_class:
        client = OpenRouterClient(api_key=api_key)

    # Assert
    assert client.api_key == api_key
    mock_async_openai_class.assert_called_once_with(
        api_key=api_key,
        base_url=OpenRouterClient.DEFAULT_BASE_URL
    )

def test_openrouter_client_init_with_base_url():
    """Tests initialization with a custom base URL."""
    # Arrange
    base_url = "http://custom-openrouter-proxy/v1"

    # Act
    with patch("openai.AsyncOpenAI") as mock_async_openai_class:
        client = OpenRouterClient(base_url=base_url) # Relies on mock_openrouter_api_key fixture

    # Assert
    assert client.api_key == "test_key_or_111" # From fixture
    mock_async_openai_class.assert_called_once_with(
        api_key="test_key_or_111",
        base_url=base_url
    )
