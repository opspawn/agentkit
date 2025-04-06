"""
Unit tests for the SimplePlanner class.
"""

import pytest
from agentkit.planning.simple_planner import SimplePlanner, Context, Plan


def test_planner_initialization():
    """Test basic initialization."""
    planner = SimplePlanner()
    assert isinstance(planner, SimplePlanner)


def test_generate_plan_returns_plan():
    """Test that generate_plan returns the expected dummy plan structure."""
    planner = SimplePlanner()
    goal = "Test goal"
    context: Context = {"messages": [{"role": "user", "content": "Hello"}]}

    plan: Plan = planner.generate_plan(goal=goal, context=context)

    # Check if the plan is a list
    assert isinstance(plan, list)
    # Check if the plan is not empty (for the dummy plan)
    assert len(plan) > 0
    # Check if each step in the plan is a dictionary
    for step in plan:
        assert isinstance(step, dict)
        assert "action" in step
        assert "details" in step

    # Check the specific dummy plan content
    assert plan[0]["action"] == "log"
    assert goal in plan[0]["details"]
    assert plan[1]["action"] == "complete"
