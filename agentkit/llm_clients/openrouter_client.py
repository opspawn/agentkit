import os
from typing import Dict, Any, Optional, List

from openai import AsyncOpenAI, OpenAIError

from agentkit.core.interfaces.llm_client import BaseLlmClient, LlmResponse


class OpenRouterClient(BaseLlmClient):
    """
    LLM Client implementation for models accessed via OpenRouter
    (using the OpenAI-compatible API).
    """
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initializes the OpenRouter client.

        Args:
            api_key: OpenRouter API key. Defaults to OPENROUTER_API_KEY env var.
            base_url: OpenRouter API base URL. Defaults to OpenRouter's default.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided or found in environment variables (OPENROUTER_API_KEY).")

        self.base_url = base_url or self.DEFAULT_BASE_URL

        # Use the AsyncOpenAI client configured for OpenRouter
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        # TODO: Add optional headers like HTTP-Referer, X-Title if needed

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None, # Model must be specified in OpenRouter format (e.g., "anthropic/claude-3-opus")
        stop_sequences: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LlmResponse:
        """
        Generates text based on a prompt using the OpenRouter API.

        Args:
            prompt: The input prompt for the LLM.
            model: The specific model identifier in OpenRouter format (e.g., "google/gemini-pro"). REQUIRED.
            stop_sequences: List of sequences to stop generation at.
            temperature: Sampling temperature.
            max_tokens: Maximum number of tokens to generate.
            **kwargs: Additional arguments compatible with the OpenAI API format.

        Returns:
            An LlmResponse object containing the generated content and metadata.
        """
        if not model:
            raise ValueError("Model identifier is required for OpenRouterClient.")

        # 1. Format prompt to messages (same as OpenAiClient)
        #    Include system prompt if provided in kwargs.
        messages = []
        system_prompt = kwargs.pop("system_prompt", None) # Extract system_prompt from kwargs
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # 2. Prepare API params (same as OpenAiClient)
        api_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stop": stop_sequences,
            **kwargs,
        }
        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens

        try:
            # 3. Call self.client.chat.completions.create(...)
            # The self.client is already configured with OpenRouter base_url and api_key
            response = await self.client.chat.completions.create(**api_params)

            # 5. Map successful response to LlmResponse (same as OpenAiClient)
            choice = response.choices[0]
            content = choice.message.content or ""
            usage = response.usage
            usage_dict = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            } if usage else None

            return LlmResponse(
                content=content,
                model_used=response.model, # OpenRouter response includes model used
                usage_metadata=usage_dict,
                finish_reason=choice.finish_reason,
                error=None,
            )

        except OpenAIError as e:
            # 4. & 6. Handle potential OpenAIError and map errors
            return LlmResponse(
                content="",
                model_used=model,
                error=f"OpenRouter API error (via OpenAI SDK): {e}",
            )
        except Exception as e:
            # Catch any other unexpected errors
            return LlmResponse(
                content="",
                model_used=model,
                error=f"An unexpected error occurred: {e}",
            )
