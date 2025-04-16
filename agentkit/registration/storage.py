from typing import Dict, Optional
from agentkit.core.models import AgentInfo

# Simple in-memory storage for registered agents
# In a real application, this might be replaced by Redis, a database, etc.
_agent_registry: Dict[str, AgentInfo] = {}

class AgentStorage:
    """Manages the storage and retrieval of registered agent information."""

    def add_agent(self, agent_info: AgentInfo) -> None:
        """
        Adds a new agent to the registry.

        Args:
            agent_info: The AgentInfo object to store.

        Raises:
            ValueError: If an agent with the same agentId or agentName already exists.
        """
        if agent_info.agentId in _agent_registry:
            raise ValueError(f"Agent with ID {agent_info.agentId} already registered.")
        # Check for name collision as well, depending on requirements
        if self.get_agent_by_name(agent_info.agentName):
             raise ValueError(f"Agent with name '{agent_info.agentName}' already registered.")

        _agent_registry[agent_info.agentId] = agent_info
        print(f"Agent registered: {agent_info.agentName} (ID: {agent_info.agentId})") # Basic logging

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """
        Retrieves agent information by agent ID.

        Args:
            agent_id: The unique ID of the agent.

        Returns:
            The AgentInfo object if found, otherwise None.
        """
        return _agent_registry.get(agent_id)

    def get_agent_by_name(self, agent_name: str) -> Optional[AgentInfo]:
        """
        Retrieves agent information by agent name.

        Args:
            agent_name: The name of the agent.

        Returns:
            The AgentInfo object if found, otherwise None.
        """
        for agent in _agent_registry.values():
            if agent.agentName == agent_name:
                return agent
        return None

    def list_agents(self) -> list[AgentInfo]:
        """Returns a list of all registered agents."""
        return list(_agent_registry.values())

    def clear_all(self) -> None:
        """Clears the registry (useful for testing)."""
        _agent_registry.clear()

# Singleton instance
agent_storage = AgentStorage()