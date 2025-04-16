"""
Example Agent: Ping Agent

This script demonstrates the basic usage of the AgentKit SDK to:
1. Register a simple agent.
2. Send a 'ping' message to the registered agent itself.
"""

import os
from agentkit.sdk.client import AgentKitClient, AgentKitError
from agentkit.core.models import AgentRegistrationPayload, MessagePayload

# Configuration - Adjust if your AgentKit API runs elsewhere
AGENTKIT_API_URL = os.getenv("AGENTKIT_API_URL", "http://localhost:8000/v1")

def run_ping_agent():
    """Registers an agent and sends a ping message to itself."""
    print(f"--- Running Ping Agent Example ---")
    print(f"Using AgentKit API at: {AGENTKIT_API_URL}")

    client = AgentKitClient(base_url=AGENTKIT_API_URL)
    agent_id = None

    try:
        # 1. Register the Agent
        print("\nAttempting to register agent...")
        agent_name = "PingAgent"
        capabilities = ["ping"]
        version = "1.0.0"
        contact_endpoint = "http://example.com/ping_agent_contact" # Placeholder
        metadata = {"example_type": "ping_agent"}

        # Call register_agent with individual arguments
        agent_id = client.register_agent(
            agent_name=agent_name,
            capabilities=capabilities,
            version=version,
            contact_endpoint=contact_endpoint,
            metadata=metadata
        )
        print(f"Agent registered successfully! Agent ID: {agent_id}")

        # 2. Send Ping Message to Self
        print(f"\nAttempting to send 'ping' message from {agent_id} to {agent_id}...")
        message_type = "ping"
        payload = {"data": "hello from ping agent!"}
        context = {"trace_id": "ping-example-123"}

        # Call send_message with individual arguments
        # Note: SDK uses sender_id, target_agent_id, session_context
        response = client.send_message(
            target_agent_id=agent_id, # Sending to self
            sender_id=agent_id,
            message_type=message_type,
            payload=payload,
            session_context=context
        )
        print(f"Message sent successfully!")
        # The SDK's send_message returns the 'data' part of the response
        print(f"API Response Data: {response}")

    except AgentKitError as e:
        print(f"\nAn AgentKit API error occurred: {e}")
        if e.detail:
            print(f"Details: {e.detail}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\n--- Ping Agent Example Finished ---")
        # Note: In a real agent, you might want to unregister or handle cleanup.
        # This example focuses purely on registration and sending.

if __name__ == "__main__":
    run_ping_agent()