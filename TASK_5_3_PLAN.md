# Plan for Task 5.3: Generic LLM Tool & Examples

## 1. Overview

This plan outlines the steps required to complete Task 5.3: "Create sample projects and comprehensive tutorials showcasing the Python SDK and CLI usage." The core of this task is implementing a generic, model-agnostic LLM tool using the `litellm` library, creating an example agent that uses this tool, and documenting its usage.

## 2. Detailed Steps

1.  **Add Dependencies:**
    *   **File:** `requirements.txt`
    *   **Action:** Add `litellm` and `python-dotenv` to the list of dependencies.

2.  **Update `.gitignore`:**
    *   **File:** `.gitignore`
    *   **Action:** Add `.env` to the `.gitignore` file to prevent accidental commits of API keys.

3.  **Implement `GenericLLMTool`:**
    *   **File:** Create `agentkit/tools/llm_tool.py`
    *   **Action:**
        *   Define a new class `GenericLLMTool` inheriting from `ToolInterface`.
        *   Implement the tool's logic using `litellm.completion()` to call various LLM APIs.
        *   The tool should accept parameters like `model`, `messages`, and potentially other common LLM parameters (e.g., `temperature`, `max_tokens`).
        *   Load API keys from environment variables (using `python-dotenv` and `os.getenv`).
        *   Include necessary Pydantic models for input/output validation if needed.
        *   Add clear docstrings.

4.  **Register `GenericLLMTool`:**
    *   **File:** `agentkit/tools/registry.py` (or wherever tool registration occurs)
    *   **Action:** Import and register an instance of `GenericLLMTool` in the tool registry so it can be discovered and used by agents.

5.  **Update Docker Compose for `.env`:**
    *   **File:** `docker-compose.yml`
    *   **Action:** Modify the `agentkit-api` service definition to load environment variables from a `.env` file using `env_file: .env`. This allows the API service (and thus the tool running within it) to access the necessary API keys.

6.  **Create LLM Agent Example:**
    *   **File:** Create `examples/llm_agent_example.py`
    *   **Action:**
        *   Create a simple agent that uses the AgentKit SDK.
        *   The agent should demonstrate how to invoke the `GenericLLMTool`.
        *   It should take a simple prompt, send it to the LLM tool, and print the response.
        *   Include instructions in comments on how to run it and the prerequisite of having a `.env` file.

7.  **Update Examples README:**
    *   **File:** `examples/README.md`
    *   **Action:** Add a section describing the new `llm_agent_example.py`, explaining its purpose and how to run it, emphasizing the need for the `.env` file.

8.  **Create Tutorial:**
    *   **File:** Create `docs/TUTORIAL.md` (or update an existing tutorial file)
    *   **Action:** Write a tutorial that guides users through:
        *   Setting up the environment, including the `.env` file with API keys.
        *   Understanding the `GenericLLMTool`.
        *   Running the `llm_agent_example.py`.
        *   Explaining how to use the tool within their own agents.

## 3. Dependencies & Prerequisites

*   The user running the example will need to create a `.env` file in the project root directory containing the necessary API keys for the desired LLM provider(s) (e.g., `OPENAI_API_KEY=sk-...`). Clear instructions for this must be provided in the documentation.

## 4. Next Steps

Once this plan is approved, implementation will proceed step-by-step, starting with adding dependencies to `requirements.txt`. Each step will require confirmation before moving to the next.