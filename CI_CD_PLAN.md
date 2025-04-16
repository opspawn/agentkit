# Plan for Task 4.3: Refine CI/CD Pipeline

This document outlines the plan to refine the GitHub Actions CI/CD workflow (`.github/workflows/ci.yml`) for the AgentKit Python Module.

**Objective:** Implement Task 4.3 - Refine the GitHub Actions CI/CD pipeline.

**Requirements:** The pipeline must:
*   Run unit tests (`pytest tests/`).
*   Run integration tests (`pytest tests/integration/`), which require Docker Compose (`docker-compose.yml`) to be running.
*   Enforce linting (`flake8`).
*   Check code formatting (`black --check`).
*   Generate and report code coverage (`pytest-cov`).

**Plan Steps:**

1.  **Restructure Jobs:** Split the current `lint-and-test` job into three distinct jobs:
    *   `lint-and-format`: Runs `flake8` and `black --check` on Python 3.9.
    *   `unit-tests`: Runs unit tests (`pytest tests/ --ignore=tests/integration`) using the Python version matrix (`3.9` - `3.12`). Generates code coverage reports.
    *   `integration-tests`: Runs integration tests (`pytest tests/integration/`) on Python 3.9, managing the Docker Compose environment.

2.  **Implement Code Coverage:**
    *   Ensure `pytest-cov` is installed in the `unit-tests` job.
    *   Modify the `pytest` command to: `pytest tests/ --cov=agentkit --cov-report=term --cov-report=xml --ignore=tests/integration`.
    *   Add a step to upload the generated `coverage.xml` file as a build artifact using `actions/upload-artifact@v4`.

3.  **Enable Integration Testing:**
    *   In the `integration-tests` job:
        *   Use `ubuntu-latest` runner.
        *   Set up Python 3.9.
        *   Install dependencies.
        *   Build Docker services: `docker-compose build`
        *   Start Docker services: `docker-compose up -d`
        *   Wait for services to be ready (e.g., `sleep 15`).
        *   Run integration tests: `pytest tests/integration/`
        *   Add a final step (`if: always()`) to stop and remove Docker containers: `docker-compose down`

**Proposed Workflow Structure:**

```mermaid
graph TD
    Start[Push/PR on main/develop] --> LintFormat[Lint & Format Job (Python 3.9)]
    Start --> UnitTests[Unit Tests Job (Matrix: Py 3.9-3.12)]
    Start --> IntegrationTests[Integration Tests Job (Python 3.9)]

    subgraph UnitTests
        direction TB
        UT_Setup[Setup Python ${{ matrix.python-version }}] --> UT_Install[Install Deps (incl. pytest-cov)]
        UT_Install --> UT_Run[Run pytest tests/ --cov --ignore=tests/integration]
        UT_Run --> UT_Upload[Upload coverage.xml]
    end

    subgraph IntegrationTests
        direction TB
        IT_Setup[Setup Python 3.9] --> IT_Install[Install Deps]
        IT_Install --> IT_DockerBuild[Docker Compose Build]
        IT_DockerBuild --> IT_DockerUp[Docker Compose Up -d]
        IT_DockerUp --> IT_Wait[Wait for Services (e.g., sleep 15)]
        IT_Wait --> IT_Run[Run pytest tests/integration/]
        IT_Run --> IT_DockerDown[Docker Compose Down (always runs)]
    end

    LintFormat --> End{CI Pass/Fail}
    UnitTests --> End
    IntegrationTests --> End

    style Start fill:#f9f
    style End fill:#f9f
```

**Decision:** Coverage reports (`coverage.xml`) will be uploaded as build artifacts.