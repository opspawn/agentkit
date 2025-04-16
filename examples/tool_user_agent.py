"""
Example Agent: Tool User Agent

This script demonstrates using the AgentKit SDK to:
1. Register a simple agent.
2. Send a message intended to invoke a registered tool (the mock_tool).
"""

import os
from agentkit.sdk.client import AgentKitClient, AgentKitError
from agentkit.core.models import AgentRegistrationPayload, MessagePayload

# Configuration - Adjust if your AgentKit API runs elsewhere
AGENTKIT_API_URL = os.getenv("AGENTKIT_API_URL", "http://localhost:8000/v1")
MOCK_TOOL_NAME = "mock_tool" # The name the mock tool is registered under in main.py

def run_tool_user_agent():
    """Registers an agent and sends a message to invoke a tool."""
    print(f"--- Running Tool User Agent Example ---")
    print(f"Using AgentKit API at: {AGENTKIT_API_URL}")

    client = AgentKitClient(base_url=AGENTKIT_API_URL)
    agent_id = None

    try:
        # 1. Register the Agent
        print("\nAttempting to register agent...")
        agent_name = "ToolUserAgent"
        capabilities = ["tool_user"]
        version = "1.0.0"
        contact_endpoint = "http://example.com/tool_user_contact" # Placeholder
        metadata = {"example_type": "tool_user_agent"}

        # Call register_agent with individual arguments
        agent_id = client.register_agent(
            agent_name=agent_name,
            capabilities=capabilities,
            version=version,
            contact_endpoint=contact_endpoint,
            metadata=metadata
        )
        print(f"Agent registered successfully! Agent ID: {agent_id}")

        # 2. Send Tool Invocation Message
        print(f"\nAttempting to send 'tool_invocation' message from {agent_id}...")
        message_type = "tool_invocation"
        payload = {
            "tool_name": MOCK_TOOL_NAME,
            "arguments": {
                "query": "What is the weather in London?",
                "details": {"units": "celsius"}
            } # Example arguments matching mock_tool.py expectation
        }
        context = {"trace_id": "tool-example-456"}

        # Call send_message with individual arguments
        # Note: SDK uses sender_id, target_agent_id, session_context
        # For tool invocation, target_agent_id might be less relevant,
        # but we send to self as per the original logic.
        response = client.send_message(
            target_agent_id=agent_id,
            sender_id=agent_id,
            message_type=message_type,
            payload=payload,
            session_context=context
        )
        print(f"Tool invocation message sent successfully!")
        # The SDK's send_message returns the 'data' part of the response
        print(f"API Response Data: {response}")

    except AgentKitError as e:
        print(f"\nAn AgentKit API error occurred: {e}")
        # Safely check for response_data which might contain more details
        if e.response_data:
            print(f"API Response Data: {e.response_data}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\n--- Tool User Agent Example Finished ---")

if __name__ == "__main__":
    run_tool_user_agent()