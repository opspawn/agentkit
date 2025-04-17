# Tutorial: Using the Generic LLM Tool in AgentKit

This tutorial guides you through setting up and using the built-in `GenericLLMTool` within the AgentKit Python module. This tool allows your agents to interact with a wide variety of Large Language Models (LLMs) supported by the `litellm` library.

## 1. Introduction

AgentKit includes a `GenericLLMTool` (registered as `generic_llm_completion`) that acts as a unified interface to different LLM providers (OpenAI, Anthropic, Google Gemini, etc.). Instead of writing separate code for each provider, you can use this single tool, specifying the desired model and providing your API keys.

## 2. Prerequisites

Before you begin, ensure you have the following set up:

*   **AgentKit Project:** You have cloned or set up the AgentKit Python project.
*   **Dependencies:** You have installed the necessary Python dependencies from the project root:
    ```bash
    pip install -r requirements.txt
    ```
*   **AgentKit API Running:** The core AgentKit API service must be running. The recommended way to run it for this tutorial (as it handles environment variables correctly) is using Docker Compose from the project root:
    ```bash
    docker-compose up --build api
    ```
    Alternatively, if not using Docker, ensure the API is running via `uvicorn main:app --reload --port 8000`.
*   **LLM API Key(s):** You need an API key from at least one LLM provider (like OpenAI, Anthropic, Cohere, Google AI Studio, etc.) that `litellm` supports.

## 3. Setting Up Your `.env` File

The `GenericLLMTool` securely accesses your LLM API keys via environment variables. `litellm` automatically detects keys set in the environment following specific naming conventions (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`).

1.  **Create `.env` File:** In the **root directory** of your AgentKit project (the same level as `docker-compose.yml` and `requirements.txt`), create a file named `.env`.
2.  **Add API Keys:** Add your API key(s) to this file, one per line, following the required format for `litellm`. For example:
    ```dotenv
    # .env file contents

    # Example for OpenAI
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # Example for Anthropic
    # ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # Example for Google Gemini
    # GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # Add other keys as needed based on litellm documentation
    ```
    *Replace the placeholder keys with your actual keys.*
3.  **Save the File:** Save the `.env` file.
4.  **Security:** The `.gitignore` file in the project should already be configured to prevent this `.env` file from being accidentally committed to version control. **Never commit your API keys.**

When you run the AgentKit API using `docker-compose up`, the `env_file: .env` directive in `docker-compose.yml` makes these variables available to the API service container, where the `GenericLLMTool` can access them.

## 4. Running the Example (`llm_agent_example.py`)

The `examples/` directory contains a script specifically designed to demonstrate the `GenericLLMTool`.

1.  **Navigate to Project Root:** Open your terminal in the root directory of the AgentKit project.
2.  **Ensure API is Running:** Make sure the AgentKit API is running (preferably via `docker-compose up api`).
3.  **Configure Model (Optional):** Open `examples/llm_agent_example.py` in your editor. Find the line:
    ```python
    llm_model = "gpt-3.5-turbo"
    ```
    Change `"gpt-3.5-turbo"` to the identifier of a model you have an API key for in your `.env` file (e.g., `"claude-3-haiku-20240307"`, `"gemini/gemini-1.5-flash"`). Refer to `litellm` documentation for model identifiers.
4.  **Run the Script:** Execute the example script:
    ```bash
    python examples/llm_agent_example.py
    ```

## 5. Understanding the Output

The script will:
1.  Print connection information.
2.  Register a temporary "dummy" agent (needed to satisfy the API route structure).
3.  Print the parameters being sent to the `generic_llm_completion` tool.
4.  Print status messages indicating the tool invocation.
5.  If successful, print the full JSON response received from the `litellm` library (nested within the AgentKit API response).
6.  Attempt to extract and print the main text content from the LLM's response.

If an error occurs (e.g., missing API key, invalid model name, network issue), the script will print an error message and potentially the error details received from the API.

## 6. Using the Tool in Your Own Agent

You can invoke the `generic_llm_completion` tool from any agent script using the AgentKit SDK, similar to the example. Here's a simplified snippet:

```python
from agentkit.sdk.client import AgentKitClient, AgentKitError

# Assume client is initialized and a valid agent_id exists
client = AgentKitClient()
my_agent_id = "your_registered_agent_id" # The ID of the agent making the call
target_api_agent_id = "any_valid_registered_agent_id" # ID for the API route

try:
    tool_payload = {
        "tool_name": "generic_llm_completion",
        "arguments": {
            "model": "gpt-4o", # Or another model
            "messages": [
                {"role": "user", "content": "What is the capital of France?"}
            ]
            # Add other optional params like max_tokens, temperature if needed
        }
    }

    response_data = client.send_message(
        target_agent_id=target_api_agent_id, # Route requires a valid ID
        sender_id=my_agent_id,
        message_type="tool_invocation",
        payload=tool_payload
    )

    # Process the response_data which contains the tool result
    if response_data and response_data.get("status") == "success":
        llm_result = response_data.get("result", {})
        # Extract content from llm_result based on its structure
        print("LLM Result:", llm_result)

except AgentKitError as e:
    print(f"Error calling LLM tool: {e}")

```

Remember to handle the response structure appropriately based on the `litellm` output for the specific model you called.

---

This concludes the tutorial on using the `GenericLLMTool`. You can now integrate powerful language model capabilities into your AgentKit agents!