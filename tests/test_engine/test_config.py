"""Tests for SwarmFlow configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

from swarmflow.config import LLMProvider, SwarmFlowConfig, get_config, reset_config


class TestConfig:
    def test_default_config(self):
        config = SwarmFlowConfig()
        assert config.llm.provider == LLMProvider.OPENROUTER
        assert config.llm.model == "openai/gpt-4o"
        assert config.llm.temperature == 0.3

    def test_load_from_empty(self):
        config = SwarmFlowConfig.load(config_path=None)
        assert config.llm.provider == LLMProvider.OPENROUTER

    def test_env_override_api_key(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-123"}):
            reset_config()
            config = SwarmFlowConfig.load()
            assert config.llm.api_key == "test-key-123"

    def test_env_override_model(self):
        with patch.dict(os.environ, {"SWARMFLOW_MODEL": "anthropic/claude-3.5-sonnet"}):
            reset_config()
            config = SwarmFlowConfig.load()
            assert config.llm.model == "anthropic/claude-3.5-sonnet"

    def test_env_override_ollama(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://localhost:11434"}):
            reset_config()
            config = SwarmFlowConfig.load()
            assert config.llm.provider == LLMProvider.OLLAMA
            assert config.llm.base_url == "http://localhost:11434"

    def test_templates_dir_defaults_to_builtin(self):
        config = SwarmFlowConfig.load()
        assert "templates" in config.templates_dir

    def test_get_config_singleton(self):
        reset_config()
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reset_config(self):
        reset_config()
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2
