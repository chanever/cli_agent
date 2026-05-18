"""OpenAI-compatible vLLM client."""

from __future__ import annotations

from openai import OpenAI

from llm.base import BaseLLMClient


class VLLMClient(BaseLLMClient):
    """LLM adapter for vLLM OpenAI-compatible endpoints."""

    provider = "vllm"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate a response from a vLLM OpenAI-compatible server."""
        request = {
            "model": self.model,
            "messages": messages,
        }
        temperature = kwargs.get("temperature")
        if temperature is not None:
            request["temperature"] = temperature

        response = self.client.chat.completions.create(**request)
        return response.choices[0].message.content or ""
