"""OpenAI Chat Completions client."""

from __future__ import annotations

from openai import OpenAI

from llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """LLM adapter for OpenAI models."""

    provider = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate a response using the Chat Completions API."""
        request = {
            "model": self.model,
            "messages": messages,
        }
        temperature = kwargs.get("temperature")
        if temperature is not None and not self._uses_default_temperature_only():
            request["temperature"] = temperature

        response = self.client.chat.completions.create(**request)
        return response.choices[0].message.content or ""

    def _uses_default_temperature_only(self) -> bool:
        """Return whether this model rejects custom temperature values."""
        normalized_model = self.model.lower()
        return normalized_model.startswith(("gpt-5", "o1", "o3", "o4"))
