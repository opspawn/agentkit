import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import litellm

# Import the base interface
from agentkit.tools.interface import ToolInterface

# Set litellm verbosity (optional, uncomment if logs are too noisy)
# litellm.set_verbose = False

class GenericLLMTool(ToolInterface):
    """
    A generic tool to interact with various Large Language Models (LLMs)
    using the litellm library.

    This tool acts as a bridge to the litellm.acompletion function, allowing
    agents to request text generation from a wide range of models.

    It requires API keys for the respective LLM providers to be set as
    environment variables (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.).
    These keys are typically loaded from a `.env` file in the project root.
    """

    def __init__(self):
        """
        Initializes the tool and loads environment variables from a `.env` file
        if it exists, making API keys available for litellm.
        """
        load_dotenv()

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        """
        Returns the definition of the tool, including its name, description,
        and the schema for its parameters based on common litellm inputs.
        """
        return {
            "name": "generic_llm_completion",
            "description": (
                "Calls a specified Large Language Model (LLM) using the litellm library "
                "to get a text completion based on input messages. Requires appropriate "
                "API keys for the chosen model's provider to be set as environment variables "
                "(e.g., OPENAI_API_KEY)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "The model identifier for the LLM (e.g., 'gpt-4o', 'claude-3-haiku-20240307', 'gemini/gemini-1.5-flash')."
                    },
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        },
                        "description": "A list of message objects representing the conversation history or prompt."
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Optional: Maximum number of tokens to generate in the completion."
                    },
                    "temperature": {
                        "type": "number",
                        "format": "float",
                        "minimum": 0.0,
                        "maximum": 2.0, # Common range
                        "description": "Optional: Sampling temperature (0.0 to 2.0). Higher values make output more random."
                    },
                    "top_p": {
                        "type": "number",
                        "format": "float",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Optional: Nucleus sampling parameter. Considers tokens with top_p probability mass."
                    },
                    "stream": {
                        "type": "boolean",
                        "default": False,
                        "description": "Optional: Whether to stream the response chunk by chunk. (Note: AgentKit's core messaging might need adjustments to fully handle streamed responses)."
                    },
                    "stop": {
                        "type": ["string", "array"],
                        "items": {"type": "string"},
                        "description": "Optional: A stop sequence or list of sequences where the API will stop generating further tokens."
                    },
                    "presence_penalty": {
                        "type": "number",
                        "format": "float",
                        "minimum": -2.0,
                        "maximum": 2.0,
                        "description": "Optional: Penalty for new tokens based on whether they appear in the text so far."
                    },
                    "frequency_penalty": {
                        "type": "number",
                        "format": "float",
                        "minimum": -2.0,
                        "maximum": 2.0,
                        "description": "Optional: Penalty for new tokens based on their existing frequency in the text so far."
                    }
                    # Note: 'functions', 'function_call', 'tools', 'tool_choice' are omitted
                    # as AgentKit has its own tool handling mechanism. If direct model tool use
                    # is needed, this tool would require modification.
                },
                "required": ["model", "messages"]
            }
        }

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the LLM completion call using litellm.acompletion.

        Args:
            parameters: A dictionary containing the validated parameters ('model', 'messages', etc.).
            context: Optional context dictionary (not currently used by this tool).

        Returns:
            A dictionary containing the execution status ('success' or 'error')
            and either the 'result' (the full litellm ModelResponse as a dict)
            or an 'error_message'.
        """
        model = parameters.get("model")
        messages = parameters.get("messages")

        if not model or not messages:
            return {"status": "error", "error_message": "Missing required parameters: 'model' and 'messages'."}

        # Prepare arguments for litellm, including only the provided optional ones
        llm_kwargs = {
            "model": model,
            "messages": messages,
        }
        # List of optional parameters defined in get_definition
        optional_params = [
            "max_tokens", "temperature", "top_p", "stream", "stop",
            "presence_penalty", "frequency_penalty"
        ]
        for param in optional_params:
            if param in parameters:
                llm_kwargs[param] = parameters[param]

        try:
            # Ensure API keys are loaded (might be redundant if __init__ already ran, but safe)
            load_dotenv()

            # Make the asynchronous call to litellm
            print(f"Calling litellm.acompletion with kwargs: {llm_kwargs}") # Basic logging
            response = await litellm.acompletion(**llm_kwargs)

            # Process the response - litellm returns a ModelResponse object.
            # Convert it to a dictionary for a standardized result structure.
            result_data = response.dict()
            print(f"litellm.acompletion successful. Result: {result_data}") # Basic logging

            return {"status": "success", "result": result_data}

        except Exception as e:
            # Catch potential errors from litellm (API errors, config errors, etc.)
            # Log the error for debugging purposes
            error_msg = f"LLM execution failed: {type(e).__name__}: {str(e)}"
            print(f"Error during litellm execution: {error_msg}") # Basic logging
            # Consider logging the full traceback if needed for deeper debugging
            # import traceback
            # print(traceback.format_exc())
            return {"status": "error", "error_message": error_msg}