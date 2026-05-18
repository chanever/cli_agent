"""Short-term step memory for prompt context."""

from __future__ import annotations


class AgentMemory:
    """Stores compact history entries from previous steps."""

    def __init__(self, max_items: int, max_summary_chars: int = 1000) -> None:
        self.max_items = max_items
        self.max_summary_chars = max_summary_chars
        self._items: list[dict] = []

    def add(self, step: int, action: dict, result: dict | None) -> None:
        """Add one compact step record to memory."""
        result = result or {}
        self._items.append(
            {
                "step": step,
                "action": action.get("type"),
                "command": action.get("command"),
                "reason": action.get("reason"),
                "stdout_summary": self._tail(result.get("stdout", "")),
                "stderr_summary": self._tail(result.get("stderr", "")),
                "exit_code": result.get("exit_code"),
                "timed_out": result.get("timed_out"),
            }
        )

    def recent(self) -> list[dict]:
        """Return recent history items for prompts."""
        return self._items[-self.max_items :]

    def snapshot(self) -> list[dict]:
        """Return a full copy suitable for logging."""
        return list(self._items)

    def _tail(self, value: str) -> str:
        """Keep only the tail of a long output string."""
        if not isinstance(value, str):
            value = str(value)
        return value[-self.max_summary_chars:]
