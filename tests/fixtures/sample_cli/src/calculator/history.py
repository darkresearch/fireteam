"""Command history tracking.

NOTE: This module uses global state and needs refactoring to use a class.
"""

# Global state - this is the "bad" pattern we want the agent to refactor
_history: list[str] = []


def add_entry(operation: str, a: float, b: float, result: float) -> None:
    """Add an entry to the history."""
    entry = f"{operation}({a}, {b}) = {result}"
    _history.append(entry)


def get_history() -> list[str]:
    """Get all history entries."""
    return _history.copy()


def clear_history() -> None:
    """Clear all history entries."""
    global _history
    _history = []


def get_last_entry() -> str | None:
    """Get the most recent history entry."""
    if _history:
        return _history[-1]
    return None
