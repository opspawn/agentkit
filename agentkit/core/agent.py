# agentkit/agentkit/core/agent.py
"""Core Agent class definition for agentkit."""

import asyncio
from typing import Any, Dict, List, Optional

# Interface Imports
from agentkit.core.interfaces import (
    BaseMemory,
    BasePlanner,
    BaseSecurityManager,
    BaseToolManager,
)

# Concrete Implementation Imports (for defaults)
from agentkit.memory.short_term import ShortTermMemory
from agentkit.planning.simple_planner import SimplePlanner
from agentkit.tools.registry import ToolRegistry, ToolNotFoundError
from agentkit.tools.schemas import ToolResult

# Placeholder Security Manager (if needed for default)
# from .interfaces.security import BaseSecurityManager # Already imported above
class PlaceholderSecurityManager(BaseSecurityManager):
    """A default, permissive security manager."""
    async def check_permissions(self, action: str, context: Dict[str, Any]) -> bool:
        print(f"Security Check (Placeholder): Allowing action '{action}'")
        return True



class Agent:
    """
    The core agent class responsible for coordinating planning, memory, and execution.
    Uses dependency injection for core components based on defined interfaces.
    """

    def __init__(
        self,
        planner: Optional[BasePlanner] = None,
        memory: Optional[BaseMemory] = None,
        tool_manager: Optional[BaseToolManager] = None,
        security_manager: Optional[BaseSecurityManager] = None,
        profile: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the Agent.

        Args:
            planner: An instance implementing BasePlanner. Defaults to SimplePlanner.
            memory: An instance implementing BaseMemory. Defaults to ShortTermMemory.
            tool_manager: An instance implementing BaseToolManager. Defaults to ToolRegistry.
            security_manager: An instance implementing BaseSecurityManager. Defaults to PlaceholderSecurityManager.
            profile: A dictionary containing agent configuration, persona, etc. Defaults to an empty dict.
        """
        self.planner: BasePlanner = planner if planner is not None else SimplePlanner()
        self.memory: BaseMemory = memory if memory is not None else ShortTermMemory()
        # Default to ToolRegistry which implements BaseToolManager
        self.tool_manager: BaseToolManager = tool_manager if tool_manager is not None else ToolRegistry()
        self.security_manager: BaseSecurityManager = security_manager if security_manager is not None else PlaceholderSecurityManager()
        self.profile: Dict[str, Any] = profile if profile is not None else {}

        # Attempt to get tool count if the tool_manager is a ToolRegistry (common case)
        tool_count = "N/A"
        if isinstance(self.tool_manager, ToolRegistry):
             # Reason: Provide tool count info if possible, handle cases where it's not a ToolRegistry.
             tool_count = len(self.tool_manager.list_tools())

        print(
            f"Agent initialized with Planner: {type(self.planner).__name__}, "
            f"Memory: {type(self.memory).__name__}, "
            f"ToolManager: {type(self.tool_manager).__name__} ({tool_count} tools), "
            f"SecurityManager: {type(self.security_manager).__name__}"
        )

    async def _get_context(self) -> Dict[str, Any]:
        """
        Constructs the context for the planner based on memory, profile, and available tools.
        """
        tool_specs = []
        # Check if the tool_manager has list_tools (like ToolRegistry)
        if isinstance(self.tool_manager, ToolRegistry):
             # Reason: Safely access list_tools only if available on the concrete type.
             tool_specs = [spec.model_dump() for spec in self.tool_manager.list_tools()]

        # Retrieve context asynchronously from memory
        messages = await self.memory.get_context()

        return {
            "messages": messages,
            "profile": self.profile,
            "available_tools": tool_specs,
        }

    def run(self, goal: str) -> Any:
        """Synchronous wrapper for the main async execution loop."""
        # Ensure execution happens in an async context
        return asyncio.run(self.run_async(goal))

    async def run_async(self, goal: str) -> Any:
        """
        Asynchronous execution loop for a given task or goal.

        Args:
            goal: The objective to achieve.

        Returns:
            The final result of the task execution.
        """
        print(f"\nAgent starting task: {goal}")
        await self.memory.add_message(role="user", content=goal)

        # 1. Get context
        context = await self._get_context()
        print(f"Context prepared with {len(context.get('messages', []))} messages.")

        # 2. Generate plan
        try:
            plan: List[Dict[str, Any]] = await self.planner.plan(goal=goal, context=context)
            print(f"Plan generated with {len(plan)} steps.")
        except Exception as e:
            # Handle planner errors
            error_msg = f"Planning failed: {e}"
            print(f"    - {error_msg}")
            await self.memory.add_message(role="assistant", content=error_msg)
            return error_msg # Return error immediately

        # Handle empty plan
        if not plan:
            empty_plan_msg = "Planner returned an empty plan. Task cannot proceed."
            print(f"    - {empty_plan_msg}")
            await self.memory.add_message(role="assistant", content=empty_plan_msg)
            return empty_plan_msg

        # 3. Execute plan steps
        print("Executing plan:")
        final_result: Any = None
        step_results: List[Any] = []  # Store results of each step if needed

        for i, step in enumerate(plan):
            print(f"  - Executing Step {i + 1}: {step}")

            # Security Check (Placeholder)
            action = step.get('action', 'unknown')
            action_desc = action
            if action == 'tool_call':
                # Correctly access tool_name within args
                tool_name = step.get('args', {}).get('tool_name', '')
                action_desc = f"{action}:{tool_name}"

            if not await self.security_manager.check_permissions(action=action_desc, context={"step": step}):
                permission_error_msg = f"Permission denied for action '{action_desc}'."
                print(f"    - Step failed: {permission_error_msg}")
                final_result = f"Task failed at step {i + 1}: {permission_error_msg}"
                # Use the specific error message for memory
                await self.memory.add_message(role="assistant", content=f"Step {i+1} outcome: {permission_error_msg}")
                break # Stop execution on permission denial

            step_outcome = await self._execute_step(step)
            step_results.append(step_outcome)  # Store outcome (e.g., ToolResult)

            # Update memory after each step
            # Refined memory update logic
            if isinstance(step_outcome, ToolResult):
                memory_content = f"Tool '{step_outcome.tool_name}' called with args {step_outcome.tool_args}. "
                if step_outcome.error:
                    memory_content += f"Failed: {step_outcome.error}"
                else:
                    memory_content += f"Result: {step_outcome.output}"
                await self.memory.add_message(role="tool", content=memory_content, metadata={"tool_result": step_outcome.model_dump()})
            else:
                # Handle non-tool results (e.g., completion message)
                 # Add outcome for non-tool steps (like log, or unknown placeholder)
                 await self.memory.add_message(role="assistant", content=f"Step {i+1} outcome: {step_outcome}")


            # Check if the step resulted in an error or completion
            step_failed = False
            if isinstance(step_outcome, ToolResult) and step_outcome.error:
                print(f"    - Step failed (Tool Error): {step_outcome.error}")
                final_result = f"Task failed at step {i + 1}: {step_outcome.error}"
                step_failed = True
                # Memory already updated above
            elif isinstance(step_outcome, str) and step_outcome.startswith("Unknown action type:"):
                 # Handle unknown action error specifically if needed, though memory is updated above
                 print(f"    - Step failed (Unknown Action): {step_outcome}")
                 final_result = f"Task failed at step {i + 1}: {step_outcome}"
                 step_failed = True
                 # Memory already updated above

            if step_failed:
                 break # Stop execution on error

            # Check for completion *after* checking for errors
            if step.get("action") == "complete":
                final_result = step.get("args", {}).get("message", "Task completed successfully.")
                print(f"    - Task marked complete.")
                # Memory already updated above
                break  # Stop execution on completion

        # If loop finished *and* no final_result was set by break (error/completion)
        if final_result is None:
            no_completion_msg = "Plan executed but no explicit completion step found."
            print(f"    - {no_completion_msg}")
            # Only add this message if the loop finished normally
            await self.memory.add_message(role="assistant", content=f"Final Result: {no_completion_msg}")
            final_result = no_completion_msg # Set the final result


        # Log final memory state size
        current_context = await self.memory.get_context()
        print(f"Task finished. Final message count: {len(current_context)}")

        return final_result

    async def _execute_step(self, step: Dict[str, Any]) -> Any: # Renamed from execute_task_async
        """Executes a single step from the plan using the appropriate manager."""
        action = step.get("action")
        args = step.get("args", {}) # Use 'args' consistently with planner output

        if action == "tool_call":
            tool_name = args.get("tool_name") # Expect tool_name within args
            tool_args = args.get("arguments", {}) # Expect arguments within args
            if not tool_name:
                # Reason: Ensure tool_name is provided for tool calls.
                return ToolResult(tool_name="unknown", tool_args=tool_args, error="Missing 'tool_name' in tool_call args.", status_code=400)

            print(f"    - Calling tool manager to execute: {tool_name} with args: {tool_args}")
            # Delegate execution to the tool manager
            result: ToolResult = await self.tool_manager.execute_tool(tool_name, tool_args)

            if result.error:
                print(f"    - Tool execution failed (reported by manager): {result.error}")
            else:
                print(f"    - Tool execution successful (reported by manager). Output: {result.output}")
            return result # Return the result directly from the manager

        elif action == "complete":
            # No specific execution, just return message from args
            return args.get("message", "Completion step executed.")
        elif action == "log":
             # Simple logging action
             log_message = args.get("message", "Log step executed.")
             print(f"    - Log: {log_message}")
             return f"Log action executed: {log_message}"
        else:
            # Handle unknown actions by returning an error message
            unknown_action_msg = f"Unknown action type: '{action}'."
            print(f"    - {unknown_action_msg}")
            return unknown_action_msg # Return the error message as the outcome
