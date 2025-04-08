# agentkit/tests/memory/test_short_term.py
import pytest

from agentkit.memory.short_term import ShortTermMemory


def test_short_term_memory_initialization():
    """Tests that ShortTermMemory initializes with an empty history."""
    memory = ShortTermMemory()
    assert memory.get_history() == []


def test_short_term_memory_add_entry():
    """Tests adding single and multiple entries."""
    memory = ShortTermMemory()
    entry1 = {"type": "user", "content": "Hello"}
    memory.add_entry(entry1)
    assert memory.get_history() == [entry1]

    entry2 = {"type": "agent", "content": "Hi there!"}
    memory.add_entry(entry2)
    assert memory.get_history() == [entry1, entry2]


def test_short_term_memory_get_history_returns_copy():
    """Tests that get_history returns a copy, not the internal list."""
    memory = ShortTermMemory()
    entry1 = {"type": "user", "content": "Hello"}
    memory.add_entry(entry1)

    history_copy = memory.get_history()
    assert history_copy == [entry1]

    # Modify the returned copy
    history_copy.append({"type": "system", "content": "Modified"})

    # Ensure the internal history remains unchanged
    assert memory.get_history() == [entry1]


def test_short_term_memory_clear():
    """Tests clearing the memory."""
    memory = ShortTermMemory()
    memory.add_entry({"type": "user", "content": "Hello"})
    memory.add_entry({"type": "agent", "content": "Hi there!"})
    assert len(memory.get_history()) == 2

    memory.clear()
    assert memory.get_history() == []

    # Test clearing already empty memory
    memory.clear()
    assert memory.get_history() == []


def test_short_term_memory_add_complex_entry():
    """Tests adding entries with nested structures."""
    memory = ShortTermMemory()
    complex_entry = {
        "type": "tool_result",
        "tool_name": "calculator",
        "result": {"value": 10, "error": None},
    }
    memory.add_entry(complex_entry)
    assert memory.get_history() == [complex_entry]
