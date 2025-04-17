# Plan: AgentKit Modifications for Ops-Core Integration Readiness (Task B7)

**Objective:** Enhance the AgentKit Python module to fully support the expected integration points with the Ops-Core system, preparing it for seamless interaction within the Opspawn ecosystem.

**New Backlog Task:** Task B7: Enhance AgentKit for Ops-Core Integration Readiness

**Plan Details:**

1.  **SDK Enhancement (`agentkit/sdk/client.py`):**
    *   **Goal:** Provide a streamlined way for agents to report their state to Ops-Core.
    *   **Action:** Add a new asynchronous method `report_state_to_opscore` to the `agentkit.sdk.client.AgentKit` class.
    *   **Method Signature:** `async def report_state_to_opscore(self, agent_id: str, state: str, details: Optional[dict] = None) -> None:` (or return a response object/status).
    *   **Functionality:**
        *   Read `OPSCORE_API_URL` and `OPSCORE_API_KEY` from environment variables (using `os.getenv`). Handle cases where they might be missing (log warning/error).
        *   Construct the target URL: `{OPSCORE_API_URL}/v1/opscore/agent/{agent_id}/state`.
        *   Construct the JSON payload including `agentId`, `timestamp` (ISO8601 format), `state`, and optional `details`.
        *   Use the existing `httpx.AsyncClient` instance (`self._client`) to make an asynchronous `POST` request.
        *   Include the `OPSCORE_API_KEY` in the request headers (e.g., `Authorization: Bearer {key}` or `X-API-Key: {key}` - *Need to confirm Ops-Core's expected header*).
        *   Implement basic error handling: Log warnings/errors for connection issues or non-successful HTTP status codes (e.g., >= 400) returned by Ops-Core. Consider raising an exception for critical failures.

2.  **Configuration Updates:**
    *   **Goal:** Standardize how Ops-Core connection details are configured.
    *   **Action:**
        *   Define standard environment variables: `OPSCORE_API_URL` and `OPSCORE_API_KEY`.
        *   Update `docs/configuration.md`: Add a new section explaining these variables, their purpose, and how agents/SDK use them.
        *   Update/Create `.env.example`: Include commented-out placeholders for `OPSCORE_API_URL` and `OPSCORE_API_KEY`.
        *   Ensure `.gitignore` includes `.env`.

3.  **New Example Agent (`examples/opscore_aware_agent.py`):**
    *   **Goal:** Demonstrate best practices for building an agent that interacts with Ops-Core.
    *   **Action:** Create a new example script.
    *   **Functionality:**
        *   Load environment variables (using `dotenv`).
        *   Initialize the `AgentKit` SDK client.
        *   Register the agent using `sdk.register_agent(...)`.
        *   Implement a simple agent logic (e.g., a FastAPI endpoint listening at its `contactEndpoint`).
        *   Demonstrate calling `sdk.report_state_to_opscore(...)` at key points:
            *   After registration (`idle` or `ready`).
            *   When receiving a task/message (`active`).
            *   After completing a task (`idle`).
            *   If an error occurs (`error` with details).
        *   Include basic logic to receive and log a hypothetical "workflow task" message sent from Ops-Core via the AgentKit messaging endpoint.
    *   **Documentation:** Update `examples/README.md` to describe this new example and its purpose.

4.  **Testing Strategy:**
    *   **Goal:** Ensure the new SDK functionality works correctly and reliably.
    *   **SDK Unit Tests (`tests/sdk/test_client.py`):**
        *   Use `pytest-mock` to mock `httpx.AsyncClient.post` and `os.getenv`.
        *   Test `report_state_to_opscore`:
            *   Verify correct URL construction based on mocked `OPSCORE_API_URL` and `agent_id`.
            *   Verify correct JSON payload generation (including timestamp format).
            *   Verify correct API key header inclusion based on mocked `OPSCORE_API_KEY`.
            *   Test successful POST simulation (mock returns 2xx).
            *   Test error handling for simulated non-2xx responses from Ops-Core.
            *   Test error handling for simulated `httpx` exceptions (e.g., `ConnectError`).
            *   Test behavior when config variables are missing.
    *   **Integration Tests (`tests/integration/test_opscore_integration.py`):**
        *   Use `pytest-httpserver` to create a mock Ops-Core API endpoint.
        *   Configure the mock server to expect `POST` requests at `/v1/opscore/agent/{agentId}/state` with specific headers (API key) and JSON payload structure.
        *   Write a test that:
            *   Sets the `OPSCORE_API_URL` environment variable to the mock server's URL and sets a mock `OPSCORE_API_KEY`.
            *   Initializes the `AgentKit` SDK.
            *   Calls `sdk.report_state_to_opscore(...)`.
            *   Asserts that the mock server received the expected request (using `httpserver.expect_request`).
        *   (Optional Advanced Test): Simulate the full loop: Register an agent -> Ops-Core (mock) triggers workflow via AgentKit API -> Agent receives message -> Agent reports state back to Ops-Core (mock). This would involve coordinating the mock server and potentially running a simplified agent process.

5.  **Documentation Updates (Core Docs):**
    *   **Goal:** Inform developers how to use the new capabilities.
    *   **Action:**
        *   Update `docs/TUTORIAL.md`: Add a section on making agents "Ops-Core Aware", explaining the state reporting requirement and how to use the new SDK method and configuration.
        *   Review `README.md`: Briefly mention the added capability for Ops-Core integration.

6.  **Task Tracking (`TASK.md`):**
    *   **Goal:** Keep the project task list up-to-date.
    *   **Action:** Add a new task under "Backlog / Future Enhancements":
        *   `[ ] Task B7: Enhance AgentKit for Ops-Core Integration Readiness (SDK method, config, example, tests).`