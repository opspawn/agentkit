import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock

# Mock the NEW google.genai module before it's imported by the client
google_mock = MagicMock()
google_mock.genai = MagicMock()
google_mock.genai.Client = MagicMock() # Mock the Client class
google_mock.genai.types = MagicMock() # Mock types too

# Apply the mock to the sys.modules cache
import sys
sys.modules['google'] = google_mock
sys.modules['google.genai'] = google_mock.genai
# sys.modules['google.genai.types'] = google_mock.genai.types # Already mocked above

# Now import the client which will use the mocked genai
from agentkit.llm_clients.google_client import GoogleClient
from agentkit.core.interfaces.llm_client import LlmResponse
# Import the aliased types from the client module if needed, or mock directly
# from agentkit.llm_clients.google_client import genai_types # This won't work as genai is mocked
genai_types_mock = google_mock.genai.types # Use the mocked types

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_google_api_key(monkeypatch):
    """Fixture to provide a mock Google API key environment variable."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_789")
    # Reset the Client mock for each test
    google_mock.genai.Client.reset_mock()

@pytest.fixture
def mock_genai_client_instance():
    """Fixture for the mocked genai.Client() instance."""
    mock_instance = MagicMock()
    mock_instance.models = MagicMock()
    # Mock the generate_content method (assuming it needs to be async based on BaseLlmClient)
    mock_instance.models.generate_content = AsyncMock()
    google_mock.genai.Client.return_value = mock_instance
    return mock_instance

@pytest.fixture
def google_client(mock_genai_client_instance): # Depends on the mocked instance
    """Fixture for the GoogleClient instance."""
    # Client initialization now calls genai.Client()
    client = GoogleClient()
    # Assert Client was called (without args, relying on env var)
    google_mock.genai.Client.assert_called_once_with()
    # Ensure the internal client is the mocked one
    assert client.client == mock_genai_client_instance
    return client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_google_client_generate_success(google_client, mock_genai_client_instance):
    """Tests successful generation using the Google client."""
    # Arrange
    # Mock the response structure from client.models.generate_content
    mock_response = MagicMock()
    type(mock_response).text = PropertyMock(return_value="Generated Google text.")
    # Mock candidates and finish_reason (using string/enum name based on new SDK assumption)
    mock_candidate = MagicMock()
    # Let's assume the new SDK returns the reason as an enum or string directly
    type(mock_candidate).finish_reason = PropertyMock(return_value="STOP") # Or maybe genai_types.FinishReason.STOP
    mock_response.candidates = [mock_candidate]
    # Mock usage metadata
    mock_response.usage_metadata = {"prompt_token_count": 10, "candidates_token_count": 20, "total_token_count": 30}

    # Configure the mock generate_content method on the client instance
    mock_genai_client_instance.models.generate_content.return_value = mock_response

    prompt = "Explain Gemini."
    model = "gemini-1.5-pro-latest" # Model name without prefix for input
    temperature = 0.8
    max_tokens = 200

    # Act
    response = await google_client.generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=["\n\n"],
        top_p=0.9 # Test kwargs passthrough
    )

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "Generated Google text."
    assert response.model_used == model
    assert response.error is None
    assert response.finish_reason == "stop" # Mapped from 1
    assert response.usage_metadata == {"prompt_token_count": 10, "candidates_token_count": 20, "total_token_count": 30}

    # Verify the mock API call to the new client method
    # Note: generate() is async, but the mocked generate_content might be called synchronously
    # depending on how the SDK/mocking works. Let's assume await is needed.
    # If generate_content is sync, use assert_called_once_with
    mock_genai_client_instance.models.generate_content.assert_called_once() # Use assert_called_once if sync
    call_args, call_kwargs = mock_genai_client_instance.models.generate_content.call_args

    assert call_kwargs["model"] == f"models/{model}" # Check prefix added
    assert call_kwargs["contents"] == prompt
    gen_config = call_kwargs["generation_config"]
    # Access attributes of the mocked GenerationConfig
    assert gen_config.temperature == temperature
    assert gen_config.max_output_tokens == max_tokens
    assert gen_config.stop_sequences == ["\n\n"]
    assert gen_config.top_p == 0.9

@pytest.mark.asyncio
async def test_google_client_generate_api_error(google_client, mock_genai_client_instance):
    """Tests handling of Google API errors during generation."""
    # Arrange
    # Configure the mock generate_content method to raise an error
    mock_genai_client_instance.models.generate_content.side_effect = Exception("Simulated Google API error")

    prompt = "This will cause a Google error."
    model = "gemini-pro" # Model name without prefix

    # Act
    response = await google_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "Google Gemini API error: Simulated Google API error" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    # Check the new mock was called
    mock_genai_client_instance.models.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_google_client_generate_blocked_prompt(google_client, mock_genai_client_instance):
    """Tests handling of a blocked prompt response."""
    # Arrange
    # Mock the response structure for a blocked prompt
    mock_response = MagicMock()
    # Mock response.text to raise ValueError
    type(mock_response).text = PropertyMock(side_effect=ValueError("Content blocked"))
    # Mock prompt feedback structure (adjust based on actual new SDK structure if needed)
    mock_feedback = MagicMock()
    type(mock_feedback).block_reason = PropertyMock()
    type(mock_feedback.block_reason).name = PropertyMock(return_value="SAFETY") # Example
    type(mock_response).prompt_feedback = PropertyMock(return_value=mock_feedback)
    mock_response.candidates = [] # No candidates

    # Configure the mock generate_content method
    mock_genai_client_instance.models.generate_content.return_value = mock_response

    prompt = "A potentially unsafe prompt."
    model = "gemini-pro" # Model name without prefix

    # Act
    response = await google_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "Blocked: SAFETY"
    assert response.model_used == model
    assert response.error is None # Not an API error, but a safety block
    assert response.finish_reason == "safety" # Overridden due to block
    assert response.usage_metadata is None
    # Check the new mock was called
    mock_genai_client_instance.models.generate_content.assert_called_once()


def test_google_client_init_missing_key(monkeypatch, mock_genai_client_instance): # Add mock instance fixture
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False) # Ensure env var is not set
    google_mock.genai.Client.reset_mock() # Reset mock before test

    # Act & Assert
    with pytest.raises(ValueError, match="Google API key not provided"):
        GoogleClient()
    # Ensure Client wasn't called without a key if env var is missing
    google_mock.genai.Client.assert_not_called()


def test_google_client_init_with_key_arg(mock_genai_client_instance): # Add mock instance fixture
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_google_key_123"
    google_mock.genai.Client.reset_mock() # Reset mock before test

    # Act
    client = GoogleClient(api_key=api_key)

    # Assert
    # Check that genai.Client was called with the arg key
    google_mock.genai.Client.assert_called_once_with(api_key=api_key)
    # Check internal client is the mocked one
    assert client.client == mock_genai_client_instance
