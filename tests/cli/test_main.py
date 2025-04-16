import pytest
import json
from unittest.mock import patch, MagicMock
from pydantic import HttpUrl # Import HttpUrl for assertion
from typer.testing import CliRunner

# Import the Typer app instance from the module we are testing
from agentkit.cli.main import app
from agentkit.sdk.client import AgentKitClient, AgentKitError

# Create a CliRunner instance to invoke commands
runner = CliRunner()

# --- Test Fixtures (if needed later) ---
# Example:
# @pytest.fixture
# def mock_client():
#     client = MagicMock(spec=AgentKitClient)
#     # Configure mock methods as needed
#     return client

# --- Tests for the 'register' command ---

def test_register_success_basic():
    """Test successful agent registration with minimal required options."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    mock_client_instance.register_agent.return_value = "agent-123" # Simulate successful registration

    # Patch the get_client function to return our mock
    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance) as mock_get_client:
        result = runner.invoke(app, [
            "register",
            "--name", "test-agent",
            "--version", "1.0",
            "--endpoint", "http://localhost:9000/agent"
        ])

        print(f"STDOUT: {result.stdout}")
        # print(f"STDERR: {result.stderr}") # Removed: Not needed for basic success check & avoids capture error
        print(f"Exception: {result.exception}") # Should be None on success

        assert result.exit_code == 0
        assert "Registering agent 'test-agent'" in result.stdout
        assert "Agent 'test-agent' registered successfully!" in result.stdout
        assert "Agent ID: agent-123" in result.stdout
        mock_get_client.assert_called_once()
        mock_client_instance.register_agent.assert_called_once_with(
            agent_name="test-agent",
            capabilities=[],
            version="1.0",
            contact_endpoint=HttpUrl("http://localhost:9000/agent"), # Expect HttpUrl object
            metadata=None
        )

def test_register_success_with_options():
    """Test successful agent registration with capabilities and metadata."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    mock_client_instance.register_agent.return_value = "agent-456"
    metadata_dict = {"description": "A test agent", "type": "tester"}
    metadata_json = json.dumps(metadata_dict)

    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance):
        result = runner.invoke(app, [
            "register",
            "-n", "test-agent-options",
            "-v", "1.1",
            "-e", "http://127.0.0.1:9001",
            "-c", "test",
            "-c", "debug",
            "-m", metadata_json
        ])

        assert result.exit_code == 0
        assert "Agent ID: agent-456" in result.stdout
        mock_client_instance.register_agent.assert_called_once_with(
            agent_name="test-agent-options",
            capabilities=["test", "debug"],
            version="1.1",
            contact_endpoint=HttpUrl("http://127.0.0.1:9001/"), # Expect HttpUrl object
            metadata=metadata_dict
        )

def test_register_invalid_endpoint_url():
    """Test registration failure with an invalid endpoint URL."""
    result = runner.invoke(app, [
        "register",
        "--name", "test-agent",
        "--version", "1.0",
        "--endpoint", "invalid-url" # Not a valid URL
    ])
    assert result.exit_code == 1
    assert "Error: Invalid endpoint URL provided: invalid-url" in result.stdout

def test_register_invalid_metadata_json():
    """Test registration failure with invalid metadata JSON."""
    result = runner.invoke(app, [
        "register",
        "--name", "test-agent",
        "--version", "1.0",
        "--endpoint", "http://localhost:9000",
        "--metadata", '{"key": "value"' # Intentionally broken JSON
    ])
    assert result.exit_code == 1
    assert "Error: Invalid JSON provided for metadata" in result.stdout

def test_register_metadata_not_object():
    """Test registration failure when metadata JSON is not an object."""
    result = runner.invoke(app, [
        "register",
        "--name", "test-agent",
        "--version", "1.0",
        "--endpoint", "http://localhost:9000",
        "--metadata", '"just a string"' # Valid JSON, but not an object
    ])
    assert result.exit_code == 1
    assert "Error: Invalid metadata structure: Metadata must be a JSON object (dictionary)." in result.stdout


def test_register_api_error():
    """Test registration failure when the API client raises AgentKitError."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    error_response = {"detail": "Registration failed"}
    mock_client_instance.register_agent.side_effect = AgentKitError("API Error", response_data=error_response)

    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance):
        result = runner.invoke(app, [
            "register",
            "--name", "test-agent",
            "--version", "1.0",
            "--endpoint", "http://localhost:9000"
        ])

        assert result.exit_code == 1
        assert "Error registering agent: API Error" in result.stdout
        assert json.dumps(error_response, indent=2) in result.stdout

def test_register_unexpected_error():
    """Test registration failure on unexpected client exception."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    mock_client_instance.register_agent.side_effect = Exception("Something broke")

    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance):
        result = runner.invoke(app, [
            "register",
            "--name", "test-agent",
            "--version", "1.0",
            "--endpoint", "http://localhost:9000"
        ])

        assert result.exit_code == 1
        assert "An unexpected error occurred: Something broke" in result.stdout


# --- Tests for the 'send' command ---

def test_send_success_basic():
    """Test successful message sending with minimal required options."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    api_response = {"status": "received", "result": "processed"}
    mock_client_instance.send_message.return_value = api_response
    payload_dict = {"command": "do_something"}
    payload_json = json.dumps(payload_dict)

    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance):
        result = runner.invoke(app, [
            "send",
            "agent-123", # target_id
            "--sender", "agent-abc",
            "--type", "command",
            payload_json
        ])

        assert result.exit_code == 0
        assert "Sending message type 'command' from 'agent-abc' to agent 'agent-123'" in result.stdout
        assert "Message sent successfully!" in result.stdout
        assert json.dumps(api_response, indent=2) in result.stdout
        mock_client_instance.send_message.assert_called_once_with(
            target_agent_id="agent-123",
            sender_id="agent-abc",
            message_type="command",
            payload=payload_dict,
            session_context=None
        )

def test_send_success_with_session():
    """Test successful message sending with session context."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    api_response = {"status": "ok"}
    mock_client_instance.send_message.return_value = api_response
    payload_dict = {"query": "status"}
    payload_json = json.dumps(payload_dict)
    session_dict = {"user_id": "user-xyz", "thread_id": "thread-1"}
    session_json = json.dumps(session_dict)

    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance):
        result = runner.invoke(app, [
            "send",
            "agent-456",
            "-s", "agent-def",
            "-t", "query",
            "--session", session_json,
            payload_json
        ])

        assert result.exit_code == 0
        assert "Message sent successfully!" in result.stdout
        mock_client_instance.send_message.assert_called_once_with(
            target_agent_id="agent-456",
            sender_id="agent-def",
            message_type="query",
            payload=payload_dict,
            session_context=session_dict
        )

def test_send_invalid_payload_json():
    """Test send failure with invalid payload JSON."""
    result = runner.invoke(app, [
        "send",
        "agent-123",
        "--sender", "agent-abc",
        "--type", "command",
        '{"key": "value"' # Broken JSON
    ])
    assert result.exit_code == 1
    assert "Error: Invalid JSON provided for payload" in result.stdout

def test_send_payload_not_object():
    """Test send failure when payload JSON is not an object."""
    result = runner.invoke(app, [
        "send",
        "agent-123",
        "--sender", "agent-abc",
        "--type", "command",
        '"just a string"' # Valid JSON, but not an object
    ])
    assert result.exit_code == 1
    assert "Error: Invalid payload structure: Payload must be a JSON object (dictionary)." in result.stdout


def test_send_invalid_session_json():
    """Test send failure with invalid session JSON."""
    payload_json = json.dumps({"command": "test"})
    result = runner.invoke(app, [
        "send",
        "agent-123",
        "--sender", "agent-abc",
        "--type", "command",
        "--session", '{"key": "value"' , # Broken JSON
        payload_json
    ])
    assert result.exit_code == 1
    assert "Error: Invalid JSON provided for session context" in result.stdout

def test_send_session_not_object():
    """Test send failure when session JSON is not an object."""
    payload_json = json.dumps({"command": "test"})
    result = runner.invoke(app, [
        "send",
        "agent-123",
        "--sender", "agent-abc",
        "--type", "command",
        "--session", '[1, 2, 3]', # Valid JSON, but not an object
        payload_json
    ])
    assert result.exit_code == 1
    assert "Error: Invalid session context structure: Session context must be a JSON object (dictionary)." in result.stdout


def test_send_api_error():
    """Test send failure when the API client raises AgentKitError."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    error_response = {"detail": "Target agent not found"}
    mock_client_instance.send_message.side_effect = AgentKitError("Send Failed", response_data=error_response)
    payload_json = json.dumps({"command": "test"})

    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance):
        result = runner.invoke(app, [
            "send",
            "agent-invalid",
            "--sender", "agent-abc",
            "--type", "command",
            payload_json
        ])

        assert result.exit_code == 1
        assert "Error sending message: Send Failed" in result.stdout
        assert json.dumps(error_response, indent=2) in result.stdout

def test_send_unexpected_error():
    """Test send failure on unexpected client exception."""
    mock_client_instance = MagicMock(spec=AgentKitClient)
    mock_client_instance.send_message.side_effect = Exception("Network issue")
    payload_json = json.dumps({"command": "test"})

    with patch('agentkit.cli.main.get_client', return_value=mock_client_instance):
        result = runner.invoke(app, [
            "send",
            "agent-123",
            "--sender", "agent-abc",
            "--type", "command",
            payload_json
        ])

        assert result.exit_code == 1
        assert "An unexpected error occurred: Network issue" in result.stdout