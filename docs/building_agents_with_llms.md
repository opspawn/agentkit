# Building AgentKit Agents with LLM Assistants

## 1. Introduction

This guide helps developers leverage Large Language Models (LLMs) like Claude, Gemini, ChatGPT, or LLM-integrated coding tools (e.g., Aider, Cursor, GitHub Copilot Chat) to accelerate the development of functional, standalone agents using the Opspawn AgentKit Python module.

Using an LLM assistant can significantly speed up the creation of core agent functionality by:
*   Generating boilerplate code for agent servers (FastAPI/Flask).
*   Scaffolding message handlers and AgentKit SDK usage patterns.
*   Assisting with implementing specific agent logic and tool integrations.
*   Helping generate unit tests for agent logic.

## 2. Setup Prerequisites

Before you start prompting an LLM assistant, ensure you have the AgentKit project set up locally. The LLM will generate code intended to run within this project structure.

1.  **Clone the Repository:**
   ```bash
   git clone https://github.com/opspawn/agentkit.git
   cd agentkit
   ```
2.  **Create Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   # On Windows use: .venv\Scripts\activate
   ```
3.  **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4.  **(Optional) Setup `.env`:** If your agent will use tools requiring API keys (like the `GenericLLMTool`), create a `.env` file in the project root and add the necessary keys. See `docs/configuration.md` for details.

With the project cloned and dependencies installed, you are ready to provide context to your LLM assistant.

## 3. Preparing the Context for the LLM

For an LLM assistant to effectively help you build an AgentKit agent, it needs sufficient context about the framework, its SDK, configuration, and examples. Instead of manually gathering and pasting multiple files, we provide a single, comprehensive context file:

**`docs/agentkit_llm_context.txt`**

**Action:** Copy the *entire contents* of `docs/agentkit_llm_context.txt` and paste it at the beginning of your conversation or prompt with the LLM assistant.

This file contains concatenated versions of key documentation (`README.md`, `configuration.md`, `TUTORIAL.md`), the SDK client code (`agentkit/sdk/client.py`), core data models, and relevant examples. Providing this upfront gives the LLM a strong foundation to understand your requests accurately.

## 4. Describing the Desired Agent to the LLM

Once you've provided the context from `agentkit_llm_context.txt`, clearly describe the agent you want to build. Be specific in your prompts. Include details like:

*   **Agent's Core Purpose:** What is the primary function or goal of this agent? (e.g., "An agent that monitors a specific API endpoint and reports changes," "An agent that uses an LLM tool to summarize text provided in messages").
*   **Agent Framework:** Specify the web framework for the agent's `contactEndpoint`. (e.g., "Use FastAPI for the agent server," "Use Flask"). *FastAPI is recommended based on examples.*
*   **Capabilities:** List the agent's intended capabilities (this is primarily for the registration metadata). (e.g., `["monitor_api", "report_changes"]`, `["summarize_text", "use_llm"]`).
*   **Message Handling:** Define the `messageType` values the agent should listen for and process at its `contactEndpoint`. Describe the logic required for each type. (e.g., "Handle messageType 'summarize_request' by extracting text from the payload," "Handle messageType 'check_endpoint'").
*   **Tool Usage:** Specify which AgentKit tools the agent needs to invoke using `await sdk.send_message(...)` with `message_type="tool_invocation"`. Include the tool name (e.g., `generic_llm_completion`, `mock_tool`) and the required arguments.
*   **Ops-Core Readiness (Optional):** If the agent might later integrate with Ops-Core, you can optionally ask the LLM to include the *structure* for state reporting. Specify: "Include calls to `await sdk.report_state_to_opscore(...)` at key lifecycle points (registration, task start/end, error) to make the agent Ops-Core ready. Note that this requires `OPSCORE_API_URL` and `OPSCORE_API_KEY` configuration later." *Initially, focus on core functionality and omit this unless needed for future compatibility.*
*   **Dependencies:** List any *additional* Python libraries the agent's specific logic requires (beyond AgentKit's own dependencies like FastAPI, httpx, etc.).
*   **Configuration:** Mention any specific environment variables the agent logic will need (beyond the standard AgentKit ones loaded via `.env`).

**Example Prompt Snippet (Focusing on Standalone Functionality):**

> "Using the provided AgentKit context, please generate the Python code for a FastAPI-based agent named 'SummarizerAgent'.
> Its capabilities are ['summarize_text', 'use_llm'].
> It should handle incoming messages with messageType 'summarize_request'. When it receives this message, it should extract the 'text_to_summarize' field from the payload.
> Then, it should use the AgentKit SDK's `send_message` method to invoke the 'generic_llm_completion' tool, passing the extracted text to the 'gpt-4o' model with a prompt asking for a concise summary.
> Log informational messages during processing."
> *(Note: This example explicitly omits Ops-Core state reporting for simplicity)*

## 5. Working Iteratively with the LLM Assistant

Don't expect the LLM to generate the perfect agent in one shot. Work iteratively:

*   **Start Simple:** Ask for the basic agent structure first (FastAPI app setup, SDK initialization, registration on startup, basic `contactEndpoint` route).
*   **Add Features Incrementally:** Ask the LLM to add specific pieces of logic one by one (e.g., "Now add the logic to handle the 'summarize_request' messageType," "Add the call to the 'generic_llm_completion' tool"). If planning for Ops-Core later, you could ask separately: "Now, add the calls to `report_state_to_opscore` to make this agent Ops-Core ready."
*   **Ask for Explanations:** If the LLM generates code you don't understand, ask it to explain that specific part.
*   **Request Refinements:** Ask for improvements: "Add logging to this function," "Add error handling using try/except AgentKitError around the SDK calls," "Can you make this part more efficient?".
*   **Generate Tests:** Ask the LLM to help generate `pytest` unit tests for your agent's message handling logic or other custom functions.

## 6. Key AgentKit Features LLMs Can Help Implement

LLMs trained on code and provided with the `agentkit_llm_context.txt` should be able to help generate code for:

*   Setting up the agent's web server (FastAPI/Flask).
*   Implementing the `contactEndpoint` route (`@app.post("/")`) and parsing the `IncomingMessage` model.
*   Correctly using the asynchronous `AgentKitClient` SDK methods (`await client.register_agent(...)`, `await client.send_message(...)`).
*   *Optionally*, implementing calls to `await client.report_state_to_opscore(...)` if specifically requested for Ops-Core readiness.
*   Loading environment variables using `python-dotenv`.
*   Basic Python `logging` setup.
*   Implementing standard Python logic within message handlers or helper functions.

## 7. Best Practices for LLM-Assisted Agent Development

*   **Provide Context:** Always start by providing the content of `docs/agentkit_llm_context.txt`.
*   **Be Specific:** Clearly define requirements in your prompts.
*   **Iterate:** Build the agent piece by piece.
*   **Emphasize Async:** Remind the LLM that the AgentKit SDK is asynchronous and requires `async`/`await`.
*   **Configuration:** Instruct the LLM to rely on environment variables (`.env`) for configuration (API keys, URLs).
*   **Error Handling:** Explicitly ask for `try...except AgentKitError` blocks around SDK calls.
*   **Focus:** Prioritize core AgentKit functionality (registration, message handling, tool use) first. Add Ops-Core state reporting logic only if explicitly requested for future compatibility.
*   **Review Critically:** **Never** blindly trust or run LLM-generated code. Always review it carefully.

## 8. Next Steps (After LLM Generation)

1.  **Human Review:** **Thoroughly review all generated code.** Check for:
    *   Correctness: Does it do what you asked?
    *   Security: Are inputs handled safely? Are secrets exposed?
    *   Efficiency: Is the logic reasonable?
    *   Adherence to AgentKit patterns (async SDK usage, error handling).
2.  **Testing:**
    *   Run any generated unit tests (`pytest`).
    *   Write additional tests as needed.
    *   Run the agent locally.
    *   Test its interaction with a running AgentKit API (use `docker-compose up`).
    *   If Ops-Core state reporting logic was included, test it against a mock Ops-Core endpoint (using tools like `pytest-httpserver` or a simple mock server).
    3.  **Refinement:** Manually add more sophisticated error handling, logging, comments, and type hints as needed to meet project standards.
    4.  **Deployment:** Plan how your agent will be deployed (e.g., as a standalone Docker container).

By following this process, you can effectively partner with LLM assistants to build robust and functional standalone agents using the Opspawn AgentKit, while also preparing them for potential future integration with Ops-Core if needed.