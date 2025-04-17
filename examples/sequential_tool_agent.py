"""
Example Agent: Sequential Tool User

This script demonstrates an agent that performs a sequence of actions:
1. Registers itself with the AgentKit API.
2. Invokes the 'mock_tool' via the API to get some data (simulated calculation).
3. If the first tool call is successful, it uses the result to construct a prompt.
4. Invokes the 'generic_llm_completion' tool via the API with the constructed prompt.
5. Prints the final response from the LLM.

This showcases handling tool results and chaining tool calls within agent logic.
Requires:
- AgentKit API running (with mock_tool registered, usually via docker-compose).
- .env file configured with API keys for the chosen LLM model.
"""

import os
from agentkit.sdk.client import AgentKitClient, AgentKitError

# --- Configuration ---
AGENTKIT_API_URL = os.getenv("AGENTKIT_API_URL", "http://localhost:8000/v1")
# Ensure this model is available and you have API keys in .env
LLM_MODEL_TO_USE = os.getenv("EXAMPLE_LLM_MODEL", "gpt-3.5-turbo")

def run_sequential_tool_agent():
    """Registers agent, calls mock_tool, then calls LLM tool with the result."""
    print(f"--- Running Sequential Tool User Example ---")
    print(f"Using AgentKit API at: {AGENTKIT_API_URL}")
    print(f"Using LLM Model: {LLM_MODEL_TO_USE} (ensure .env is configured)")

    client = AgentKitClient(base_url=AGENTKIT_API_URL)
    agent_id = None

    try:
        # 1. Register the Agent
        print("\nAttempting to register agent...")
        agent_name = "SequentialToolAgent"
        # Contact endpoint isn't needed as this agent only makes outbound calls
        contact_endpoint = "http://example.com/sequential_callback"

        agent_id = client.register_agent(
            agent_name=agent_name,
            capabilities=["sequential_tool_use", "mock_tool", "llm"],
            version="1.0.0",
            contact_endpoint=contact_endpoint,
            metadata={"example_type": "sequential_tool_agent"}
        )
        print(f"Agent registered successfully! Agent ID: {agent_id}")

        # 2. Call Mock Tool
        print(f"\nAttempting to call 'mock_tool'...")
        mock_tool_args = {"x": 15, "y": 7} # Example arguments
        mock_tool_response = client.send_message(
            target_agent_id=agent_id, # Target self for tool call routing
            sender_id=agent_id,
            message_type="tool_invocation",
            payload={"tool_name": "mock_tool", "arguments": mock_tool_args}
        )
        print(f"Mock tool response received: {mock_tool_response}")

        # Check if mock_tool call was successful and extract result
        # Note: The structure depends on how mock_tool returns data.
        # Assuming it returns something like: {'status': 'success', 'result': {'sum': 22}}
        # Adjust extraction logic based on actual mock_tool implementation if needed.
        mock_tool_result_data = None
        if isinstance(mock_tool_response, dict) and mock_tool_response.get("status") == "success":
             # Let's assume the actual result is nested within 'data' based on ApiResponse model
             tool_output = mock_tool_response.get("data", {})
             if isinstance(tool_output, dict):
                  # Further assume the mock tool itself returns a dict with a 'result' key
                  mock_tool_result_data = tool_output.get("result") # Or adjust key as needed

        if mock_tool_result_data is None:
             print("\nMock tool did not return a successful result. Aborting LLM call.")
             return

        print(f"Extracted result from mock_tool: {mock_tool_result_data}")

        # 3. Call Generic LLM Tool using the result
        print(f"\nAttempting to call 'generic_llm_completion'...")

        # Construct prompt using the result
        # Ensure result is serializable (e.g., convert number to string if needed)
        prompt = f"Explain the significance or properties of the following data obtained from a previous step: {str(mock_tool_result_data)}"
        messages = [{"role": "user", "content": prompt}]

        llm_response = client.send_message(
            target_agent_id=agent_id, # Target self for tool call routing
            sender_id=agent_id,
            message_type="tool_invocation",
            payload={
                "tool_name": "generic_llm_completion",
                "arguments": {
                    "model": LLM_MODEL_TO_USE,
                    "messages": messages
                }
            }
        )
        print(f"LLM tool response received.")

        # Extract and print the LLM's content
        llm_content = "Could not extract LLM content."
        if isinstance(llm_response, dict) and llm_response.get("status") == "success":
            llm_data = llm_response.get("data", {})
            # Structure depends on litellm response, often choices[0].message.content
            try:
                llm_content = llm_data['choices'][0]['message']['content']
            except (KeyError, IndexError, TypeError):
                print(f"Could not parse LLM content from response data: {llm_data}")
                llm_content = f"Raw LLM Response Data: {llm_data}" # Show raw if parsing fails

        print("\n--- Final LLM Response ---")
        print(llm_content)
        print("--------------------------")


    except AgentKitError as e:
        print(f"\nAn AgentKit API error occurred: {e}")
        if e.detail:
            print(f"Details: {e.detail}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\n--- Sequential Tool User Example Finished ---")

if __name__ == "__main__":
    # Ensure mock_tool is running, e.g., via docker-compose up api mock_tool
    # Ensure .env file is configured for the LLM model
    run_sequential_tool_agent()