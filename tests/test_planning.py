# agentkit/tests/test_planning.py
"""Unit tests for the SimplePlanner class."""

import pytest
from typing import Dict, Any, List
from agentkit.planning.simple_planner import SimplePlanner



def test_planner_initialization():
    """Test basic initialization."""
    planner = SimplePlanner()
    assert isinstance(planner, SimplePlanner)


@pytest.mark.asyncio
async def test_plan_returns_plan():
    """Test that the async plan method returns the expected dummy plan structure."""
    planner = SimplePlanner()
    goal = "Test goal"
    context: Dict[str, Any] = {"messages": [{"role": "user", "content": "Hello"}]}

    plan: List[Dict[str, Any]] = await planner.plan(goal=goal, context=context)

    # Check if the plan is a list
    assert isinstance(plan, list)
    # Check if the plan is not empty (for the dummy plan)
    assert len(plan) > 0
    # Check if each step in the plan is a dictionary
    for step in plan:
        assert isinstance(step, dict)
        assert "action" in step
        assert "args" in step # Check for 'args' now

    # Check the specific dummy plan content
    assert plan[0]["action"] == "log"
    assert "message" in plan[0]["args"]
    assert goal in plan[0]["args"]["message"]
    assert plan[1]["action"] == "complete"
    assert "message" in plan[1]["args"]
