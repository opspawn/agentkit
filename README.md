# AgentKit Python Module (Opspawn)

[![CI Status](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml) <!-- Placeholder - Update with actual repo URL -->

Core Python module for the Opspawn AgentKit, enabling rapid prototyping and building of autonomous AI agents.

## Overview

AgentKit provides a foundational framework for developing AI agents in Python. It includes modules and APIs for:

*   **Agent Registration:** Registering agents with the system and managing their metadata.
*   **Messaging:** Sending structured messages between agents or external systems via a central API.
*   **Tool Integration:** Allowing agents to invoke registered tools (external APIs or internal functions).

This module is designed with a local-first approach for ease of development and testing, using FastAPI for the core API and Pydantic for data validation. Core functionality has been validated through unit, integration, load, and user acceptance testing.

## Features

*   RESTful API for agent management and interaction.
*   Standardized JSON-based communication protocols.
*   In-memory storage for agent and tool registration.
*   Python SDK for client-side interaction.
*   Command-line interface (CLI) for testing and basic operations.
*   Extensible tool integration interface (supports external HTTP tools).
*   Containerized deployment using Docker.
*   Example agents demonstrating core SDK usage.

## Getting Started

### Prerequisites

*   Python 3.9+
*   Docker & Docker Compose
*   Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_ORG/YOUR_REPO.git # Placeholder - Update URL
    cd YOUR_REPO
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    # On Windows use: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running Locally (Development Server)

You can run the AgentKit API server directly using Uvicorn (useful for development):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. The interactive API documentation (Swagger UI) can be accessed at `http://localhost:8000/docs`. Note that the mock tool service will not be available when running this way.

### Running with Docker Compose (Recommended for Full Functionality)

This method runs the AgentKit API and the mock tool service, required for some examples.

1.  **Build and start the services:**
    ```bash
    docker-compose up -d --build
    ```

The API will be available at `http://localhost:8000`.

To stop the services:
```bash
docker-compose down
```

## Usage

### Python SDK

The SDK provides a convenient way to interact with the AgentKit API from Python scripts.

```python
from agentkit.sdk.client import AgentKitClient, AgentKitError
# Note: HttpUrl validation is handled internally by the SDK now.
# Pass endpoint as a string.

# Initialize the client (adjust base_url if API runs elsewhere)
# Assumes API is running via Docker Compose at default port
client = AgentKitClient(base_url="http://localhost:8000/v1") # Ensure /v1 prefix

try:
    # Register an agent
    agent_id = client.register_agent(
        agent_name="MyPythonAgentSDK",
        capabilities=["process_data", "use_calculator"],
        version="1.2",
        contact_endpoint="http://my-agent-service:9000/callback", # Placeholder
        metadata={"description": "Processes incoming data streams."}
    )
    print(f"Agent registered with ID: {agent_id}")

    # Send a message (e.g., invoking the mock tool)
    response_data = client.send_message(
        target_agent_id=agent_id, # Can be self or another agent
        sender_id="sdk_trigger_001",
        message_type="tool_invocation",
        payload={
            "tool_name": "mock_tool", # Use the registered mock tool
            "arguments": {"query": "Test query from SDK"}
        },
        session_context={"example_session": "sdk_run_1"}
    )
    print(f"Message sent. Response data: {response_data}")

except AgentKitError as e:
    print(f"An AgentKit API error occurred: {e}")
    if e.response_data:
        print(f"Response: {e.response_data}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

```

### Command-Line Interface (CLI)

The CLI offers quick commands for common tasks.

**Register an agent:**

```bash
python -m agentkit.cli.main register \
    --name "MyCliAgent" \
    --version "1.0" \
    --endpoint "http://my-cli-agent.local/api" \
    --capability "reporting" \
    --capability "logging" \
    --metadata '{"description": "Agent registered via CLI"}'
```

**Send a message:**

```bash
# Example: Sending a simple query
python -m agentkit.cli.main send <TARGET_AGENT_ID> \
    --sender "cli_sender_01" \
    --type "intent_query" \
    '{"query": "What is the current status?"}'

# Example: Invoking the mock tool
python -m agentkit.cli.main send <TARGET_AGENT_ID> \
    --sender "cli_tool_user_02" \
    --type "tool_invocation" \
    '{"tool_name": "mock_tool", "arguments": {"query": "Test query from CLI"}}'
```

*(Run `python -m agentkit.cli.main --help` for more details)*

### Running Examples

The `examples/` directory contains scripts demonstrating SDK usage.

**Prerequisites:** Ensure the AgentKit services are running via Docker Compose:
```bash
docker-compose up -d --build
```

**Run the Ping Agent example:**
```bash
python examples/ping_agent.py
```
This script registers an agent and sends a message to itself.

**Run the Tool User Agent example:**
```bash
python examples/tool_user_agent.py
```
This script registers an agent and sends a message to invoke the `mock_tool`.

## API Documentation

Interactive API documentation (Swagger UI) is available at the `/docs` endpoint when the server is running (e.g., `http://localhost:8000/docs`).

ReDoc documentation is available at `/redoc`.

## Project Structure

```
agentkit/          # Main package source code
├── api/           # FastAPI application, endpoints, middleware
├── cli/           # Command-line interface logic
├── core/          # Core models (Pydantic) and shared utilities
├── messaging/     # Logic related to message handling
├── registration/  # Agent registration logic and storage
├── sdk/           # Python SDK client
└── tools/         # Tool interface and registry
tests/             # Unit and integration tests (pytest)
├── api/
├── cli/
├── integration/
├── mock_services/ # Mock external services for testing
├── registration/
├── sdk/
└── tools/
docs/              # Project documentation (Markdown)
examples/          # Example agent implementations
├── ping_agent.py
└── tool_user_agent.py
memory-bank/       # Roo's Memory Bank for project context
.github/workflows/ # CI/CD workflows (GitHub Actions)
├── ci.yml
.coverage          # Test coverage report data
AgentkitDevelopmentDoc.md # Original development requirements doc
DEVELOPMENT_PLAN.md # Detailed development plan
Dockerfile         # Container definition for API service
docker-compose.yml # Docker Compose configuration
locustfile.py      # Locust load test definition
main.py            # FastAPI application entry point
PLANNING.md        # High-level project planning
README.md          # This file
requirements.txt   # Python dependencies
TASK.md            # Task checklist
TESTING_STRATEGY.md # Detailed testing strategy
UAT_PLAN_TASK_4_5.md # User Acceptance Test plan for Task 4.5
```

## Contributing

Please refer to `CONTRIBUTING.md` (to be created) for details on how to contribute to this project, including coding standards, pull request guidelines, and issue reporting.

## License

*(Specify License - e.g., MIT, Apache 2.0)* - TBD