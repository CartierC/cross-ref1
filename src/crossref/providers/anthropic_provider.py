from __future__ import annotations

import os

from .base import Provider

DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, model: str | None = None, **kwargs):
        super().__init__(model=model or DEFAULT_MODEL, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic  # lazy import: optional dependency

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _complete_once(self, system: str, user: str) -> str:
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
