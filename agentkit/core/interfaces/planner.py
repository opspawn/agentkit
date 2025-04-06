# agentkit/agentkit/core/interfaces/planner.py
"""Abstract Base Class for agent planners."""

import abc
from typing import Any, Dict, List


class BasePlanner(abc.ABC):
    """Abstract base class for agent planning modules."""

    @abc.abstractmethod
    async def plan(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a sequence of steps (actions) to achieve a given goal.

        Args:
            goal: The objective for the agent.
            context: Supporting information or state relevant to planning.

        Returns:
            A list of dictionaries, where each dictionary represents a step
            (e.g., {'action': 'tool_name', 'args': {...}}).
        """
        raise NotImplementedError
