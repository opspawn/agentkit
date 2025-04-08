# agentkit/tests/planning/test_placeholder_planner.py
import pytest

from agentkit.core.interfaces.planner import Plan, PlanStep # Added comma
from agentkit.planning.placeholder_planner import PlaceholderPlanner


@pytest.mark.asyncio
async def test_placeholder_planner_plan():
    """Tests the plan method of PlaceholderPlanner."""
    planner = PlaceholderPlanner()
    goal = "Test goal"
    history = [{"type": "user", "content": "Start"}]

    # Execute the plan method
    plan_result = await planner.plan(goal=goal, history=history)

    # Assertions
    assert isinstance(plan_result, Plan)
    assert len(plan_result.steps) == 1

    step = plan_result.steps[0]
    assert isinstance(step, PlanStep)
    assert step.action_type == "final_answer"
    assert "answer" in step.details
    assert step.details["answer"] == f"Placeholder plan for goal: {goal}"


@pytest.mark.asyncio
async def test_placeholder_planner_plan_empty_history():
    """Tests the plan method with empty history."""
    planner = PlaceholderPlanner()
    goal = "Another goal"
    history = []

    plan_result = await planner.plan(goal=goal, history=history)

    assert isinstance(plan_result, Plan)
    assert len(plan_result.steps) == 1
    step = plan_result.steps[0]
    assert step.action_type == "final_answer"
    assert step.details["answer"] == f"Placeholder plan for goal: {goal}"
