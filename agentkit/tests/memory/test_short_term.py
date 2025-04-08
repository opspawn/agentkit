# agentkit/agentkit/tests/memory/test_short_term.py
import pytest
from agentkit.memory.short_term import ShortTermMemory

# --- Test Cases ---

@pytest.mark.asyncio
async def test_short_term_memory_initialization():
    """Tests that ShortTermMemory initializes with an empty message list."""
    memory = ShortTermMemory()
    context = await memory.get_context()
    assert context == []

@pytest.mark.asyncio
async def test_short_term_memory_add_message():
    """Tests adding single and multiple messages."""
    memory = ShortTermMemory()
    role1, content1 = "user", "Hello"
    await memory.add_message(role=role1, content=content1)
    context1 = await memory.get_context()
    assert context1 == [{"role": role1, "content": content1}]

    role2, content2 = "agent", "Hi there!"
    await memory.add_message(role=role2, content=content2)
    context2 = await memory.get_context()
    assert context2 == [
        {"role": role1, "content": content1},
        {"role": role2, "content": content2},
    ]

@pytest.mark.asyncio
async def test_short_term_memory_get_context_returns_copy():
    """Tests that get_context returns a copy, not the internal list."""
    memory = ShortTermMemory()
    role1, content1 = "user", "Hello"
    await memory.add_message(role=role1, content=content1)

    context_copy = await memory.get_context()
    assert context_copy == [{"role": role1, "content": content1}]

    # Modify the returned copy
    context_copy.append({"role": "system", "content": "Modified"})

    # Ensure the internal messages list remains unchanged
    original_context = await memory.get_context()
    assert original_context == [{"role": role1, "content": content1}]

@pytest.mark.asyncio
async def test_short_term_memory_clear():
    """Tests clearing the memory."""
    memory = ShortTermMemory()
    await memory.add_message(role="user", content="Hello")
    await memory.add_message(role="agent", content="Hi there!")
    context1 = await memory.get_context()
    assert len(context1) == 2

    await memory.clear()
    context2 = await memory.get_context()
    assert context2 == []

    # Test clearing already empty memory
    await memory.clear()
    context3 = await memory.get_context()
    assert context3 == []

@pytest.mark.asyncio
async def test_short_term_memory_max_size():
    """Tests the max_size functionality."""
    memory = ShortTermMemory(max_size=2)
    msg1 = {"role": "user", "content": "Msg 1"}
    msg2 = {"role": "agent", "content": "Msg 2"}
    msg3 = {"role": "user", "content": "Msg 3"}

    await memory.add_message(role=msg1["role"], content=msg1["content"])
    await memory.add_message(role=msg2["role"], content=msg2["content"])
    context1 = await memory.get_context()
    assert context1 == [msg1, msg2]

    # This should push out msg1
    await memory.add_message(role=msg3["role"], content=msg3["content"])
    context2 = await memory.get_context()
    assert context2 == [msg2, msg3] # Only the last two messages remain

@pytest.mark.asyncio
async def test_short_term_memory_add_message_with_metadata():
    """Tests adding messages with metadata."""
    memory = ShortTermMemory()
    role = "tool"
    content = "Tool output"
    metadata = {"tool_name": "calculator", "status": "success"}

    await memory.add_message(role=role, content=content, metadata=metadata)
    context = await memory.get_context()
    expected_message = {"role": role, "content": content, **metadata} # Metadata merged
    assert context == [expected_message]
