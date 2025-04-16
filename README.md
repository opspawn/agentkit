# AgentKit Python Module (Opspawn)

[![CI Status](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml) <!-- Placeholder - Update with actual repo URL -->

Core Python module for the Opspawn AgentKit, enabling rapid prototyping and building of autonomous AI agents.

## Overview

AgentKit provides a foundational framework for developing AI agents in Python. It includes modules and APIs for:

*   **Agent Registration:** Registering agents with the system and managing their metadata.
*   **Messaging:** Sending structured messages between agents or external systems via a central API.
*   **Tool Integration:** Allowing agents to invoke registered tools (external APIs or internal functions).

This module is designed with a local-first approach for ease of development and testing, using FastAPI for the core API and Pydantic for data validation.

## Features

*   RESTful API for agent management and interaction.
*   Standardized JSON-based communication protocols.
*   In-memory storage for agent and tool registration (initially).
*   Basic Python SDK for client-side interaction.
*   Command-line interface (CLI) for testing and basic operations.
*   Extensible tool integration interface.
*   Containerized deployment using Docker.

## Getting Started

### Prerequisites

*   Python 3.9+
*   Docker & Docker Compose (optional, for running as a service)
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
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running Locally (Development Server)

You can run the AgentKit API server directly using Uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. The interactive API documentation (Swagger UI) can be accessed at `http://localhost:8000/docs`.

### Running with Docker Compose

To run the service using Docker:

1.  **Build the image:**
    ```bash
    docker-compose build
    ```

2.  **Start the service:**
    ```bash
    docker-compose up
    ```

The API will be available at `http://localhost:8000`.

## Usage

### Python SDK

The SDK provides a convenient way to interact with the AgentKit API from Python scripts or other agents.

```python
from agentkit.sdk.client import AgentKitClient, AgentKitError
from pydantic import HttpUrl

# Initialize the client (adjust base_url if API runs elsewhere)
client = AgentKitClient(base_url="http://localhost:8000")

try:
    # Register an agent
    agent_id = client.register_agent(
        agent_name="MyPythonAgent",
        capabilities=["process_data", "use_calculator"],
        version="1.1",
        contact_endpoint=HttpUrl("http://my-agent-service:9000/callback"),
        metadata={"description": "Processes incoming data streams."}
    )
    print(f"Agent registered with ID: {agent_id}")

    # Send a message (e.g., invoking a tool)
    response_data = client.send_message(
        target_agent_id=agent_id, # Can be self or another agent
        sender_id="external_trigger_001",
        message_type="tool_invocation",
        payload={
            "tool_name": "calculator", # Assuming a 'calculator' tool is registered
            "parameters": {"operation": "add", "a": 5, "b": 7}
        }
    )
    print(f"Message sent. Response data: {response_data}")

except AgentKitError as e:
    print(f"An AgentKit API error occurred: {e}")
    if e.response_data:
        print(f"Response: {e.response_data}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

```

*(More SDK examples to be added)*

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

# Example: Invoking a tool
python -m agentkit.cli.main send <TARGET_AGENT_ID> \
    --sender "cli_tool_user_02" \
    --type "tool_invocation" \
    '{"tool_name": "some_tool", "parameters": {"param1": "value1"}}'
```

*(Run `python -m agentkit.cli.main --help` for more details)*

## API Documentation

Interactive API documentation (Swagger UI) is available at the `/docs` endpoint when the server is running (e.g., `http://localhost:8000/docs`).

ReDoc documentation is available at `/redoc`.

## Project Structure

```
agentkit/          # Main package source code
├── api/           # FastAPI application, endpoints, middleware
├── cli/           # Command-line interface logic
├── core/          # Core models (Pydantic) and shared utilities
├── messaging/     # Logic related to message handling (TBD)
├── registration/  # Agent registration logic and storage
├── sdk/           # Python SDK client
└── tools/         # Tool interface and registry
tests/             # Unit and integration tests (pytest)
docs/              # Project documentation (Markdown)
examples/          # Example agent implementations (TBD)
memory-bank/       # Roo's Memory Bank for project context
.github/workflows/ # CI/CD workflows (GitHub Actions)
Dockerfile         # Container definition
docker-compose.yml # Docker Compose configuration
main.py            # FastAPI application entry point
requirements.txt   # Python dependencies
README.md          # This file
DEVELOPMENT_PLAN.md # Detailed development plan
PLANNING.md        # High-level project planning
TASK.md            # Task checklist
...
```

## Contributing

Please refer to `CONTRIBUTING.md` (to be created) for details on how to contribute to this project, including coding standards, pull request guidelines, and issue reporting.

## License

*(Specify License - e.g., MIT, Apache 2.0)* - TBD