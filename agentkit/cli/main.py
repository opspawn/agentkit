import typer
import json
from typing import List, Optional
from pydantic import HttpUrl, ValidationError # For URL validation
from agentkit.sdk.client import AgentKitClient, AgentKitError

app = typer.Typer(help="AgentKit CLI - Interact with the AgentKit API.")

# Global state/context if needed, e.g., for API URL
state = {"api_url": "http://localhost:8000"}

def get_client() -> AgentKitClient:
    """Initializes and returns an AgentKitClient instance."""
    return AgentKitClient(base_url=state["api_url"])

@app.command()
def register(
    name: str = typer.Option(..., "--name", "-n", help="Unique name for the agent."),
    version: str = typer.Option(..., "--version", "-v", help="Version string for the agent."),
    endpoint: str = typer.Option(..., "--endpoint", "-e", help="URL endpoint where the agent can be reached."),
    capability: Optional[List[str]] = typer.Option(None, "--capability", "-c", help="Capability of the agent (can specify multiple times)."),
    metadata_json: Optional[str] = typer.Option(None, "--metadata", "-m", help="Optional metadata as a JSON string (e.g., '{\"description\": \"...\"}')"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Override the default AgentKit API URL.")
):
    """
    Register a new agent with the AgentKit service.
    """
    if api_url:
        state["api_url"] = api_url

    client = get_client()
    capabilities = capability if capability else []
    metadata = None

    # Validate endpoint URL
    try:
        validated_endpoint = HttpUrl(endpoint)
    except ValidationError:
        typer.secho(f"Error: Invalid endpoint URL provided: {endpoint}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Parse metadata JSON if provided
    if metadata_json:
        try:
            metadata = json.loads(metadata_json)
            if not isinstance(metadata, dict):
                 raise ValueError("Metadata must be a JSON object (dictionary).")
            # Basic check for expected structure (optional)
            # if "description" not in metadata and "config" not in metadata:
            #     typer.secho("Warning: Metadata JSON doesn't contain common keys like 'description' or 'config'.", fg=typer.colors.YELLOW)
        except json.JSONDecodeError:
            typer.secho(f"Error: Invalid JSON provided for metadata: {metadata_json}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        except ValueError as e:
             typer.secho(f"Error: Invalid metadata structure: {e}", fg=typer.colors.RED)
             raise typer.Exit(code=1)


    try:
        typer.echo(f"Registering agent '{name}' with API at {state['api_url']}...")
        agent_id = client.register_agent(
            agent_name=name,
            capabilities=capabilities,
            version=version,
            contact_endpoint=validated_endpoint,
            metadata=metadata
        )
        typer.secho(f"Agent '{name}' registered successfully!", fg=typer.colors.GREEN)
        typer.echo(f"Agent ID: {agent_id}")
    except AgentKitError as e:
        typer.secho(f"Error registering agent: {e}", fg=typer.colors.RED)
        if e.response_data:
            typer.echo(f"API Response Data: {json.dumps(e.response_data, indent=2)}")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def send(
    target_id: str = typer.Argument(..., help="The ID of the agent to send the message to."),
    sender_id: str = typer.Option(..., "--sender", "-s", help="The ID of the agent sending the message."),
    type: str = typer.Option(..., "--type", "-t", help="Type of the message (e.g., 'intent_query', 'tool_invocation')."),
    payload_json: str = typer.Argument(..., help="The message payload as a JSON string."),
    session_json: Optional[str] = typer.Option(None, "--session", help="Optional session context as a JSON string."),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Override the default AgentKit API URL.")
):
    """
    Send a message to a specific agent.
    """
    if api_url:
        state["api_url"] = api_url

    client = get_client()
    payload = None
    session_context = None

    # Parse payload JSON
    try:
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object (dictionary).")
    except json.JSONDecodeError:
        typer.secho(f"Error: Invalid JSON provided for payload: {payload_json}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except ValueError as e:
        typer.secho(f"Error: Invalid payload structure: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Parse session context JSON if provided
    if session_json:
        try:
            session_context = json.loads(session_json)
            if not isinstance(session_context, dict):
                 raise ValueError("Session context must be a JSON object (dictionary).")
        except json.JSONDecodeError:
            typer.secho(f"Error: Invalid JSON provided for session context: {session_json}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        except ValueError as e:
             typer.secho(f"Error: Invalid session context structure: {e}", fg=typer.colors.RED)
             raise typer.Exit(code=1)

    try:
        typer.echo(f"Sending message type '{type}' from '{sender_id}' to agent '{target_id}'...")
        response_data = client.send_message(
            target_agent_id=target_id,
            sender_id=sender_id,
            message_type=type,
            payload=payload,
            session_context=session_context
        )
        typer.secho("Message sent successfully!", fg=typer.colors.GREEN)
        typer.echo("Response Data:")
        typer.echo(json.dumps(response_data, indent=2))

    except AgentKitError as e:
        typer.secho(f"Error sending message: {e}", fg=typer.colors.RED)
        if e.response_data:
            typer.echo(f"API Response Data: {json.dumps(e.response_data, indent=2)}")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()