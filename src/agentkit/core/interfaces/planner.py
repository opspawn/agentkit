# agentkit/agentkit/core/interfaces/planner.py
"""Abstract Base Class for agent planners."""

import abc
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


# --- Data Models for Planning ---

class PlanStep(BaseModel):
    """Represents a single step in an execution plan."""
    action_type: Literal["tool_call", "final_answer", "error"]
    details: Dict[str, Any] = Field(default_factory=dict)

class Plan(BaseModel):
    """Represents a sequence of steps to achieve a goal."""
    steps: List[PlanStep] = Field(default_factory=list)


# --- Abstract Base Class ---

class BasePlanner(abc.ABC):
    """Abstract base class for agent planning modules."""

    @abc.abstractmethod
    async def plan(self, goal: str, context: Dict[str, Any]) -> Plan: # Changed return type annotation
        """
        Generate a sequence of steps (actions) to achieve a given goal.

        Args:
            goal: The objective for the agent.
            context: Supporting information or state relevant to planning.

        Returns:
            A Plan object containing the sequence of steps.
        """
        raise NotImplementedError
