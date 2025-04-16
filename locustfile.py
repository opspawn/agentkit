import random
from locust import HttpUser, task, between

class AgentKitUser(HttpUser):
    """
    User class that does requests to the AgentKit API.
    Simulates registering an agent and then sending messages.
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    registered_agent_id = None
    host = "http://localhost:8000" # Default host if not specified in CLI

    def on_start(self):
        """
        Called when a Locust start before any task is scheduled.
        Registers an agent for this user.
        """
        self.register_agent()

    def register_agent(self):
        """Registers a new agent and stores its ID."""
        agent_name = f"loadtest-agent-{random.randint(1000, 9999)}"
        payload = {
            "agentName": agent_name,
            "version": "1.0",
            "description": "Agent created during load testing",
            "capabilities": ["ping_responder"],
            "contactEndpoint": f"http://fake-agent-{agent_name}.local/run",
            "metadata": {"load_test_run": True}
        }
        try:
            with self.client.post("/v1/agents/register", json=payload, catch_response=True, name="/v1/agents/register") as response:
                if response.status_code == 201:
                    self.registered_agent_id = response.json().get("agentId")
                    response.success()
                    print(f"Registered agent: {self.registered_agent_id}")
                else:
                    response.failure(f"Failed to register agent, status code: {response.status_code}, response: {response.text}")
        except Exception as e:
            print(f"Exception during registration: {e}")


    @task(1) # Higher weight for sending messages
    def send_simple_message(self):
        """Sends a simple 'ping' message to a randomly chosen (or self) agent."""
        if not self.registered_agent_id:
            # If registration failed or hasn't completed, try registering again instead of sending message
            self.register_agent()
            return

        # For simplicity, send message to self in this basic test
        target_agent_id = self.registered_agent_id

        message_payload = {
            "senderAgentId": self.registered_agent_id,
            "messageType": "ping",
            "payload": {"data": f"Hello from {self.registered_agent_id}"},
            "context": {"traceId": f"trace-{random.randint(10000, 99999)}"}
        }
        url = f"/v1/agents/{target_agent_id}/run"
        try:
            with self.client.post(url, json=message_payload, catch_response=True, name="/v1/agents/{agentId}/run") as response:
                if response.status_code == 200:
                    response.success()
                else:
                    # Treat non-200 responses as failures for load testing
                    response.failure(f"Failed to send message, status code: {response.status_code}, response: {response.text}")
        except Exception as e:
            print(f"Exception during sending message: {e}")

    # Optional: Add a task for re-registering if needed, lower weight
    # @task(1)
    # def maybe_register_again(self):
    #     """ Occasionally re-register to test registration under load """
    #     if random.random() < 0.1: # 10% chance
    #         self.register_agent()