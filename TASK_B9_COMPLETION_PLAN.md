# Plan to Complete Task B9: Fix Tests & Update Docs

**Objective:** Complete Task B9 - Ops-Core Service Features, which involves fixing remaining test failures and updating documentation.

## Steps

1.  **Identify Failing Tests:**
    *   Execute `pytest` to get a detailed report of the 11 failing tests (file names, line numbers, errors).

2.  **Analyze Test Failures:**
    *   Categorize failures based on `pytest` output and `activeContext.md` insights (e.g., integration tests, background task issues).
    *   Prioritize fixing `tests/integration/test_workflows.py`, potentially refactoring to use `TestClient` and mocking instead of a live service.

3.  **Fix Tests:**
    *   Implement code changes in identified test files.
    *   Ensure mocks (`pytest-httpx`, `pytest-httpserver`) are correctly configured.
    *   Verify test environment configuration (`.env`).

4.  **Verify Test Fixes:**
    *   Run `pytest` again to confirm all relevant tests pass.

5.  **Update Documentation:**
    *   Review code changes in `agentkit/api/endpoints/registration.py`, `agentkit/api/endpoints/messaging.py`, `agentkit/core/models.py`.
    *   **`docs/opscore_integration.md`:** Explain webhook configuration and async `/run` behavior for AgentKit developers.
    *   **`docs/agentkit_integration_for_opscore.md`:** Detail webhook payload, HMAC verification, and async dispatch flow for Ops-Core developers.
    *   **`README.md` & `docs/TUTORIAL.md`:** Briefly mention new features and link to detailed guides.
    *   **`docs/configuration.md`:** Ensure webhook environment variables (`OPSCORE_WEBHOOK_URL`, `OPSCORE_WEBHOOK_SECRET`) are documented.

6.  **Finalize Task Status:**
    *   Update `TASK.md`: Mark Task B9 as complete.
    *   Update `memory-bank/progress.md`: Move Task B9 to "Completed".
    *   Update `memory-bank/activeContext.md`: Update focus, changes, and next steps.

## Plan Visualization

```mermaid
graph TD
    A[Start B9 Completion] --> B(Run pytest);
    B --> C{Analyze Failures};
    C --> D[Prioritize Workflow/Integration Tests];
    D --> E[Fix Tests (Refactor/Adjust Mocks)];
    E --> F(Run pytest again);
    F -- Pass --> G{Update Documentation};
    F -- Fail --> E;
    G --> H[Update opscore_integration.md];
    G --> I[Update agentkit_integration_for_opscore.md];
    G --> J[Update README/TUTORIAL];
    G --> K[Update configuration.md];
    H & I & J & K --> L[Update TASK.md & Memory Bank];
    L --> M[Plan Complete];