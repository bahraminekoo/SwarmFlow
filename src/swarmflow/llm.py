"""LLM factory — switchable between OpenRouter and Ollama."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from swarmflow.config import LLMConfig, LLMProvider, get_config


def create_llm(config: LLMConfig | None = None, **overrides) -> ChatOpenAI:
    """Create a ChatOpenAI-compatible LLM instance.

    Works with both OpenRouter (remote) and Ollama (local) since both
    expose an OpenAI-compatible API.

    Args:
        config: LLM configuration. Uses global config if None.
        **overrides: Override any config field (e.g. temperature=0.7).
    """
    if config is None:
        config = get_config().llm

    base_url = overrides.pop("base_url", config.base_url)
    model = overrides.pop("model", config.model)
    temperature = overrides.pop("temperature", config.temperature)
    max_tokens = overrides.pop("max_tokens", config.max_tokens)
    api_key = overrides.pop("api_key", config.api_key)

    if config.provider == LLMProvider.OLLAMA:
        # Ollama doesn't need a real API key but langchain requires one
        api_key = api_key or "ollama"
        base_url = base_url or "http://localhost:11434/v1"

    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **overrides,
    )
