"""Anthropic Messages API client."""

from __future__ import annotations

import anthropic

from llm.base import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    """LLM adapter for Anthropic Claude models."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate a response using Anthropic messages."""
        request = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": messages,
        }
        temperature = kwargs.get("temperature")
        if temperature is not None:
            request["temperature"] = temperature

        response = self.client.messages.create(**request)
        parts: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "\n".join(parts)
