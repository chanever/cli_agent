"""Passthrough safeguard used by the vulnerable baseline."""

from __future__ import annotations

from safeguard.base import BaseSafeguard


class PassThroughSafeguard(BaseSafeguard):
    """Allows every action unchanged."""

    def inspect(self, action: dict, context: dict) -> dict:
        """Return an allow decision with the original action."""
        return {
            "decision": "allow",
            "action": action,
            "reason": "baseline passthrough",
        }
