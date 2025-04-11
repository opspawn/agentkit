# agentkit/planning/placeholder_planner.py
from typing import Any, Dict, List

from agentkit.core.interfaces.planner import BasePlanner, Plan, PlanStep


class PlaceholderPlanner(BasePlanner):
    """
    A simple placeholder implementation of the BasePlanner interface.

    This planner does not perform any real planning logic. It can be used
    for testing the agent structure or as a base for more complex planners.
    By default, it returns an empty plan.
    """

    async def plan(self, goal: str, history: List[Dict[str, Any]]) -> Plan:
        """
        Generates a placeholder plan.

        Currently returns an empty plan, indicating no steps are needed
        or that planning is not implemented.

        Args:
            goal (str): The objective the agent needs to achieve (ignored).
            history (List[Dict[str, Any]]): The current memory history (ignored).

        Returns:
            Plan: An empty plan.
        """
        # For MVP, just return an empty plan or a single "final_answer" step.
        # Let's return a single step indicating completion for now.
        final_step = PlanStep(
            action_type="final_answer", details={"answer": f"Placeholder plan for goal: {goal}"}
        )
        return Plan(steps=[final_step])

        # Alternatively, raise NotImplementedError:
        # raise NotImplementedError(
        #     "PlaceholderPlanner does not implement actual planning logic."
        # )
