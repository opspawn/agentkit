# agentkit/core/agent.py
import asyncio
from typing import Any, Dict, Optional

from agentkit.core.interfaces import (
    BaseMemory,
    BasePlanner,
    BaseSecurityManager,
    BaseToolManager,
)


class Agent:
    """
    Core Agent class responsible for orchestrating planning, memory, and tool use.

    This class integrates different modules (planner, memory, tool manager, security manager)
    to achieve a given goal by executing a sequence of steps.
    """

    def __init__(
        self,
        memory: BaseMemory,
        planner: BasePlanner,
        tool_manager: BaseToolManager,
        security_manager: BaseSecurityManager,
    ):
        """
        Initializes the Agent with its core components.

        Args:
            memory: The memory module instance.
            planner: The planning module instance.
            tool_manager: The tool management module instance.
            security_manager: The security management module instance.
        """
        if not isinstance(memory, BaseMemory):
            raise TypeError("memory must be an instance of BaseMemory")
        if not isinstance(planner, BasePlanner):
            raise TypeError("planner must be an instance of BasePlanner")
        if not isinstance(tool_manager, BaseToolManager):
            raise TypeError("tool_manager must be an instance of BaseToolManager")
        if not isinstance(security_manager, BaseSecurityManager):
            raise TypeError("security_manager must be an instance of BaseSecurityManager")

        self.memory = memory
        self.planner = planner
        self.tool_manager = tool_manager
        self.security_manager = security_manager

    async def run(self, goal: str) -> Dict[str, Any]:
        """
        Executes the agent's main loop to achieve the specified goal.

        Args:
            goal (str): The objective for the agent to accomplish.

        Returns:
            Dict[str, Any]: A dictionary containing the final result or outcome.
                            The structure may vary based on the task completion.
        """
        print(f"Agent starting run for goal: {goal}")
        self.memory.add_entry({"type": "goal", "content": goal})

        # --- Main Execution Loop (Simplified for MVP) ---
        # In a more complex agent, this would be a loop that continues
        # until a final answer is reached or a step limit is hit.
        # It would involve planning, executing steps, observing results,
        # and re-planning if necessary.

        # 1. Plan
        current_history = self.memory.get_history()
        print(f"Generating plan with history: {current_history}")
        plan = await self.planner.plan(goal=goal, history=current_history)
        self.memory.add_entry({"type": "plan", "content": plan.dict()})
        print(f"Generated plan: {plan.dict()}")

        final_result: Dict[str, Any] = {"status": "No steps executed"}

        # 2. Execute Steps (Simplified - assumes only one step for now)
        if plan.steps:
            step = plan.steps[0]  # Process only the first step in MVP
            print(f"Processing step: {step.dict()}")
            self.memory.add_entry({"type": "step_taken", "content": step.dict()})

            # 3. Security Check
            is_allowed = self.security_manager.check_execution(
                action_type=step.action_type, details=step.details
            )
            print(f"Security check result: {'Allowed' if is_allowed else 'Denied'}")

            if not is_allowed:
                error_msg = "Action denied by security manager."
                self.memory.add_entry({"type": "error", "content": error_msg})
                final_result = {"status": "Failed", "reason": error_msg}
            else:
                # 4. Execute Action (Simplified)
                if step.action_type == "tool_call":
                    # This part will be more relevant after Task 2.3 (Tool Integration)
                    # and when using a planner that generates tool calls.
                    tool_name = step.details.get("name")
                    tool_input = step.details.get("input", {})
                    if tool_name:
                        print(f"Executing tool: {tool_name} with input: {tool_input}")
                        # Actually execute the tool via the tool manager
                        tool_result = await self.tool_manager.execute_tool(
                            name=tool_name, tool_input=tool_input
                        )
                        tool_result_data = tool_result.dict() # Convert ToolResult to dict
                        self.memory.add_entry(
                            {"type": "tool_result", "tool_name": tool_name, "result": tool_result_data}
                        )
                        # Determine final status based on tool result
                        if tool_result.error:
                             final_result = {"status": "Tool Failed", "result": tool_result_data}
                        else:
                             final_result = {"status": "Tool Executed", "result": tool_result_data}
                    else:
                        error_msg = "Tool call step missing tool name."
                        self.memory.add_entry({"type": "error", "content": error_msg})
                        final_result = {"status": "Failed", "reason": error_msg}

                elif step.action_type == "final_answer":
                    answer = step.details.get("answer", "No answer provided.")
                    print(f"Final answer step: {answer}")
                    self.memory.add_entry({"type": "final_answer", "content": answer})
                    final_result = {"status": "Completed", "answer": answer}
                else:
                    print(f"Unknown action type: {step.action_type}")
                    self.memory.add_entry(
                        {"type": "error", "content": f"Unknown action type: {step.action_type}"}
                    )
                    final_result = {"status": "Failed", "reason": f"Unknown action type: {step.action_type}"}
        else:
            print("Plan contained no steps.")
            self.memory.add_entry({"type": "info", "content": "Plan contained no steps."})
            final_result = {"status": "Completed", "reason": "No steps in plan"}

        print(f"Agent run finished. Final result: {final_result}")
        return final_result

    async def reset(self):
        """Resets the agent's memory."""
        print("Resetting agent memory.")
        self.memory.clear()
