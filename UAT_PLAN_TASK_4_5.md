# UAT Plan: Task 4.5 - AgentKit Python Module

## 1. Objective

Conduct User Acceptance Testing (UAT) for the AgentKit Python module by implementing and testing simple agent examples using the Python SDK. This validates core functionality (registration, messaging, tool invocation) from an end-user perspective.

## 2. UAT Scenarios

Two primary scenarios will be implemented and tested:

*   **Scenario 1: Ping Agent (`examples/ping_agent.py`)**
    *   An agent registers itself using the SDK.
    *   The agent sends a `ping` message type to itself via the SDK.
    *   Verification: The script confirms successful API acceptance for both registration and message sending.

*   **Scenario 2: Basic Tool User Agent (`examples/tool_user_agent.py`)**
    *   An agent registers itself using the SDK.
    *   The agent sends a message via the SDK designed to invoke the existing mock tool service (`tests/mock_services/mock_tool.py`).
    *   Verification: The script confirms successful API acceptance for both registration and message sending (implying the tool invocation request was processed by the API).

## 3. Implementation & Testing Steps

```mermaid
graph TD
    A[Start UAT Task 4.5] --> B{Define Scenarios};
    B -- Scenario 1 --> C[Ping Agent];
    B -- Scenario 2 --> D[Tool User Agent];
    C --> E;
    D --> E[Check examples/ Directory (Done - Empty)];
    E --> F[Implement Example Scripts];
    F --> G[Prepare Test Environment (Docker)];
    G --> H[Execute & Verify Examples];
    H --> I[Document UAT Results];
    I --> J[Update TASK.md & Memory Bank];
    J --> K[End UAT Task 4.5];

    style C fill:#f9f,stroke:#333,stroke-width:1px
    style D fill:#f9f,stroke:#333,stroke-width:1px
```

1.  **Define UAT Scenarios:** (Completed - See Section 2)
2.  **Explore `examples/` Directory:** (Completed - Directory is empty)
3.  **Implement Example Agents:**
    *   Create `examples/ping_agent.py`.
    *   Create `examples/tool_user_agent.py`.
    *   Utilize `agentkit.sdk.client.AgentKitClient` for registration and messaging.
    *   Adhere to project coding standards.
4.  **Prepare Testing Environment:**
    *   Ensure `docker-compose up -d` starts the AgentKit API and Mock Tool Service.
5.  **Test Examples:**
    *   Run `docker-compose up -d`.
    *   Execute `python examples/ping_agent.py`.
    *   Execute `python examples/tool_user_agent.py`.
    *   Verify successful execution and confirmation messages from scripts.
6.  **Document UAT:**
    *   Mark Task 4.5 complete in `TASK.md`.
    *   Update `memory-bank/activeContext.md` and `memory-bank/progress.md`.
    *   *(Optional)* Create `examples/README.md`.

## 4. Next Steps (Post-Plan Documentation)

Proceed with Step 3: Implement Example Agents.