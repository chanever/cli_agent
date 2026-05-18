"""Safeguard interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSafeguard(ABC):
    """Interface for inspecting or changing actions before execution."""

    @abstractmethod
    def inspect(self, action: dict, context: dict) -> dict:
        """Return an allow, block, or modify decision."""
        raise NotImplementedError
