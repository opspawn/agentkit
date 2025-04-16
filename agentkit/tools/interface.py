from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ToolInterface(ABC):
    """
    Abstract Base Class for all tool connectors.

    Defines the standard methods that any tool integrated with AgentKit
    must implement.
    """

    @abstractmethod
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the tool's primary function.

        Args:
            parameters: A dictionary containing the parameters required by the tool,
                        validated against the tool's definition.
            context: Optional dictionary containing contextual information that might
                     be relevant for the tool's execution (e.g., user info, session data).

        Returns:
            A dictionary containing the result of the tool's execution.
            The structure of this dictionary should be consistent for a given tool.
            It's recommended to include a 'status' field ('success' or 'error')
            and either a 'result' or 'error_message' field.
            Example success: {"status": "success", "result": ...}
            Example error: {"status": "error", "error_message": "..."}
        """
        pass

    @classmethod
    @abstractmethod
    def get_definition(cls) -> Dict[str, Any]:
        """
        Returns the tool's definition metadata.

        This metadata is used for registration and discovery, and potentially
        for validating input parameters before execution.

        Returns:
            A dictionary describing the tool, including its name, description,
            and parameter schema.
            Example:
            {
                "name": "weather_lookup",
                "description": "Looks up the current weather for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
                    },
                    "required": ["location"]
                }
            }
        """
        pass

# Example Usage (Not part of the interface, just for illustration):
#
# class WeatherTool(ToolInterface):
#     async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#         location = parameters.get("location")
#         unit = parameters.get("unit", "celsius")
#         # ... actual weather lookup logic ...
#         return {"status": "success", "result": {"temp": 25, "unit": unit, "condition": "sunny"}}
#
#     @classmethod
#     def get_definition(cls) -> Dict[str, Any]:
#         return {
#             "name": "weather_lookup",
#             "description": "Looks up the current weather for a given location.",
#             "parameters": { ... } # As above
#         }