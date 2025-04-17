import os
from agentkit.sdk.client import AgentKitClient, AgentKitError
from pydantic import HttpUrl

# --- Configuration ---
# Ensure the AgentKit API is running, typically via: uvicorn main:app --reload
AGENTKIT_API_BASE_URL = os.getenv("AGENTKIT_URL", "http://127.0.0.1:8000")

# --- Prerequisites ---
# 1. AgentKit API must be running at AGENTKIT_API_BASE_URL.
# 2. A .env file must exist in the project root containing the API key
#    for the desired LLM provider (e.g., OPENAI_API_KEY=sk-...).
#    The GenericLLMTool loads this file.

def run_llm_tool_example():
    """
    Demonstrates invoking the GenericLLMTool via the AgentKit SDK.
    """
    print(f"Connecting to AgentKit API at: {AGENTKIT_API_BASE_URL}")
    client = AgentKitClient(base_url=AGENTKIT_API_BASE_URL)

    # --- Register a Dummy Agent ---
    # The API endpoint /v1/agents/{agent_id}/run requires a valid agent_id,
    # even though the tool invocation itself is handled centrally by the API
    # based on the tool registry. We register a dummy agent here just to
    # get an ID to use in the path.
    dummy_agent_id = None
    try:
        dummy_agent_name = "dummy_agent_for_tool_test"
        dummy_endpoint = HttpUrl("http://localhost:9999/dummy") # Doesn't need to be reachable
        print(f"Registering dummy agent '{dummy_agent_name}'...")
        dummy_agent_id = client.register_agent(
            agent_name=dummy_agent_name,
            capabilities=["placeholder"],
            version="1.0",
            contact_endpoint=dummy_endpoint,
            metadata={"description": "Temporary agent to satisfy API route for tool invocation"}
        )
        print(f"Dummy agent registered with ID: {dummy_agent_id}")
    except AgentKitError as e:
        print(f"Error registering dummy agent: {e}")
        # Check if it's a conflict error (agent might already exist from previous run)
        if e.status_code == 409: # Assuming 409 Conflict for existing agent name
             print("Dummy agent might already exist. Attempting to proceed...")
             # In a real scenario, you might want to fetch the existing ID
             # For this example, we'll just hardcode the name as the ID if registration fails with 409
             # THIS IS NOT ROBUST - assumes the API uses name as ID on conflict, which it likely doesn't.
             # A better approach would be to list agents or handle the error more gracefully.
             # For simplicity here, we'll just try to use the name.
             dummy_agent_id = dummy_agent_name # Fallback - likely won't work unless API is modified
        else:
            return # Stop if registration failed for other reasons

    if not dummy_agent_id:
         print("Could not obtain a valid dummy agent ID. Exiting.")
         return

    # --- Define LLM Tool Parameters ---
    # IMPORTANT: Replace 'gpt-3.5-turbo' with a model you have API key access to
    #            via the .env file (e.g., 'claude-3-haiku-20240307', 'gemini/gemini-1.5-flash').
    llm_model = "gpt-3.5-turbo"
    llm_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain the concept of asynchronous programming in Python in simple terms."}
    ]

    # --- Prepare Tool Invocation Payload ---
    tool_payload = {
        "tool_name": "generic_llm_completion",
        "arguments": {
            "model": llm_model,
            "messages": llm_messages,
            "max_tokens": 150, # Optional
            "temperature": 0.7 # Optional
        }
    }

    # --- Send Message to Invoke Tool ---
    print(f"\nInvoking tool '{tool_payload['tool_name']}' via agent endpoint {dummy_agent_id}...")
    try:
        # The sender_id can be anything descriptive for this type of call
        sender_id = "llm_example_script_runner"
        response_data = client.send_message(
            target_agent_id=dummy_agent_id, # Use the dummy agent ID for the API route
            sender_id=sender_id,
            message_type="tool_invocation",
            payload=tool_payload
        )

        print("\n--- Tool Invocation Successful ---")
        # The actual LLM response is nested within the 'result' field of the 'data'
        if response_data and isinstance(response_data, dict):
             tool_result = response_data.get("result")
             if tool_result:
                  print("Full Tool Result:")
                  import json
                  print(json.dumps(tool_result, indent=2))

                  # Extract and print the primary message content
                  if "choices" in tool_result and tool_result["choices"]:
                       first_choice = tool_result["choices"][0]
                       if "message" in first_choice and "content" in first_choice["message"]:
                            print("\nLLM Response Content:")
                            print(first_choice["message"]["content"])
                       else:
                            print("\nCould not find message content in the expected location within the result.")
                  else:
                       print("\nCould not find 'choices' in the result.")
             else:
                  print("Tool executed successfully, but no 'result' field found in the response data.")
                  print("Full Response Data:")
                  print(response_data)

        else:
             print("Tool executed successfully, but the response data format was unexpected.")
             print("Full Response Data:")
             print(response_data)


    except AgentKitError as e:
        print(f"\n--- Tool Invocation Failed ---")
        print(f"Error: {e}")
        if e.response_data:
            import json
            print("Error Response Data:")
            print(json.dumps(e.response_data, indent=2))

if __name__ == "__main__":
    # Ensure .env is loaded relative to this script if needed directly,
    # although the tool itself loads it when instantiated within the API process.
    # from dotenv import load_dotenv
    # load_dotenv() # Usually loaded by the tool/API

    run_llm_tool_example()