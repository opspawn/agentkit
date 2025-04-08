import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock

# Mock the google.generativeai module before it's imported by the client
# This is crucial because genai.configure is called at the module level upon import
# if the client module were imported first.
google_mock = MagicMock()
google_mock.generativeai = MagicMock()
google_mock.generativeai.configure = MagicMock()
google_mock.generativeai.GenerativeModel = MagicMock()

# Apply the mock to the sys.modules cache
import sys
sys.modules['google'] = google_mock
sys.modules['google.generativeai'] = google_mock.generativeai
sys.modules['google.generativeai.types'] = MagicMock() # Mock types too

# Now import the client which will use the mocked genai
from agentkit.llm_clients.google_client import GoogleClient
from agentkit.core.interfaces.llm_client import LlmResponse

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_google_api_key(monkeypatch):
    """Fixture to provide a mock Google API key environment variable."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_789")
    # Reset the configure mock for each test to ensure isolation
    google_mock.generativeai.configure.reset_mock()

@pytest.fixture
def google_client():
    """Fixture for the GoogleClient instance."""
    # The client initialization calls genai.configure, which is mocked
    client = GoogleClient()
    # Assert configure was called during init
    google_mock.generativeai.configure.assert_called_once_with(api_key="test_google_key_789")
    return client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_google_client_generate_success(google_client):
    """Tests successful generation using the Google client."""
    # Arrange
    mock_model_instance = AsyncMock()
    google_mock.generativeai.GenerativeModel.return_value = mock_model_instance

    # Mock the response structure from generate_content_async
    mock_response = AsyncMock()
    # Use PropertyMock for attributes like 'text' that might raise errors
    type(mock_response).text = PropertyMock(return_value="Generated Google text.")
    # Mock candidates and finish_reason (assuming successful stop)
    mock_candidate = MagicMock()
    mock_candidate.finish_reason = 1 # FINISH_REASON_STOP
    mock_response.candidates = [mock_candidate]
    # Mock usage metadata (if available, otherwise None)
    mock_response.usage_metadata = {"prompt_token_count": 10, "candidates_token_count": 20, "total_token_count": 30}

    mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response)

    prompt = "Explain Gemini."
    model = "gemini-1.5-pro-latest"
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

    # Verify the mock API call
    google_mock.generativeai.GenerativeModel.assert_called_once_with(model_name=model)
    mock_model_instance.generate_content_async.assert_awaited_once()
    call_args, call_kwargs = mock_model_instance.generate_content_async.call_args
    assert call_kwargs["contents"] == prompt
    gen_config = call_kwargs["generation_config"]
    assert gen_config.temperature == temperature
    assert gen_config.max_output_tokens == max_tokens
    assert gen_config.stop_sequences == ["\n\n"]
    assert gen_config.top_p == 0.9 # Verify kwargs passthrough

@pytest.mark.asyncio
async def test_google_client_generate_api_error(google_client):
    """Tests handling of Google API errors during generation."""
    # Arrange
    mock_model_instance = AsyncMock()
    google_mock.generativeai.GenerativeModel.return_value = mock_model_instance
    mock_model_instance.generate_content_async = AsyncMock(
        side_effect=Exception("Simulated Google API error") # Use generic Exception for now
    )

    prompt = "This will cause a Google error."
    model = "gemini-pro"

    # Act
    response = await google_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "Google Gemini API error: Simulated Google API error" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    mock_model_instance.generate_content_async.assert_awaited_once()

@pytest.mark.asyncio
async def test_google_client_generate_blocked_prompt(google_client):
    """Tests handling of a blocked prompt response."""
    # Arrange
    mock_model_instance = AsyncMock()
    google_mock.generativeai.GenerativeModel.return_value = mock_model_instance

    mock_response = AsyncMock()
    # Mock response.text to raise ValueError, simulating blocked content
    type(mock_response).text = PropertyMock(side_effect=ValueError("Content blocked"))
    # Mock prompt feedback
    mock_feedback = MagicMock()
    mock_feedback.block_reason.name = "SAFETY"
    mock_response.prompt_feedback = mock_feedback
    mock_response.candidates = [] # No candidates when blocked

    mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response)

    prompt = "A potentially unsafe prompt."
    model = "gemini-pro"

    # Act
    response = await google_client.generate(prompt=prompt, model=model)

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "Blocked: SAFETY"
    assert response.model_used == model
    assert response.error is None # Not an API error, but a safety block
    assert response.finish_reason == "safety" # Overridden due to block
    assert response.usage_metadata is None
    mock_model_instance.generate_content_async.assert_awaited_once()


def test_google_client_init_missing_key(monkeypatch):
    """Tests that initialization fails if the API key is missing."""
    # Arrange
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False) # Ensure env var is not set

    # Act & Assert
    with pytest.raises(ValueError, match="Google API key not provided"):
        GoogleClient()
    # Ensure configure wasn't called without a key
    google_mock.generativeai.configure.assert_not_called()


def test_google_client_init_with_key_arg():
    """Tests initialization with the API key passed as an argument."""
    # Arrange
    api_key = "arg_google_key_123"

    # Act
    client = GoogleClient(api_key=api_key)

    # Assert
    assert client.api_key == api_key
    # Check that genai.configure was called with the arg key
    google_mock.generativeai.configure.assert_called_once_with(api_key=api_key)
