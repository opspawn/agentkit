from typing import Dict, Optional, Type, Union
from pydantic import HttpUrl, ValidationError # For URL validation
from agentkit.tools.interface import ToolInterface
from agentkit.core.models import ToolDefinition # Using this for structure consistency

# In-memory storage for available tools
_tool_registry: Dict[str, Type[ToolInterface]] = {} # For local Python classes
_external_tool_endpoints: Dict[str, str] = {}      # For external HTTP endpoints
_tool_definitions: Dict[str, ToolDefinition] = {} # Common storage for definitions

class ToolRegistry:
    """Manages the registration and retrieval of available local and external tools."""

    def register_tool(self, tool_class: Type[ToolInterface]) -> None:
        """
        Registers a tool class.

        Retrieves the tool definition using get_definition() and stores both
        the class and its definition.

        Args:
            tool_class: The class implementing ToolInterface to register.

        Raises:
            ValueError: If a tool with the same name is already registered
                        or if the class doesn't implement ToolInterface correctly.
            TypeError: If the provided item is not a class or not a subclass
                       of ToolInterface.
        """
        if not isinstance(tool_class, type):
             raise TypeError(f"Expected a class, but got {type(tool_class)}")
        if not issubclass(tool_class, ToolInterface):
            raise TypeError(f"Tool class {tool_class.__name__} must inherit from ToolInterface.")

        try:
            definition_dict = tool_class.get_definition()
            # Basic validation of definition structure
            if not all(k in definition_dict for k in ["name", "description", "parameters"]):
                 raise ValueError("Tool definition must include 'name', 'description', and 'parameters'.")

            tool_name = definition_dict["name"]
            if not isinstance(tool_name, str) or not tool_name:
                raise ValueError("Tool definition 'name' must be a non-empty string.")

            if tool_name in _tool_registry or tool_name in _external_tool_endpoints:
                raise ValueError(f"Tool name '{tool_name}' conflicts with an existing registration.")

            # Create a ToolDefinition model instance for structured storage
            tool_def_model = ToolDefinition(
                name=tool_name,
                description=definition_dict.get("description"),
                interface_details=definition_dict # Store the whole definition here for now
            )

            _tool_registry[tool_name] = tool_class
            _tool_definitions[tool_name] = tool_def_model
            print(f"Local tool class registered: {tool_name}") # Basic logging

        # Removed specific AbstractMethodError catch block;
        # issubclass check and Python's TypeError on instantiation handle this.
        except Exception as e:
            # Catch potential errors during get_definition() or validation
            raise ValueError(f"Failed to register tool {tool_class.__name__}: {e}")


    def register_external_tool(self, name: str, description: str, parameters: dict, endpoint_url: str) -> None:
        """
        Registers an external tool accessible via an HTTP endpoint.

        Args:
            name: The unique name for the tool.
            description: A description of what the tool does.
            parameters: A dictionary describing the expected parameters (e.g., JSON schema).
            endpoint_url: The URL where the external tool can be invoked.

        Raises:
            ValueError: If the name conflicts with an existing registration or if the URL is invalid.
            TypeError: If input types are incorrect.
        """
        if not isinstance(name, str) or not name:
            raise TypeError("Tool name must be a non-empty string.")
        if not isinstance(description, str): # Allow empty description
             description = ""
        if not isinstance(parameters, dict):
            raise TypeError("Tool parameters must be a dictionary.")
        if not isinstance(endpoint_url, str):
             raise TypeError("Tool endpoint_url must be a string.")

        # Validate URL
        try:
            HttpUrl(endpoint_url) # Use Pydantic for validation
        except ValidationError as e:
            raise ValueError(f"Invalid endpoint URL '{endpoint_url}': {e}") from e

        if name in _tool_registry or name in _external_tool_endpoints:
            raise ValueError(f"Tool name '{name}' conflicts with an existing registration.")

        # Create definition dictionary and model
        definition_dict = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "type": "external", # Add type indicator
            "endpoint": endpoint_url
        }
        tool_def_model = ToolDefinition(
            name=name,
            description=description,
            interface_details=definition_dict
        )

        _external_tool_endpoints[name] = endpoint_url
        _tool_definitions[name] = tool_def_model
        print(f"External tool registered: {name} at {endpoint_url}") # Basic logging


    def get_tool_class(self, tool_name: str) -> Optional[Type[ToolInterface]]:
        """
        Retrieves the class for a registered tool by name.

        Args:
            tool_name: The name of the tool.

        Returns:
            The tool class if found, otherwise None.
        """
        """Retrieves the class ONLY for a locally registered tool."""
        return _tool_registry.get(tool_name)

    def get_tool_endpoint(self, tool_name: str) -> Optional[str]:
        """Retrieves the endpoint URL for an externally registered tool."""
        return _external_tool_endpoints.get(tool_name)

    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Retrieves the definition for a registered tool by name.

        Args:
            tool_name: The name of the tool.

        Returns:
            The ToolDefinition object if found, otherwise None.
        """
        return _tool_definitions.get(tool_name)

    def list_tool_definitions(self) -> list[ToolDefinition]:
        """Returns a list of definitions for all registered tools."""
        return list(_tool_definitions.values())

    def clear_all(self) -> None:
        """Clears the registry (useful for testing)."""
        _tool_registry.clear()
        _external_tool_endpoints.clear()
        _tool_definitions.clear()

# Singleton instance
tool_registry = ToolRegistry()

# Example: How a tool might be registered at startup
# from some_module import MyToolClass
# tool_registry.register_tool(MyToolClass)