"""
Core Agent class definition for agentkit.
"""

import asyncio
from typing import Dict, Any, Optional, List

# Assuming the memory and planner modules are structured correctly
# Adjust imports based on final package structure if needed
from agentkit.memory.short_term import ShortTermMemory, Message
from agentkit.planning.simple_planner import SimplePlanner, Plan, Context
# Import tool components
from agentkit.tools import ToolRegistry, ToolResult, ToolExecutionError, ToolNotFoundError

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
        tool_registry: Optional[ToolRegistry] = None,
        profile: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the Agent.

        Args:
            planner: An instance of a planner component (e.g., SimplePlanner).
                     Defaults to a new SimplePlanner if None.
            memory: An instance of a memory component (e.g., ShortTermMemory).
                    Defaults to a new ShortTermMemory if None.
            tool_registry: An instance of ToolRegistry containing available tools.
                           Defaults to a new empty ToolRegistry if None.
            profile: A dictionary containing agent configuration, persona, etc.
                     Defaults to an empty dict.
        """
        self.planner = planner if planner is not None else SimplePlanner()
        self.memory = memory if memory is not None else ShortTermMemory()
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
        self.profile = profile if profile is not None else {}
        print(
            f"Agent initialized with Planner: {type(self.planner).__name__}, "
            f"Memory: {type(self.memory).__name__}, "
            f"Tools: {len(self.tool_registry.list_tools())}"
        )

    def _get_context(self) -> Context:
        """
        Constructs the context for the planner based on memory, profile, and available tools.
        """
        # Include tool specifications in the context for the planner
        tool_specs = [spec.model_dump() for spec in self.tool_registry.list_tools()]
        return {
            "messages": self.memory.get_messages(),
            "profile": self.profile,
            "available_tools": tool_specs,
        }

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
            The final result of the task execution.
        """
        # Ensure execution happens in an async context if tools are async
        return asyncio.run(self.execute_task_async(goal))

    async def execute_task_async(self, goal: str) -> Any:
        """
        Asynchronous execution of a given task or goal.

        Args:
            goal: The objective to achieve.

        Returns:
            The final result of the task execution.
        """
        print(f"\nAgent executing task: {goal}")

        # 1. Get context
        context = self._get_context()
        print(f"Context prepared with {len(context.get('messages', []))} messages.")

        # 2. Generate plan
        plan: Plan = self.planner.generate_plan(goal=goal, context=context)
        print(f"Plan generated with {len(plan)} steps.")

        # 3. Execute plan steps
        print("Executing plan:")
        final_result = None
        step_results: List[Any] = [] # Store results of each step if needed

        for i, step in enumerate(plan):
            print(f"  - Executing Step {i+1}: {step}")
            step_outcome = await self._execute_step(step)
            step_results.append(step_outcome) # Store outcome (e.g., ToolResult)

            # Update memory after each step
            # TODO: Refine memory update logic (e.g., add ToolResult details)
            self.memory.add_message({"role": "assistant", "content": f"Step {i+1} outcome: {step_outcome}"})

            # Check if the step resulted in an error or completion
            if isinstance(step_outcome, ToolResult) and step_outcome.error:
                print(f"    - Step failed: {step_outcome.error}")
                final_result = f"Task failed at step {i+1}: {step_outcome.error}"
                break # Stop execution on error
            elif step.get("action") == "complete":
                final_result = step.get("details", "Task completed successfully.")
                print(f"    - Task marked complete.")
                break # Stop execution on completion

        # If loop finished without explicit completion/error
        if final_result is None:
            final_result = "Plan executed, but no explicit completion step found."
            print(f"    - {final_result}")


        # 4. Final Memory Update (Goal + Final Result)
        self.memory.add_message({"role": "user", "content": goal})
        self.memory.add_message({"role": "assistant", "content": f"Final Result: {final_result}"})
        print(f"Memory updated. Current message count: {len(self.memory.get_messages())}") # Use get_messages()

        return final_result

    async def _execute_step(self, step: Dict[str, Any]) -> Any:
        """
        Executes a single step from the plan.

        Currently handles 'tool_call' actions.

        Args:
            step: A dictionary representing the plan step.

        Returns:
            The result of the step execution (e.g., ToolResult or step details).
        """
        action = step.get("action")

        if action == "tool_call":
            tool_name = step.get("tool_name")
            arguments = step.get("arguments", {})
            if not tool_name:
                return ToolResult(tool_name="unknown", tool_input=arguments, error="Missing 'tool_name' in tool_call step.")

            print(f"    - Calling tool: {tool_name} with args: {arguments}")
            try:
                result: ToolResult = await self.tool_registry.execute_tool(tool_name, arguments)
                if result.error:
                    print(f"    - Tool execution failed: {result.error}")
                else:
                    print(f"    - Tool execution successful. Output: {result.output}")
                return result
            except (ToolNotFoundError, ToolExecutionError, Exception) as e:
                 # Reason: Catch potential errors during registry interaction or unexpected issues.
                print(f"    - Error during tool execution attempt: {e}")
                return ToolResult(tool_name=tool_name, tool_input=arguments, error=f"Failed to execute tool: {e}")

        elif action == "complete":
            # No specific execution, just return details
            return step.get("details", "Completion step executed.")
        else:
            # Placeholder for other action types (e.g., 'think', 'respond')
            print(f"    - Executing non-tool action: {action} (details: {step.get('details')})")
            return f"Action '{action}' executed." # Placeholder result
