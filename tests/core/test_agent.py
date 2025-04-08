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


# --- Fixtures for Mocks ---

@pytest.fixture
def mock_memory():
    """Fixture for a mocked BaseMemory."""
    mock = MagicMock(spec=BaseMemory)
    mock.get_history.return_value = [] # Default empty history
    return mock

@pytest.fixture
def mock_planner():
    """Fixture for a mocked BasePlanner."""
    mock = MagicMock(spec=BasePlanner)
    # Default plan: a single final_answer step
    default_plan = Plan(steps=[PlanStep(action_type="final_answer", details={"answer": "Mock answer"})])
    mock.plan = AsyncMock(return_value=default_plan)
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
    mock.check_execution.return_value = True # Default: allow execution
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

    result = await agent.run(goal)

    # Check planner call
    mock_planner.plan.assert_awaited_once_with(goal=goal, history=[]) # Assumes empty initial history from fixture

    # Check security call
    mock_security_manager.check_execution.assert_called_once_with(
        action_type="final_answer", details={"answer": final_answer}
    )

    # Check memory calls
    expected_calls = [
        call({"type": "goal", "content": goal}),
        call({"type": "plan", "content": plan.dict()}),
        call({"type": "step_taken", "content": plan.steps[0].dict()}),
        call({"type": "final_answer", "content": final_answer}),
    ]
    mock_memory.add_entry.assert_has_calls(expected_calls)

    # Check final result
    assert result == {"status": "Completed", "answer": final_answer}


@pytest.mark.asyncio
async def test_agent_run_security_denial(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the run flow when the security manager denies an action."""
    goal = "Risky task"
    plan = Plan(steps=[PlanStep(action_type="tool_call", details={"name": "risky_tool"})])
    mock_planner.plan.return_value = plan
    mock_security_manager.check_execution.return_value = False # Deny execution

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run(goal)

    # Check security call
    mock_security_manager.check_execution.assert_called_once_with(
        action_type="tool_call", details={"name": "risky_tool"}
    )

    # Check memory calls (should include error)
    expected_calls = [
        call({"type": "goal", "content": goal}),
        call({"type": "plan", "content": plan.dict()}),
        call({"type": "step_taken", "content": plan.steps[0].dict()}),
        call({"type": "error", "content": "Action denied by security manager."}),
    ]
    mock_memory.add_entry.assert_has_calls(expected_calls)

    # Check final result
    assert result == {"status": "Failed", "reason": "Action denied by security manager."}
    mock_tool_manager.execute_tool.assert_not_awaited() # Tool should not be called


@pytest.mark.asyncio
async def test_agent_run_no_steps_in_plan(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the run flow when the planner returns an empty plan."""
    goal = "Task with no steps"
    plan = Plan(steps=[]) # Empty plan
    mock_planner.plan.return_value = plan

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run(goal)

    # Check planner call
    mock_planner.plan.assert_awaited_once_with(goal=goal, history=[])

    # Check memory calls
    expected_calls = [
        call({"type": "goal", "content": goal}),
        call({"type": "plan", "content": plan.dict()}),
        call({"type": "info", "content": "Plan contained no steps."}),
    ]
    mock_memory.add_entry.assert_has_calls(expected_calls)

    # Check final result
    assert result == {"status": "Completed", "reason": "No steps in plan"}
    mock_security_manager.check_execution.assert_not_called()
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
    await agent.reset()
    mock_memory.clear.assert_called_once()


@pytest.mark.asyncio
async def test_agent_run_tool_call(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the agent run flow when the plan involves a tool call."""
    goal = "Use calculator"
    tool_name = "calculator"
    tool_input = {"query": "2+2"}
    tool_output = {"result": 4}
    plan = Plan(steps=[PlanStep(action_type="tool_call", details={"name": tool_name, "input": tool_input})])
    tool_result = ToolResult(output=tool_output, error=None)

    mock_planner.plan.return_value = plan
    mock_tool_manager.execute_tool.return_value = tool_result # Mock the tool execution result

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run(goal)

    # Check planner call
    mock_planner.plan.assert_awaited_once_with(goal=goal, history=[])

    # Check security call
    mock_security_manager.check_execution.assert_called_once_with(
        action_type="tool_call", details={"name": tool_name, "input": tool_input}
    )

    # Check tool manager call
    mock_tool_manager.execute_tool.assert_awaited_once_with(name=tool_name, tool_input=tool_input)

    # Check memory calls
    expected_calls = [
        call({"type": "goal", "content": goal}),
        call({"type": "plan", "content": plan.dict()}),
        call({"type": "step_taken", "content": plan.steps[0].dict()}),
        call({"type": "tool_result", "tool_name": tool_name, "result": tool_result.dict()}),
    ]
    mock_memory.add_entry.assert_has_calls(expected_calls)

    # Check final result
    assert result == {"status": "Tool Executed", "result": tool_result.dict()}


@pytest.mark.asyncio
async def test_agent_run_tool_call_failure(
    mock_memory, mock_planner, mock_tool_manager, mock_security_manager
):
    """Tests the agent run flow when a tool call results in an error."""
    goal = "Use broken tool"
    tool_name = "broken_calculator"
    tool_input = {"query": "1/0"}
    tool_error = "Division by zero"
    plan = Plan(steps=[PlanStep(action_type="tool_call", details={"name": tool_name, "input": tool_input})])
    tool_result = ToolResult(output=None, error=tool_error)

    mock_planner.plan.return_value = plan
    mock_tool_manager.execute_tool.return_value = tool_result # Mock the tool execution result

    agent = Agent(
        memory=mock_memory,
        planner=mock_planner,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    result = await agent.run(goal)

    # Check planner, security, tool manager calls
    mock_planner.plan.assert_awaited_once_with(goal=goal, history=[])
    mock_security_manager.check_execution.assert_called_once_with(
        action_type="tool_call", details={"name": tool_name, "input": tool_input}
    )
    mock_tool_manager.execute_tool.assert_awaited_once_with(name=tool_name, tool_input=tool_input)

    # Check memory calls
    expected_calls = [
        call({"type": "goal", "content": goal}),
        call({"type": "plan", "content": plan.dict()}),
        call({"type": "step_taken", "content": plan.steps[0].dict()}),
        call({"type": "tool_result", "tool_name": tool_name, "result": tool_result.dict()}),
    ]
    mock_memory.add_entry.assert_has_calls(expected_calls)

    # Check final result
    assert result == {"status": "Tool Failed", "result": tool_result.dict()}
