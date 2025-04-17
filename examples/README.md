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

*   **Purpose:** A very simple example demonstrating agent registration and sending a message to itself (which, with the dispatch logic added, will now likely fail unless the agent runs a server at its dummy endpoint). **See `responder_agent.py` and `requester_agent.py` for a working inter-agent communication example.**
*   **How to Run:**
    1.  Start the AgentKit API (see Prerequisites).
    2.  Run the agent script:
        ```bash
        python examples/ping_agent.py
        ```
    3.  The script sends a message to itself. The API will attempt to dispatch this message to the agent's registered `contactEndpoint`.

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
    3.  The script will register a dummy agent and then attempt to invoke the `mock_tool` tool via the API.

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

### 4. `responder_agent.py`

*   **Purpose:** An agent that registers with a real, accessible `contactEndpoint` and runs a simple Flask server to listen for messages dispatched by the AgentKit API. It acknowledges received messages.
*   **How to Run:**
    1.  Ensure the AgentKit API is running (Docker Compose recommended: `docker-compose up --build api`).
    2.  Run the responder agent script in a separate terminal:
        ```bash
        python examples/responder_agent.py
        ```
    3.  This agent will register itself and then block while the Flask server runs, waiting for incoming messages on port 9001 (by default). Keep this terminal open.

### 5. `requester_agent.py`

*   **Purpose:** An agent that registers itself, looks up the `ResponderAgent` by name, and sends it a message via the AgentKit API's dispatch mechanism. Demonstrates basic agent-to-agent communication.
*   **How to Run:**
    1.  Ensure the AgentKit API is running (`docker-compose up --build api`).
    2.  Ensure the `responder_agent.py` script is running in another terminal.
    3.  Run the requester agent script:
        ```bash
        python examples/requester_agent.py
        ```
    4.  The script will register itself, find the ResponderAgent's ID, send a message, and print the response received from the API (which includes the acknowledgement from the ResponderAgent's Flask server).

### 6. `sequential_tool_agent.py`

*   **Purpose:** Demonstrates an agent calling one tool (`mock_tool`), processing its result, and then using that result to call another tool (`generic_llm_completion`). Showcases basic workflow logic within an agent.
*   **Prerequisites:**
    *   AgentKit API running *with the mock tool service* (`docker-compose up --build api mock_tool`).
    *   A `.env` file in the project root containing the necessary API key(s) for your chosen LLM provider (e.g., `OPENAI_API_KEY=sk-...`).
*   **How to Run:**
    1.  Ensure the AgentKit API and mock tool service are running via Docker Compose.
    2.  Ensure your `.env` file is configured for the desired LLM model (default is `gpt-3.5-turbo`).
    3.  Run the script:
        ```bash
        python examples/sequential_tool_agent.py
        ```
    4.  The script registers itself, calls `mock_tool`, uses the result to create a prompt, calls `generic_llm_completion`, and prints the final LLM response.