# Development Plan: AgentKit Python Module

This plan outlines the development strategy for the AgentKit Python Module, based on the initial planning documents and Memory Bank context.

**1. Foundational Decisions & Setup (Phase 1 Refined)**

*   **Goal:** Establish a solid foundation for development, including environment, tooling, and key technical choices.
*   **Key Decision - API Framework:**
    *   **Recommendation:** Adopt **FastAPI**.
    *   **Reasoning:** Aligns strongly with project goals: Built-in Pydantic validation, automatic OpenAPI documentation, high performance, modern Python features.
*   **Key Decision - Initial Storage:**
    *   **Recommendation:** Start with an **in-memory Python dictionary**.
    *   **Reasoning:** Sufficient for local-first development and rapid prototyping. Defers Redis complexity.
*   **Tasks:**
    1.  **Git Repository Setup:** Initialize Git repo, define branching strategy (Task 1.1).
    2.  **Local Environment:** Configure Python 3.9+ `venv`, create `requirements.txt` (FastAPI, Uvicorn, Pydantic, Pytest, Requests, Black, Flake8) (Task 1.2).
    3.  **Project Structure:** Create initial directory layout (api/, core/, registration/, messaging/, tools/, tests/, docs/, examples/, .github/, etc.).
    4.  **Containerization:** Create basic `Dockerfile` (uvicorn) and `docker-compose.yml` (Task 1.3).
    5.  **Basic CI:** Set up GitHub Actions for linting (`black`, `flake8`) and initial testing (`pytest`) (Partial Task 4.3).
    6.  **Update Memory Bank:** Document FastAPI and in-memory storage decisions (Done).

**2. Core Module Development (Phase 2 Refined)**

*   **Goal:** Implement the core API endpoints and business logic iteratively with tests.
*   **Development Approach:** TDD/Test-alongside development, PEP8, type hints.
*   **Tasks:**
    1.  **FastAPI App Setup:** Initialize FastAPI app (`agentkit/api/main.py`).
    2.  **Core Models (Pydantic):** Define models in `agentkit/core/models.py` (AgentRegistrationPayload, AgentInfo, MessagePayload, ToolDefinition, ApiResponse).
    3.  **Agent Registration Module (`agentkit/registration/`, `agentkit/api/endpoints/registration.py`):** Implement storage, `POST /v1/agents/register` endpoint, validation, `pytest` tests (Tasks 2.1, 2.2, 2.3).
    4.  **Messaging Interface Module (`agentkit/messaging/`, `agentkit/api/endpoints/messaging.py`):** Implement `POST /v1/agents/{agentId}/run` endpoint, validation, placeholder dispatch logic, error responses, `pytest` tests (Tasks 2.4, 2.5, 2.6).
    5.  **Tool Integration Module (`agentkit/tools/`, integrated into Messaging):** Define `ToolInterface` ABC, implement Tool Registry (in-memory), handle `"tool_invocation"` message type in dispatcher, document registration, `pytest` tests (Tasks 2.7, 2.8).
    6.  **Logging Middleware:** Implement basic FastAPI middleware for structured logging (Task 3.4 - initial).

**3. Integration & Interfaces (Phase 3 Refined)**

*   **Goal:** Create the Python SDK and CLI for developer interaction.
*   **Tasks:**
    1.  **Python SDK (`agentkit-sdk` or `agentkit/sdk/`):** Create client class (using `requests`/`httpx`), implement API wrapper methods (`register_agent`, `send_message`), add tests (Task 3.1).
    2.  **CLI Tool (`agentkit/cli/main.py`):** Use `typer`/`click`, implement commands wrapping SDK functions, add tests (Task 3.2).
    3.  **SDK/API Integration:** Test SDK/CLI against the running API service (Task 3.3).

**4. Testing & Validation (Phase 4 Refined)**

*   **Goal:** Ensure high quality, robustness, and reliability.
*   **Tasks:**
    1.  **Enhance Unit Tests:** Increase coverage (>80%), test edge cases/failures (Task 4.1).
    2.  **Integration Tests (`tests/integration/`):** Write `pytest` tests for full workflows using Docker/SDK (Task 4.2).
    3.  **Refine CI/CD:** Ensure CI runs unit/integration tests, linting, formatting, coverage (Task 4.3).
    4.  **Basic Load Testing:** Use `locust` for key endpoints (Task 4.4).
    5.  **User Acceptance Testing (UAT):** Implement and test example agents (`examples/`) (Task 4.5).

**5. Documentation & Finalization (Phase 5 Refined)**

*   **Goal:** Produce comprehensive documentation and prepare for release.
*   **Tasks:**
    1.  **README.md:** Update comprehensively (Installation, Config, Usage, Examples) (Task 5.1).
    2.  **API Docs (Swagger):** Review/enhance auto-generated docs (Task 5.2).
    3.  **Sample Projects (`examples/`):** Finalize and document examples (Task 5.3).
    4.  **Configuration Docs:** Create `docs/configuration.md` (Task 5.4).
    5.  **Contribution Guide:** Create `CONTRIBUTING.md`.
    6.  **Final Review:** Code review, docs proofreading, final testing (Task 5.5).

**Mermaid Diagrams:**

*   **High-Level Component Interaction:**
    ```mermaid
    graph TD
        subgraph Developer Interaction
            SDK[Python SDK]
            CLI[CLI Tool]
        end

        subgraph AgentKit Service (FastAPI)
            API[REST API Endpoints /v1]
            MW[Middleware (Logging, Errors)]
            REG[Registration Module] --- STORE
            MSG[Messaging Module] --- STORE
            TOOL[Tool Integration Logic] --- STORE
            STORE[(In-Memory Storage <br/> Agent Meta, Tool Registry)]
        end

        Developer[Developer] --> SDK
        Developer --> CLI
        SDK --> API
        CLI --> API
        API --> MW
        MW --> REG
        MW --> MSG
        MSG --> TOOL

        style Developer fill:#f9f,stroke:#333,stroke-width:2px
        style SDK fill:#ccf,stroke:#333,stroke-width:1px
        style CLI fill:#ccf,stroke:#333,stroke-width:1px
    ```

*   **Phase 2 Module Structure (Conceptual):**
    ```mermaid
    graph LR
        subgraph agentkit [agentkit Package]
            direction LR
            subgraph api [api]
                direction TB
                ep_reg[endpoints/registration.py]
                ep_msg[endpoints/messaging.py]
                main[main.py]
            end
            subgraph core [core]
                direction TB
                models[models.py (Pydantic)]
                errors[errors.py]
            end
            subgraph registration [registration]
                direction TB
                logic_reg[logic.py]
                storage_reg[storage.py]
            end
            subgraph messaging [messaging]
                direction TB
                logic_msg[logic.py]
                dispatcher[dispatcher.py]
            end
            subgraph tools [tools]
                direction TB
                interface[interface.py (ABC)]
                registry[registry.py]
            end
        end

        main --> ep_reg
        main --> ep_msg
        ep_reg --> logic_reg
        ep_msg --> dispatcher
        dispatcher --> logic_msg
        dispatcher --> registry # Tool invocation check
        logic_reg --> storage_reg
        registry --> interface # Uses interface definitions
        logic_reg --> models
        logic_msg --> models
        registry --> models # ToolDefinition model