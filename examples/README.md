# AgentKit Python Examples

This directory contains example scripts demonstrating how to use the AgentKit Python SDK and interact with the AgentKit API.

## Prerequisites

*   **AgentKit API Running:** Ensure the main AgentKit API service is running. You can typically start it from the project root using Docker Compose:
    ```bash
    docker-compose up --build api
    ```
    Or directly with Uvicorn (ensure dependencies are installed):
    ```bash
    uvicorn main:app --reload --port 8000
    ```
*   **Python Environment:** Make sure you have the necessary dependencies installed in your Python environment (usually via `pip install -r requirements.txt` in the project root).
*   **`.env` File (for LLM Example):** The `llm_agent_example.py` requires a `.env` file in the project root directory containing API keys for the LLM provider you intend to use (e.g., `OPENAI_API_KEY=sk-...`).

## Examples

### 1. `ping_agent.py`

*   **Purpose:** A very simple agent that registers itself and listens for incoming messages on a specified endpoint. It simply prints received messages. This demonstrates basic agent registration and receiving messages.
*   **How to Run:**
    1.  Start the AgentKit API (see Prerequisites).
    2.  Run the agent script:
        ```bash
        python examples/ping_agent.py
        ```
    3.  You can then send messages to this agent using the AgentKit CLI or SDK (targeting the agent ID printed by the script).

### 2. `tool_user_agent.py`

*   **Purpose:** Demonstrates how an agent can use the AgentKit SDK to invoke a tool registered within the AgentKit service (specifically, the mock tool running via Docker Compose).
*   **How to Run:**
    1.  Start the AgentKit API *and* the mock tool service using Docker Compose:
        ```bash
        docker-compose up --build api mock_tool
        ```
    2.  Run the agent script:
        ```bash
        python examples/tool_user_agent.py
        ```
    3.  The script will register a dummy agent and then attempt to invoke the `mock_tool_echo` tool via the API.

### 3. `llm_agent_example.py`

*   **Purpose:** Shows how to invoke the built-in `generic_llm_completion` tool to interact with various Large Language Models (LLMs) supported by `litellm`.
*   **Prerequisites:**
    *   AgentKit API running.
    *   A `.env` file in the project root containing the necessary API key(s) for your chosen LLM provider (e.g., `OPENAI_API_KEY=sk-...`, `ANTHROPIC_API_KEY=sk-...`). The `GenericLLMTool` running inside the API service will load this file.
*   **How to Run:**
    1.  Ensure the AgentKit API is running (Docker Compose recommended as it handles the `.env` loading for the API service):
        ```bash
        docker-compose up --build api
        ```
    2.  Modify the `llm_model` variable inside `llm_agent_example.py` to match a model you have API key access to (defined in your `.env` file).
    3.  Run the script:
        ```bash
        python examples/llm_agent_example.py
        ```
    4.  The script registers a dummy agent and then calls the `generic_llm_completion` tool via the API, printing the LLM's response.