import pytest
from agentkit.registration.storage import agent_storage, AgentStorage
from agentkit.core.models import AgentInfo, AgentMetadata

# Fixture to ensure clean storage for each test
@pytest.fixture(autouse=True)
def clear_storage_before_each_test():
    agent_storage.clear_all()
    yield # Test runs here
    agent_storage.clear_all()

# Sample data for testing
def create_sample_agent_info(name="TestAgent", version="1.0", endpoint="http://test.com"):
    return AgentInfo(
        agentName=name,
        capabilities=["test"],
        version=version,
        contactEndpoint=endpoint,
        metadata=AgentMetadata(description="A test agent")
    )

def test_add_agent_success():
    """Test successfully adding a new agent."""
    agent_info = create_sample_agent_info()
    agent_storage.add_agent(agent_info)
    assert agent_storage.get_agent(agent_info.agentId) == agent_info
    assert agent_storage.get_agent_by_name(agent_info.agentName) == agent_info
    assert len(agent_storage.list_agents()) == 1

def test_add_agent_duplicate_id():
    """Test adding an agent with an existing agentId raises ValueError."""
    agent_info1 = create_sample_agent_info(name="Agent1")
    agent_storage.add_agent(agent_info1)

    agent_info2 = create_sample_agent_info(name="Agent2")
    # Manually set the ID to collide
    agent_info2.agentId = agent_info1.agentId

    with pytest.raises(ValueError, match=f"Agent with ID {agent_info1.agentId} already registered."):
        agent_storage.add_agent(agent_info2)
    assert len(agent_storage.list_agents()) == 1 # Ensure second agent wasn't added

def test_add_agent_duplicate_name():
    """Test adding an agent with an existing agentName raises ValueError."""
    agent_info1 = create_sample_agent_info(name="DuplicateNameAgent")
    agent_storage.add_agent(agent_info1)

    agent_info2 = create_sample_agent_info(name="DuplicateNameAgent") # Same name, different ID

    with pytest.raises(ValueError, match=f"Agent with name '{agent_info1.agentName}' already registered."):
        agent_storage.add_agent(agent_info2)
    assert len(agent_storage.list_agents()) == 1 # Ensure second agent wasn't added

def test_get_agent_found():
    """Test retrieving an existing agent by ID."""
    agent_info = create_sample_agent_info()
    agent_storage.add_agent(agent_info)
    retrieved_agent = agent_storage.get_agent(agent_info.agentId)
    assert retrieved_agent == agent_info

def test_get_agent_not_found():
    """Test retrieving a non-existent agent by ID returns None."""
    retrieved_agent = agent_storage.get_agent("non-existent-id")
    assert retrieved_agent is None

def test_get_agent_by_name_found():
    """Test retrieving an existing agent by name."""
    agent_info = create_sample_agent_info(name="NamedAgent")
    agent_storage.add_agent(agent_info)
    retrieved_agent = agent_storage.get_agent_by_name("NamedAgent")
    assert retrieved_agent == agent_info

def test_get_agent_by_name_not_found():
    """Test retrieving a non-existent agent by name returns None."""
    retrieved_agent = agent_storage.get_agent_by_name("NonExistentName")
    assert retrieved_agent is None

def test_list_agents_empty():
    """Test listing agents when the registry is empty."""
    assert agent_storage.list_agents() == []

def test_list_agents_multiple():
    """Test listing agents when multiple are registered."""
    agent1 = create_sample_agent_info(name="Agent1")
    agent2 = create_sample_agent_info(name="Agent2")
    agent_storage.add_agent(agent1)
    agent_storage.add_agent(agent2)
    agent_list = agent_storage.list_agents()
    assert len(agent_list) == 2
    # Order isn't guaranteed in dicts pre-3.7, so check presence
    assert agent1 in agent_list
    assert agent2 in agent_list

def test_clear_all():
    """Test clearing the agent registry."""
    agent_storage.add_agent(create_sample_agent_info())
    assert len(agent_storage.list_agents()) == 1
    agent_storage.clear_all()
    assert len(agent_storage.list_agents()) == 0
    assert agent_storage.get_agent_by_name("TestAgent") is None