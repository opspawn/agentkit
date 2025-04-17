# AgentKit Configuration Guide

This document provides a comprehensive guide to configuring the AgentKit Python module environment. It covers environment variables, Docker setup, testing configurations, and external dependencies that require specific setup.

## 1. Environment Variables

AgentKit utilizes environment variables for configuration, particularly for sensitive information like API keys. The primary mechanism for managing these locally is through a `.env` file located at the project root.

### Mechanism

-   Create a file named `.env` in the root directory of the project (`/home/sf2/Workspace/23-opspawn/4-v2/agentkit`).
-   The AgentKit API service (when run via Docker Compose) and local scripts/tests (using the `python-dotenv` library) automatically load variables defined in this file.

### Security

**IMPORTANT:** The `.env` file should **never** be committed to version control as it often contains sensitive credentials. Ensure your project's `.gitignore` file includes an entry for `.env`.

```gitignore
# Example .gitignore entry
.env
```

### `.env` Template

You can use the following template to create your `.env` file. Populate it with the necessary values for the services you intend to use.

```plaintext
# .env file for AgentKit Configuration

# --- LLM Provider API Keys (Required for llm_agent_example.py and live tests) ---
# Add keys for the LLM providers you intend to use via litellm.
# Only provide keys for the services you will actually call.
# See litellm documentation for the correct variable names for each provider.
# Examples:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-api03-...
# COHERE_API_KEY=...
# AZURE_API_KEY=...
# AZURE_API_BASE=https://your-deployment.openai.azure.com/
# AZURE_API_VERSION=2023-07-01-preview
# HUGGINGFACE_API_KEY=hf_...
# GEMINI_API_KEY=...
# Add other provider keys as needed by litellm

# --- Ops-Core Integration (Required for state reporting) ---
# URL of the running Ops-Core API service
OPSCORE_API_URL=http://localhost:8080 # Replace with actual Ops-Core URL if different
# API Key for authenticating with the Ops-Core API
OPSCORE_API_KEY=your_opscore_api_key_here

# --- AgentKit API Service (Optional Overrides) ---
# These typically do not need to be set, as defaults are handled
# by the FastAPI application and Docker Compose.
# HOST=0.0.0.0
# PORT=8000

# --- Other configurations (if added in the future) ---
# Example: DATABASE_URL=...
```

### Specific Variable Details

#### LLM Provider Keys
-   **Purpose:** Authenticate with external LLM services (OpenAI, Anthropic, etc.).
-   **Used By:** `GenericLLMTool` via `litellm`.
-   **Context:** Required when running `examples/llm_agent_example.py` or live integration tests (`pytest -m live_llm`). Also required by the API service in Docker if agents invoke the LLM tool.

#### Ops-Core Integration Variables
-   `OPSCORE_API_URL`: The base URL for the Ops-Core API service.
-   `OPSCORE_API_KEY`: The API key required to authenticate requests to the Ops-Core API.
-   **Purpose:** Allow AgentKit agents (via the SDK) to report their state to the Ops-Core lifecycle management system.
-   **Used By:** `AgentKitClient.report_state_to_opscore` method.
-   **Context:** Required by any agent that needs to integrate with Ops-Core state tracking, particularly when running the planned `examples/opscore_aware_agent.py`.

### Usage Contexts

-   **API Service (Docker Compose):** The `docker-compose.yml` file is configured to use the `.env` file. Variables defined here (especially API keys) are passed into the `api_service` container, making them accessible to the FastAPI application and tools like `GenericLLMTool` when running within Docker.
-   **Example Scripts (`examples/`):** Scripts like `examples/llm_agent_example.py` directly load the `.env` file using `python-dotenv` when run locally (outside of Docker). They require the relevant LLM API keys (e.g., `OPENAI_API_KEY`) to interact with `litellm`.
-   **Live Integration Tests (`tests/integration/`):** Tests marked with `@pytest.mark.live_llm` (e.g., `test_llm_tool_live.py`) also load the `.env` file when run locally via `pytest`. They require the necessary API keys to execute live calls to external LLM services.

## 2. Docker Configuration

Docker is used to containerize the AgentKit API service for consistent deployment and local development/testing.

-   **`Dockerfile`:** Defines the steps to build the Docker image for the `api_service`. This includes installing dependencies from `requirements.txt` and setting up the FastAPI application with Uvicorn.
-   **`docker-compose.yml`:** Orchestrates the running container(s).
    -   It defines the `api_service`, builds it using the `Dockerfile`, maps ports (e.g., 8000:8000), and mounts necessary volumes.
    -   Crucially, it includes `env_file: .env`, which instructs Docker Compose to load variables from the `.env` file in the project root and make them available as environment variables *inside* the `api_service` container.

## 3. Testing Configuration (`pytest.ini`)

The `pytest.ini` file configures the behavior of the `pytest` testing framework for this project.

```ini
[pytest]
# Automatically run any asyncio tests with the pytest-asyncio plugin
asyncio_mode = auto

# Register custom markers for filtering tests
markers =
    live_llm: Run tests that make live calls to LLM APIs (requires .env configuration)
    # Add other markers here if needed
```

-   **`asyncio_mode = auto`:** Ensures `pytest-asyncio` correctly handles asynchronous tests used in AgentKit (e.g., for FastAPI test clients).
-   **`markers`:** Defines custom markers like `live_llm`. This allows you to selectively run or skip tests. For example, to run only non-live tests: `pytest -m "not live_llm"`. To run only live LLM tests: `pytest -m live_llm`.

## 4. External Dependencies Requiring Setup

Most Python dependencies are listed in `requirements.txt` and installed automatically via `pip`. However, some require specific user configuration:

-   **`litellm`:**
    -   **Purpose:** Used by the `GenericLLMTool` (`agentkit/tools/llm_tool.py`) to provide a unified interface for interacting with various Large Language Models (LLMs).
    -   **Configuration:** Requires API keys for the specific LLM providers you wish to use. These keys **must** be set as environment variables, typically via the `.env` file as described in Section 1. Refer to the official `litellm` documentation for the exact environment variable names required by each supported provider. AgentKit simply passes the environment through; it does not manage the keys directly beyond loading the `.env` file.

Ensure your `.env` file is correctly configured before running examples or tests that utilize the `GenericLLMTool`.