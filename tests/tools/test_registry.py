import pytest
from typing import Dict, Any, Optional, Type
from agentkit.tools.registry import tool_registry, ToolRegistry
from agentkit.tools.interface import ToolInterface
from agentkit.core.models import ToolDefinition

# --- Dummy Tool for Testing ---

class DummyTool(ToolInterface):
    """A simple tool for testing the registry."""
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        name = parameters.get("name", "World")
        return {"status": "success", "result": f"Hello, {name}!"}

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        return {
            "name": "dummy_hello",
            "description": "A simple hello world tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet", "default": "World"}
                },
                "required": []
            }
        }

class AnotherDummyTool(ToolInterface):
    """Another simple tool for testing."""
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "success", "result": "Another tool executed"}

    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        return {
            "name": "another_dummy",
            "description": "Another dummy tool.",
            "parameters": {"type": "object", "properties": {}}
        }

class InvalidToolMissingMethods(ToolInterface): # Missing abstract methods
     pass

class InvalidToolBadDefinition(ToolInterface):
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {}
    @classmethod
    def get_definition(cls) -> Dict[str, Any]:
        return {"name": "bad_def"} # Missing description and parameters

# --- Fixtures ---

@pytest.fixture(autouse=True)
def clear_registry_before_each_test():
    tool_registry.clear_all()
    yield
    tool_registry.clear_all()

# --- Test Cases ---

def test_register_tool_success():
    """Test successfully registering a valid tool class."""
    tool_registry.register_tool(DummyTool)
    assert tool_registry.get_tool_class("dummy_hello") == DummyTool
    definition = tool_registry.get_tool_definition("dummy_hello")
    assert definition is not None
    assert isinstance(definition, ToolDefinition)
    assert definition.name == "dummy_hello"
    assert definition.description == "A simple hello world tool."
    assert "parameters" in definition.interface_details # Check definition stored correctly
    assert len(tool_registry.list_tool_definitions()) == 1

def test_register_tool_duplicate_name():
    """Test registering a tool with a name that already exists."""
    tool_registry.register_tool(DummyTool)
    with pytest.raises(ValueError, match="Tool with name 'dummy_hello' already registered."):
        tool_registry.register_tool(DummyTool) # Try registering the same class again
    # Try registering a different class with the same name
    class DummyToolClone(DummyTool): pass
    with pytest.raises(ValueError, match="Tool with name 'dummy_hello' already registered."):
         tool_registry.register_tool(DummyToolClone)
    assert len(tool_registry.list_tool_definitions()) == 1

def test_register_tool_not_a_class():
    """Test registering something that is not a class."""
    instance = DummyTool()
    with pytest.raises(TypeError, match="Expected a class, but got"):
        tool_registry.register_tool(instance) # type: ignore

def test_register_tool_not_subclass():
    """Test registering a class that doesn't inherit from ToolInterface."""
    class NotATool: pass
    with pytest.raises(TypeError, match="must inherit from ToolInterface"):
        tool_registry.register_tool(NotATool) # type: ignore

def test_register_tool_missing_methods():
    """Test registering a class missing abstract methods (results in definition error)."""
    # The attempt to call get_definition() on a class missing the abstract method
    # will likely fail first when the registry tries to validate the definition.
    with pytest.raises(ValueError, match="Failed to register tool InvalidToolMissingMethods"):
        tool_registry.register_tool(InvalidToolMissingMethods)


def test_register_tool_bad_definition():
    """Test registering a tool with an incomplete definition."""
    with pytest.raises(ValueError, match="Tool definition must include 'name', 'description', and 'parameters'."):
        tool_registry.register_tool(InvalidToolBadDefinition)

def test_get_tool_class_found():
    """Test retrieving an existing tool class."""
    tool_registry.register_tool(DummyTool)
    assert tool_registry.get_tool_class("dummy_hello") == DummyTool

def test_get_tool_class_not_found():
    """Test retrieving a non-existent tool class."""
    assert tool_registry.get_tool_class("non_existent_tool") is None

def test_get_tool_definition_found():
    """Test retrieving an existing tool definition."""
    tool_registry.register_tool(DummyTool)
    definition = tool_registry.get_tool_definition("dummy_hello")
    assert definition is not None
    assert definition.name == "dummy_hello"

def test_get_tool_definition_not_found():
    """Test retrieving a non-existent tool definition."""
    assert tool_registry.get_tool_definition("non_existent_tool") is None

def test_list_tool_definitions_empty():
    """Test listing definitions when the registry is empty."""
    assert tool_registry.list_tool_definitions() == []

def test_list_tool_definitions_multiple():
    """Test listing definitions when multiple tools are registered."""
    tool_registry.register_tool(DummyTool)
    tool_registry.register_tool(AnotherDummyTool)
    definitions = tool_registry.list_tool_definitions()
    assert len(definitions) == 2
    names = {d.name for d in definitions}
    assert "dummy_hello" in names
    assert "another_dummy" in names

def test_clear_all():
    """Test clearing the tool registry."""
    tool_registry.register_tool(DummyTool)
    assert len(tool_registry.list_tool_definitions()) == 1
    tool_registry.clear_all()
    assert len(tool_registry.list_tool_definitions()) == 0
    assert tool_registry.get_tool_class("dummy_hello") is None
    assert tool_registry.get_tool_definition("dummy_hello") is None