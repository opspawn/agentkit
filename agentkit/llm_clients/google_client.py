import os
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse, GenerationConfig

from agentkit.core.interfaces.llm_client import BaseLlmClient, LlmResponse


class GoogleClient(BaseLlmClient):
    """LLM Client implementation for Google Gemini models."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the Google Gemini client.

        Args:
            api_key: Google API key. Defaults to GOOGLE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not provided or found in environment variables (GOOGLE_API_KEY).")

        genai.configure(api_key=self.api_key)
        # Note: Model is instantiated per-request in generate method

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = "gemini-pro", # Default model
        stop_sequences: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None, # Called max_output_tokens in Gemini
        **kwargs: Any
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
            # 1. Instantiate the model
            generative_model = genai.GenerativeModel(model_name=model)

            # 2. Prepare GenerationConfig
            config_params = {
                "temperature": temperature,
                # Map BaseLlmClient max_tokens to Gemini's max_output_tokens
                "max_output_tokens": max_tokens,
                "stop_sequences": stop_sequences,
                # Extract relevant kwargs for GenerationConfig
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                # candidate_count is another potential param, default is 1
            }
            # Filter out None values as GenerationConfig doesn't accept them for all fields
            filtered_config_params = {k: v for k, v in config_params.items() if v is not None}
            generation_config = GenerationConfig(**filtered_config_params)

            # 3. Call model.generate_content_async
            response = await generative_model.generate_content_async(
                contents=prompt, # Simple string prompt
                generation_config=generation_config,
                # safety_settings=... # Could add safety settings later
            )

            # 5. Map the successful response to LlmResponse
            # Gemini's finish_reason mapping (refer to google.generativeai.types.FinishReason)
            finish_reason_map = {
                0: "unspecified", # FINISH_REASON_UNSPECIFIED
                1: "stop",        # STOP
                2: "length",      # MAX_TOKENS
                3: "safety",      # SAFETY
                4: "recitation",  # RECITATION
                5: "other",       # OTHER
            }
            # Access finish_reason safely, might be complex depending on response structure
            # Assuming simple case where response.candidates[0] exists
            raw_finish_reason = 0 # Default to unspecified
            if response.candidates:
                 raw_finish_reason = response.candidates[0].finish_reason

            finish_reason = finish_reason_map.get(raw_finish_reason, "unknown")

            # Extract text content safely
            content = ""
            try:
                content = response.text
            except ValueError:
                # Handle cases where response.text might raise error (e.g., blocked prompt)
                content = f"Blocked: {response.prompt_feedback.block_reason.name}"
                finish_reason = "safety" # Override finish reason if blocked

            # Usage metadata is not directly available in the standard async response
            # It might be in response.usage_metadata but needs verification
            usage_metadata = getattr(response, 'usage_metadata', None) # Safely access if exists

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
