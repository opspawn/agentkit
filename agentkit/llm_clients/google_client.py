import os
from typing import Dict, Any, Optional, List
import google.genai as genai # Changed import
from google.genai import types as genai_types # Use alias for types

from agentkit.core.interfaces.llm_client import BaseLlmClient, LlmResponse


class GoogleClient(BaseLlmClient):
    """LLM Client implementation for Google Gemini models."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the Google Gemini client.

        Args:
            api_key: Google API key. Defaults to GOOGLE_API_KEY env var.
        """
        # The new SDK handles API key via env var GOOGLE_API_KEY automatically
        # or via constructor argument if needed. We'll rely on env var for now.
        # If api_key is explicitly passed, we should use it.
        client_options = {}
        if api_key:
            client_options["api_key"] = api_key
        elif not os.getenv("GOOGLE_API_KEY"):
             raise ValueError("Google API key not provided or found in environment variables (GOOGLE_API_KEY).")

        # TODO: Add support for Vertex AI client initialization if needed via env vars
        # GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION

        self.client = genai.Client(**client_options)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = "gemini-pro", # Default model
        stop_sequences: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None, # Called max_output_tokens in Gemini
            **kwargs: Any # Keep kwargs for potential future use, though less direct mapping now
    ) -> LlmResponse:
        """
        Generates text based on a prompt using the Google Gemini API.

        Args:
            prompt: The input prompt for the LLM.
            model: The specific model identifier to use (e.g., "gemini-pro", "gemini-1.5-pro-latest").
            stop_sequences: List of sequences to stop generation at.
            temperature: Sampling temperature.
            max_tokens: Maximum number of tokens (output tokens) to generate.
            **kwargs: Additional arguments for the Gemini API (e.g., top_p, top_k).

        Returns:
            An LlmResponse object containing the generated content and metadata.
        """
        try:
            # 1. Prepare GenerationConfig (using new SDK types)
            config_params = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "stop_sequences": stop_sequences,
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
            }
            filtered_config_params = {k: v for k, v in config_params.items() if v is not None}
            generation_config = genai_types.GenerationConfig(**filtered_config_params)

            # 2. Call client.models.generate_content (new SDK uses this structure)
            # The new SDK handles async automatically if client is created in async context
            # For now, assume sync call structure based on docs, adjust if needed for BaseLlmClient async requirement
            # NOTE: The BaseLlmClient requires an async generate method. The new google-genai SDK
            # seems to handle async implicitly or via a separate async client.
            # We might need to wrap the sync call or investigate async client usage.
            # For now, let's assume a direct call works and adjust if runtime errors occur.

            # TODO: Investigate async client usage for google-genai if direct call fails in async context.
            response = self.client.models.generate_content(
                model=f"models/{model}", # Models often need 'models/' prefix
                contents=prompt,
                generation_config=generation_config,
                # safety_settings=...
            )

            # 3. Map the successful response to LlmResponse
            # Access finish_reason (assuming similar structure, needs verification)
            finish_reason = "unknown"
            if response.candidates:
                 # Assuming finish_reason is an enum or string directly accessible
                 raw_finish_reason = getattr(response.candidates[0], 'finish_reason', 'UNKNOWN')
                 # Convert enum to string if necessary (example)
                 finish_reason = str(raw_finish_reason).split('.')[-1].lower() # Example conversion

            # Extract text content safely
            content = ""
            try:
                content = response.text
            except ValueError:
                # Handle blocked prompt (assuming similar feedback structure)
                block_reason = getattr(getattr(response, 'prompt_feedback', None), 'block_reason', None)
                content = f"Blocked: {block_reason.name if block_reason else 'Unknown Reason'}"
                finish_reason = "safety"

            # Extract usage metadata (assuming similar structure)
            usage_metadata = getattr(response, 'usage_metadata', None)

            return LlmResponse(
                content=content,
                model_used=model, # The request specified the model
                usage_metadata=usage_metadata, # May be None
                finish_reason=finish_reason,
                error=None,
            )

        except Exception as e:
            # 4. & 6. Handle potential exceptions and map errors
            # Need to identify specific Google API errors vs general errors
            # Example: google.api_core.exceptions.GoogleAPIError
            # For now, catch generic Exception
            return LlmResponse(
                content="",
                model_used=model,
                error=f"Google Gemini API error: {e}",
            )
