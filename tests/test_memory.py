"""
Unit tests for the ShortTermMemory class.
"""

import pytest
from agentkit.memory.short_term import ShortTermMemory, Message


def test_memory_initialization():
    """Test basic initialization."""
    memory = ShortTermMemory(max_size=5)
    assert len(memory) == 0
    assert memory.max_size == 5
    assert memory.get_messages() == []


def test_add_message():
    """Test adding messages within the max_size limit."""
    memory = ShortTermMemory(max_size=3)
    msg1: Message = {"role": "user", "content": "Hello"}
    msg2: Message = {"role": "assistant", "content": "Hi there!"}

    memory.add_message(msg1)
    assert len(memory) == 1
    assert memory.get_messages() == [msg1]

    memory.add_message(msg2)
    assert len(memory) == 2
    assert memory.get_messages() == [msg1, msg2]


def test_add_message_exceed_limit():
    """Test adding messages that exceed the max_size limit."""
    memory = ShortTermMemory(max_size=2)
    msg1: Message = {"role": "user", "content": "First"}
    msg2: Message = {"role": "assistant", "content": "Second"}
    msg3: Message = {"role": "user", "content": "Third"}

    memory.add_message(msg1)
    memory.add_message(msg2)
    assert len(memory) == 2
    assert memory.get_messages() == [msg1, msg2]

    # Adding the third message should remove the first one
    memory.add_message(msg3)
    assert len(memory) == 2
    assert memory.get_messages() == [msg2, msg3]  # msg1 should be gone


def test_clear_memory():
    """Test clearing the memory."""
    memory = ShortTermMemory(max_size=3)
    msg1: Message = {"role": "user", "content": "Test"}
    memory.add_message(msg1)
    assert len(memory) == 1

    memory.clear()
    assert len(memory) == 0
    assert memory.get_messages() == []


def test_get_messages_returns_copy():
    """Test that get_messages returns a copy, not the original list."""
    memory = ShortTermMemory(max_size=3)
    msg1: Message = {"role": "user", "content": "Original"}
    memory.add_message(msg1)

    retrieved_messages = memory.get_messages()
    assert retrieved_messages == [msg1]

    # Modify the retrieved list
    retrieved_messages.append({"role": "system", "content": "Modified"})

    # Check that the original memory is unchanged
    assert len(memory) == 1
    assert memory.get_messages() == [msg1]
