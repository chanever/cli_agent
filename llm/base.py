"""Base LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Abstract generation interface used by the agent runner."""

    provider: str
    model: str

    @abstractmethod
    def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate a text response from chat-style messages."""
        raise NotImplementedError
