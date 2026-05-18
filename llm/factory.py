"""Factory for LLM adapters."""

from __future__ import annotations

from config import Config
from llm.base import BaseLLMClient


def create_llm_client(provider: str, config: Config) -> BaseLLMClient:
    """Create an LLM client for a configured provider."""
    selected = provider.lower()
    if selected == "openai":
        from llm.openai_client import OpenAIClient

        return OpenAIClient(api_key=config.openai_api_key, model=config.openai_model)
    if selected == "anthropic":
        from llm.anthropic_client import AnthropicClient

        return AnthropicClient(api_key=config.anthropic_api_key, model=config.anthropic_model)
    if selected == "gemini":
        from llm.gemini_client import GeminiClient

        return GeminiClient(api_key=config.gemini_api_key, model=config.gemini_model)
    if selected == "vllm":
        from llm.vllm_client import VLLMClient

        return VLLMClient(base_url=config.vllm_base_url, api_key=config.vllm_api_key, model=config.vllm_model)
    raise ValueError(f"Unsupported LLM provider: {provider}")
