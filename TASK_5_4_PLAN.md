# Plan for Task 5.4: Configuration Documentation (`docs/configuration.md`)

**Objective:** Document configuration details, environment variables, and external dependencies for the AgentKit Python module.

**Target File:** `docs/configuration.md`

**Plan:**

1.  **Introduction:**
    *   Briefly explain the purpose of this document: to guide users on configuring the AgentKit Python module environment, including necessary variables, Docker setup, and external dependencies.

2.  **Environment Variables:**
    *   **Mechanism:** Explain the use of `.env` files at the project root for managing environment variables, particularly secrets like API keys. Mention that `python-dotenv` is used to load these.
    *   **Security:** Emphasize adding `.env` to `.gitignore`.
    *   **Template:** Provide a template or example structure for the `.env` file (`.env.example` content).
        ```plaintext
        # Example .env file for AgentKit

        # --- LLM Provider API Keys (Required for llm_agent_example.py and live tests) ---
        # Add keys for the providers you intend to use via litellm
        # OPENAI_API_KEY=sk-...
        # ANTHROPIC_API_KEY=sk-...
        # COHERE_API_KEY=...
        # AZURE_API_KEY=...
        # AZURE_API_BASE=...
        # AZURE_API_VERSION=...
        # HUGGINGFACE_API_KEY=hf_...
        # Add other provider keys as needed by litellm

        # --- AgentKit API Service (Optional Overrides) ---
        # Default host and port are defined in the code/Docker Compose
        # HOST=0.0.0.0
        # PORT=8000

        # --- Other configurations if added later ---
        ```
    *   **Usage:**
        *   **API Service:** Explain how `docker-compose.yml` passes the `.env` file to the service container. Mention potential future overrides (`HOST`/`PORT`).
        *   **Examples:** Detail specific variables required by `examples/llm_agent_example.py` (e.g., `OPENAI_API_KEY`).
        *   **Live Tests:** Mention that live integration tests also require relevant API keys in `.env`.

3.  **Docker Configuration:**
    *   **Overview:** Briefly describe the roles of `Dockerfile` and `docker-compose.yml`.
    *   **Environment Variables:** Reiterate how `docker-compose.yml` loads variables from `.env` into the `api_service` container.

4.  **Testing Configuration:**
    *   **`pytest.ini`:** Explain its purpose - configuring markers (`@pytest.mark.live_llm`), `asyncio_mode`, etc.

5.  **External Dependencies Requiring Setup:**
    *   **`litellm`:** State that it requires API keys set as environment variables (detailed in the `.env` section).
    *   **Other Dependencies:** Mention `requirements.txt` dependencies are handled by `pip`.

---

**Diagram (Optional):**

```mermaid
graph LR
    subgraph User Setup
        direction TB
        ENV_File[.env File] -- Contains --> API_Keys[API Keys, etc.]
    end

    subgraph Runtime Environment
        direction TB
        DockerCompose[docker-compose.yml] -- Loads --> ENV_File
        DockerCompose -- Passes Vars to --> APIService[API Service Container]
        APIService -- Uses --> LiteLLM[litellm / GenericLLMTool]
        APIService -- Uses --> FastAPI[FastAPI App]
        LiteLLM -- Needs --> API_Keys
    end

    subgraph Local Scripts/Tests
        direction TB
        Pytest[pytest] -- Reads --> PytestINI[pytest.ini]
        Pytest -- Runs --> LiveTests[Live Tests]
        ExampleScript[llm_agent_example.py] -- Reads --> ENV_File_Local[(.env File)]
        LiveTests -- Reads --> ENV_File_Local
        ExampleScript -- Uses --> LiteLLM_Local[litellm]
        LiveTests -- Uses --> LiteLLM_Local
        LiteLLM_Local -- Needs --> API_Keys_Local[API Keys, etc.]
    end

    ENV_File --> ENV_File_Local # User creates/manages this file
    API_Keys --> API_Keys_Local # Same keys used in both contexts

    style ENV_File fill:#lightgrey,stroke:#333,stroke-width:2px
    style ENV_File_Local fill:#lightgrey,stroke:#333,stroke-width:2px