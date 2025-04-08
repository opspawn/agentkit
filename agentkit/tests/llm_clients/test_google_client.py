import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock

# Import the client AFTER potential patches are applied in fixtures/tests
from agentkit.llm_clients.google_client import GoogleClient
from agentkit.core.interfaces.llm_client import LlmResponse

# --- Fixtures ---

@pytest.fixture(autouse=True)
def mock_google_api_key_env(monkeypatch):
    """Fixture to provide a mock Google API key environment variable."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_789")

# Use patch for the genai module and genai_types alias where they are imported
@pytest.fixture
def mock_genai_and_types():
    """Fixture to mock 'genai' and 'genai_types' used by GoogleClient."""
    # Patch both the main module and the aliased types import
    with patch('agentkit.llm_clients.google_client.genai') as mock_genai_module, \
         patch('agentkit.llm_clients.google_client.genai_types') as mock_genai_types_module:

        # Configure the mock Client class within the mocked genai module
        mock_client_instance = MagicMock()
        mock_client_instance.models = MagicMock()
        # Use MagicMock assuming the underlying SDK call is synchronous
        mock_client_instance.models.generate_content = MagicMock()
        mock_genai_module.Client.return_value = mock_client_instance

        # Configure the GenerationConfig mock on the *patched types module*
        mock_genai_types_module.GenerationConfig = MagicMock()

        # Yield both mocks if needed, or just the primary one if types is only used internally
        yield mock_genai_module, mock_genai_types_module

@pytest.fixture
def google_client(mock_genai_and_types): # Depends on the mocked modules
    """Fixture for the GoogleClient instance, ensuring genai and types are mocked."""
    mock_genai, mock_genai_types = mock_genai_and_types
    # Reset the mock before creating the client instance for this test
    mock_genai.Client.reset_mock()
    mock_genai_types.GenerationConfig.reset_mock() # Also reset this mock
    client = GoogleClient()
    # Assert Client was called (without args, relying on env var)
    mock_genai.Client.assert_called_once_with()
    # Ensure the internal client is the mocked one
    assert client.client == mock_genai.Client.return_value
    return client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_google_client_generate_success(google_client, mock_genai_and_types):
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

    mock_genai, mock_genai_types = mock_genai_and_types
    # Configure the mock generate_content method on the client instance
    # The client instance is mock_genai.Client.return_value
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

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
    mock_genai.Client.return_value.models.generate_content.assert_called_once()
    call_args, call_kwargs = mock_genai.Client.return_value.models.generate_content.call_args

    assert call_kwargs["model"] == f"models/{model}" # Check prefix added
    assert call_kwargs["contents"] == prompt
    # Access the mocked GenerationConfig used in the call
    # Verify GenerationConfig was called correctly using the *patched types mock*
    mock_genai_types.GenerationConfig.assert_called_once()
    config_call_args, config_call_kwargs = mock_genai_types.GenerationConfig.call_args
    assert config_call_kwargs["temperature"] == temperature
    assert config_call_kwargs["max_output_tokens"] == max_tokens
    assert config_call_kwargs["stop_sequences"] == ["\n\n"]
    assert config_call_kwargs["top_p"] == 0.9
    # Assert the config instance passed to generate_content was the one returned by the mocked constructor
    assert call_kwargs["generation_config"] == mock_genai_types.GenerationConfig.return_value


@pytest.mark.asyncio
async def test_google_client_generate_api_error(google_client, mock_genai_and_types):
    """Tests handling of Google API errors during generation."""
    # Arrange
    mock_genai, _ = mock_genai_and_types # Only need genai mock here
    # Configure the mock generate_content method to raise an error
    mock_genai.Client.return_value.models.generate_content.side_effect = Exception("Simulated Google API error")

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
    mock_genai.Client.return_value.models.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_google_client_generate_blocked_prompt(google_client, mock_genai_and_types):
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

    mock_genai, _ = mock_genai_and_types # Only need genai mock here
    # Configure the mock generate_content method
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    # --- Debug: Verify PropertyMock raises error ---
    with pytest.raises(ValueError, match="Content blocked"):
        _ = mock_response.text
    # --- End Debug ---

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
    mock_genai.Client.return_value.models.generate_content.assert_called_once()


# Use the mock_genai_and_types fixture which handles patching
def test_google_client_init_missing_key(monkeypatch, mock_genai_and_types):
    """Tests that initialization fails if the API key is missing."""
    mock_genai, _ = mock_genai_and_types
    # Arrange
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False) # Ensure env var is not set
    mock_genai.Client.reset_mock() # Reset mock before test

    # Act & Assert
    with pytest.raises(ValueError, match="Google API key not provided"):
        GoogleClient()
    # Ensure Client wasn't called without a key if env var is missing
    mock_genai.Client.assert_not_called()


# Use the mock_genai_and_types fixture which handles patching
def test_google_client_init_with_key_arg(mock_genai_and_types):
    """Tests initialization with the API key passed as an argument."""
    mock_genai, _ = mock_genai_and_types
    # Arrange
    api_key = "arg_google_key_123"
    mock_genai.Client.reset_mock() # Reset mock before test

    # Act
    client = GoogleClient(api_key=api_key)

    # Assert
    # Check that genai.Client was called with the arg key
    mock_genai.Client.assert_called_once_with(api_key=api_key)
    # Check internal client is the mocked one
    assert client.client == mock_genai.Client.return_value
