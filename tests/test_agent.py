# agentkit/tests/test_agent.py
"""Unit tests for the core Agent class."""

import pytest
from unittest.mock import MagicMock, AsyncMock  # Use AsyncMock for async methods

from agentkit.core.agent import Agent, PlaceholderSecurityManager
from agentkit.core.interfaces import (
    BaseMemory,
    BasePlanner,
    BaseSecurityManager,
    BaseToolManager,
)
# Import concrete classes for checking defaults
from agentkit.memory.short_term import ShortTermMemory
from agentkit.planning.simple_planner import SimplePlanner
from agentkit.tools.registry import ToolRegistry
from agentkit.tools.schemas import ToolResult, ToolSpec, DEFAULT_SCHEMA, Tool # Added DEFAULT_SCHEMA, Tool



def test_agent_initialization_defaults():
    """Test agent initialization with default components."""
    agent = Agent()
    assert isinstance(agent.planner, SimplePlanner)
    assert isinstance(agent.memory, ShortTermMemory)
    assert isinstance(agent.tool_manager, ToolRegistry)
    assert isinstance(agent.security_manager, PlaceholderSecurityManager)
    assert agent.profile == {}


def test_agent_initialization_custom_components():
    """Test agent initialization with custom components using mocks."""
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)
    mock_profile = {"name": "TestAgent", "role": "tester"}

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
        profile=mock_profile,
    )
    assert agent.planner is mock_planner
    assert agent.memory is mock_memory
    assert agent.tool_manager is mock_tool_manager
    assert agent.security_manager is mock_security_manager
    assert agent.profile == mock_profile


@pytest.mark.asyncio
async def test_agent_run_async_flow_completion():
    """Test the basic flow of run_async ending with a completion step."""
    # Use mocks for dependencies
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    goal = "Achieve test objective"
    dummy_context = {"messages": [], "profile": {}, "available_tools": []}
    dummy_plan = [
        {"action": "log", "args": {"message": "Starting..."}},
        {"action": "complete", "args": {"message": "Test objective achieved"}},
    ]

    # Setup mock return values
    mock_memory.get_context.return_value = dummy_context["messages"]
    mock_planner.plan.return_value = dummy_plan
    mock_security_manager.check_permissions.return_value = True # Allow all actions

    # Execute the task asynchronously
    result = await agent.run_async(goal)

    # Assertions
    # 1. Memory received initial goal
    mock_memory.add_message.assert_any_call(role="user", content=goal)

    # 2. Planner was called with the goal and context
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=dummy_context)

    # 3. Security manager checked permissions for steps
    assert mock_security_manager.check_permissions.call_count == len(dummy_plan)
    mock_security_manager.check_permissions.assert_any_call(action="log", context={"step": dummy_plan[0]})
    mock_security_manager.check_permissions.assert_any_call(action="complete", context={"step": dummy_plan[1]})


    # 4. Memory was updated for each step outcome
    #    (Goal + Log Step Outcome + Completion Step Outcome)
    assert mock_memory.add_message.call_count == 3
    mock_memory.add_message.assert_any_call(role="assistant", content="Step 1 outcome: Log action executed: Starting...")
    mock_memory.add_message.assert_any_call(role="assistant", content="Step 2 outcome: Test objective achieved")


    # 5. Result is correct
    assert result == "Test objective achieved"


@pytest.mark.asyncio
async def test_agent_run_async_flow_tool_call():
    """Test the flow of run_async involving a tool call."""
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    goal = "Use the calculator"
    dummy_context = {"messages": [], "profile": {}, "available_tools": []}
    tool_name = "calculator"
    tool_args = {"op": "add", "a": 1, "b": 2}
    dummy_plan = [
        {"action": "tool_call", "args": {"tool_name": tool_name, "arguments": tool_args}},
        {"action": "complete", "args": {"message": "Calculation done"}},
    ]
    tool_result_output = 3
    tool_result = ToolResult(tool_name=tool_name, tool_args=tool_args, output=tool_result_output, status_code=200)

    # Setup mock return values
    mock_memory.get_context.return_value = dummy_context["messages"]
    mock_planner.plan.return_value = dummy_plan
    mock_security_manager.check_permissions.return_value = True
    mock_tool_manager.execute_tool.return_value = tool_result # Mock tool execution result

    # Execute
    result = await agent.run_async(goal)

    # Assertions
    mock_memory.add_message.assert_any_call(role="user", content=goal)
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=dummy_context)
    assert mock_security_manager.check_permissions.call_count == len(dummy_plan)
    mock_security_manager.check_permissions.assert_any_call(action=f"tool_call:{tool_name}", context={"step": dummy_plan[0]})

    # Tool manager was called correctly
    mock_tool_manager.execute_tool.assert_awaited_once_with(tool_name, tool_args)

    # Memory updated with tool result
    expected_tool_memory = f"Tool '{tool_name}' called with args {tool_args}. Result: {tool_result_output}"
    # Check if any call matches the tool result structure
    found_tool_memory_call = False
    for call in mock_memory.add_message.await_args_list:
        if call.kwargs.get("role") == "tool" and call.kwargs.get("content") == expected_tool_memory:
            found_tool_memory_call = True
            assert call.kwargs.get("metadata") == {"tool_result": tool_result.model_dump()}
            break
    assert found_tool_memory_call, "Tool result message not found in memory calls"

    # Memory updated with completion step
    mock_memory.add_message.assert_any_call(role="assistant", content="Step 2 outcome: Calculation done")

    # Final result
    assert result == "Calculation done"


@pytest.mark.asyncio
async def test_agent_run_async_flow_tool_error():
    """Test the flow of run_async when a tool call results in an error."""
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    goal = "Use broken tool"
    dummy_context = {"messages": [], "profile": {}, "available_tools": []}
    tool_name = "broken_tool"
    tool_args = {}
    dummy_plan = [
        {"action": "tool_call", "args": {"tool_name": tool_name, "arguments": tool_args}},
        {"action": "complete", "args": {"message": "Should not reach here"}}, # This step won't run
    ]
    error_message = "Tool malfunctioned"
    tool_error_result = ToolResult(tool_name=tool_name, tool_args=tool_args, error=error_message, status_code=500)

    # Setup mocks
    mock_memory.get_context.return_value = dummy_context["messages"]
    mock_planner.plan.return_value = dummy_plan
    mock_security_manager.check_permissions.return_value = True
    mock_tool_manager.execute_tool.return_value = tool_error_result # Mock tool error

    # Execute
    result = await agent.run_async(goal)

    # Assertions
    mock_memory.add_message.assert_any_call(role="user", content=goal)
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=dummy_context)
    # Security check only happens for the first step
    mock_security_manager.check_permissions.assert_awaited_once_with(action=f"tool_call:{tool_name}", context={"step": dummy_plan[0]})
    mock_tool_manager.execute_tool.assert_awaited_once_with(tool_name, tool_args)

    # Memory updated with tool error
    expected_tool_memory = f"Tool '{tool_name}' called with args {tool_args}. Failed: {error_message}"
    found_tool_memory_call = False
    for call in mock_memory.add_message.await_args_list:
        if call.kwargs.get("role") == "tool" and call.kwargs.get("content") == expected_tool_memory:
            found_tool_memory_call = True
            assert call.kwargs.get("metadata") == {"tool_result": tool_error_result.model_dump()}
            break
    assert found_tool_memory_call, "Tool error message not found in memory calls"

    # Final result reflects the error
    assert result == f"Task failed at step 1: {error_message}"


@pytest.mark.asyncio
async def test_agent_get_context():
    """Test the _get_context method asynchronously."""
    mock_memory = AsyncMock(spec=BaseMemory)
    # Use ToolRegistry directly to test tool listing part
    tool_registry = ToolRegistry()
    # Add a dummy tool for testing context
    # Use DEFAULT_SCHEMA for tools without specific input/output models
    dummy_tool_spec = ToolSpec(
        name="dummy",
        description="A test tool",
        input_schema=DEFAULT_SCHEMA, # Use DEFAULT_SCHEMA
        output_schema=DEFAULT_SCHEMA # Use DEFAULT_SCHEMA
    )
    # Need a concrete Tool subclass instance to add to registry
    class DummyTool(Tool):
        spec = dummy_tool_spec
        def execute(self, args): return "dummy output" # Needs execute method
    dummy_tool_instance = DummyTool()
    tool_registry.add_tool(dummy_tool_instance)

    profile = {"persona": "helpful assistant"}
    agent = Agent(memory=mock_memory, tool_manager=tool_registry, profile=profile)

    dummy_messages = [{"role": "user", "content": "Question"}]
    mock_memory.get_context.return_value = dummy_messages

    context = await agent._get_context()

    mock_memory.get_context.assert_awaited_once()
    assert "messages" in context
    assert "profile" in context
    assert "available_tools" in context
    assert context["messages"] == dummy_messages
    assert context["profile"] == profile
    assert len(context["available_tools"]) == 1
    assert context["available_tools"][0] == dummy_tool_spec.model_dump()


@pytest.mark.asyncio
async def test_agent_run_async_security_failure():
    """Test the flow when the security manager denies permission."""
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    goal = "Do something forbidden"
    dummy_context = {"messages": [], "profile": {}, "available_tools": []}
    dummy_plan = [
        {"action": "forbidden_action", "args": {}},
        {"action": "complete", "args": {"message": "Should not reach"}},
    ]

    # Setup mocks
    mock_memory.get_context.return_value = dummy_context["messages"]
    mock_planner.plan.return_value = dummy_plan
    # Security manager denies the first action
    mock_security_manager.check_permissions.return_value = False

    # Execute
    result = await agent.run_async(goal)

    # Assertions
    mock_memory.add_message.assert_any_call(role="user", content=goal)
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=dummy_context)
    # Security check was called for the first step
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action="forbidden_action", context={"step": dummy_plan[0]}
    )
    # Tool manager should not be called
    mock_tool_manager.execute_tool.assert_not_awaited()
    # Memory should only contain the goal and the error message
    assert mock_memory.add_message.call_count == 2 # Goal + Error message
    # Check the specific error message added to memory
    mock_memory.add_message.assert_any_call(
        role="assistant",
        content="Step 1 outcome: Permission denied for action 'forbidden_action'."
    )
    # Final result reflects the permission error
    assert result == "Task failed at step 1: Permission denied for action 'forbidden_action'."


@pytest.mark.asyncio
async def test_agent_run_async_planner_error():
    """Test the flow when the planner raises an exception."""
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    goal = "Plan something complex"
    dummy_context = {"messages": [], "profile": {}, "available_tools": []}
    planner_exception = ValueError("Planning failed")

    # Setup mocks
    mock_memory.get_context.return_value = dummy_context["messages"]
    # Planner raises an error
    mock_planner.plan.side_effect = planner_exception

    # Execute
    result = await agent.run_async(goal)

    # Assertions
    mock_memory.add_message.assert_any_call(role="user", content=goal)
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=dummy_context)
    # Security and tool manager should not be called
    mock_security_manager.check_permissions.assert_not_awaited()
    mock_tool_manager.execute_tool.assert_not_awaited()
    # Memory should contain goal and planning error
    assert mock_memory.add_message.call_count == 2 # Goal + Error message
    mock_memory.add_message.assert_any_call(
        role="assistant",
        content=f"Planning failed: {planner_exception}"
    )
    # Final result reflects the planning error
    assert result == f"Planning failed: {planner_exception}"


@pytest.mark.asyncio
async def test_agent_run_async_invalid_action():
    """Test the flow when the plan contains an unknown action."""
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    goal = "Try unknown action"
    dummy_context = {"messages": [], "profile": {}, "available_tools": []}
    dummy_plan = [
        {"action": "unknown_action", "args": {}},
    ]

    # Setup mocks
    mock_memory.get_context.return_value = dummy_context["messages"]
    mock_planner.plan.return_value = dummy_plan
    mock_security_manager.check_permissions.return_value = True # Allow it

    # Execute
    result = await agent.run_async(goal)

    # Assertions
    mock_memory.add_message.assert_any_call(role="user", content=goal)
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=dummy_context)
    mock_security_manager.check_permissions.assert_awaited_once_with(
        action="unknown_action", context={"step": dummy_plan[0]}
    )
    # Tool manager should not be called
    mock_tool_manager.execute_tool.assert_not_awaited()
    # Memory should contain goal and invalid action error outcome
    assert mock_memory.add_message.call_count == 2 # Goal + Error outcome
    mock_memory.add_message.assert_any_call(
        role="assistant",
        content="Step 1 outcome: Unknown action type: 'unknown_action'."
    )
    # Final result reflects the error
    assert result == "Task failed at step 1: Unknown action type: 'unknown_action'."


@pytest.mark.asyncio
async def test_agent_run_async_empty_plan():
    """Test the flow when the planner returns an empty plan."""
    mock_planner = AsyncMock(spec=BasePlanner)
    mock_memory = AsyncMock(spec=BaseMemory)
    mock_tool_manager = AsyncMock(spec=BaseToolManager)
    mock_security_manager = AsyncMock(spec=BaseSecurityManager)

    agent = Agent(
        planner=mock_planner,
        memory=mock_memory,
        tool_manager=mock_tool_manager,
        security_manager=mock_security_manager,
    )

    goal = "Do nothing"
    dummy_context = {"messages": [], "profile": {}, "available_tools": []}
    dummy_plan = [] # Empty plan

    # Setup mocks
    mock_memory.get_context.return_value = dummy_context["messages"]
    mock_planner.plan.return_value = dummy_plan

    # Execute
    result = await agent.run_async(goal)

    # Assertions
    mock_memory.add_message.assert_any_call(role="user", content=goal)
    mock_planner.plan.assert_awaited_once_with(goal=goal, context=dummy_context)
    # Security and tool manager should not be called
    mock_security_manager.check_permissions.assert_not_awaited()
    mock_tool_manager.execute_tool.assert_not_awaited()
    # Memory should contain goal and empty plan message
    assert mock_memory.add_message.call_count == 2 # Goal + Error message
    mock_memory.add_message.assert_any_call(
        role="assistant",
        content="Planner returned an empty plan. Task cannot proceed."
    )
    # Final result reflects the empty plan
    assert result == "Planner returned an empty plan. Task cannot proceed."
