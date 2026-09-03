from __future__ import annotations

from .anthropic_provider import AnthropicProvider
from .base import Provider, ProviderError, RetryPolicy
from .gemini_provider import GeminiProvider
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider

_REGISTRY: dict[str, type[Provider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "mock": MockProvider,
}


def get_provider(name: str, model: str | None = None, **kwargs) -> Provider:
    try:
        cls = _REGISTRY[name.lower()]
    except KeyError as exc:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {', '.join(sorted(_REGISTRY))}"
        ) from exc
    return cls(model=model, **kwargs)


__all__ = [
    "Provider",
    "ProviderError",
    "RetryPolicy",
    "AnthropicProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "MockProvider",
    "get_provider",
]
