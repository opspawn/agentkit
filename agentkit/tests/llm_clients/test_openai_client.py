import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Import necessary types from the real library for type hinting if needed
# but the library itself will be mocked during tests.
from openai import OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
# Use the specific Choice class path if needed, or rely on mock structure
from openai.types.chat.chat_completion import Choice as ChatCompletionChoice
from openai.types.completion_usage import CompletionUsage

# Import the client AFTER potential patches are applied in fixtures/tests
from agentkit.llm_clients.openai_client import OpenAiClient
from agentkit.core.interfaces.llm_client import LlmResponse

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_openai_api_key_env(monkeypatch):
    """Fixture to provide a mock OpenAI API key environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_123")

# Use patch for the AsyncOpenAI class where it's imported in the client code
@pytest.fixture
def mock_openai():
    """Fixture to mock the AsyncOpenAI class used by OpenAiClient."""
    with patch('agentkit.llm_clients.openai_client.AsyncOpenAI') as mock_async_openai_class:
        # Configure the mock instance that the mocked class will return
        mock_client_instance = AsyncMock() # Use AsyncMock for the instance
        # Mock the nested structure: client.chat.completions.create
        mock_client_instance.chat = AsyncMock()
        mock_client_instance.chat.completions = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock() # Mock the create method
        mock_async_openai_class.return_value = mock_client_instance
        yield mock_async_openai_class # Yield the mocked class

@pytest.fixture
def openai_client(mock_openai): # Depends on the mocked AsyncOpenAI class
    """Fixture for the OpenAiClient instance, ensuring AsyncOpenAI is mocked."""
    # Reset the mock before creating the client instance for this test
    mock_openai.reset_mock()
    # Reset the nested mock method as well
    mock_openai.return_value.chat.completions.create.reset_mock()
    client = OpenAiClient()
    # Assert AsyncOpenAI was called (without args, relying on env var)
    mock_openai.assert_called_once_with(api_key="test_key_123", base_url=None)
    # Ensure the internal client is the mocked one
    assert client.client == mock_openai.return_value
    return client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_openai_client_generate_success(openai_client, mock_openai):
    """Tests successful generation using the OpenAI client."""
    # Arrange
    # The mock instance is mock_openai.return_value
    mock_client_instance = mock_openai.return_value

    # Mock the response structure based on OpenAI's ChatCompletion object
    # Use the imported Choice class or rely on MagicMock structure
    mock_choice = ChatCompletionChoice(
        index=0,
        message=ChatCompletionMessage(role="assistant", content="This is the generated text."),
        finish_reason="stop"
    )
    mock_usage = CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    mock_completion = ChatCompletion(
        id="chatcmpl-123",
        choices=[mock_choice],
        created=1677652288,
        model="gpt-4", # Use the model name expected in the response
        object="chat.completion",
        usage=mock_usage
    )
    # Configure the mock create method on the client instance
    mock_client_instance.chat.completions.create.return_value = mock_completion

    prompt = "Tell me a story."
    model = "gpt-4" # Match the model used in the request
    temperature = 0.5
    max_tokens = 150
    system_prompt = "You are a tech expert." # Add system prompt

    # Act
    response = await openai_client.generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=["\n"],
        system_prompt=system_prompt, # Pass system prompt
        top_p=0.9 # Test other kwargs passthrough
    )

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "This is the generated text."
    assert response.model_used == "gpt-4" # Assert correct model
    assert response.error is None
    assert response.finish_reason == "stop"
    assert response.usage_metadata == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
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
    assert call_kwargs["top_p"] == 0.9 # Verify kwargs passthrough

@pytest.mark.asyncio
async def test_openai_client_generate_api_error(openai_client, mock_openai):
    """Tests handling of OpenAI API errors during generation."""
    # Arrange
    mock_client_instance = mock_openai.return_value
    mock_client_instance.chat.completions.create.side_effect = OpenAIError("Simulated API error")

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
async def test_openai_client_generate_unexpected_error(openai_client, mock_openai):
    """Tests handling of unexpected errors during generation."""
    # Arrange
    mock_client_instance = mock_openai.return_value
    mock_client_instance.chat.completions.create.side_effect = Exception("Something went wrong unexpectedly")

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

# Use the mock_openai fixture which handles patching
def test_openai_client_init_missing_key(monkeypatch, mock_openai):
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("OPENAI_API_KEY", raising=False) # Ensure env var is not set
    mock_openai.reset_mock() # Reset mock since it's autoused via env var fixture

    # Act & Assert
    with pytest.raises(ValueError, match="OpenAI API key not provided"):
        OpenAiClient()
    mock_openai.assert_not_called() # Ensure constructor wasn't called

# Use the mock_openai fixture which handles patching
def test_openai_client_init_with_key_arg(mock_openai):
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_key_456"
    mock_openai.reset_mock() # Reset mock before test

    # Act
    client = OpenAiClient(api_key=api_key)

    # Assert
    assert client.api_key == api_key
    # Check that the *mocked* AsyncOpenAI class was called correctly
    mock_openai.assert_called_once_with(api_key=api_key, base_url=None)
    assert client.client == mock_openai.return_value # Check internal client

# Use the mock_openai fixture which handles patching
def test_openai_client_init_with_base_url(mock_openai):
    """Tests initialization with a custom base URL."""
    # Arrange
    base_url = "http://localhost:8080/v1"
    api_key_from_env = "test_key_123" # From mock_openai_api_key_env
    mock_openai.reset_mock() # Reset mock before test

    # Act
    client = OpenAiClient(base_url=base_url) # Relies on env var fixture for key

    # Assert
    assert client.api_key == api_key_from_env # From fixture
    # Check that the *mocked* AsyncOpenAI class was called correctly
    mock_openai.assert_called_once_with(api_key=api_key_from_env, base_url=base_url)
    assert client.client == mock_openai.return_value # Check internal client
