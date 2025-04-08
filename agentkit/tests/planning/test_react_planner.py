import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import json # For formatting expected input
from pydantic import BaseModel

from agentkit.core.interfaces.llm_client import BaseLlmClient, LlmResponse
from agentkit.core.interfaces.planner import Plan, PlanStep
from agentkit.planning.react_planner import ReActPlanner
from agentkit.tools.schemas import ToolSpec
from agentkit.tools.mcp_proxy import mcp_proxy_tool_spec # Import the spec

# --- Mocks and Fixtures ---

class MockLlmClient(BaseLlmClient):
    """Mock LLM Client for testing."""
    def __init__(self):
        self.generate = AsyncMock()

    async def generate(self, prompt: str, **kwargs) -> LlmResponse:
        # This method is mocked using self.generate in the fixture
        pass

@pytest.fixture
def mock_llm_client():
    """Fixture to provide a mocked LLM client instance."""
    return MockLlmClient()

@pytest.fixture
def react_planner(mock_llm_client):
    """Fixture to provide a ReActPlanner instance with a mocked LLM client."""
    return ReActPlanner(llm_client=mock_llm_client)

# Example ToolSpec for testing
class AddInput(BaseModel):
    a: int
    b: int

add_tool_spec = ToolSpec(
    name="add",
    description="Adds two integers.",
    input_schema=AddInput # Pass the class directly
)

# --- Test Cases ---

@pytest.mark.asyncio
async def test_react_planner_plan_tool_call(react_planner, mock_llm_client):
    """Tests generating a plan step that calls a tool."""
    # Arrange
    goal = "Add 5 and 3"
    tools = [add_tool_spec]
    history = [{"Thought": "I need to add 5 and 3."}, {"Action": "Initial state"}] # Example history

    # Mock LLM response for a tool call
    llm_response_text = """
Thought: I need to use the 'add' tool with inputs a=5 and b=3.
Action: Tool Name: add Input: {"a": 5, "b": 3}
"""
    mock_llm_client.generate.return_value = LlmResponse(
        content=llm_response_text, model_used="test-model", error=None
    )

    # Act
    plan = await react_planner.plan(goal=goal, available_tools=tools, history=history)

    # Assert
    assert isinstance(plan, Plan)
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert isinstance(step, PlanStep)
    assert step.action_type == "tool_call"
    assert step.details["tool_name"] == "add"
    assert step.details["tool_input"] == {"a": 5, "b": 3}

    # Verify LLM call
    mock_llm_client.generate.assert_awaited_once()
    call_args, call_kwargs = mock_llm_client.generate.call_args
    assert "Goal: Add 5 and 3" in call_kwargs["prompt"]
    assert "- add: Adds two integers." in call_kwargs["prompt"]
    assert "Thought: I need to add 5 and 3." in call_kwargs["prompt"] # Check history formatting
    assert call_kwargs["stop_sequences"] == ["\nObservation:"]

@pytest.mark.asyncio
async def test_react_planner_plan_final_answer(react_planner, mock_llm_client):
    """Tests generating a plan step with a final answer."""
    # Arrange
    goal = "What is 2+2?"
    tools = [] # No tools needed
    history = [
        {"Thought": "The user asked a simple math question."},
        {"Action": "Tool Name: calculator Input: {'query': '2+2'}"},
        {"Observation": "Result: 4"}
    ]

    # Mock LLM response for a final answer
    llm_response_text = """
Thought: I have the result from the calculator. The answer is 4.
Action: Final Answer: The sum is 4.
"""
    mock_llm_client.generate.return_value = LlmResponse(
        content=llm_response_text, model_used="test-model", error=None
    )

    # Act
    plan = await react_planner.plan(goal=goal, available_tools=tools, history=history)

    # Assert
    assert isinstance(plan, Plan)
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert isinstance(step, PlanStep)
    assert step.action_type == "final_answer"
    assert step.details["answer"] == "The sum is 4."

    # Verify LLM call
    mock_llm_client.generate.assert_awaited_once()
    call_args, call_kwargs = mock_llm_client.generate.call_args
    assert "Goal: What is 2+2?" in call_kwargs["prompt"]
    assert "Observation: Result: 4" in call_kwargs["prompt"] # Check history formatting

@pytest.mark.asyncio
async def test_react_planner_plan_llm_error(react_planner, mock_llm_client):
    """Tests handling an error from the LLM client."""
    # Arrange
    goal = "Test LLM error"
    tools = []
    history = []

    # Mock LLM error response
    mock_llm_client.generate.return_value = LlmResponse(
        content="", model_used="error-model", error="LLM unavailable"
    )

    # Act
    plan = await react_planner.plan(goal=goal, available_tools=tools, history=history)

    # Assert
    assert isinstance(plan, Plan)
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert isinstance(step, PlanStep)
    assert step.action_type == "error"
    assert "LLM unavailable" in step.details["message"]
    mock_llm_client.generate.assert_awaited_once()

@pytest.mark.asyncio
async def test_react_planner_plan_parsing_error(react_planner, mock_llm_client):
    """Tests handling a failure to parse the LLM response."""
    # Arrange
    goal = "Test parsing error"
    tools = []
    history = []

    # Mock LLM response with unparseable action
    llm_response_text = "Thought: I am confused.\nAction: Gibberish"
    mock_llm_client.generate.return_value = LlmResponse(
        content=llm_response_text, model_used="test-model", error=None
    )

    # Act
    plan = await react_planner.plan(goal=goal, available_tools=tools, history=history)

    # Assert
    assert isinstance(plan, Plan)
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert isinstance(step, PlanStep)
    assert step.action_type == "error"
    assert "Failed to parse LLM response" in step.details["message"]
    mock_llm_client.generate.assert_awaited_once()

def test_react_planner_init_invalid_client():
    """Tests that planner initialization fails with invalid LLM client type."""
    with pytest.raises(TypeError, match="llm_client must be an instance of BaseLlmClient"):
        ReActPlanner(llm_client=MagicMock()) # Pass a generic mock, not BaseLlmClient


@pytest.mark.asyncio
async def test_react_planner_plan_mcp_proxy_call(react_planner, mock_llm_client):
    """Tests generating a plan step that calls the mcp_proxy_tool."""
    # Arrange
    goal = "Use the external weather tool to find the weather in London."
    # Include the MCP proxy tool spec along with any other tools
    tools = [add_tool_spec, mcp_proxy_tool_spec]
    history = [{"Thought": "I need to use an external tool via the MCP proxy."}]

    # Mock LLM response for an MCP proxy tool call
    mcp_input = {
        "server_name": "weather_server",
        "tool_name": "get_weather",
        "arguments": {"city": "London"}
    }
    # Format input exactly as the LLM might produce it (JSON string)
    mcp_input_json_str = json.dumps(mcp_input)

    llm_response_text = f"""
Thought: The user wants weather information, which requires the external weather tool accessed via the MCP proxy.
Action: Tool Name: mcp_proxy_tool Input: {mcp_input_json_str}
"""
    mock_llm_client.generate.return_value = LlmResponse(
        content=llm_response_text, model_used="test-model", error=None
    )

    # Act
    plan = await react_planner.plan(goal=goal, available_tools=tools, history=history)

    # Assert
    assert isinstance(plan, Plan)
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert isinstance(step, PlanStep)
    assert step.action_type == "tool_call"
    assert step.details["tool_name"] == "mcp_proxy_tool"
    # Assert the parsed input dictionary matches the expected structure
    assert step.details["tool_input"] == mcp_input

    # Verify LLM call
    mock_llm_client.generate.assert_awaited_once()
    call_args, call_kwargs = mock_llm_client.generate.call_args
    assert "Goal: Use the external weather tool" in call_kwargs["prompt"]
    assert f"- {mcp_proxy_tool_spec.name}: {mcp_proxy_tool_spec.description}" in call_kwargs["prompt"]
    assert "Thought: I need to use an external tool via the MCP proxy." in call_kwargs["prompt"]
    assert call_kwargs["stop_sequences"] == ["\nObservation:"]
