"""
Core Agent class definition for agentkit.
"""

from typing import Dict, Any, Optional

# Assuming the memory and planner modules are structured correctly
# Adjust imports based on final package structure if needed
from agentkit.memory.short_term import ShortTermMemory, Message
from agentkit.planning.simple_planner import SimplePlanner, Plan, Context


class Agent:
    """
    The core agent class responsible for coordinating planning, memory, and execution.
    """

    def __init__(
        self,
        planner: Optional[SimplePlanner] = None,
        memory: Optional[ShortTermMemory] = None,
        profile: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the Agent.

        Args:
            planner: An instance of a planner component (e.g., SimplePlanner).
                     Defaults to a new SimplePlanner if None.
            memory: An instance of a memory component (e.g., ShortTermMemory).
                    Defaults to a new ShortTermMemory if None.
            profile: A dictionary containing agent configuration, persona, etc.
                     Defaults to an empty dict.
        """
        self.planner = planner if planner is not None else SimplePlanner()
        self.memory = memory if memory is not None else ShortTermMemory()
        self.profile = profile if profile is not None else {}
        print(f"Agent initialized with Planner: {type(self.planner).__name__}, Memory: {type(self.memory).__name__}")

    def _get_context(self) -> Context:
        """
        Constructs the context for the planner based on memory and profile.
        """
        # Simple context for MVP: just includes current messages
        return {"messages": self.memory.get_messages(), "profile": self.profile}

    def execute_task(self, goal: str) -> Any:
        """
        Executes a given task or goal.

        This involves:
        1. Getting the current context (including memory).
        2. Generating a plan using the planner.
        3. (Future Step) Executing the plan steps (e.g., calling tools).
        4. (Future Step) Updating memory based on execution.

        Args:
            goal: The objective to achieve.

        Returns:
            The result of the task execution (placeholder for MVP).
        """
        print(f"\nAgent executing task: {goal}")

        # 1. Get context
        context = self._get_context()
        print(f"Context prepared with {len(context.get('messages', []))} messages.")

        # 2. Generate plan
        plan: Plan = self.planner.generate_plan(goal=goal, context=context)
        print(f"Plan generated with {len(plan)} steps.")

        # 3. Execute plan (Placeholder for MVP)
        print("Executing plan (MVP - logging steps):")
        result = None
        for step in plan:
            print(f"  - Step: {step}")
            # In a real agent, this would involve dispatching actions, calling tools, etc.
            if step.get("action") == "complete":
                result = step.get("details", "Task completed.")

        # 4. Update memory (Placeholder for MVP)
        # Example: Add the goal and result to memory
        self.memory.add_message({"role": "user", "content": goal})
        self.memory.add_message({"role": "assistant", "content": f"Result: {result}"})
        print(f"Memory updated. Current message count: {len(self.memory)}")

        return result
