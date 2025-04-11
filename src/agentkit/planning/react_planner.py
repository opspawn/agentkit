from typing import List, Dict, Any, Optional

from agentkit.core.interfaces.llm_client import BaseLlmClient, LlmResponse
from agentkit.core.interfaces.planner import BasePlanner, Plan, PlanStep
from agentkit.tools.schemas import ToolSpec # Needed for tool descriptions in prompt

# Basic ReAct Prompt Structure (can be refined)
REACT_PROMPT_TEMPLATE = """
You are a helpful assistant designed to achieve goals by thinking step-by-step and using available tools.

Goal: {goal}

Available Tools:
{tool_descriptions}

Thought Process (ReAct Format):
Thought: [Your reasoning about the current state and next action]
Action: [The action to take, either 'Final Answer: [your final answer]' or 'Tool Name: [tool_name] Input: [input_json]']
Observation: [Result of the action, or initial state]
... (Repeat Thought/Action/Observation)

Current History:
{history}

Begin!

Thought:
"""

class ReActPlanner(BasePlanner):
    """
    A planner that implements the ReAct (Reasoning + Acting) prompting strategy.
    """
    def __init__(self, llm_client: BaseLlmClient):
        """
        Initializes the ReActPlanner.

        Args:
            llm_client: An instance of BaseLlmClient to interact with the LLM.
        """
        if not isinstance(llm_client, BaseLlmClient):
            raise TypeError("llm_client must be an instance of BaseLlmClient")
        self.llm_client = llm_client

    async def plan(
        self,
        goal: str,
        available_tools: List[ToolSpec],
        history: Optional[List[Dict[str, Any]]] = None,
        max_steps: int = 10,
        **kwargs: Any
    ) -> Plan:
        """
        Generates a plan using the ReAct strategy.

        In ReAct, the "plan" is generated step-by-step within the execution loop.
        This method might initiate the first step or could be adapted depending
        on how the Agent orchestrates the ReAct loop.

        For now, this method will generate the *next* step based on the history.

        Args:
            goal: The overall objective.
            available_tools: A list of tools the agent can use.
            history: The history of previous Thought/Action/Observation steps.
            max_steps: Maximum planning steps (not directly used in single-step generation).
            **kwargs: Additional arguments for the LLM call.

        Returns:
            A Plan object containing the next proposed step (Action).
        """
        history = history or []

        # Format tool descriptions
        tool_descs = "\n".join([f"- {t.name}: {t.description} (Input Schema: {t.input_schema})" for t in available_tools])

        # Format history
        history_str = "\n".join([f"{step_type}: {step_content}" for item in history for step_type, step_content in item.items()])

        # Construct the prompt
        prompt = REACT_PROMPT_TEMPLATE.format(
            goal=goal,
            tool_descriptions=tool_descs,
            history=history_str
        )

        # Generate the next thought/action using the LLM
        llm_response: LlmResponse = await self.llm_client.generate(
            prompt=prompt,
            stop_sequences=["\nObservation:"], # Stop before the next observation
            **kwargs
        )

        if llm_response.error:
            # Handle LLM error - maybe return an error step?
            return Plan(steps=[PlanStep(action_type="error", details={"message": llm_response.error})])

        # Parse the LLM response to extract the next Action
        # This requires robust parsing logic based on the expected ReAct format.
        # TODO: Implement robust parsing logic for Thought/Action
        parsed_action = self._parse_react_response(llm_response.content)

        if not parsed_action:
             # Handle parsing failure
             return Plan(steps=[PlanStep(action_type="error", details={"message": "Failed to parse LLM response for action."})])

        # Create a PlanStep based on the parsed action
        # The 'thought' is implicitly part of the LLM generation but not stored separately here yet.
        if parsed_action.get("action_type") == "final_answer":
            step = PlanStep(action_type="final_answer", details={"answer": parsed_action.get("answer", "")})
        elif parsed_action.get("action_type") == "tool_call":
            step = PlanStep(
                action_type="tool_call",
                details={
                    "tool_name": parsed_action.get("tool_name", ""),
                    "tool_input": parsed_action.get("tool_input", {})
                }
            )
        else:
             # Handle unknown action type
             step = PlanStep(action_type="error", details={"message": f"Unknown action type parsed: {parsed_action}"})


        return Plan(steps=[step]) # Return a plan with just the next step

    def _parse_react_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parses the LLM's response text to extract the Action.

        Expected format:
        Thought: ...
        Action: Final Answer: ...
        OR
        Action: Tool Name: tool_name Input: {...}

        Args:
            response_text: The raw text generated by the LLM.

        Returns:
            A dictionary representing the parsed action, or None if parsing fails.
        """
        # TODO: Implement robust parsing logic. This is a simplified example.
        action_line = None
        lines = response_text.strip().split('\n')
        for line in lines:
            if line.startswith("Action:"):
                action_line = line.strip()
                break

        if not action_line:
            return None

        action_content = action_line[len("Action:"):].strip()

        if action_content.startswith("Final Answer:"):
            answer = action_content[len("Final Answer:"):].strip()
            return {"action_type": "final_answer", "answer": answer}
        elif ":" in action_content and "Input:" in action_content:
             # Attempt to parse Tool Name: ... Input: ...
             try:
                 tool_part, input_part = action_content.split(" Input:", 1)
                 tool_name = tool_part.split(":", 1)[1].strip()
                 # Basic JSON parsing attempt - might need more robust handling
                 import json
                 tool_input_str = input_part.strip()
                 # Try to handle potential markdown code blocks
                 if tool_input_str.startswith("```json"):
                     tool_input_str = tool_input_str[len("```json"):].strip()
                 if tool_input_str.endswith("```"):
                     tool_input_str = tool_input_str[:-len("```")].strip()

                 tool_input = json.loads(tool_input_str)
                 return {"action_type": "tool_call", "tool_name": tool_name, "tool_input": tool_input}
             except Exception:
                 # Parsing failed
                 return None # Or return an error structure
        else:
            # Unrecognized action format
            return None
