"""
Example Agent: Requester Agent

This script demonstrates an agent that:
1. Registers itself with the AgentKit API.
2. Takes a target agent name (e.g., "ResponderAgent") as input.
3. Looks up the target agent's ID using the SDK (or assumes a known ID).
4. Sends a custom message to the target agent via the AgentKit API's dispatch mechanism.
5. Prints the response received from the API (which should include the target agent's acknowledgement).

This agent is designed to interact with the ResponderAgent example.
"""

import os
import sys
import time
from agentkit.sdk.client import AgentKitClient, AgentKitError

# --- Configuration ---
AGENTKIT_API_URL = os.getenv("AGENTKIT_API_URL", "http://localhost:8000/v1")
DEFAULT_TARGET_AGENT_NAME = "ResponderAgent"

def run_requester_agent(target_agent_name: str):
    """Registers this agent and sends a message to the target agent."""
    print(f"--- Running Requester Agent Example ---")
    print(f"Using AgentKit API at: {AGENTKIT_API_URL}")
    print(f"Targeting agent named: '{target_agent_name}'")

    client = AgentKitClient(base_url=AGENTKIT_API_URL)
    requester_agent_id = None
    target_agent_id = None

    try:
        # 1. Register the Requester Agent
        print("\nAttempting to register Requester agent...")
        requester_agent_name = "RequesterAgent"
        # Contact endpoint isn't strictly needed if this agent only sends
        requester_contact_endpoint = "http://example.com/requester_callback"

        requester_agent_id = client.register_agent(
            agent_name=requester_agent_name,
            capabilities=["request"],
            version="1.0.0",
            contact_endpoint=requester_contact_endpoint,
            metadata={"example_type": "requester_agent"}
        )
        print(f"Requester Agent registered successfully! Agent ID: {requester_agent_id}")

        # 2. Find the Target Agent ID (Robust way: List and find by name)
        # Note: In a real scenario, discovery might be handled differently.
        # Adding a small delay to allow the Responder agent to register if run concurrently.
        print(f"\nLooking for target agent '{target_agent_name}'...")
        time.sleep(1) # Small delay
        registered_agents = client.list_agents()
        found_target = False
        for agent in registered_agents:
            if agent.agentName == target_agent_name:
                target_agent_id = agent.agentId
                print(f"Found target agent '{target_agent_name}' with ID: {target_agent_id}")
                found_target = True
                break

        if not found_target:
            print(f"Error: Target agent '{target_agent_name}' not found in registry.")
            print("Please ensure the ResponderAgent example is running and registered.")
            return # Exit if target not found

        # 3. Send Message to Target Agent via API Dispatch
        print(f"\nAttempting to send 'task_request' message from {requester_agent_id} to {target_agent_id}...")
        message_type = "task_request"
        payload = {"task": "Please acknowledge receipt.", "priority": "medium"}
        context = {"trace_id": "requester-example-456"}

        response = client.send_message(
            target_agent_id=target_agent_id,
            sender_id=requester_agent_id,
            message_type=message_type,
            payload=payload,
            session_context=context
        )
        print(f"Message sent successfully!")
        # The response 'data' should contain the JSON response from the ResponderAgent's Flask server
        print(f"API Response Data (including Responder's ack): {response}")

    except AgentKitError as e:
        print(f"\nAn AgentKit API error occurred: {e}")
        if e.detail:
            print(f"Details: {e.detail}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\n--- Requester Agent Example Finished ---")

if __name__ == "__main__":
    target_name = DEFAULT_TARGET_AGENT_NAME
    if len(sys.argv) > 1:
        target_name = sys.argv[1] # Allow specifying target name via command line

    run_requester_agent(target_name)