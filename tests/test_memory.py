# agentkit/tests/test_memory.py
"""Unit tests for the ShortTermMemory class."""

import pytest
from typing import Dict, Any
from agentkit.memory.short_term import ShortTermMemory



@pytest.mark.asyncio
async def test_memory_initialization():
    """Test basic initialization."""
    memory = ShortTermMemory(max_size=5)
    assert memory.max_size == 5
    messages = await memory.get_context()
    assert messages == []
    # len() is not directly applicable anymore, check message list length
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_add_message():
    """Test adding messages within the max_size limit."""
    memory = ShortTermMemory(max_size=3)
    role1, content1 = "user", "Hello"
    role2, content2 = "assistant", "Hi there!"
    expected_msg1: Dict[str, Any] = {"role": role1, "content": content1}
    expected_msg2: Dict[str, Any] = {"role": role2, "content": content2}

    await memory.add_message(role=role1, content=content1)
    messages = await memory.get_context()
    assert len(messages) == 1
    assert messages == [expected_msg1]

    await memory.add_message(role=role2, content=content2)
    messages = await memory.get_context()
    assert len(messages) == 2
    assert messages == [expected_msg1, expected_msg2]


@pytest.mark.asyncio
async def test_add_message_with_metadata():
    """Test adding messages with metadata."""
    memory = ShortTermMemory(max_size=3)
    role1, content1 = "tool", "Result is 5"
    metadata1 = {"tool_name": "calculator", "tool_args": {"op": "add"}}
    expected_msg1: Dict[str, Any] = {"role": role1, "content": content1, **metadata1}

    await memory.add_message(role=role1, content=content1, metadata=metadata1)
    messages = await memory.get_context()
    assert len(messages) == 1
    assert messages == [expected_msg1]


@pytest.mark.asyncio
async def test_add_message_exceed_limit():
    """Test adding messages that exceed the max_size limit."""
    memory = ShortTermMemory(max_size=2)
    role1, content1 = "user", "First"
    role2, content2 = "assistant", "Second"
    role3, content3 = "user", "Third"
    expected_msg1: Dict[str, Any] = {"role": role1, "content": content1}
    expected_msg2: Dict[str, Any] = {"role": role2, "content": content2}
    expected_msg3: Dict[str, Any] = {"role": role3, "content": content3}

    await memory.add_message(role=role1, content=content1)
    await memory.add_message(role=role2, content=content2)
    messages = await memory.get_context()
    assert len(messages) == 2
    assert messages == [expected_msg1, expected_msg2]

    # Adding the third message should remove the first one
    await memory.add_message(role=role3, content=content3)
    messages = await memory.get_context()
    assert len(messages) == 2
    assert messages == [expected_msg2, expected_msg3]  # msg1 should be gone


@pytest.mark.asyncio
async def test_clear_memory():
    """Test clearing the memory."""
    memory = ShortTermMemory(max_size=3)
    role1, content1 = "user", "Test"
    await memory.add_message(role=role1, content=content1)
    messages_before = await memory.get_context()
    assert len(messages_before) == 1

    await memory.clear()
    messages_after = await memory.get_context()
    assert len(messages_after) == 0
    assert messages_after == []


@pytest.mark.asyncio
async def test_get_context_returns_copy():
    """Test that get_context returns a copy, not the original list."""
    memory = ShortTermMemory(max_size=3)
    role1, content1 = "user", "Original"
    expected_msg1: Dict[str, Any] = {"role": role1, "content": content1}
    await memory.add_message(role=role1, content=content1)

    retrieved_messages = await memory.get_context()
    assert retrieved_messages == [expected_msg1]

    # Modify the retrieved list
    retrieved_messages.append({"role": "system", "content": "Modified"})

    # Check that the original memory is unchanged
    original_messages = await memory.get_context()
    assert len(original_messages) == 1
    assert original_messages == [expected_msg1]


@pytest.mark.asyncio
async def test_memory_max_size_zero():
    """Test initialization and adding messages with max_size=0."""
    memory = ShortTermMemory(max_size=0)
    assert memory.max_size == 0

    await memory.add_message(role="user", content="Message 1")
    messages = await memory.get_context()
    assert len(messages) == 0 # No messages should be stored

    await memory.add_message(role="assistant", content="Message 2")
    messages = await memory.get_context()
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_memory_max_size_none():
    """Test initialization and adding messages with max_size=None (unlimited)."""
    memory = ShortTermMemory(max_size=None)
    assert memory.max_size is None

    # Add a few messages
    await memory.add_message(role="user", content="Message 1")
    await memory.add_message(role="assistant", content="Message 2")
    await memory.add_message(role="user", content="Message 3")

    messages = await memory.get_context()
    assert len(messages) == 3 # All messages should be stored

    # Add more messages
    for i in range(4, 10):
        await memory.add_message(role="user", content=f"Message {i}")

    messages = await memory.get_context()
    assert len(messages) == 9 # All messages should still be there
