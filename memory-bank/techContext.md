# Tech Context: AgentKit Python Module

## 1. Core Technologies

-   **Programming Language:** Python (Version 3.9+ required). This is the primary language for the initial module and SDK development.
-   **Web Framework:** **FastAPI**. Chosen for built-in Pydantic validation and automatic OpenAPI documentation generation, aligning with project goals for standardization and developer experience.
-   **Data Format:** JSON. This is the standard for all API request/response payloads and internal data structures like the tool catalog. Strict JSON Schema validation will be implemented.
-   **Initial Data Storage:** **In-memory Python dictionary**. Chosen for simplicity and speed in local-first development and rapid prototyping. Redis integration is deferred.

## 2. Development & Testing Environment

-   **Package Management:** Standard Python tools (pip, venv). Requirements will be managed via `requirements.txt` or similar.
-   **Testing Framework:** `pytest` is the designated tool for writing and running unit and integration tests for the Python code.
-   **Containerization:** Docker is planned for packaging the application. Docker Compose will be used to orchestrate multi-container setups for local testing (e.g., simulating multiple agents or dependencies like Redis if used).
-   **Version Control:** Git (repository hosted on GitHub, GitLab, etc.).
-   **Continuous Integration/Continuous Deployment (CI/CD):** GitHub Actions are planned to automate testing (running `pytest`), linting (e.g., using `flake8` or `pylint`), and code formatting (e.g., using `black`) on commits/pull requests.

## 3. Key Libraries & Dependencies (Planned/Potential)

-   **FastAPI:** For the web server/API.
-   **Uvicorn:** ASGI server to run FastAPI.
-   **Pydantic:** Likely used for data validation (especially if using FastAPI) and defining data models based on JSON schemas.
-   **Requests:** For the Python SDK to make HTTP calls to the AgentKit API.
-   **(Deferred) Redis-py:** If Redis is integrated later.
-   **Pytest:** For testing.
-   **Black, Flake8/Pylint:** For code formatting and linting.

## 4. Technical Constraints & Considerations

-   **Python Version:** Must maintain compatibility with Python 3.9 and later.
-   **Local-First Performance:** The system must run efficiently on typical developer machines without excessive resource consumption.
-   **Security:** Input validation (via JSON schemas and potentially Pydantic) is crucial. Secure API design principles must be followed. No sensitive data should be stored insecurely.
-   **Interoperability:** Strict adherence to the defined JSON schemas and REST API conventions is necessary for future integration with other Opspawn components and language SDKs (like TypeScript).
-   **Statelessness (API):** API endpoints should ideally be stateless, relying on data passed in requests or retrieved from the storage layer.
-   **Non-goals (Initial):** Complex cloud orchestration, persistent database integration (beyond Redis exploration), advanced asynchronous messaging patterns (initially focus on synchronous REST).

## 5. Tool Usage Patterns

-   **API Development:** Use **FastAPI** following standard practices for routing, request handling, Pydantic model validation, dependency injection, and response generation.
-   **Testing:** Write tests using `pytest`, covering different scenarios (happy path, edge cases, error conditions). Use fixtures and mocking where appropriate.
-   **CI/CD:** Configure GitHub Actions workflows to trigger on pushes/PRs to relevant branches, running linting, formatting checks, and `pytest`.
-   **Documentation:** Leverage **FastAPI's automatic Swagger/OpenAPI documentation generation**. Maintain README and other Markdown docs.