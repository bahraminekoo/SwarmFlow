"""Configuration management for SwarmFlow."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    provider: LLMProvider = LLMProvider.OPENROUTER
    model: str = "qwen/qwen3-8b"
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096


class DatabaseConfig(BaseModel):
    path: str = "./data/swarmflow.db"


class DashboardConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080


class SwarmFlowConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    templates_dir: str = ""

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> SwarmFlowConfig:
        """Load config from YAML file, then overlay environment variables."""
        data: dict[str, Any] = {}

        # Auto-load .env file if present
        load_dotenv()

        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

        config = cls(**data)

        # Environment variable overrides
        if api_key := os.getenv("OPENROUTER_API_KEY"):
            config.llm.api_key = api_key
        if model := os.getenv("SWARMFLOW_MODEL"):
            config.llm.model = model
        if ollama_url := os.getenv("OLLAMA_BASE_URL"):
            config.llm.base_url = ollama_url
            config.llm.provider = LLMProvider.OLLAMA

        # Resolve templates directory
        if not config.templates_dir:
            config.templates_dir = str(Path(__file__).parent / "templates")

        return config


# Global config singleton
_config: SwarmFlowConfig | None = None


def get_config(config_path: str | Path | None = None) -> SwarmFlowConfig:
    """Get or create the global config."""
    global _config
    if _config is None:
        _config = SwarmFlowConfig.load(config_path)
    return _config


def reset_config() -> None:
    """Reset the global config (useful for testing)."""
    global _config
    _config = None
