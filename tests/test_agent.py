"""
Unit tests for the core Agent class.
"""

import pytest
from unittest.mock import MagicMock  # Using unittest.mock for simplicity here

from agentkit.core.agent import Agent
from agentkit.memory.short_term import ShortTermMemory
from agentkit.planning.simple_planner import SimplePlanner


def test_agent_initialization_defaults():
    """Test agent initialization with default components."""
    agent = Agent()
    assert isinstance(agent.planner, SimplePlanner)
    assert isinstance(agent.memory, ShortTermMemory)
    assert agent.profile == {}


def test_agent_initialization_custom_components():
    """Test agent initialization with custom components."""
    mock_planner = MagicMock(spec=SimplePlanner)
    mock_memory = MagicMock(spec=ShortTermMemory)
    mock_profile = {"name": "TestAgent", "role": "tester"}

    agent = Agent(planner=mock_planner, memory=mock_memory, profile=mock_profile)
    assert agent.planner is mock_planner
    assert agent.memory is mock_memory
    assert agent.profile == mock_profile


def test_agent_execute_task_flow():
    """Test the basic flow of execute_task."""
    # Use real components for this integration test
    memory = ShortTermMemory(max_size=10)
    planner = SimplePlanner()
    agent = Agent(planner=planner, memory=memory)

    goal = "Achieve test objective"

    # Mock the planner's generate_plan to control the output
    dummy_plan = [
        {"action": "step1", "details": "Do something"},
        {"action": "complete", "details": "Test objective achieved"},
    ]
    planner.generate_plan = MagicMock(return_value=dummy_plan)

    # Execute the task
    result = agent.execute_task(goal)

    # Assertions
    # 1. Planner was called with the goal and context
    planner.generate_plan.assert_called_once()
    call_args, call_kwargs = planner.generate_plan.call_args
    assert call_kwargs.get("goal") == goal
    assert "messages" in call_kwargs.get("context", {})
    assert "profile" in call_kwargs.get("context", {})
    assert "available_tools" in call_kwargs.get("context", {}) # Check for tools context

    # 2. Memory was updated (Step 1 outcome, Step 2 outcome, User Goal, Final Result)
    messages = memory.get_messages()
    assert len(messages) == 4
    # Check message order and content based on Agent implementation
    assert messages[0]["role"] == "assistant" # Step 1 outcome
    assert "Step 1 outcome" in messages[0]["content"]
    assert messages[1]["role"] == "assistant" # Step 2 outcome
    assert "Step 2 outcome" in messages[1]["content"]
    assert messages[2]["role"] == "user"      # Goal
    assert messages[2]["content"] == goal
    assert messages[3]["role"] == "assistant" # Final Result
    assert "Final Result: Test objective achieved" in messages[3]["content"]

    # 3. Result is correct
    assert result == "Test objective achieved"


def test_agent_get_context():
    """Test the _get_context method."""
    memory = ShortTermMemory()
    profile = {"persona": "helpful assistant"}
    agent = Agent(memory=memory, profile=profile)

    memory.add_message({"role": "user", "content": "Question"})
    context = agent._get_context()

    assert "messages" in context
    assert "profile" in context
    assert context["messages"] == [{"role": "user", "content": "Question"}]
    assert context["profile"] == profile
