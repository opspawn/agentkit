# System Patterns: AgentKit Python Module

## 1. Architecture Overview

AgentKit follows a modular, layered architecture designed for local-first development with future scalability in mind.

-   **Modularity:** Core functionalities are separated into distinct modules:
    -   Agent Registration Module
    -   Messaging Interface Module
    -   Tool Integration Module
    -   Python SDK (wraps API interactions)
    This separation allows for independent development, testing, and potential replacement or enhancement of individual parts.
-   **Layered Design:**
    1.  **Interface Layer:** Exposes RESTful API endpoints (built with Flask/FastAPI) for external interaction (e.g., agent registration, message sending). Standardized JSON schemas are used for data exchange.
    2.  **Core Logic Layer:** Contains the business logic for each module (registration validation, message parsing/dispatching, tool invocation logic).
    3.  **Integration/Middleware Layer:** Handles cross-cutting concerns like standardized data formatting (including metadata), error handling, and structured logging.
    4.  **(Future) Data Layer:** Initially uses in-memory storage (Python dict or Redis) for agent metadata and tool registry, with plans for potential integration with persistent storage later.
-   **Local-First Approach:** Designed to run efficiently on a local machine, likely using Docker/Docker Compose for environment consistency and multi-agent simulation. Clear adaptation plans are intended for future cloud deployment.
-   **Standardized Communication:** Relies heavily on well-defined RESTful APIs and JSON schemas for all interactions (agent-to-system, potentially agent-to-agent via the system). This ensures interoperability and simplifies integration with other Opspawn components or future language SDKs.

## 2. Core Components & Relationships

-   **Agent Registration Module:**
    -   Receives registration requests via `POST /agents/register`.
    -   Validates payload against a JSON schema.
    -   Generates a unique Agent ID.
    -   Stores agent metadata (name, capabilities, version, contactEndpoint, custom metadata) in the chosen storage (initially in-memory/Redis).
    -   Returns registration confirmation.
-   **Messaging Interface Module:**
    -   Receives messages via `POST /agents/{agentId}/run`.
    -   Parses the standardized JSON message payload (including sender/receiver IDs, type, payload, context).
    -   Dispatches the message/command to the target agent (likely by invoking its `contactEndpoint` or an internal handler if applicable).
    -   Handles synchronous responses and potentially asynchronous notifications (future).
    -   Standardizes response formats.
-   **Tool Integration Module:**
    -   Provides a generic interface (e.g., Python abstract base class) for external tools.
    -   Maintains a Tool Catalog/Registry (likely JSON-based) listing available tools, their interfaces, and necessary metadata (e.g., authentication, parameter mapping).
    -   Handles the invocation of tools based on agent requests, managing parameter mapping and response standardization.
    -   Designed for plug-and-play addition/update of tools.
-   **Python SDK:**
    -   Acts as a client library for developers.
    -   Wraps the REST API calls for registration, messaging, and tool use into convenient Python functions.
    -   Provides type hints and clear documentation to simplify development.

## 3. Key Technical Decisions & Patterns

-   **API:** RESTful HTTP endpoints are the primary interaction method.
-   **Data Format:** JSON is the universal data exchange format, with strict schema validation enforced.
-   **Framework:** Flask or FastAPI for the Python API implementation.
-   **Storage (Initial):** In-memory dictionary or Redis for agent registration and tool catalog data. This prioritizes speed for local development but requires a plan for persistence if needed long-term.
-   **Tool Integration:** Abstract Base Class (ABC) or similar interface pattern in Python to define a standard contract for all tool connectors. Registry pattern for managing available tools.
-   **Containerization:** Docker and Docker Compose are planned for packaging and local multi-agent simulation.
-   **Error Handling:** Standard HTTP status codes combined with structured JSON error responses (including error codes and messages). Try-catch patterns within modules.
-   **Logging:** Structured logging (likely JSON format) for key events to facilitate debugging and potential future log aggregation.

## 4. Critical Implementation Paths

-   Defining and enforcing the JSON schemas for registration, messaging, and tool interactions is critical for interoperability.
-   Implementing the core logic for message dispatching and response handling in the Messaging Interface Module.
-   Designing a flexible and extensible Tool Connector Interface and registry mechanism.
-   Ensuring the Python SDK accurately and conveniently reflects the API capabilities.