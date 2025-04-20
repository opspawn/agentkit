# AgentKit & Ops-Core Integration Guide

## 1. Introduction

### Purpose
This guide explains how AI agents built using the **AgentKit** Python module interact with the **Ops-Core** system within the Opspawn ecosystem. AgentKit focuses on enabling the rapid development and prototyping of agents, while Ops-Core provides the infrastructure for managing agent lifecycles, tracking state, and orchestrating complex workflows involving multiple agents.

### Audience
This document is intended for developers building agents using the AgentKit Python module who need their agents to function correctly under Ops-Core management.

### Scope
This guide covers the essential communication points, required configurations, and data flows between AgentKit agents and the Ops-Core infrastructure. It focuses on how agents report their status and receive tasks.

## 2. Core Interaction Points

Successful integration relies on understanding these key interactions:

### Agent Registration & Synchronization
-   Agents are initially registered using the AgentKit SDK's `register_agent` method, which calls the AgentKit API (`POST /v1/agents/register`).
-   This registration provides AgentKit (and subsequently Ops-Core) with crucial metadata, including the agent's unique `agentId` and its `contactEndpoint` (the URL where the agent listens for messages).
-   Ops-Core needs this information to know which agents exist and how to potentially dispatch tasks to them via AgentKit.
-   **Webhook Notification:** To facilitate synchronization, the AgentKit API service can be configured to automatically send a webhook notification to Ops-Core immediately after an agent successfully registers. See the next section for details.

### Webhook Notifications (AgentKit -> Ops-Core)
-   **Purpose:** Allows AgentKit to proactively inform Ops-Core about agent lifecycle events, starting with registration.
-   **Mechanism:** When an agent registers via `POST /v1/agents/register`, the AgentKit service can send an asynchronous POST request to a pre-configured Ops-Core webhook URL.
-   **Configuration (AgentKit Service):** This requires the AgentKit service environment to have two variables set:
    *   `OPSCORE_WEBHOOK_URL`: The URL endpoint on the Ops-Core service that listens for these notifications.
    *   `OPSCORE_WEBHOOK_SECRET`: A shared secret key used by AgentKit to generate an HMAC-SHA256 signature for the webhook request.
    *   See the [Configuration Guide](configuration.md) for setup details.
-   **Security:** The webhook request includes `X-AgentKit-Timestamp` and `X-AgentKit-Signature` headers. Ops-Core uses the timestamp and the shared secret to compute its own signature and verify it against the one received, ensuring the request is authentic and hasn't been tampered with.
-   **Payload Sent to Ops-Core:** The JSON payload contains the event type and the registered agent's details. See `docs/agentkit_integration_for_opscore.md` for the exact payload structure.

### State Reporting (Agent -> Ops-Core)
-   **Requirement:** This is a critical integration point. Ops-Core **requires** agents to actively report their operational state (e.g., `initializing`, `idle`, `active`, `error`) so it can track their lifecycle and make informed decisions for workflow orchestration.
-   **Mechanism:** Agents **must** use the AgentKit SDK's asynchronous `report_state_to_opscore` method to send these updates directly to the Ops-Core API.
-   **SDK Method:**
    ```python
    await sdk_client.report_state_to_opscore(
        agent_id: str,
        state: str,          # e.g., "idle", "active", "error"
        details: Optional[dict] = None # Optional context, like error details
    )
    ```
-   **Configuration:** This SDK method requires two environment variables to be set in the agent's environment (e.g., via a `.env` file):
    *   `OPSCORE_API_URL`: The base URL of the running Ops-Core API service.
    *   `OPSCORE_API_KEY`: The API key needed to authenticate with the Ops-Core API.
    *   See the [Configuration Guide](configuration.md) for setup details.
-   **Underlying API Call:** The SDK method makes a direct call to the Ops-Core API: `POST /v1/opscore/agent/{agentId}/state`.
-   **Payload Sent to Ops-Core:** The JSON payload includes the agent's ID, the reported state, a UTC timestamp, and any optional details:
    ```json
    {
      "agentId": "your_agent_id",
      "timestamp": "2024-01-01T12:00:00.000000+00:00", // ISO 8601 format
      "state": "active",
      "details": {"current_task": "processing_data"} // Example details
    }
    ```
-   **Example:** The `examples/opscore_aware_agent.py` script provides a practical example of implementing state reporting within an agent.

### Workflow Initiation (Ops-Core -> Agent)
-   **Mechanism:** Ops-Core orchestrates workflows by sending tasks or commands to agents. It initiates this by making a request to the AgentKit API's `/v1/agents/{agentId}/run` endpoint with the task details.
-   **AgentKit Behavior (Task B9 Update):**
    *   For messages identified as **tool invocations**, AgentKit attempts to execute the tool synchronously and returns the result (or an error).
    *   For **all other messages** (including workflow tasks sent by Ops-Core), AgentKit now responds **immediately** to the caller (Ops-Core) with a `202 Accepted` status.
    *   AgentKit then schedules a **background task** to forward the original message payload to the target agent's registered `contactEndpoint`.
-   **Agent Responsibility:** The agent's own HTTP server (listening at its `contactEndpoint`) **must** still be implemented to:
    *   Receive incoming POST requests (now dispatched asynchronously by AgentKit).
    *   Parse the message payload (which will contain the task details sent by Ops-Core).
    *   Execute the requested task or command based on the `messageType` and `payload`.
    *   Remember to report state changes (`active`, `idle`, `error`) back to Ops-Core using `report_state_to_opscore` during and after task processing.

### Logging & Debugging
-   Ops-Core provides centralized logging.
-   By reporting state changes (especially `error` states with details), agents contribute valuable information to Ops-Core's monitoring and debugging capabilities.

## 3. Data Flow Diagram

This diagram illustrates the primary communication flows:

```mermaid
sequenceDiagram
    participant Agent
    participant AgentKit SDK
    participant AgentKit API
    participant Ops-Core API
    participant Ops-Core Internal

    Note over Agent, AgentKit SDK: Agent Registration
    Agent->>AgentKit SDK: register_agent(...)
    AgentKit SDK->>AgentKit API: POST /v1/agents/register
    AgentKit API-->>AgentKit SDK: Registration OK (201 Created, agentId)
    AgentKit SDK-->>Agent: agentId

    Note over AgentKit API, Ops-Core Internal: AgentKit Sends Webhook (Async)
    AgentKit API->>Ops-Core Internal: POST /webhook (Registration Payload + HMAC)
    Ops-Core Internal-->>AgentKit API: Webhook Ack (200 OK)

    Note over Ops-Core Internal, AgentKit API: Ops-Core Syncs Agent Info (Alternative/Backup)
    Ops-Core Internal->>AgentKit API: Sync/Fetch Registration Data (Mechanism TBD)
    AgentKit API-->>Ops-Core Internal: Agent Metadata (incl. contactEndpoint)

    Note over Agent, AgentKit SDK, Ops-Core API: Agent Reports Initial State
    Agent->>AgentKit SDK: report_state_to_opscore(agentId, "idle", ...)
    AgentKit SDK->>Ops-Core API: POST /v1/opscore/agent/{agentId}/state (Payload: state="idle", ...)
    Ops-Core API-->>AgentKit SDK: State Update OK
    AgentKit SDK-->>Agent: Report Success/Error

    Note over Ops-Core Internal, Ops-Core API, AgentKit API, Agent: Ops-Core Dispatches Task
    Ops-Core Internal->>Ops-Core API: Initiate Workflow for Agent
    Ops-Core API->>AgentKit API: POST /v1/agents/{agentId}/run (Workflow Task Message)
    AgentKit API-->>Ops-Core API: Task Accepted (202 Accepted)

    Note over AgentKit API, Agent: AgentKit Dispatches Task (Async)
    AgentKit API->>Agent: POST {contactEndpoint} (Forwarded Workflow Message)
    Agent-->>AgentKit API: Dispatch Ack (Agent's HTTP Response, e.g., 200 OK)

    Note over Agent, AgentKit SDK, Ops-Core API: Agent Processes Task & Reports State
    Agent->>Agent: Process Workflow Task...
    Agent->>AgentKit SDK: report_state_to_opscore(agentId, "active", ...)
    AgentKit SDK->>Ops-Core API: POST /v1/opscore/agent/{agentId}/state (Payload: state="active", ...)
    Ops-Core API-->>AgentKit SDK: State Update OK
    AgentKit SDK-->>Agent: Report Success/Error
    Agent->>Agent: ...Finish Task Processing
    Agent->>AgentKit SDK: report_state_to_opscore(agentId, "idle", ...)
    AgentKit SDK->>Ops-Core API: POST /v1/opscore/agent/{agentId}/state (Payload: state="idle", ...)
    Ops-Core API-->>AgentKit SDK: State Update OK
    AgentKit SDK-->>Agent: Report Success/Error
```

## 4. Implementation Guide for Agent Developers

To ensure your AgentKit agent integrates correctly with Ops-Core:

1.  **Configure Environment:** Set the `OPSCORE_API_URL` and `OPSCORE_API_KEY` environment variables in your agent's runtime environment (e.g., `.env` file).
2.  **Use Async SDK:** Initialize and use the asynchronous `AgentKitClient` from `agentkit.sdk.client`. Remember to `await` its methods and close it gracefully (`await client.close()`).
3.  **Implement State Reporting:** Call `await sdk_client.report_state_to_opscore(...)` at crucial points in your agent's lifecycle:
    *   After successful registration (e.g., report `idle`).
    *   When starting work on a received task (report `active`).
    *   After successfully completing a task (report `idle`).
    *   If an unrecoverable error occurs during processing (report `error` with relevant `details`).
4.  **Handle Workflow Messages:** Implement logic in your agent's message handler (the function receiving requests at its `contactEndpoint`) to recognize and process messages originating from Ops-Core (e.g., based on `messageType` like `"workflow_task"`). Remember that AgentKit dispatches these asynchronously after returning `202 Accepted` to the original caller (Ops-Core).
5.  **Error Handling:** Wrap calls to `report_state_to_opscore` in `try...except AgentKitError` blocks to handle potential failures in communicating with Ops-Core. Decide on your agent's behavior if state reporting fails (e.g., log the error, retry, enter a degraded state).
6.  **Refer to Example:** Study `examples/opscore_aware_agent.py` for a practical implementation within a FastAPI agent structure.

## 5. Future Considerations

As Ops-Core evolves, further integration points might emerge, such as:
*   More granular event reporting from agents.
*   Direct agent interaction with Ops-Core's advanced logging or tracing APIs.
*   Support for asynchronous notifications from Ops-Core to agents (beyond the current request/response message dispatch).

Keep an eye on Ops-Core documentation for future integration capabilities.