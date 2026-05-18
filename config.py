"""Configuration loading for the vulnerable CLI agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _int_env(name: str, default: int) -> int:
    """Read an integer environment variable with a default."""
    value = os.getenv(name)
    return default if value is None or value == "" else int(value)


def _float_env(name: str, default: float) -> float:
    """Read a float environment variable with a default."""
    value = os.getenv(name)
    return default if value is None or value == "" else float(value)


def _optional_float_env(name: str) -> float | None:
    """Read an optional float environment variable."""
    value = os.getenv(name)
    return None if value is None or value == "" else float(value)


@dataclass
class Config:
    """Runtime settings sourced from environment variables and CLI overrides."""

    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    vllm_base_url: str = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
    vllm_api_key: str = os.getenv("VLLM_API_KEY", "dummy")
    vllm_model: str = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    workspace_dir: str = os.getenv("WORKSPACE_DIR", "./workspace")
    log_dir: str = os.getenv("LOG_DIR", "./logs")
    max_steps: int = _int_env("MAX_STEPS", 20)
    command_timeout: int = _int_env("COMMAND_TIMEOUT", 30)
    max_output_chars: int = _int_env("MAX_OUTPUT_CHARS", 6000)
    max_history_items: int = _int_env("MAX_HISTORY_ITEMS", 8)
    temperature: float | None = _optional_float_env("TEMPERATURE")
    log_prompt: bool = True

    def resolve_paths(self, base_dir: Path | None = None) -> "Config":
        """Resolve workspace and log paths relative to the project directory."""
        root = base_dir or Path(__file__).resolve().parent
        workspace = Path(self.workspace_dir)
        logs = Path(self.log_dir)
        if not workspace.is_absolute():
            workspace = root / workspace
        if not logs.is_absolute():
            logs = root / logs
        self.workspace_dir = str(workspace)
        self.log_dir = str(logs)
        return self

    def model_for_provider(self, provider: str | None = None) -> str:
        """Return the configured model name for a provider."""
        selected = (provider or self.llm_provider).lower()
        if selected == "openai":
            return self.openai_model
        if selected == "anthropic":
            return self.anthropic_model
        if selected == "gemini":
            return self.gemini_model
        if selected == "vllm":
            return self.vllm_model
        return ""
