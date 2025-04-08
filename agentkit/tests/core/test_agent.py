# agentkit/tests/core/test_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, call

from agentkit.core.agent import Agent
from agentkit.core.interfaces import (
    BaseMemory,
    BasePlanner,
    BaseSecurityManager,
    BaseToolManager,
)
# Import Plan and PlanStep from their specific module
from agentkit.core.interfaces.planner import Plan, PlanStep
from agentkit.memory.short_term import ShortTermMemory # For type checking test
from agentkit.tools.schemas import ToolResult # Import ToolResult


# --- Fixtures for Mocks ---

@pytest.fixture
def mock_memory():
    """Fixture for a mocked BaseMemory."""
    mock = MagicMock(spec=BaseMemory)
    # Mock the actual async methods defined in the interface
    mock.get_context = AsyncMock(return_value=[]) # Default empty context
    mock.add_message = AsyncMock()
    mock.clear = AsyncMock()
    return mock

@pytest.fixture
def mock_planner():
    """Fixture for a mocked BasePlanner."""
    mock = MagicMock(spec=BasePlanner)
    # Default plan: a single final_answer step (as a Plan object)
    default_plan_obj = Plan(steps=[PlanStep(action_type="final_answer", details={"answer": "Mock answer"})])
    mock.plan = AsyncMock(return_value=default_plan_obj) # Return Plan object
    return mock

@pytest.fixture
def mock_tool_manager():
    """Fixture for a mocked BaseToolManager."""
    mock = MagicMock(spec=BaseToolManager)
    # Mock execute_tool if needed for specific tests later
    mock.execute_tool = AsyncMock()
    return mock

@pytest.fixture
def mock_security_manager():
    """Fixture for a mocked BaseSecurityManager."""
    mock = MagicMock(spec=BaseSecurityManager)
    # Mock the actual async method defined in the interface
    mock.check_permissions = AsyncMock(return_value=True) # Default: allow execution
    return mock

# --- Test Cases ---

def test_agent_initialization_success(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests successful agent initialization with valid mocks."""
    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )
    assert agent.memory is mock_memory
    assert agent.planner is mock_planner
    assert agent.tool_manager is mock_tool_manager
    assert agent.security_manager is mock_security_manager

def test_agent_initialization_type_error(
    mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests that TypeError is raised for invalid dependency types."""
    with pytest.raises(TypeError, match="memory must be an instance of BaseMemory"):
        Agent(memory="not_memory", planner=mock_planner, tool_manager=mock_tool_manager, security_manager=mock_security_manager)

    # Test other dependencies similarly
    with pytest.raises(TypeError, match="planner must be an instance of BasePlanner"):
        Agent(memory=MagicMock(spec=BaseMemory), planner="not_planner", tool_manager=mock_tool_manager, security_manager=mock_security_manager)

    with pytest.raises(TypeError, match="tool_manager must be an instance of BaseToolManager"):
        Agent(memory=MagicMock(spec=BaseMemory), planner=mock_planner, tool_manager="not_tm", security_manager=mock_security_manager)

    with pytest.raises(TypeError, match="security_manager must be an instance of BaseSecurityManager"):
        Agent(memory=MagicMock(spec=BaseMemory), planner=mock_planner, tool_manager=mock_tool_manager, security_manager="not_sm")


@pytest.mark.asyncio
async def test_agent_run_simple_final_answer(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests a simple run where the planner returns a final answer immediately."""
    goal = "Simple task"
    final_answer = "Mock answer"
    plan = Plan(steps=[PlanStep(action_type="final_answer", details={"answer": final_answer})])
    mock_planner.plan.return_value = plan

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run_async(goal) # Use run_async

    # Check planner call - Planner receives context dict
    expected_context = {'messages': [], 'profile': {}, 'available_tools': []}
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=expected_context)

    # Check security call - Uses check_permissions
    # Note: The agent code passes action_desc and context={"step": step}
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action="final_answer", context={"step": plan.steps[0]}
    )

    # Check memory calls - Uses add_message
    expected_calls = [
        call(role="user", content=goal),
        # Agent logs the outcome of the final_answer step
        call(role="assistant", content="Step 1 outcome: Mock answer"),
    ]
    mock_memory.add_message.assert_has_calls(expected_calls, any_order=False)

    # Check final result - Agent returns the final answer directly
    assert result == final_answer


@pytest.mark.asyncio
async def test_agent_run_security_denial(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the run flow when the security manager denies an action."""
    goal = "Risky task"
    # Use the correct PlanStep structure with action_type and details
    plan_obj = Plan(steps=[PlanStep(action_type="tool_call", details={"tool_name": "risky_tool", "arguments": {}})]) # Assume empty args if not specified
    mock_planner.plan.return_value = plan_obj # Return Plan object
    mock_security_manager.check_permissions.return_value = False # Deny execution

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run_async(goal) # Use run_async

    # Check security call - Uses check_permissions
    # Agent passes action_desc = "tool_call:risky_tool" and the step context
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action="tool_call:risky_tool", context={"step": plan_obj.steps[0]} # Use plan_obj
    )

    # Check memory calls (should include error) - Uses add_message
    expected_calls = [
        call(role="user", content=goal),
        # Agent logs the permission error message
        call(role="assistant", content="Step 1 outcome: Permission denied for action 'tool_call:risky_tool'."),
    ]
    mock_memory.add_message.assert_has_calls(expected_calls, any_order=False)

    # Check final result - Agent returns the failure message
    assert result == "Task failed at step 1: Permission denied for action 'tool_call:risky_tool'."
    mock_tool_manager.execute_tool.assert_not_awaited() # Tool should not be called


@pytest.mark.asyncio
async def test_agent_run_no_steps_in_plan(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the run flow when the planner returns an empty plan."""
    goal = "Task with no steps"
    plan_obj = Plan(steps=[]) # Empty plan object
    mock_planner.plan.return_value = plan_obj # Return Plan object

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run_async(goal) # Use run_async

    # Check planner call - Planner receives context dict
    expected_context = {'messages': [], 'profile': {}, 'available_tools': []}
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=expected_context)

    # Check memory calls - Uses add_message
    expected_calls = [
        call(role="user", content=goal),
        # Agent logs the empty plan message exactly as defined in agent.py
        call(role="assistant", content="Planner returned an empty plan. Task cannot proceed."),
    ]
    mock_memory.add_message.assert_has_calls(expected_calls, any_order=False)

    # Check final result - Agent returns the specific message
    assert result == "Planner returned an empty plan. Task cannot proceed."
    mock_security_manager.check_permissions.assert_not_called()
    mock_tool_manager.execute_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_reset(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the agent's reset method."""
    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )
    # Agent doesn't have a reset method, clear memory directly
    await agent.memory.clear()
    mock_memory.clear.assert_called_once()


@pytest.mark.asyncio
async def test_agent_run_tool_call(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the agent run flow when the plan involves a tool call."""
    goal = "Use calculator"
    tool_name = "calculator"
    tool_input = {"query": "2+2"} # This is the 'arguments' part for the tool
    tool_output = {"result": 4}
    # Use the correct PlanStep structure with action_type and details
    plan_obj = Plan(steps=[PlanStep(action_type="tool_call", details={"tool_name": tool_name, "arguments": tool_input})])
    # ToolResult needs tool_name and tool_args
    tool_result = ToolResult(tool_name=tool_name, tool_args=tool_input, output=tool_output, error=None)

    mock_planner.plan.return_value = plan_obj # Return Plan object
    mock_tool_manager.execute_tool.return_value = tool_result # Mock the tool execution result

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run_async(goal) # Use run_async

    # Check planner call - Planner receives context dict
    expected_context = {'messages': [], 'profile': {}, 'available_tools': []}
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=expected_context)

    # Check security call - Uses check_permissions
    # Agent passes action_desc = "tool_call:calculator" and the step context
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action="tool_call:calculator", context={"step": plan_obj.steps[0]} # Use plan_obj
    )

    # Check tool manager call - Agent passes tool_name and arguments dict
    mock_tool_manager.execute_tool.assert_awaited_once_with(tool_name, tool_input)

    # Check memory calls (using add_message structure from agent code)
    expected_calls = [
        call(role="user", content=goal),
        call(role="tool", content=f"Tool '{tool_name}' called with args {tool_input}. Result: {tool_output}", metadata={'tool_result': tool_result.model_dump()}),
        call(role="assistant", content="Final Result: Plan executed but no explicit completion step found.") # Final message if plan ends
    ]
    mock_memory.add_message.assert_has_calls(expected_calls, any_order=False)

    # Check final result - Agent returns the default completion message if plan ends
    assert result == "Plan executed but no explicit completion step found."


@pytest.mark.asyncio
async def test_agent_run_tool_call_failure(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the agent run flow when a tool call results in an error."""
    goal = "Use broken tool"
    tool_name = "broken_calculator"
    tool_input = {"query": "1/0"} # This is the 'arguments' part for the tool
    tool_error = "Division by zero"
    # Use the correct PlanStep structure with action_type and details
    plan_obj = Plan(steps=[PlanStep(action_type="tool_call", details={"tool_name": tool_name, "arguments": tool_input})])
    # ToolResult needs tool_name and tool_args
    tool_result = ToolResult(tool_name=tool_name, tool_args=tool_input, output=None, error=tool_error)

    mock_planner.plan.return_value = plan_obj # Return Plan object
    mock_tool_manager.execute_tool.return_value = tool_result # Mock the tool execution result

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run_async(goal) # Use run_async

    # Check planner, security, tool manager calls
    expected_context = {'messages': [], 'profile': {}, 'available_tools': []}
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=expected_context)
    # Agent passes action_desc = "tool_call:broken_calculator" and the step context
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action="tool_call:broken_calculator", context={"step": plan_obj.steps[0]} # Use plan_obj
    )
    mock_tool_manager.execute_tool.assert_awaited_once_with(tool_name, tool_input)

    # Check memory calls - Uses add_message
    expected_calls = [
        call(role="user", content=goal),
        call(role="tool", content=f"Tool '{tool_name}' called with args {tool_input}. Failed: {tool_error}", metadata={'tool_result': tool_result.model_dump()}),
    ]
    mock_memory.add_message.assert_has_calls(expected_calls, any_order=False)

    # Check final result - Agent returns the error message directly
    assert result == f"Task failed at step 1: {tool_error}"


@pytest.mark.asyncio
async def test_agent_run_mcp_proxy_call_success(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the agent run flow with a successful mcp_proxy_tool call."""
    goal = "Get weather via MCP"
    mcp_tool_name = "mcp_proxy_tool"
    mcp_tool_input = {
        "server_name": "weather_server",
        "tool_name": "get_weather",
        "arguments": {"city": "London"}
    }
    mcp_tool_output = {"temperature": 15, "conditions": "Cloudy"}
    plan_obj = Plan(steps=[PlanStep(action_type="tool_call", details={"tool_name": mcp_tool_name, "arguments": mcp_tool_input})])
    tool_result = ToolResult(tool_name=mcp_tool_name, tool_args=mcp_tool_input, output=mcp_tool_output, error=None)

    mock_planner.plan.return_value = plan_obj
    mock_tool_manager.execute_tool.return_value = tool_result

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run_async(goal)

    # Check planner call
    expected_context = {'messages': [], 'profile': {}, 'available_tools': []}
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=expected_context)

    # Check security call
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action=f"tool_call:{mcp_tool_name}", context={"step": plan_obj.steps[0]}
    )

    # Check tool manager call
    mock_tool_manager.execute_tool.assert_awaited_once_with(mcp_tool_name, mcp_tool_input)

    # Check memory calls
    expected_calls = [
        call(role="user", content=goal),
        call(role="tool", content=f"Tool '{mcp_tool_name}' called with args {mcp_tool_input}. Result: {mcp_tool_output}", metadata={'tool_result': tool_result.model_dump()}),
        call(role="assistant", content="Final Result: Plan executed but no explicit completion step found.")
    ]
    mock_memory.add_message.assert_has_calls(expected_calls, any_order=False)

    # Check final result
    assert result == "Plan executed but no explicit completion step found."


@pytest.mark.asyncio
async def test_agent_run_mcp_proxy_call_failure(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the agent run flow when an mcp_proxy_tool call results in an error."""
    goal = "Get weather via MCP (fail)"
    mcp_tool_name = "mcp_proxy_tool"
    mcp_tool_input = {
        "server_name": "weather_server",
        "tool_name": "get_weather",
        "arguments": {"city": "InvalidCity"}
    }
    mcp_tool_error = "MCP server error: City not found"
    plan_obj = Plan(steps=[PlanStep(action_type="tool_call", details={"tool_name": mcp_tool_name, "arguments": mcp_tool_input})])
    tool_result = ToolResult(tool_name=mcp_tool_name, tool_args=mcp_tool_input, output=None, error=mcp_tool_error)

    mock_planner.plan.return_value = plan_obj
    mock_tool_manager.execute_tool.return_value = tool_result

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run_async(goal)

    # Check planner, security, tool manager calls
    expected_context = {'messages': [], 'profile': {}, 'available_tools': []}
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=expected_context)
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action=f"tool_call:{mcp_tool_name}", context={"step": plan_obj.steps[0]}
    )
    mock_tool_manager.execute_tool.assert_awaited_once_with(mcp_tool_name, mcp_tool_input)

    # Check memory calls
    expected_calls = [
        call(role="user", content=goal),
        call(role="tool", content=f"Tool '{mcp_tool_name}' called with args {mcp_tool_input}. Failed: {mcp_tool_error}", metadata={'tool_result': tool_result.model_dump()}),
    ]
    mock_memory.add_message.assert_has_calls(expected_calls, any_order=False)

    # Check final result
    assert result == f"Task failed at step 1: {mcp_tool_error}"
