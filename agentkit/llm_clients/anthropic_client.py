import os
from typing import Dict, Any, Optional, List

from anthropic import AsyncAnthropic, AnthropicError

from agentkit.core.interfaces.llm_client import BaseLlmClient, LlmResponse


class AnthropicClient(BaseLlmClient):
    """LLM Client implementation for Anthropic models."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initializes the Anthropic client.

        Args:
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
            base_url: Anthropic API base URL. Defaults to Anthropic's default.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided or found in environment variables (ANTHROPIC_API_KEY).")

        # Note: Anthropic SDK uses base_url parameter differently if needed
        self.client = AsyncAnthropic(api_key=self.api_key, base_url=base_url)
        # TODO: Add more robust initialization if needed

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = "claude-3-opus-20240229", # Default model
        stop_sequences: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1024, # Anthropic requires max_tokens
        **kwargs: Any
    ) -> LlmResponse:
        """
        Generates text based on a prompt using the Anthropic API.

        Args:
            prompt: The input prompt for the LLM. Assumed to be the user message.
                    System prompts can be passed via kwargs['system_prompt'].
            model: The specific model identifier to use (e.g., "claude-3-opus-20240229").
            stop_sequences: List of sequences to stop generation at.
            temperature: Sampling temperature.
            max_tokens: Maximum number of tokens to generate. Required by Anthropic.
            **kwargs: Additional arguments for the Anthropic API (e.g., top_p, top_k, system_prompt).

        Returns:
            An LlmResponse object containing the generated content and metadata.
        """
        if max_tokens is None:
             # Anthropic API requires max_tokens, setting a default if not provided
             max_tokens = 1024
             # Consider logging a warning here

        # 1. Format the prompt into the required 'messages' structure (user role).
        messages = [{"role": "user", "content": prompt}]

        # 2. Extract system_prompt from kwargs if present.
        system_prompt = kwargs.pop("system_prompt", None)

        # 3. Prepare API parameters
        api_params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens, # Required by Anthropic
            "temperature": temperature,
            "stop_sequences": stop_sequences,
            **kwargs, # Pass through any additional provider-specific args (e.g., top_p, top_k)
        }
        if system_prompt:
            api_params["system"] = system_prompt

        try:
            # 4. Call self.client.messages.create(...)
            response = await self.client.messages.create(**api_params)

            # 6. Map the successful response to LlmResponse
            # Assuming the response structure based on documentation
            content = ""
            if response.content and isinstance(response.content, list) and len(response.content) > 0:
                 # Check if the first block is a text block
                 if hasattr(response.content[0], 'text'):
                     content = response.content[0].text

            usage_dict = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            } if response.usage else None

            # Map Anthropic's stop_reason to our finish_reason
            finish_reason_map = {
                "end_turn": "stop",
                "max_tokens": "length",
                "stop_sequence": "stop_sequence", # Keep as is
                # Add other mappings if necessary
            }
            finish_reason = finish_reason_map.get(response.stop_reason, response.stop_reason) # Default to original if no map

            return LlmResponse(
                content=content,
                model_used=response.model, # Anthropic response includes model used
                usage_metadata=usage_dict,
                finish_reason=finish_reason,
                error=None,
            )

        except AnthropicError as e:
            # 5. Handle potential AnthropicError exceptions.
            # 7. Map errors to LlmResponse.error.
            return LlmResponse(
                content="",
                model_used=model,
                error=f"Anthropic API error: {e}",
            )
        except Exception as e:
            # Catch any other unexpected errors during the process
            return LlmResponse(
                content="",
                model_used=model,
                error=f"An unexpected error occurred: {e}",
            )
