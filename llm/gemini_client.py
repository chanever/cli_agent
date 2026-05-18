"""Google Gemini client."""

from __future__ import annotations

import google.generativeai as genai

from llm.base import BaseLLMClient


class GeminiClient(BaseLLMClient):
    """LLM adapter for Gemini models."""

    provider = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate a response using google-generativeai."""
        prompt = "\n\n".join(str(message.get("content", "")) for message in messages)
        temperature = kwargs.get("temperature")
        generation_config = {"temperature": temperature} if temperature is not None else None
        response = self.client.generate_content(prompt, generation_config=generation_config)
        return response.text or ""
