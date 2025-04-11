import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Need OpenAI types and errors as OpenRouter uses the OpenAI SDK format
from openai import OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice as ChatCompletionChoice # Use specific import if needed
from openai.types.completion_usage import CompletionUsage

# Import the client AFTER potential patches are applied in fixtures/tests
from agentkit.llm_clients.openrouter_client import OpenRouterClient
from agentkit.core.interfaces.llm_client import LlmResponse

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_openrouter_api_key_env(monkeypatch):
    """Fixture to provide a mock OpenRouter API key environment variable."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_or_111")

# Use patch for the AsyncOpenAI class where it's imported in the client code
@pytest.fixture
def mock_openai_for_or():
    """Fixture to mock the AsyncOpenAI class used by OpenRouterClient."""
    # Target the import within the openrouter_client module
    with patch('agentkit.llm_clients.openrouter_client.AsyncOpenAI') as mock_async_openai_class:
        # Configure the mock instance that the mocked class will return
        mock_client_instance = AsyncMock() # Use AsyncMock for the instance
        # Mock the nested structure: client.chat.completions.create
        mock_client_instance.chat = AsyncMock()
        mock_client_instance.chat.completions = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock() # Mock the create method
        mock_async_openai_class.return_value = mock_client_instance
        yield mock_async_openai_class # Yield the mocked class

@pytest.fixture
def openrouter_client(mock_openai_for_or): # Depends on the mocked AsyncOpenAI class
    """Fixture for the OpenRouterClient instance, ensuring AsyncOpenAI is mocked."""
    # Reset the mock before creating the client instance for this test
    mock_openai_for_or.reset_mock()
    # Reset the nested mock method as well
    mock_openai_for_or.return_value.chat.completions.create.reset_mock()
    client = OpenRouterClient()
    # Assert AsyncOpenAI was called with OpenRouter base URL and env var key
    mock_openai_for_or.assert_called_once_with(
        api_key="test_key_or_111",
        base_url=OpenRouterClient.DEFAULT_BASE_URL # Use class attribute for default
    )
    # Ensure the internal client is the mocked one
    assert client.client == mock_openai_for_or.return_value
    return client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_openrouter_client_generate_success(openrouter_client, mock_openai_for_or):
    """Tests successful generation using the OpenRouter client."""
    # Arrange
    # The mock instance is mock_openai_for_or.return_value
    mock_client_instance = mock_openai_for_or.return_value

    # Mock the response structure based on OpenAI's ChatCompletion object
    mock_choice = ChatCompletionChoice(
        index=0,
        message=ChatCompletionMessage(role="assistant", content="Generated text via OpenRouter."),
        finish_reason="stop"
    )
    mock_usage = CompletionUsage(prompt_tokens=6, completion_tokens=12, total_tokens=18)
    mock_completion = ChatCompletion(
        id="or-chatcmpl-123",
        choices=[mock_choice],
        created=1677652300,
        model="anthropic/claude-3-haiku-20240307", # Use the model name expected in the response
        object="chat.completion",
        usage=mock_usage
    )
    # Configure the mock create method on the client instance
    mock_client_instance.chat.completions.create.return_value = mock_completion

    prompt = "Summarize this article."
    model = "anthropic/claude-3-haiku-20240307" # Match the model used in the request
    temperature = 0.9
    max_tokens = 150
    system_prompt = "You are an OpenRouter expert." # Add system prompt

    # Act
    response = await openrouter_client.generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=["\n"],
        system_prompt=system_prompt, # Pass system prompt
        top_p=0.8 # Test other kwargs passthrough
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
    # Check messages structure including system prompt
    expected_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    assert call_kwargs["messages"] == expected_messages
    assert call_kwargs["temperature"] == temperature
    assert call_kwargs["max_tokens"] == max_tokens
    assert call_kwargs["stop"] == ["\n"] # OpenAI uses 'stop' not 'stop_sequences'
    assert call_kwargs["top_p"] == 0.8 # Verify kwargs passthrough

@pytest.mark.asyncio
async def test_openrouter_client_generate_api_error(openrouter_client, mock_openai_for_or):
    """Tests handling of API errors (via OpenAI SDK) during generation."""
    # Arrange
    mock_client_instance = mock_openai_for_or.return_value
    mock_client_instance.chat.completions.create.side_effect = OpenAIError("Simulated OpenRouter API error")

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
async def test_openrouter_client_generate_unexpected_error(openrouter_client, mock_openai_for_or):
    """Tests handling of unexpected errors during generation."""
    # Arrange
    mock_client_instance = mock_openai_for_or.return_value
    mock_client_instance.chat.completions.create.side_effect = Exception("Something else failed")

    prompt = "Trigger unexpected failure."
    model = "openai/gpt-4" # Required model

    # Act
    response = await openrouter_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    # Check for the generic error message from the client
    assert "An unexpected error occurred: Something else failed" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    mock_client_instance.chat.completions.create.assert_awaited_once()


# Use the mock_openai_for_or fixture which handles patching
def test_openrouter_client_init_missing_key(monkeypatch, mock_openai_for_or):
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False) # Ensure env var is not set
    mock_openai_for_or.reset_mock() # Reset mock since it's autoused via env var fixture

    # Act & Assert
    with pytest.raises(ValueError, match="OpenRouter API key not provided"):
        OpenRouterClient()
    mock_openai_for_or.assert_not_called() # Ensure constructor wasn't called

# Use the mock_openai_for_or fixture which handles patching
def test_openrouter_client_init_with_key_arg(mock_openai_for_or):
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_or_key_222"
    mock_openai_for_or.reset_mock() # Reset mock before test

    # Act
    client = OpenRouterClient(api_key=api_key)

    # Assert
    assert client.api_key == api_key
    # Check that the *mocked* AsyncOpenAI class was called correctly
    mock_openai_for_or.assert_called_once_with(
        api_key=api_key,
        base_url=OpenRouterClient.DEFAULT_BASE_URL
    )
    assert client.client == mock_openai_for_or.return_value # Check internal client

# Use the mock_openai_for_or fixture which handles patching
def test_openrouter_client_init_with_base_url(mock_openai_for_or):
    """Tests initialization with a custom base URL."""
    # Arrange
    base_url = "http://custom-openrouter-proxy/v1"
    api_key_from_env = "test_key_or_111" # From mock_openrouter_api_key_env
    mock_openai_for_or.reset_mock() # Reset mock before test

    # Act
    client = OpenRouterClient(base_url=base_url) # Relies on env var fixture for key

    # Assert
    assert client.api_key == api_key_from_env # From fixture
    # Check that the *mocked* AsyncOpenAI class was called correctly
    mock_openai_for_or.assert_called_once_with(
        api_key=api_key_from_env,
        base_url=base_url
    )
    assert client.client == mock_openai_for_or.return_value # Check internal client
