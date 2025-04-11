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
        # Mock the async interface 'aio' and its 'models' attribute
        mock_client_instance.aio = MagicMock()
        mock_client_instance.aio.models = MagicMock()
        # Mock the async generate_content method
        mock_client_instance.aio.models.generate_content = AsyncMock() # Use AsyncMock
        mock_genai_module.Client.return_value = mock_client_instance

        # Configure the GenerationConfig mock on the *patched types module*
        # Add the __annotations__ attribute that the client code expects
        mock_config_constructor = MagicMock()
        mock_config_constructor.__annotations__ = {} # Add expected attribute
        mock_genai_types_module.GenerationConfig = mock_config_constructor
        # Mock Content and Part types used for constructing the 'contents' argument
        mock_genai_types_module.Content = MagicMock()
        mock_genai_types_module.Part = MagicMock()
        mock_genai_types_module.Part.from_text = MagicMock()

        # Yield both mocks
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

# Removed xfail marker again to capture debug output
@pytest.mark.asyncio
async def test_google_client_generate_success(google_client, mock_genai_and_types):
    """Tests successful generation using the Google client."""
    # Arrange
    mock_genai, mock_genai_types = mock_genai_and_types

    # Define the expected LlmResponse object that the client's generate method should return
    expected_llm_response = LlmResponse(
        content="Generated Google text.",
        model_used="gemini-1.5-pro-latest",
        usage_metadata={"prompt_token_count": 10, "candidates_token_count": 20, "total_token_count": 30},
        finish_reason="stop",
        error=None,
    )

    # Mock the SDK's generate_content method to return an object that, when processed by the client,
    # results in the expected_llm_response. We need a mock SDK response that has the necessary attributes
    # for the client code to extract the data.

    # Mock the nested structure that response.text likely relies on
    mock_part = MagicMock()
    mock_part.text = "Generated Google text." # Set the text on the part

    mock_content = MagicMock()
    mock_content.parts = [mock_part]

    mock_candidate = MagicMock()
    mock_candidate.content = mock_content
    # Revert to PropertyMock for finish_reason as direct assignment didn't help
    type(mock_candidate).finish_reason = PropertyMock(return_value="STOP")

    mock_sdk_response = MagicMock()
    # Mock the underlying structure
    mock_sdk_response.candidates = [mock_candidate]
    mock_sdk_response.usage_metadata = {"prompt_token_count": 10, "candidates_token_count": 20, "total_token_count": 30}

    # Revert to PropertyMock for .text, aligning with documentation/intent
    type(mock_sdk_response).text = PropertyMock(return_value="Generated Google text.")

    # Configure the mock aio.models.generate_content method to return this mock SDK response
    mock_genai.Client.return_value.aio.models.generate_content.return_value = mock_sdk_response

    # Define input messages list
    messages = [{"role": "user", "content": "Explain Gemini."}]
    system_prompt = "Be concise."
    model = "gemini-1.5-pro-latest" # Model name without prefix for input
    temperature = 0.8
    max_tokens = 200

    # Mock the return value of the Part factory
    mock_part_instance = MagicMock()
    mock_genai_types.Part.from_text.return_value = mock_part_instance
    # Mock the return value of the Content constructor
    mock_content_instance = MagicMock()
    mock_genai_types.Content.return_value = mock_content_instance


    # Act
    response = await google_client.generate(
        messages=messages, # Pass messages list
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=["\n\n"],
        top_p=0.9, # Test kwargs passthrough
        system_prompt=system_prompt # Pass system prompt via kwargs
    )

    # Assert - Compare individual fields instead of the whole object
    assert isinstance(response, LlmResponse)
    assert response.content == expected_llm_response.content, f"Content mismatch: Expected '{expected_llm_response.content}', got '{response.content}'"
    assert response.model_used == expected_llm_response.model_used
    assert response.usage_metadata == expected_llm_response.usage_metadata
    assert response.finish_reason == expected_llm_response.finish_reason
    assert response.error == expected_llm_response.error

    # Verify the mock API call to the async method
    mock_genai.Client.return_value.aio.models.generate_content.assert_awaited_once() # Use assert_awaited_once
    call_args, call_kwargs = mock_genai.Client.return_value.aio.models.generate_content.call_args

    assert call_kwargs["model"] == f"models/{model}" # Check prefix added

    # Verify the 'contents' argument structure
    # Check that Part.from_text was called with the correct content
    mock_genai_types.Part.from_text.assert_called_once_with(messages[0]["content"])
    # Check that Content was called with the correct role and the mocked part
    mock_genai_types.Content.assert_called_once_with(role=messages[0]["role"], parts=[mock_part_instance])
    # Check that the list passed to generate_content contains the mocked Content instance
    assert call_kwargs["contents"] == [mock_content_instance]

    # Verify GenerationConfig was called correctly using the *patched types mock*
    mock_genai_types.GenerationConfig.assert_called_once()
    config_call_args, config_call_kwargs = mock_genai_types.GenerationConfig.call_args
    assert config_call_kwargs["temperature"] == temperature
    assert config_call_kwargs["max_output_tokens"] == max_tokens
    assert config_call_kwargs["stop_sequences"] == ["\n\n"]
    assert config_call_kwargs["top_p"] == 0.9
    assert config_call_kwargs["system_instruction"] == system_prompt # Check system prompt
    # Assert the config instance passed to generate_content was the one returned by the mocked constructor
    assert call_kwargs["generation_config"] == mock_genai_types.GenerationConfig.return_value


@pytest.mark.asyncio
async def test_google_client_generate_api_error(google_client, mock_genai_and_types):
    """Tests handling of Google API errors during generation."""
    # Arrange
    mock_genai, _ = mock_genai_and_types # Only need genai mock here
    # Configure the mock async generate_content method to raise an error
    mock_genai.Client.return_value.aio.models.generate_content.side_effect = Exception("Simulated Google API error")

    messages = [{"role": "user", "content": "This will cause a Google error."}] # Use messages list
    model = "gemini-pro" # Model name without prefix

    # Act
    response = await google_client.generate(messages=messages, model=model) # Pass messages

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == ""
    assert response.model_used == model
    assert "Google Gemini API error: Simulated Google API error" in response.error
    assert response.usage_metadata is None
    assert response.finish_reason is None
    # Check the async mock was called
    mock_genai.Client.return_value.aio.models.generate_content.assert_awaited_once() # Use assert_awaited_once

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
    # Configure the mock async generate_content method
    mock_genai.Client.return_value.aio.models.generate_content.return_value = mock_response

    # --- Debug: Verify PropertyMock raises error ---
    with pytest.raises(ValueError, match="Content blocked"):
        _ = mock_response.text
    # --- End Debug ---

    messages = [{"role": "user", "content": "A potentially unsafe prompt."}] # Use messages list
    model = "gemini-pro" # Model name without prefix

    # Act
    response = await google_client.generate(messages=messages, model=model) # Pass messages

    # Assert
    assert isinstance(response, LlmResponse)
    assert response.content == "Blocked: SAFETY"
    assert response.model_used == model
    assert response.error is None # Not an API error, but a safety block
    assert response.finish_reason == "safety" # Overridden due to block
    assert response.usage_metadata is None
    # Check the async mock was called
    mock_genai.Client.return_value.aio.models.generate_content.assert_awaited_once() # Use assert_awaited_once


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
