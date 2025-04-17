"""
Example Agent: Responder Agent

This script demonstrates an agent that:
1. Registers itself with a specific, locally accessible contact endpoint.
2. Runs a simple Flask web server to listen for incoming messages at that endpoint.
3. Processes received messages (prints them) and sends back an acknowledgement.

This agent is designed to be the target for messages dispatched by the AgentKit API
when another agent uses the `send_message` function targeting this agent's ID.
"""

import os
import threading
from flask import Flask, request, jsonify
from agentkit.sdk.client import AgentKitClient, AgentKitError
from agentkit.core.models import MessagePayload # Import the model for type hinting

# --- Configuration ---
AGENTKIT_API_URL = os.getenv("AGENTKIT_API_URL", "http://localhost:8000/v1")
RESPONDER_HOST = "0.0.0.0" # Listen on all available interfaces
RESPONDER_PORT = 9001      # Port for this agent's server
RESPONDER_ENDPOINT_PATH = "/receive_message"
RESPONDER_CONTACT_URL = f"http://host.docker.internal:{RESPONDER_PORT}{RESPONDER_ENDPOINT_PATH}"
# Note: Using host.docker.internal allows the AgentKit API container to reach this server running on the host machine.
# If running AgentKit API outside Docker, use http://localhost:{RESPONDER_PORT}{RESPONDER_ENDPOINT_PATH} or similar.

# Global variable to store the agent ID
responder_agent_id = None

# --- Flask App Setup ---
flask_app = Flask(__name__)

@flask_app.route(RESPONDER_ENDPOINT_PATH, methods=['POST'])
def handle_incoming_message():
    """Handles messages dispatched by the AgentKit API."""
    print(f"\n--- Responder Agent received a message at {RESPONDER_ENDPOINT_PATH} ---")
    if not request.is_json:
        print("Error: Request is not JSON")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    data = request.get_json()
    print(f"Received Raw Data: {data}")

    try:
        # Validate received data against MessagePayload model (optional but good practice)
        received_message = MessagePayload(**data)
        print(f"Received Message Type: {received_message.messageType}")
        print(f"Sender ID: {received_message.senderId}")
        print(f"Payload: {received_message.payload}")
        if received_message.sessionContext:
            print(f"Session Context: {received_message.sessionContext}")

        # Send back a success response
        response_data = {
            "status": "acknowledged",
            "message": f"Message of type '{received_message.messageType}' received by Responder Agent.",
            "received_sender": received_message.senderId
        }
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error processing received message: {e}")
        return jsonify({"status": "error", "message": f"Failed to process message: {e}"}), 500

# --- Agent Registration ---
def register_responder_agent():
    """Registers the responder agent with the AgentKit API."""
    global responder_agent_id
    print(f"--- Registering Responder Agent ---")
    print(f"Using AgentKit API at: {AGENTKIT_API_URL}")
    print(f"Attempting to register with contact endpoint: {RESPONDER_CONTACT_URL}")

    client = AgentKitClient(base_url=AGENTKIT_API_URL)

    try:
        agent_name = "ResponderAgent"
        capabilities = ["respond"]
        version = "1.0.0"
        metadata = {"example_type": "responder_agent"}

        responder_agent_id = client.register_agent(
            agent_name=agent_name,
            capabilities=capabilities,
            version=version,
            contact_endpoint=RESPONDER_CONTACT_URL,
            metadata=metadata
        )
        print(f"Responder Agent registered successfully! Agent ID: {responder_agent_id}")
        print(f"Agent '{agent_name}' listening at {RESPONDER_CONTACT_URL}")

    except AgentKitError as e:
        print(f"\nAn AgentKit API error occurred during registration: {e}")
        if e.detail:
            print(f"Details: {e.detail}")
        responder_agent_id = None # Ensure ID is None if registration fails
    except Exception as e:
        print(f"\nAn unexpected error occurred during registration: {e}")
        responder_agent_id = None

# --- Main Execution ---
def run_flask_app():
    """Runs the Flask server."""
    print(f"\nStarting Flask server on {RESPONDER_HOST}:{RESPONDER_PORT}...")
    # Turn off Flask's default logging to avoid duplicate messages with our prints
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    flask_app.run(host=RESPONDER_HOST, port=RESPONDER_PORT)

if __name__ == "__main__":
    import logging # Import here for server logging control

    register_responder_agent()

    if responder_agent_id:
        # Start Flask server in a separate thread or process if needed,
        # but for this simple example, running it directly is fine.
        # It will block here until interrupted.
        run_flask_app()
    else:
        print("\nAgent registration failed. Cannot start Flask server.")

    print("\n--- Responder Agent Example Finished ---")